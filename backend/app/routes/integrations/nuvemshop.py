# -*- coding: utf-8 -*-
"""
Rotas de integracao Nuvemshop (OAuth + Webhooks).
"""

import json
import logging
import re
import threading
from datetime import datetime
from typing import Dict, List

import requests
from flask import Blueprint, current_app, redirect, request

from app import db
from app.config import Config
from app.integrations.nuvemshop import (
    NuvemshopOrderImporter,
    NuvemshopTokenService,
    verify_nuvemshop_hmac,
)
from app.integrations.nuvemshop.client import NuvemshopClient
from app.middleware import requires_role
from app.models.nuvemshop_store import NuvemshopStore
from app.models.nuvemshop_webhook_delivery import NuvemshopWebhookDelivery
from app.models.pedido import Pedido, datetime_now_brazil
from app.models.pedido_external_ref import PedidoExternalRef
from app.models.pedido_manual_override import PedidoManualOverride
from app.schemas.common import error_response, success_response

logger = logging.getLogger(__name__)

nuvemshop_bp = Blueprint("nuvemshop", __name__, url_prefix="/api/integrations/nuvemshop")


# ---------------------------------------------------------------------------
# Background webhook processing (Ack-First, Process-Later)
# ---------------------------------------------------------------------------

def _process_webhook_background(app, delivery_id: int) -> None:
    """
    Executa o processamento pesado de um webhook em thread separada.

    Recebe a instancia real do Flask ``app`` (nao o proxy ``current_app``)
    para poder criar um application-context proprio da thread.

    Se qualquer etapa falhar, o erro e logado e o delivery permanece como
    ``pending`` (ou ``failed`` se o importer chegou a rodar), garantindo que
    o endpoint ``/process-pending`` possa recupera-lo depois.
    """
    with app.app_context():
        try:
            logger.info(
                "[WebhookBG] Iniciando processamento do delivery_id=%s", delivery_id
            )

            delivery = NuvemshopWebhookDelivery.query.get(delivery_id)
            if not delivery:
                logger.error(
                    "[WebhookBG] Delivery %s nao encontrado no banco.", delivery_id
                )
                return

            if delivery.status != "pending":
                logger.info(
                    "[WebhookBG] Delivery %s ja processado (status=%s). Ignorando.",
                    delivery_id,
                    delivery.status,
                )
                return

            store = NuvemshopStore.query.filter_by(
                store_id=delivery.store_id
            ).first()

            if not store:
                logger.warning(
                    "[WebhookBG] Loja store_id=%s nao encontrada. "
                    "Delivery %s permanece como pending.",
                    delivery.store_id,
                    delivery_id,
                )
                return

            if not Config.NUVEMSHOP_USER_AGENT:
                logger.warning(
                    "[WebhookBG] NUVEMSHOP_USER_AGENT nao configurado. "
                    "Delivery %s permanece como pending.",
                    delivery_id,
                )
                return

            importer = NuvemshopOrderImporter(store, Config.NUVEMSHOP_USER_AGENT)
            success = importer.process_delivery(delivery)

            if success:
                logger.info(
                    "[WebhookBG] Delivery %s processado com sucesso.", delivery_id
                )
            else:
                logger.warning(
                    "[WebhookBG] Delivery %s processado com falha "
                    "(verificar last_error no banco).",
                    delivery_id,
                )

        except Exception:
            # logger.exception ja inclui traceback completo
            logger.exception(
                "[WebhookBG] Erro nao tratado ao processar delivery_id=%s",
                delivery_id,
            )
            # Nao relançar: a thread morre silenciosamente mas o delivery
            # continua como 'pending' e pode ser reprocessado via /process-pending.


def _build_public_url(path: str) -> str:
    base = Config.NUVEMSHOP_PUBLIC_BASE_URL.rstrip("/")
    return f"{base}{path}"


def _ensure_webhook(client: NuvemshopClient, event: str, url: str) -> None:
    existing = client.list_webhooks(event=event)
    if isinstance(existing, list):
        for entry in existing:
            if entry.get("event") == event and entry.get("url") == url:
                return
    client.create_webhook(event, url)


def _setup_order_webhooks(client: NuvemshopClient, webhook_url: str) -> None:
    # LGPD webhooks (store/customers redact/data_request) são configurados no painel do app.
    # Aqui criamos apenas os webhooks operacionais de pedidos via API.
    for event in [
        "order/created",
        "order/paid",
        "order/updated",
        "order/cancelled",
        "order/custom_fields_updated",
    ]:
        _ensure_webhook(client, event, webhook_url)


@nuvemshop_bp.route("/install", methods=["GET"])
@requires_role("admin")
def nuvemshop_install():
    if not Config.NUVEMSHOP_APP_ID or not Config.NUVEMSHOP_PUBLIC_BASE_URL:
        return error_response(
            "NUVEMSHOP_APP_ID e NUVEMSHOP_PUBLIC_BASE_URL devem estar configurados",
            400,
        )

    redirect_uri = _build_public_url("/api/integrations/nuvemshop/oauth/callback")
    # Precisamos de write_notifications para criar/gerenciar webhooks via API.
    scope = "read_orders,write_notifications"
    authorize_url = (
        f"https://www.tiendanube.com/apps/{Config.NUVEMSHOP_APP_ID}/authorize"
        f"?redirect_uri={redirect_uri}&scope={scope}"
    )

    if request.args.get("redirect", "").lower() == "true":
        return redirect(authorize_url)

    return success_response({"authorize_url": authorize_url})


@nuvemshop_bp.route("/oauth/callback", methods=["GET"])
def nuvemshop_oauth_callback():
    code = request.args.get("code")
    if not code:
        return error_response("Parametro code ausente", 400)

    if not Config.NUVEMSHOP_CLIENT_SECRET or not Config.NUVEMSHOP_APP_ID:
        return error_response(
            "Credenciais Nuvemshop nao configuradas no servidor",
            400,
            details={
                "required_env": ["NUVEMSHOP_APP_ID", "NUVEMSHOP_CLIENT_SECRET"],
            },
        )

    redirect_uri = _build_public_url("/api/integrations/nuvemshop/oauth/callback")
    try:
        token_data = NuvemshopTokenService.exchange_code(
            code=code,
            app_id=Config.NUVEMSHOP_APP_ID,
            client_secret=Config.NUVEMSHOP_CLIENT_SECRET,
            redirect_uri=redirect_uri,
        )
    except Exception as exc:
        return error_response(
            "Falha ao trocar code por access_token (erro de rede)",
            400,
            details={"error_type": type(exc).__name__},
        )

    access_token = token_data.get("access_token")
    store_id = token_data.get("user_id")
    if not access_token or not store_id:
        details = {
            "status_code": token_data.get("_status_code"),
            "redirect_uri": redirect_uri,
            "hint": "Verifique se a Redirect URL no painel do app está exatamente igual (incluindo https e dominio) e gere um novo code (expira rapido).",
        }
        # Passar apenas campos não-sensíveis
        for key in ("error", "error_description", "scope"):
            if key in token_data:
                details[key] = token_data.get(key)
        return error_response("Falha ao autenticar com a Nuvemshop", 400, details=details)

    store = NuvemshopStore.query.filter_by(store_id=str(store_id)).first()
    if store:
        store.access_token = access_token
        store.active = True
        store.uninstalled_at = None
    else:
        store = NuvemshopStore(store_id=str(store_id), access_token=access_token, active=True)
        db.session.add(store)
    db.session.commit()

    if not Config.NUVEMSHOP_USER_AGENT:
        return error_response(
            "NUVEMSHOP_USER_AGENT nao configurado no servidor",
            400,
            details={
                "required_env": ["NUVEMSHOP_USER_AGENT"],
                "example": "SeuApp (contato@seudominio.com)",
            },
        )

    client = NuvemshopClient(
        store_id=str(store_id),
        access_token=access_token,
        user_agent=Config.NUVEMSHOP_USER_AGENT,
    )
    webhook_url = _build_public_url("/api/integrations/nuvemshop/webhooks")

    try:
        _setup_order_webhooks(client, webhook_url)
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        body = ""
        try:
            body = (exc.response.text or "")[:500] if exc.response is not None else ""
        except Exception:
            body = ""
        return error_response(
            "Falha ao criar webhooks na loja",
            400,
            details={
                "hint": "Se este erro persistir, confira se o app foi reinstalado com o escopo `write_notifications`.",
                "http_status": status_code,
                "response_body": body,
            },
        )
    except Exception as exc:
        return error_response(
            "Falha ao criar webhooks na loja",
            400,
            details={
                "error_type": type(exc).__name__,
                "hint": "Confira escopos/permissoes do app e tente novamente.",
            },
        )

    return success_response({"store_id": store_id, "status": "connected"})


@nuvemshop_bp.route("/setup-webhooks", methods=["POST"])
@requires_role("admin")
def nuvemshop_setup_webhooks():
    """
    Recria webhooks de pedidos via API (sem reinstalar o app).
    LGPD webhooks devem ser configurados no painel do app (URLs obrigatórias).
    """
    if not Config.NUVEMSHOP_USER_AGENT:
        return error_response(
            "NUVEMSHOP_USER_AGENT nao configurado no servidor",
            400,
            details={"required_env": ["NUVEMSHOP_USER_AGENT"]},
        )

    store_id = request.args.get("store_id")
    if not store_id:
        store = (
            NuvemshopStore.query.filter_by(active=True).order_by(NuvemshopStore.id.desc()).first()
        )
    else:
        store = NuvemshopStore.query.filter_by(store_id=str(store_id)).first()

    if not store:
        return error_response("Loja Nuvemshop nao encontrada", 404)

    client = NuvemshopClient(
        store_id=str(store.store_id),
        access_token=store.access_token,
        user_agent=Config.NUVEMSHOP_USER_AGENT,
    )
    webhook_url = _build_public_url("/api/integrations/nuvemshop/webhooks")

    try:
        _setup_order_webhooks(client, webhook_url)
    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        body = ""
        try:
            body = (exc.response.text or "")[:500] if exc.response is not None else ""
        except Exception:
            body = ""
        return error_response(
            "Falha ao criar webhooks na loja",
            400,
            details={
                "http_status": status_code,
                "response_body": body,
                "hint": "Garanta que o app tem escopo `write_notifications` e que o token salvo é o mais recente (reinstale se necessário).",
            },
        )

    return success_response(
        {
            "store_id": str(store.store_id),
            "webhook_url": webhook_url,
            "events": ["order/created", "order/paid", "order/updated", "order/cancelled"],
            "status": "ok",
        }
    )


@nuvemshop_bp.route("/webhooks", methods=["POST"])
def nuvemshop_webhooks():
    if not Config.NUVEMSHOP_CLIENT_SECRET:
        return error_response(
            "NUVEMSHOP_CLIENT_SECRET nao configurado no servidor",
            500,
            details={"required_env": ["NUVEMSHOP_CLIENT_SECRET"]},
        )
    raw_body = request.get_data() or b""
    signature = request.headers.get("x-linkedstore-hmac-sha256")
    if not signature:
        signature = request.headers.get("HTTP_X_LINKEDSTORE_HMAC_SHA256")

    if not verify_nuvemshop_hmac(raw_body, signature, Config.NUVEMSHOP_CLIENT_SECRET):
        return error_response("Assinatura invalida", 401)

    try:
        payload = request.get_json() or {}
    except Exception:
        return error_response("Payload invalido", 400)

    store_id = payload.get("store_id")
    event = payload.get("event")
    resource_id = payload.get("id")

    headers_subset: Dict[str, str] = {}
    for key in ("User-Agent", "Content-Type", "X-Linkedstore-Hmac-Sha256"):
        value = request.headers.get(key)
        if value:
            headers_subset[key] = value

    delivery = NuvemshopWebhookDelivery(
        store_id=str(store_id),
        event=str(event or ""),
        resource_id=str(resource_id) if resource_id is not None else None,
        raw_body=raw_body.decode("utf-8", errors="ignore"),
        headers_json=json.dumps(headers_subset, ensure_ascii=True),
        status="pending",
    )
    db.session.add(delivery)
    db.session.commit()

    # --- Ack-First, Process-Later ---
    # Disparar thread de background para processar o webhook de forma assincrona.
    # A resposta 200 OK e retornada imediatamente para a Nuvemshop, evitando
    # timeouts e retransmissoes desnecessarias.
    # Se a thread falhar, o delivery permanece como 'pending' e pode ser
    # reprocessado via /process-pending (fallback de seguranca).
    app_real = current_app._get_current_object()
    thread = threading.Thread(
        target=_process_webhook_background,
        args=(app_real, delivery.id),
        name=f"WebhookBG-{delivery.id}",
        daemon=False,
    )
    thread.start()

    logger.info(
        "[Webhook] Delivery %s persistido e thread de background disparada (event=%s).",
        delivery.id,
        event,
    )

    return success_response({"received": True, "processing": "background"})


@nuvemshop_bp.route("/process-pending", methods=["POST"])
@requires_role("admin")
def nuvemshop_process_pending():
    limit = request.args.get("limit", type=int) or 50
    if not Config.NUVEMSHOP_USER_AGENT:
        return error_response(
            "NUVEMSHOP_USER_AGENT nao configurado no servidor",
            400,
            details={
                "required_env": ["NUVEMSHOP_USER_AGENT"],
                "hint": "Configure no .env/servidor e reinicie o backend. Veja backend/docs/NUVEMSHOP_CREDENTIALS.md",
            },
        )

    deliveries = (
        NuvemshopWebhookDelivery.query.filter_by(status="pending")
        .order_by(NuvemshopWebhookDelivery.received_at.asc())
        .limit(limit)
        .all()
    )

    if not deliveries:
        return success_response({"processed": 0, "failed": 0})

    stores_map: Dict[str, NuvemshopStore] = {}
    processed = 0
    failed = 0

    for delivery in deliveries:
        store_id = delivery.store_id
        if store_id not in stores_map:
            store = NuvemshopStore.query.filter_by(store_id=store_id).first()
            stores_map[store_id] = store
        store = stores_map.get(store_id)

        if not store:
            delivery.status = "failed"
            delivery.last_error = "store_not_found"
            delivery.processed_at = datetime_now_brazil()
            db.session.commit()
            failed += 1
            continue

        importer = NuvemshopOrderImporter(store, Config.NUVEMSHOP_USER_AGENT)
        if importer.process_delivery(delivery):
            processed += 1
        else:
            failed += 1

    return success_response({"processed": processed, "failed": failed})


@nuvemshop_bp.route("/pedidos-pendentes-agendamento", methods=["GET"])
@requires_role("admin")
def listar_pedidos_pendentes_agendamento():
    refs = PedidoExternalRef.query.filter_by(provider="nuvemshop", schedule_pending=True).all()
    pedidos: List[Dict[str, str]] = []
    for ref in refs:
        pedido = Pedido.query.get(ref.pedido_id)
        if not pedido:
            continue
        pedidos.append(
            {
                "pedido_id": pedido.id,
                "cliente": pedido.cliente,
                "destinatario": pedido.destinatario,
                "dia_entrega": pedido.dia_entrega.strftime("%Y-%m-%d")
                if pedido.dia_entrega
                else None,
                "horario": pedido.horario,
                "valor": pedido.valor,
                "produto": pedido.produto,
                "endereco": pedido.endereco,
                "status_pagamento": pedido.status_pagamento,
                "observacoes": pedido.observacoes,
            }
        )

    return success_response({"total": len(pedidos), "pedidos": pedidos})


def _enrich_pedido_from_api(pedido: Pedido, ref: PedidoExternalRef) -> bool:
    """
    Re-busca o pedido na API Nuvemshop e preenche campos que estejam
    vazios ou com valores placeholder no pedido local.

    Retorna True se algum campo foi atualizado, False caso contrario.
    Best-effort: erros de rede/API são logados mas não propagados.
    """
    from app.integrations.nuvemshop.mapper import map_nuvemshop_order_to_pedido_data

    store = NuvemshopStore.query.filter_by(store_id=ref.store_id).first()
    if not store or not store.active or not Config.NUVEMSHOP_USER_AGENT:
        return False

    try:
        client = NuvemshopClient(
            store_id=str(store.store_id),
            access_token=store.access_token,
            user_agent=Config.NUVEMSHOP_USER_AGENT,
        )
        order = client.get_order(ref.external_order_id)
    except Exception as exc:
        logger.warning(
            "Falha ao buscar pedido %s na API Nuvemshop para enriquecimento: %s",
            ref.external_order_id,
            exc,
        )
        return False

    pedido_data, _, _, _ = map_nuvemshop_order_to_pedido_data(order)

    # Compor endereco completo (mesma logica do importer)
    parts = [
        pedido_data.get("rua"),
        pedido_data.get("numero"),
        pedido_data.get("complemento"),
        pedido_data.get("bairro"),
        pedido_data.get("cidade"),
        pedido_data.get("cep"),
    ]
    clean = [p for p in parts if p]
    pedido_data["endereco"] = " - ".join(clean) if clean else None

    overridden_fields = PedidoManualOverride.get_overridden_fields(pedido.id)
    changed = False

    # Mapa de campo -> (novo_valor, valores_placeholder_que_permitem_update)
    enrich_map = {
        "destinatario": (pedido_data.get("destinatario"), ("", "Nao informado", pedido.cliente)),
        "cliente": (pedido_data.get("cliente"), ("", "Nao informado")),
        "valor": (pedido_data.get("valor"), ("", "R$ 0,00", "R$ 0.00", None)),
        "produto": (pedido_data.get("produto"), ("", "Produto Nuvemshop")),
        "telefone_cliente": (pedido_data.get("telefone_cliente"), ("", "0000000000")),
        "endereco": (pedido_data.get("endereco"), ("", None)),
        "rua": (pedido_data.get("rua"), ("", None)),
        "numero": (pedido_data.get("numero"), ("", None)),
        "bairro": (pedido_data.get("bairro"), ("", None)),
        "cidade": (pedido_data.get("cidade"), ("", None)),
        "cep": (pedido_data.get("cep"), ("", None)),
        "status_pagamento": (pedido_data.get("status_pagamento"), ()),
        "pagamento": (pedido_data.get("pagamento"), ("", None)),
        "obs_entrega": (pedido_data.get("obs_entrega"), ("", None)),
        "mensagem": (pedido_data.get("mensagem"), ("", None)),
    }

    for field, (new_val, placeholders) in enrich_map.items():
        if field in overridden_fields:
            continue
        if not new_val:
            continue
        current = getattr(pedido, field, None) or ""
        # status_pagamento: sempre atualizar (pode mudar de Pendente para Pago)
        if field == "status_pagamento":
            if new_val != current:
                setattr(pedido, field, new_val)
                changed = True
        elif current in placeholders or not current:
            setattr(pedido, field, new_val)
            changed = True

    return changed


@nuvemshop_bp.route("/pedidos/<int:pedido_id>/definir-agendamento", methods=["POST"])
@requires_role("admin")
def definir_agendamento_pedido(pedido_id: int):
    data = request.get_json() or {}
    dia_entrega_str = str(data.get("dia_entrega") or "").strip()
    horario = str(data.get("horario") or "").strip()

    if not dia_entrega_str:
        return error_response("dia_entrega obrigatorio", 400)

    if "/" in dia_entrega_str:
        try:
            dia_entrega = datetime.strptime(dia_entrega_str, "%d/%m/%Y").date()
        except ValueError:
            return error_response("Formato de data invalido", 400)
    else:
        try:
            dia_entrega = datetime.strptime(dia_entrega_str, "%Y-%m-%d").date()
        except ValueError:
            return error_response("Formato de data invalido", 400)

    if horario:
        pattern_simples = r"^([01]?\d|2[0-3]):[0-5]\d$"
        pattern_intervalo = r"^([01]?\d|2[0-3]):[0-5]\d\s*-\s*([01]?\d|2[0-3]):[0-5]\d$"
        if not (re.match(pattern_simples, horario) or re.match(pattern_intervalo, horario)):
            return error_response("Formato de horario invalido", 400)

    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return error_response("Pedido nao encontrado", 404)

    ref = PedidoExternalRef.query.filter_by(provider="nuvemshop", pedido_id=pedido_id).first()
    if not ref:
        return error_response("Pedido nao pertence a Nuvemshop", 400)

    # Antes de confirmar agendamento, enriquecer dados do pedido re-buscando
    # da API Nuvemshop. Best-effort: se falhar, prosseguir normalmente.
    try:
        _enrich_pedido_from_api(pedido, ref)
    except Exception:
        logger.warning(
            "Falha ao enriquecer pedido %s via API (best-effort).", pedido_id, exc_info=True
        )

    pedido.dia_entrega = dia_entrega
    if horario:
        pedido.horario = horario
    pedido.updated_at = datetime_now_brazil()
    if pedido.observacoes and "AGENDAMENTO CONFIRMADO" not in pedido.observacoes:
        pedido.observacoes = f"{pedido.observacoes} | AGENDAMENTO CONFIRMADO MANUALMENTE"

    # Registrar overrides para proteger campos editados manualmente
    PedidoManualOverride.set_override(
        pedido_id=pedido_id,
        field_name="dia_entrega",
        field_value=str(dia_entrega),
        edited_by="admin",
    )
    if horario:
        PedidoManualOverride.set_override(
            pedido_id=pedido_id, field_name="horario", field_value=horario, edited_by="admin"
        )

    ref.schedule_pending = False
    ref.updated_at = datetime_now_brazil()
    db.session.commit()

    return success_response({"pedido_id": pedido.id, "status": "updated"})
