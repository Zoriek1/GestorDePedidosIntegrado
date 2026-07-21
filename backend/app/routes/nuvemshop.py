# -*- coding: utf-8 -*-
"""
Rotas de integracao Nuvemshop (OAuth + Webhooks).
"""

import json
import logging
import re
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from flask import Blueprint, current_app, g, redirect, request

from app import db
from app.config import Config
from app.integrations.nuvemshop import (
    NuvemshopOrderImporter,
    NuvemshopTokenService,
    verify_nuvemshop_hmac,
)
from app.integrations.nuvemshop.client import NuvemshopClient
from app.integrations.nuvemshop.token_service import encrypt_token
from app.middleware import requires_role
from app.models.nuvemshop_store import NuvemshopStore
from app.models.nuvemshop_webhook_delivery import NuvemshopWebhookDelivery
from app.models.pedido import Pedido, datetime_now_brazil
from app.models.pedido_external_ref import PedidoExternalRef
from app.models.pedido_manual_override import PedidoManualOverride
from app.schemas.common import error_response, success_response
from app.services.oauth_state import sign_state, verify_state
from app.services.tenancy import is_multi_store

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
            logger.info("[WebhookBG] Iniciando processamento do delivery_id=%s", delivery_id)

            delivery = NuvemshopWebhookDelivery.query.get(delivery_id)
            if not delivery:
                logger.error("[WebhookBG] Delivery %s nao encontrado no banco.", delivery_id)
                return

            if delivery.status != "pending":
                logger.info(
                    "[WebhookBG] Delivery %s ja processado (status=%s). Ignorando.",
                    delivery_id,
                    delivery.status,
                )
                return

            store = NuvemshopStore.query.filter_by(store_id=delivery.store_id).first()

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
                logger.info("[WebhookBG] Delivery %s processado com sucesso.", delivery_id)
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


def _resolve_target_store(store_id: Optional[str] = None) -> Optional[NuvemshopStore]:
    if store_id:
        query = NuvemshopStore.query.filter_by(store_id=str(store_id))
        if is_multi_store():
            tenant_id = getattr(g, "tenant_store_id", None)
            if tenant_id is None:
                return None
            query = query.filter_by(store_ref_id=tenant_id)
        return query.first()

    # Multi-tenant: resolve pela loja autenticada, nunca pela "última loja ativa".
    if is_multi_store():
        store = getattr(g, "current_store", None)
        if store is None:
            return None
        return NuvemshopStore.query.filter_by(store_ref_id=store.id).first()

    return NuvemshopStore.query.filter_by(active=True).order_by(NuvemshopStore.id.desc()).first()


def _serialize_store_config(store: Optional[NuvemshopStore]) -> Dict[str, object]:
    if not store:
        return {
            "connected": False,
            "store_id": None,
            "active": False,
            "default_vendedor_id": None,
            "default_vendedor_name": None,
        }

    return {
        "connected": True,
        "store_id": str(store.store_id),
        "active": bool(store.active),
        "default_vendedor_id": store.default_vendedor_id,
        "default_vendedor_name": (
            store.default_vendedor.name if getattr(store, "default_vendedor", None) else None
        ),
    }


@nuvemshop_bp.route("/install", methods=["GET"])
@requires_role("admin")
def nuvemshop_install():
    if not Config.NUVEMSHOP_APP_ID or not Config.NUVEMSHOP_PUBLIC_BASE_URL:
        return error_response(
            "NUVEMSHOP_APP_ID e NUVEMSHOP_PUBLIC_BASE_URL devem estar configurados",
            400,
        )

    redirect_uri = _build_public_url("/api/integrations/nuvemshop/oauth/callback")
    # Precisamos de write_notifications para webhooks e read_products para listar variantes.
    scope = "read_orders,write_notifications,read_products"
    authorize_url = (
        f"https://www.tiendanube.com/apps/{Config.NUVEMSHOP_APP_ID}/authorize"
        f"?redirect_uri={redirect_uri}&scope={scope}"
    )

    # State assinado amarra a instalação à loja autenticada (Fase B).
    store = getattr(g, "current_store", None)
    if store:
        authorize_url += f"&state={sign_state(store.id, 'nuvemshop')}"

    if request.args.get("redirect", "").lower() == "true":
        return redirect(authorize_url)

    return success_response({"authorize_url": authorize_url})


@nuvemshop_bp.route("/oauth/callback", methods=["GET"])
def nuvemshop_oauth_callback():
    code = request.args.get("code")
    if not code:
        return error_response("Parametro code ausente", 400)

    # Resolve o tenant pelo state assinado. Multi-tenant: state ausente/inválido
    # falha fechado; single-tenant cai na loja default (compat).
    verified = verify_state(request.args.get("state"), "nuvemshop")
    store_ref_id = verified["srid"] if verified else None
    if store_ref_id is None and is_multi_store():
        return error_response("State OAuth inválido ou ausente", 400)

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
        store.access_token = encrypt_token(access_token)
        store.active = True
        store.uninstalled_at = None
    else:
        store = NuvemshopStore(store_id=str(store_id), access_token=encrypt_token(access_token), active=True)
        db.session.add(store)
    # Amarra a instalação ao tenant interno resolvido pelo state (Fase B).
    if store_ref_id is not None:
        store.store_ref_id = store_ref_id
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

    # Redirecionar de volta ao app para o usuário não ficar vendo JSON
    front_url = _build_public_url("/integracoes/nuvemshop?nuvemshop=connected")
    return redirect(front_url)


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

    store = _resolve_target_store(request.args.get("store_id"))

    if not store:
        return error_response("Loja Nuvemshop nao encontrada", 404)

    client = NuvemshopClient(
        store_id=str(store.store_id),
        access_token=store.decrypted_token,
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


@nuvemshop_bp.route("/config", methods=["GET"])
@requires_role("admin")
def get_nuvemshop_config():
    store_id = request.args.get("store_id")
    store = _resolve_target_store(store_id)
    return success_response(_serialize_store_config(store))


@nuvemshop_bp.route("/disconnect", methods=["DELETE"])
@requires_role("admin")
def nuvemshop_disconnect():
    """Desconecta a Nuvemshop localmente (nao revoga no provedor)."""
    from app.models.pedido import datetime_now_brazil

    store_ref_id = getattr(g, "tenant_store_id", None)
    try:
        ns = NuvemshopStore.query.filter_by(store_ref_id=store_ref_id).first()
        if ns:
            ns.active = False
            ns.access_token = ""
            ns.uninstalled_at = datetime_now_brazil()
            db.session.commit()
        return success_response(message="Nuvemshop desconectado")
    except Exception:
        db.session.rollback()
        logger.exception("Erro ao desconectar Nuvemshop")
        return error_response("Erro ao desconectar Nuvemshop", 500)


@nuvemshop_bp.route("/config", methods=["PUT"])
@requires_role("admin")
def update_nuvemshop_config():
    from app.models.user import User

    store_id = request.args.get("store_id")
    store = _resolve_target_store(store_id)
    if not store:
        return error_response("Loja Nuvemshop nao encontrada", 404)

    data = request.get_json() or {}
    vendedor_id = data.get("vendedor_id")
    if vendedor_id in ("", 0):
        vendedor_id = None

    if vendedor_id is not None:
        try:
            vendedor_id = int(vendedor_id)
        except (TypeError, ValueError):
            return error_response("vendedor_id invalido", 400)

        vendedor = User.query.filter_by(
            id=vendedor_id,
            is_active=True,
            role="vendedor",
            store_ref_id=getattr(store, "store_ref_id", None),
        ).first()
        if not vendedor:
            return error_response("Vendedor nao encontrado", 404)

    store.default_vendedor_id = vendedor_id
    db.session.commit()

    action = "atualizado" if vendedor_id is not None else "removido"
    return success_response(
        _serialize_store_config(store),
        message=f"Vendedor padrao {action} com sucesso",
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
                "hint": "Configure no .env/servidor e reinicie o backend. Veja docs/integrations.md.",
            },
        )

    deliveries_query = NuvemshopWebhookDelivery.query.filter_by(status="pending")
    if is_multi_store():
        installation = _resolve_target_store()
        if not installation:
            logger.warning(
                "nuvemshop.process_pending_store_unresolved tenant=%s",
                getattr(g, "tenant_store_id", None),
            )
            return error_response("Loja Nuvemshop nao encontrada", 404)
        deliveries_query = deliveries_query.filter_by(store_id=str(installation.store_id))

    deliveries = (
        deliveries_query
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
        pedido = Pedido.query.filter(Pedido.id == ref.pedido_id).first()
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


@nuvemshop_bp.route("/atribuir-vendedor", methods=["POST"])
@requires_role("admin")
def atribuir_vendedor_nuvemshop():
    """Atribui um vendedor a todos os pedidos Nuvemshop que ainda não têm vendedor."""
    from app.models.user import User
    from app.services.order_commission_lifecycle import (
        apply_commission_lifecycle,
        snapshot_commission_fields,
    )

    data = request.get_json() or {}
    vendedor_id = data.get("vendedor_id")
    if not vendedor_id:
        return error_response("vendedor_id é obrigatório", 400)

    vendedor = User.query.filter_by(
        id=vendedor_id,
        is_active=True,
        store_ref_id=getattr(g, "tenant_store_id", None),
    ).first()
    if not vendedor:
        return error_response("Vendedor não encontrado", 404)

    refs = PedidoExternalRef.query.filter_by(provider="nuvemshop").all()
    atribuidos = 0
    comissoes_geradas = 0
    for ref in refs:
        pedido = Pedido.query.filter(Pedido.id == ref.pedido_id).first()
        if pedido and pedido.vendedor_id is None:
            prev = snapshot_commission_fields(pedido)
            pedido.vendedor_id = vendedor_id
            try:
                result = apply_commission_lifecycle(pedido, previous=prev, actor_id=vendedor_id)
                if result.get("generated"):
                    comissoes_geradas += 1
            except Exception:
                logger.warning(
                    "[NUVEMSHOP] Falha em apply_commission_lifecycle ao "
                    "atribuir vendedor para pedido #%s",
                    pedido.id,
                    exc_info=True,
                )
            atribuidos += 1

    db.session.commit()
    return success_response(
        {"atribuidos": atribuidos, "comissoes_geradas": comissoes_geradas},
        message=(
            f"{atribuidos} pedido(s) atribuído(s) a {vendedor.name} "
            f"({comissoes_geradas} comissão(ões) gerada(s))"
        ),
    )


def _enrich_pedido_from_api(pedido: Pedido, ref: PedidoExternalRef) -> bool:
    """
    Re-busca o pedido na API Nuvemshop e preenche campos que estejam
    vazios ou com valores placeholder no pedido local.

    Retorna True se algum campo foi atualizado, False caso contrario.
    Best-effort: erros de rede/API são logados mas não propagados.
    """
    from app.integrations.nuvemshop.mapper import map_nuvemshop_order_to_pedido_data
    from app.services.order_commission_lifecycle import (
        apply_commission_lifecycle,
        snapshot_commission_fields,
    )

    # Snapshot ANTES de qualquer mutação para o lifecycle detectar transições
    prev_snapshot = snapshot_commission_fields(pedido)

    store = NuvemshopStore.query.filter_by(
        store_id=ref.store_id,
        store_ref_id=ref.store_ref_id,
    ).first()
    if not store or not store.active or not Config.NUVEMSHOP_USER_AGENT:
        return False

    try:
        client = NuvemshopClient(
            store_id=str(store.store_id),
            access_token=store.decrypted_token,
            user_agent=Config.NUVEMSHOP_USER_AGENT,
        )
        order = client.get_order(ref.external_order_id)
        try:
            custom_fields = client.get_order_custom_fields(ref.external_order_id)
            if custom_fields:
                order["custom_fields"] = custom_fields
        except Exception:
            pass
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

    if pedido.vendedor_id is None and getattr(store, "default_vendedor_id", None):
        pedido.vendedor_id = store.default_vendedor_id
        changed = True

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

    if changed:
        # Dispara lifecycle se algo mudou (em especial transição de
        # status_pagamento Pendente→Pago, comum no caminho do enrich).
        try:
            apply_commission_lifecycle(
                pedido,
                previous=prev_snapshot,
                actor_id=getattr(pedido, "vendedor_id", None),
            )
        except Exception:
            logger.warning(
                "[NUVEMSHOP] Falha em apply_commission_lifecycle no enrich do " "pedido #%s",
                pedido.id,
                exc_info=True,
            )

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

    pedido = Pedido.query.filter(Pedido.id == pedido_id).first()
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


@nuvemshop_bp.route("/debug/pedidos-recentes", methods=["GET"])
@requires_role("admin")
def debug_pedidos_recentes():
    """
    Endpoint de debug para visualizar custom_fields de pedidos recentes da API Nuvemshop.
    """
    if not Config.NUVEMSHOP_USER_AGENT:
        return error_response(
            "NUVEMSHOP_USER_AGENT nao configurado no servidor",
            400,
            details={"required_env": ["NUVEMSHOP_USER_AGENT"]},
        )

    limit = request.args.get("limit", type=int) or 10
    days = request.args.get("days", type=int) or 1

    # Buscar loja ativa
    store = _resolve_target_store()
    if not store:
        return error_response("Nenhuma loja Nuvemshop ativa encontrada", 404)

    try:
        client = NuvemshopClient(
            store_id=str(store.store_id),
            access_token=store.decrypted_token,
            user_agent=Config.NUVEMSHOP_USER_AGENT,
        )

        # Calcular data mínima (últimos N dias)
        created_at_min = (datetime_now_brazil() - timedelta(days=days)).isoformat()

        # Buscar pedidos recentes
        orders_response = client.list_orders(limit=limit, created_at_min=created_at_min)
        orders = orders_response.get("orders", [])
        if isinstance(orders_response, list):
            orders = orders_response

        from app.integrations.nuvemshop.mapper import (
            _extract_schedule_from_custom_fields,
            map_nuvemshop_order_to_pedido_data,
        )

        pedidos_debug = []
        for order in orders:
            order_id = str(order.get("id", ""))
            order_number = order.get("number")
            created_at = order.get("created_at")

            # Custom fields vêm de endpoint separado
            custom_fields_raw = []
            try:
                custom_fields_raw = client.get_order_custom_fields(order_id)
                if custom_fields_raw:
                    order["custom_fields"] = custom_fields_raw
            except Exception:
                pass

            # Extrair custom_fields usando função do mapper
            (
                custom_field_date,
                custom_field_time,
                custom_field_name,
            ) = _extract_schedule_from_custom_fields(order)

            # Mapear pedido completo
            (
                pedido_data,
                schedule_pending,
                _,
                agendamento_source,
            ) = map_nuvemshop_order_to_pedido_data(order)

            # Verificar se já foi importado
            external_ref = PedidoExternalRef.query.filter_by(
                store_ref_id=getattr(store, "store_ref_id", None),
                provider="nuvemshop",
                store_id=str(store.store_id),
                external_order_id=order_id,
            ).first()

            pedido_info = {
                "order_id": order_id,
                "order_number": order_number,
                "created_at": created_at,
                "custom_fields_raw": custom_fields_raw,
                "custom_fields_extraidos": {
                    "dia_entrega": custom_field_date.isoformat() if custom_field_date else None,
                    "horario": custom_field_time,
                    "campo_nome": custom_field_name,
                },
                "mapeamento": {
                    "dia_entrega": (
                        pedido_data.get("dia_entrega").isoformat()
                        if pedido_data.get("dia_entrega")
                        else None
                    ),
                    "horario": pedido_data.get("horario"),
                    "agendamento_source": agendamento_source,
                    "schedule_pending": schedule_pending,
                },
                "ja_importado": external_ref is not None,
                "pedido_id": external_ref.pedido_id if external_ref else None,
            }
            pedidos_debug.append(pedido_info)

        return success_response({"total": len(pedidos_debug), "pedidos": pedidos_debug})

    except Exception as exc:
        logger.exception("Erro ao buscar pedidos recentes para debug")
        return error_response(
            f"Erro ao buscar pedidos: {str(exc)}",
            500,
            details={"error_type": type(exc).__name__},
        )


@nuvemshop_bp.route("/debug/pedido/<order_id>", methods=["GET"])
@requires_role("admin")
def debug_pedido_especifico(order_id: str):
    """
    Endpoint de debug para visualizar custom_fields de um pedido específico da API Nuvemshop.
    """
    if not Config.NUVEMSHOP_USER_AGENT:
        return error_response(
            "NUVEMSHOP_USER_AGENT nao configurado no servidor",
            400,
            details={"required_env": ["NUVEMSHOP_USER_AGENT"]},
        )

    # Buscar loja ativa
    store = _resolve_target_store()
    if not store:
        return error_response("Nenhuma loja Nuvemshop ativa encontrada", 404)

    try:
        client = NuvemshopClient(
            store_id=str(store.store_id),
            access_token=store.decrypted_token,
            user_agent=Config.NUVEMSHOP_USER_AGENT,
        )

        # Buscar pedido específico
        order = client.get_order(order_id)
        try:
            custom_fields = client.get_order_custom_fields(order_id)
            if custom_fields:
                order["custom_fields"] = custom_fields
        except Exception:
            pass

        from app.integrations.nuvemshop.mapper import (
            _extract_schedule_from_custom_fields,
            map_nuvemshop_order_to_pedido_data,
        )

        # Extrair custom_fields raw
        custom_fields_raw = order.get("custom_fields") or order.get("order_custom_fields") or []

        # Extrair custom_fields usando função do mapper
        (
            custom_field_date,
            custom_field_time,
            custom_field_name,
        ) = _extract_schedule_from_custom_fields(order)

        # Mapear pedido completo
        (
            pedido_data,
            schedule_pending,
            shipping_option_text,
            agendamento_source,
        ) = map_nuvemshop_order_to_pedido_data(order)

        # Verificar se já foi importado
        external_ref = PedidoExternalRef.query.filter_by(
            store_ref_id=getattr(store, "store_ref_id", None),
            provider="nuvemshop",
            store_id=str(store.store_id),
            external_order_id=str(order_id),
        ).first()

        pedido_local = None
        if external_ref:
            pedido_local = Pedido.query.filter(Pedido.id == external_ref.pedido_id).first()

        debug_info = {
            "order_id": str(order.get("id", "")),
            "order_number": order.get("number"),
            "created_at": order.get("created_at"),
            "order_json": order,  # JSON completo do pedido
            "custom_fields_raw": custom_fields_raw,
            "custom_fields_extraidos": {
                "dia_entrega": custom_field_date.isoformat() if custom_field_date else None,
                "horario": custom_field_time,
                "campo_nome": custom_field_name,
            },
            "mapeamento": {
                "dia_entrega": (
                    pedido_data.get("dia_entrega").isoformat()
                    if pedido_data.get("dia_entrega")
                    else None
                ),
                "horario": pedido_data.get("horario"),
                "agendamento_source": agendamento_source,
                "schedule_pending": schedule_pending,
                "shipping_option_text": shipping_option_text,
                "pedido_data_completo": pedido_data,
            },
            "status_importacao": {
                "ja_importado": external_ref is not None,
                "pedido_id": external_ref.pedido_id if external_ref else None,
                "schedule_pending": external_ref.schedule_pending if external_ref else None,
                "agendamento_source": external_ref.agendamento_source if external_ref else None,
            },
            "pedido_local": (
                {
                    "id": pedido_local.id,
                    "cliente": pedido_local.cliente,
                    "destinatario": pedido_local.destinatario,
                    "dia_entrega": (
                        pedido_local.dia_entrega.isoformat() if pedido_local.dia_entrega else None
                    ),
                    "horario": pedido_local.horario,
                    "produto": pedido_local.produto,
                    "valor": pedido_local.valor,
                }
                if pedido_local
                else None
            ),
        }

        return success_response(debug_info)

    except requests.HTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code == 404:
            return error_response(f"Pedido {order_id} nao encontrado na API Nuvemshop", 404)
        return error_response(
            f"Erro HTTP ao buscar pedido: {exc}",
            500,
            details={"http_status": status_code},
        )
    except Exception as exc:
        logger.exception("Erro ao buscar pedido específico para debug")
        return error_response(
            f"Erro ao buscar pedido: {str(exc)}",
            500,
            details={"error_type": type(exc).__name__},
        )
