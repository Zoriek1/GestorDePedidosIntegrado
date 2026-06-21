# -*- coding: utf-8 -*-
"""
Rotas de Pedidos - Blueprint para endpoints de pedidos
"""
import importlib.util
import re
from datetime import datetime
from pathlib import Path

from flask import Blueprint, g, request

# Command Pattern Imports
from app.commands.gerar_comprovante_command import GerarComprovanteCommand
from app.commands.gerar_comprovante_lote_command import (
    MAX_PEDIDOS_POR_LOTE,
    GerarComprovanteLoteCommand,
)
from app.middleware import requires_any_role, requires_edit_auth, requires_role
from app.models.lead import Lead
from app.models.pedido import datetime_now_brazil
from app.models.pedido_external_ref import PedidoExternalRef
from app.models.pedido_manual_override import PedidoManualOverride
from app.repositories.pedido_repository import PedidoRepository
from app.schemas.common import error_response, success_response
from app.schemas.pedido_schema import (
    PedidoCreateSchema,
    PedidoSchema,
    PedidoUpdateSchema,
)
from app.services.order_commission_lifecycle import (
    apply_commission_lifecycle,
    snapshot_commission_fields,
)
from app.services.track_token import build_track_url, parse_track_token
from app.utils.destructive_action_guard import (
    ensure_backup_before_destructive_action,
)
from app.utils.tracking_token import (
    extract_tracking_token_from_text,
    is_tracking_token_valid,
    normalize_tracking_token,
)

pedidos_bp = Blueprint("pedidos", __name__, url_prefix="/api/pedidos")

pedido_repo = PedidoRepository()
pedido_schema = PedidoSchema()
pedido_create_schema = PedidoCreateSchema()
pedido_update_schema = PedidoUpdateSchema()

DELIVERY_DETAIL_FIELDS = (
    "tipo_local",
    "nome_local",
    "apto",
    "bloco",
    "torre",
    "andar",
    "quadra",
    "lote",
    "complemento",
)
BUILDING_DETAIL_FIELDS = ("nome_local", "apto", "bloco", "torre", "andar")
VALID_TIPOS_LOCAL = {"casa", "predio", "comercial"}


def _clean_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalize_optional_id(value: object) -> object | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return value


def _normalize_whatsapp_code(value: object) -> str | None:
    return normalize_tracking_token(value)


def _build_payment_snapshot(data: dict, valor, status_pagamento, pagamento, pedido=None) -> dict:
    """Monta snapshot financeiro para status Parcial sem alterar o status canonico."""
    from decimal import Decimal, ROUND_HALF_UP

    from app.integrations.bling.mapper import parse_decimal_money

    status = _clean_str(status_pagamento or getattr(pedido, "status_pagamento", None))
    is_partial = status.lower().startswith("parcial")
    if not is_partial:
        return {
            "regra_pagamento": None,
            "percentual_entrada": None,
            "valor_entrada": None,
            "valor_restante": None,
            "forma_pagamento_entrada": None,
            "forma_pagamento_restante": None,
            "entrada_recebida_at": None,
            "saldo_recebido_at": getattr(pedido, "saldo_recebido_at", None) if pedido else None,
        }

    total = parse_decimal_money(valor or getattr(pedido, "valor", None))
    if total <= Decimal("0.00"):
        total = Decimal("0.00")

    entrada = parse_decimal_money(data.get("valor_entrada"))
    if entrada <= Decimal("0.00") and pedido is not None:
        entrada = parse_decimal_money(getattr(pedido, "valor_entrada", None))
    if entrada <= Decimal("0.00") and total > Decimal("0.00"):
        entrada = (total * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    restante = parse_decimal_money(data.get("valor_restante"))
    if restante <= Decimal("0.00") and total > Decimal("0.00"):
        restante = (total - entrada).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    percentual_raw = data.get("percentual_entrada")
    try:
        percentual = float(percentual_raw) if percentual_raw not in (None, "") else 50.0
    except (TypeError, ValueError):
        percentual = 50.0

    forma_entrada = _clean_str(data.get("forma_pagamento_entrada")) or _clean_str(
        getattr(pedido, "forma_pagamento_entrada", None)
    )
    forma_restante = _clean_str(data.get("forma_pagamento_restante")) or _clean_str(
        getattr(pedido, "forma_pagamento_restante", None)
    )
    forma_principal = _clean_str(pagamento or getattr(pedido, "pagamento", None))

    return {
        "regra_pagamento": _clean_str(data.get("regra_pagamento")) or "parcial_50",
        "percentual_entrada": percentual,
        "valor_entrada": entrada if entrada > Decimal("0.00") else None,
        "valor_restante": restante if restante > Decimal("0.00") else None,
        "forma_pagamento_entrada": forma_entrada or forma_principal or None,
        "forma_pagamento_restante": forma_restante or forma_principal or None,
        "entrada_recebida_at": getattr(pedido, "entrada_recebida_at", None)
        or datetime_now_brazil(),
        "saldo_recebido_at": getattr(pedido, "saldo_recebido_at", None) if pedido else None,
    }


def _apply_payment_snapshot(pedido, data: dict) -> None:
    snapshot = _build_payment_snapshot(
        data,
        data.get("valor", pedido.valor),
        data.get("status_pagamento", pedido.status_pagamento),
        data.get("pagamento", pedido.pagamento),
        pedido=pedido,
    )
    for field, value in snapshot.items():
        setattr(pedido, field, value)


def _normalize_tipo_local(value: object) -> str:
    tipo = _clean_str(value).lower()
    return tipo if tipo in VALID_TIPOS_LOCAL else "casa"


def _collect_delivery_details(data: dict, pedido=None) -> dict:
    """Normaliza campos extras de entrega e limpa campos nao aplicaveis ao tipo."""
    current_tipo = getattr(pedido, "tipo_local", None) if pedido is not None else None
    tipo_local = _normalize_tipo_local(data.get("tipo_local", current_tipo or "casa"))

    details: dict[str, str | None] = {}
    if "tipo_local" in data or pedido is None:
        details["tipo_local"] = tipo_local

    for field in DELIVERY_DETAIL_FIELDS:
        if field == "tipo_local":
            continue
        if field in data or pedido is None:
            value = _clean_str(data.get(field))
            details[field] = value or None

    if tipo_local != "casa" and ("tipo_local" in data or pedido is None):
        details["quadra"] = None
        details["lote"] = None
    if tipo_local == "casa" and ("tipo_local" in data or pedido is None):
        for field in BUILDING_DETAIL_FIELDS:
            details[field] = None

    return details


def _extract_whatsapp_token_from_payload(data: dict) -> str | None:
    token = _normalize_whatsapp_code(data.get("codigo_whatsapp") or data.get("token_rastreio"))
    if token:
        return token

    for key in ("whatsapp_message", "mensagem_whatsapp", "raw_message", "mensagem", "observacoes"):
        candidate = extract_tracking_token_from_text(data.get(key))
        if candidate:
            return candidate
    return None


def _get_current_vendedor_id() -> int | None:
    """
    Retorna o user_id do vendedor autenticado independente do método de auth.
    - JWT: lê de request.current_user
    - Basic Auth: busca User por email ou nome no banco
    Retorna None se não for vendedor ou não encontrar.
    """
    current_user = getattr(request, "current_user", None)
    if current_user:
        return current_user.get("user_id")

    # Basic Auth: authenticated_user contém email ou nome
    authenticated_user = getattr(request, "authenticated_user", None)
    if authenticated_user:
        from app.models.user import User as _User

        u = (
            _User.query.filter(
                _User.is_active.is_(True),
            )
            .filter((_User.email == authenticated_user) | (_User.name == authenticated_user))
            .first()
        )
        return u.id if u else None

    return None


def _link_lead_by_whatsapp_code(
    codigo_whatsapp: str | None,
    telefone_cliente: str | None,
    pedido_id: int | None = None,
) -> Lead | None:
    """
    Faz o casamento do lead anônimo com o telefone real do pedido.
    Grava também o pedido_id para permitir navegação direta no painel.
    Não lança erro para não bloquear criação/edição de pedido.
    """
    if not codigo_whatsapp or not telefone_cliente:
        return None
    if not is_tracking_token_valid(codigo_whatsapp):
        return None

    telefone_digits = re.sub(r"[^\d]", "", telefone_cliente)
    if not telefone_digits:
        return None

    leads = (
        Lead.query.filter(Lead.token_rastreio == codigo_whatsapp)
        .order_by(Lead.created_at.desc())
        .all()
    )
    for lead in leads:
        if lead.status == "compra_realizada":
            continue
        lead.phone = telefone_digits
        lead.status = "compra_realizada"
        if pedido_id is not None:
            lead.pedido_id = pedido_id
        return lead
    return None


def _upsert_cliente_endereco_from_pedido(pedido) -> None:
    """Salva o endereço de entrega do pedido na agenda de endereços do cliente (#17).

    Idempotente: dedup por `address_hash`. Não lança erro para não bloquear o pedido.
    Só age para pedidos de entrega com cliente vinculado e endereço minimamente preenchido.
    """
    try:
        from app import db
        from app.models import EnderecoCliente

        if not getattr(pedido, "cliente_id", None):
            return
        if (pedido.tipo_pedido or "").strip().lower() != "entrega":
            return
        if not (pedido.rua or pedido.cep):
            return

        candidate = EnderecoCliente(
            cliente_id=pedido.cliente_id,
            cep=pedido.cep,
            rua=pedido.rua,
            numero=pedido.numero,
            bairro=pedido.bairro,
            cidade=pedido.cidade,
        )
        address_hash = candidate.compute_address_hash()

        existing = EnderecoCliente.query.filter_by(
            cliente_id=pedido.cliente_id, address_hash=address_hash
        ).first()
        if existing:
            return

        candidate.address_canonical = candidate.build_address_canonical()
        candidate.address_hash = address_hash
        # Primeiro endereço do cliente vira o principal.
        if EnderecoCliente.query.filter_by(cliente_id=pedido.cliente_id).count() == 0:
            candidate.principal = True
        db.session.add(candidate)
    except Exception as e:  # noqa: BLE001 - upsert é best-effort
        print(
            f"[AVISO] Falha ao salvar endereço do cliente do pedido #{getattr(pedido, 'id', '?')}: {e}"
        )


@pedidos_bp.route("", methods=["GET"])
@requires_edit_auth
def listar_pedidos():
    """Lista pedidos com filtros opcionais"""
    try:
        from datetime import timedelta

        status = request.args.get("status")
        data_inicio = request.args.get("data_inicio")
        data_fim = request.args.get("data_fim")
        search = request.args.get("search")
        filtrar_por_criacao = request.args.get("filtrar_por_criacao", "").lower() == "true"

        # Ordenação e paginação
        # Padrão: ordenar por dia_entrega ASC (mais próximos primeiro: hoje antes de amanhã)
        sort_by = request.args.get("sort_by", "dia_entrega")
        sort_order = request.args.get("sort_order", "asc" if sort_by == "dia_entrega" else "asc")
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        # Converter datas se fornecidas
        data_inicio_obj = None
        data_fim_obj = None
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            except ValueError:
                return error_response("Formato de data_inicio inválido. Use YYYY-MM-DD", 400)
        if data_fim:
            try:
                data_fim_original = datetime.strptime(data_fim, "%Y-%m-%d").date()
                # Se filtrar_por_criacao, converter para fim_exclusivo (dia seguinte 00:00:00)
                if filtrar_por_criacao:
                    data_fim_obj = data_fim_original + timedelta(days=1)
                else:
                    data_fim_obj = data_fim_original
            except ValueError:
                return error_response("Formato de data_fim inválido. Use YYYY-MM-DD", 400)

        # REGRA CRÍTICA: Quando filtrar_por_criacao=True (usado pela tela de vendas),
        # ocultos SEMPRE ENTRAM (excluir_ocultos=False).
        # O campo 'oculto' é apenas para limpeza visual na tela de pedidos.
        # Vendas devem mostrar TODOS os pedidos do mês, incluindo ocultos.
        excluir_ocultos = not filtrar_por_criacao  # False quando filtrar_por_criacao=True

        pedidos, total = pedido_repo.buscar_com_filtros(
            status=status,
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            search=search,
            excluir_ocultos=excluir_ocultos,
            excluir_deletados=True,
            filtrar_por_criacao=filtrar_por_criacao,
            ordenar_por=sort_by,
            ordenar_direcao=sort_order,
            page=page,
            per_page=per_page,
        )

        # Serializar pedidos
        pedidos_data = [p.to_dict() for p in pedidos]

        response_data = {
            "pedidos": pedidos_data,
            "total": total,
        }

        if page is not None and per_page is not None:
            response_data["page"] = page
            response_data["per_page"] = per_page
            response_data["total_pages"] = (total + per_page - 1) // per_page if per_page > 0 else 1

        return success_response(response_data)
    except Exception as e:
        return error_response(f"Erro ao listar pedidos: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>", methods=["GET"])
@requires_edit_auth
def obter_pedido(pedido_id):
    """Obtém pedido por ID"""
    try:
        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        return success_response({"pedido": pedido.to_dict()})
    except Exception as e:
        return error_response(f"Erro ao obter pedido: {str(e)}", 500)


@pedidos_bp.route("/track/<token>", methods=["GET"])
def acompanhar_pedido(token):
    """Status público do pedido via token assinado. SEM auth (rota pública por design).

    O converter <int:pedido_id> não casa com "track/<token>", então não há conflito de
    rotas. 404 sempre genérico para não revelar se o id existe.
    """
    pedido_id = parse_track_token(token)
    if pedido_id is None:
        return error_response("Pedido não encontrado", 404)
    pedido = pedido_repo.get_by_id(pedido_id)
    if not pedido or pedido.oculto or pedido.deleted_at:
        return error_response("Pedido não encontrado", 404)
    return success_response({"pedido": pedido.to_public_dict()})


@pedidos_bp.route("/<int:pedido_id>/track-link", methods=["GET"])
@requires_edit_auth
def obter_track_link(pedido_id):
    """Devolve a URL pública de acompanhamento de um pedido já existente.

    Usado pelo painel para enviar o link por WhatsApp a qualquer momento. Exige auth
    (o token só pode ser gerado server-side, com a SECRET_KEY).
    """
    pedido = pedido_repo.get_by_id(pedido_id)
    if not pedido:
        return error_response("Pedido não encontrado", 404)
    return success_response({"track_url": build_track_url(pedido.id)})


@pedidos_bp.route("/<int:pedido_id>/status", methods=["PUT", "POST"])
@requires_any_role("admin", "atendente", "entregador", "vendedor")
def atualizar_status(pedido_id):
    """Atualiza status de um pedido"""
    try:
        from app import db

        data = request.get_json() or {}
        novo_status = data.get("status", "").strip()

        if not novo_status:
            return error_response("Status é obrigatório", 400)

        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        snapshot = snapshot_commission_fields(pedido)
        status_anterior = pedido.status
        status_pagamento_anterior = pedido.status_pagamento

        pedido.status = novo_status
        if novo_status == "concluido" and (
            not pedido.status_pagamento or pedido.status_pagamento.upper() == "PENDENTE"
        ):
            pedido.status_pagamento = "Pago"

        actor_id = None
        current = getattr(request, "current_user", None)
        if current:
            actor_id = current.get("user_id")
        apply_commission_lifecycle(pedido, previous=snapshot, actor_id=actor_id)
        pedido.updated_at = datetime_now_brazil()
        db.session.commit()

        # Meta CAPI: Purchase é disparado na criação do pedido, não em mudança de status.

        try:
            from app.utils.utmify_helper import send_utmify_if_purchase

            send_utmify_if_purchase(pedido, status_anterior, status_pagamento_anterior)
        except Exception as e:
            print(f"[AVISO] Erro ao enviar UTMify para pedido #{pedido_id}: {e}")

        # Aviso ao cliente que optou por receber notificações (push vinculado ao pedido).
        # Best-effort: só dispara em transições relevantes e nunca derruba a resposta.
        try:
            if novo_status != status_anterior:
                if novo_status == "concluido":
                    is_retirada = "retirada" in (pedido.tipo_pedido or "").lower()
                    body = (
                        "Seu pedido foi retirado. Obrigado! 💚"
                        if is_retirada
                        else "Seu pedido foi entregue. Obrigado! 💚"
                    )
                else:
                    body = {
                        "pronto_entrega": "Seu pedido está pronto e logo sai para entrega 🌷",
                        "pronto_retirada": "Seu pedido está pronto para retirada 🌷",
                        "em_rota": "Seu pedido saiu para entrega 🚚",
                    }.get(novo_status)
                if body:
                    from flask import current_app

                    from app.services.notification_service import send_push_to_pedido_async

                    send_push_to_pedido_async(
                        app=current_app._get_current_object(),
                        pedido_id=pedido.id,
                        title="Plante uma Flor",
                        body=body,
                        url=build_track_url(pedido.id),
                    )
        except Exception as e:
            print(f"[AVISO] Erro ao notificar cliente do pedido #{pedido_id}: {e}")

        return success_response(
            {"pedido": pedido.to_dict()}, message="Status atualizado com sucesso"
        )
    except Exception as e:
        from app import db

        db.session.rollback()
        return error_response(f"Erro ao atualizar status: {str(e)}", 500)


def _get_current_user_id() -> int | None:
    """Resolve o user_id do usuário atual (JWT ou Basic Auth).

    Espelha `_get_current_vendedor_id`, mas sem restrição de role.
    """
    current_user = getattr(request, "current_user", None)
    if current_user and current_user.get("user_id"):
        return current_user.get("user_id")

    authenticated_user = getattr(request, "authenticated_user", None)
    if authenticated_user:
        from app.models.user import User as _User

        u = (
            _User.query.filter(_User.is_active.is_(True))
            .filter((_User.email == authenticated_user) | (_User.name == authenticated_user))
            .first()
        )
        return u.id if u else None
    return None


def _current_role() -> str | None:
    current_user = getattr(request, "current_user", None)
    if current_user:
        return current_user.get("role")
    return getattr(request, "user_role", None)


# ====================================================================
# Endpoints do Entregador
# ====================================================================

ENTREGA_OPEN_STATUSES = ("agendado", "em_producao", "pronto_entrega", "em_rota")


@pedidos_bp.route("/disponiveis-entrega", methods=["GET"])
@requires_any_role("admin", "entregador")
def listar_disponiveis_entrega():
    """Lista pedidos do tipo Entrega ainda sem entregador atribuído."""
    try:
        from app.models import Pedido

        pedidos = (
            Pedido.query.filter(
                Pedido.tipo_pedido == "Entrega",
                Pedido.entregador_id.is_(None),
                Pedido.status.in_(ENTREGA_OPEN_STATUSES),
                Pedido.deleted_at.is_(None),
                Pedido.oculto.is_(False),
            )
            .order_by(Pedido.dia_entrega.asc(), Pedido.horario.asc())
            .all()
        )
        return success_response({"pedidos": [p.to_dict() for p in pedidos], "total": len(pedidos)})
    except Exception as e:
        return error_response(f"Erro ao listar entregas disponíveis: {str(e)}", 500)


@pedidos_bp.route("/minhas-entregas", methods=["GET"])
@requires_any_role("admin", "entregador")
def listar_minhas_entregas():
    """Lista entregas atribuídas ao entregador atual (admin pode passar ?entregador_id=N)."""
    try:
        from app.models import Pedido

        role = _current_role()
        entregador_id: int | None = None
        if role == "admin":
            qid = request.args.get("entregador_id", type=int)
            entregador_id = qid
        else:
            entregador_id = _get_current_user_id()

        if not entregador_id:
            return error_response("entregador_id não resolvido", 400)

        incluir_concluidos = request.args.get("incluir_concluidos", "").lower() == "true"

        q = Pedido.query.filter(
            Pedido.entregador_id == entregador_id,
            Pedido.deleted_at.is_(None),
        )
        if not incluir_concluidos:
            q = q.filter(Pedido.status != "concluido")

        pedidos = q.order_by(Pedido.dia_entrega.asc(), Pedido.horario.asc()).all()
        return success_response(
            {
                "pedidos": [p.to_dict() for p in pedidos],
                "total": len(pedidos),
                "entregador_id": entregador_id,
            }
        )
    except Exception as e:
        return error_response(f"Erro ao listar minhas entregas: {str(e)}", 500)


# EST-02: status a partir dos quais "pegar o pedido" promove para em_rota.
# em_rota não entra (já está em rota) e concluido nunca é rebaixado.
_PROMOVIVEIS_PARA_EM_ROTA = ("agendado", "em_producao", "pronto_entrega")


def _atribuir_um(pedido, target_entregador_id: int, override: bool) -> tuple[bool, str]:
    if pedido.deleted_at is not None:
        return False, "pedido deletado"
    if (pedido.tipo_pedido or "").lower() != "entrega":
        return False, "pedido não é de Entrega"
    if pedido.entregador_id and pedido.entregador_id != target_entregador_id and not override:
        return False, "já atribuído a outro entregador"
    pedido.entregador_id = target_entregador_id
    pedido.delivery_assigned_at = datetime_now_brazil()
    # EST-02: pegar o pedido coloca em rota (sem rebaixar concluido).
    if (pedido.status or "").lower() in _PROMOVIVEIS_PARA_EM_ROTA:
        pedido.status = "em_rota"
    pedido.updated_at = datetime_now_brazil()
    return True, "ok"


@pedidos_bp.route("/<int:pedido_id>/atribuir-entregador", methods=["POST"])
@requires_any_role("admin", "entregador", "vendedor")
def atribuir_entregador(pedido_id):
    """
    Atribui um pedido a um entregador.

    - Entregador: força entregador_id = self (ignora body).
    - Admin/Vendedor: lê body.entregador_id (pode ser null para desatribuir).
    - Admin: pode forçar override quando o pedido já está atribuído (body.override).
    """
    try:
        from app import db

        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        role = _current_role()
        body = request.get_json(silent=True) or {}
        # Admin e vendedor podem reatribuir livremente (override implícito).
        # Entregador NÃO pode "roubar" pedido alheio: override fica False.
        override = role in ("admin", "vendedor")

        # Desatribuir / retirar da rota (entregador_id=null):
        # - admin/vendedor desatribuem qualquer pedido;
        # - entregador pode retirar da rota apenas o próprio (EST-02).
        if "entregador_id" in body and body["entregador_id"] in (None, ""):
            if role == "entregador" and pedido.entregador_id != _get_current_user_id():
                return error_response("Esta entrega não está atribuída a você", 403)
            pedido.entregador_id = None
            pedido.delivery_assigned_at = None
            # EST-02: retirar da rota volta para pronto_entrega (nunca rebaixa concluido).
            if (pedido.status or "").lower() == "em_rota":
                pedido.status = "pronto_entrega"
            pedido.updated_at = datetime_now_brazil()
            db.session.commit()
            return success_response({"pedido": pedido.to_dict()}, message="Entrega retirada da rota")

        if role == "entregador":
            target_id = _get_current_user_id()
        else:  # admin ou vendedor
            target_id = body.get("entregador_id")
            try:
                target_id = int(target_id) if target_id else None
            except (TypeError, ValueError):
                target_id = None

        if not target_id:
            return error_response("entregador_id não resolvido", 400)

        # Vendedor (não-admin) não pode override em pedido já atribuído
        ok, msg = _atribuir_um(pedido, target_id, override=override)
        if not ok:
            return error_response(msg, 409 if "atribuído" in msg else 400)

        db.session.commit()
        return success_response({"pedido": pedido.to_dict()}, message="Entrega atribuída")
    except Exception as e:
        from app import db

        db.session.rollback()
        return error_response(f"Erro ao atribuir entregador: {str(e)}", 500)


@pedidos_bp.route("/atribuir-entregadores-lote", methods=["POST"])
@requires_any_role("admin", "entregador")
def atribuir_entregadores_lote():
    """Atribui vários pedidos ao entregador atual (ou ao informado, se admin)."""
    try:
        from app import db
        from app.models import Pedido

        body = request.get_json(silent=True) or {}
        ids = body.get("pedido_ids") or []
        if not isinstance(ids, list) or not ids:
            return error_response("Informe 'pedido_ids' (lista não vazia)", 400)
        try:
            ids = [int(x) for x in ids]
        except (TypeError, ValueError):
            return error_response("IDs inválidos", 400)

        role = _current_role()
        override = bool(body.get("override")) and role == "admin"
        if role == "entregador":
            target_id = _get_current_user_id()
        else:
            target_id = body.get("entregador_id") or _get_current_user_id()
            try:
                target_id = int(target_id) if target_id else None
            except (TypeError, ValueError):
                target_id = None

        if not target_id:
            return error_response("entregador_id não resolvido", 400)

        pedidos = Pedido.query.filter(Pedido.id.in_(ids)).all()
        found_ids = {p.id for p in pedidos}
        atribuidos: list[int] = []
        ignorados: list[dict] = []

        for pedido in pedidos:
            ok, msg = _atribuir_um(pedido, target_id, override=override)
            if ok:
                atribuidos.append(pedido.id)
            else:
                ignorados.append({"pedido_id": pedido.id, "motivo": msg})

        for missing in [i for i in ids if i not in found_ids]:
            ignorados.append({"pedido_id": missing, "motivo": "não encontrado"})

        db.session.commit()
        return success_response(
            {
                "atribuidos": atribuidos,
                "ignorados": ignorados,
                "entregador_id": target_id,
            },
            message=f"{len(atribuidos)} entrega(s) atribuída(s)",
        )
    except Exception as e:
        from app import db

        db.session.rollback()
        return error_response(f"Erro ao atribuir entregas: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/finalizar-entrega", methods=["POST"])
@requires_any_role("admin", "entregador")
def finalizar_entrega(pedido_id):
    """Marca a entrega como concluída e gera o CREDIT da taxa_entrega no ledger do entregador."""
    try:
        from app import db

        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        role = _current_role()
        current_id = _get_current_user_id()

        if not pedido.entregador_id:
            return error_response("Pedido sem entregador atribuído", 400)
        if role != "admin" and pedido.entregador_id != current_id:
            return error_response("Esta entrega não está atribuída a você", 403)

        # Idempotência: se já concluído, retorna o estado atual sem erro
        if (pedido.status or "").lower() == "concluido" and pedido.delivery_completed_at:
            return success_response(
                {"pedido": pedido.to_dict()},
                message="Entrega já finalizada",
            )

        snapshot = snapshot_commission_fields(pedido)
        status_anterior = pedido.status
        status_pagamento_anterior = pedido.status_pagamento

        pedido.status = "concluido"
        pedido.delivery_completed_at = datetime_now_brazil()
        if not pedido.status_pagamento or pedido.status_pagamento.upper() == "PENDENTE":
            pedido.status_pagamento = "Pago"

        # Reusa o lifecycle (comissão + taxa_entrega via apply_delivery_credit_lifecycle)
        apply_commission_lifecycle(pedido, previous=snapshot, actor_id=current_id)
        pedido.updated_at = datetime_now_brazil()
        db.session.commit()

        # Meta CAPI: Purchase é disparado na criação do pedido, não na finalização da entrega.

        try:
            from app.utils.utmify_helper import send_utmify_if_purchase

            send_utmify_if_purchase(pedido, status_anterior, status_pagamento_anterior)
        except Exception as e:
            print(f"[AVISO] Erro ao enviar UTMify para pedido #{pedido_id}: {e}")

        return success_response({"pedido": pedido.to_dict()}, message="Entrega finalizada")
    except Exception as e:
        from app import db

        db.session.rollback()
        return error_response(f"Erro ao finalizar entrega: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>", methods=["DELETE"])
@requires_any_role("admin", "vendedor")
def deletar_pedido(pedido_id):
    """Deleta pedido (admin sempre; vendedor apenas os próprios)."""

    # Fail-closed: garantir backup antes de operação destrutiva (P0.2)
    # IMPORTANTE: Esta verificação deve estar FORA do try/except genérico
    # para garantir que BackupRequiredException seja tratada corretamente
    from app.utils.destructive_action_guard import BackupRequiredException

    try:
        ensure_backup_before_destructive_action(
            reason="delete_pedido", context={"pedido_id": pedido_id}
        )
    except BackupRequiredException as backup_error:
        # Backup falhou - bloquear operação
        error_msg = str(backup_error)
        print(f"[BLOQUEADO] Operação destrutiva bloqueada: {error_msg}")
        return error_response(
            "Backup necessário antes de operação destrutiva. Falha ao criar backup. Operação bloqueada por segurança.",
            503,
            details={"error": error_msg, "pedido_id": pedido_id},
        )

    # Se chegou aqui, backup foi criado com sucesso
    try:
        print(f"[DELETE_PEDIDO] Iniciando soft delete do pedido #{pedido_id}")
        # Soft delete (P0.3) - não remove fisicamente
        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            print(f"[DELETE_PEDIDO] Pedido #{pedido_id} não encontrado")
            return error_response("Pedido não encontrado", 404)

        if pedido.is_deleted:
            print(
                f"[DELETE_PEDIDO] Pedido #{pedido_id} já foi deletado (deleted_at={pedido.deleted_at})"
            )
            return error_response("Pedido já foi deletado", 400)

        # Ownership check: vendedor só pode deletar pedido próprio
        role = _current_role()
        if role == "vendedor":
            uid = _get_current_user_id()
            if pedido.vendedor_id != uid:
                return error_response("Vendedor só pode deletar pedidos próprios", 403)

        # Obter actor (usuário) se disponível
        actor = "system"  # TODO: extrair de autenticação se disponível

        # Antes do soft delete: voidar comissão ativa, se houver, para evitar
        # crédito órfão no ledger apontando para um pedido inexistente.
        from app.services.commission_service import void_active_commission
        from app.services.delivery_credit_service import void_delivery_credit

        void_active_commission(pedido, reason="soft_delete")
        void_delivery_credit(pedido, reason="soft_delete")

        # Executar soft delete via repository (já registra auditoria)
        print(f"[DELETE_PEDIDO] Chamando soft_delete_pedido para pedido #{pedido_id}")
        pedido_atualizado = pedido_repo.soft_delete_pedido(pedido_id, actor=actor)

        if pedido_atualizado:
            print(
                f"[SUCCESS] Pedido #{pedido_id} soft-deleted com sucesso (deleted_at={pedido_atualizado.deleted_at})"
            )
            return success_response(
                {"pedido": pedido_atualizado.to_dict()},
                message="Pedido arquivado com sucesso (soft delete)",
            )
        else:
            print(
                f"[DELETE_PEDIDO] Falha ao arquivar pedido #{pedido_id} - soft_delete_pedido retornou None"
            )
            return error_response("Falha ao arquivar pedido", 500)

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(
            f"[ERRO] Exceção inesperada ao deletar pedido #{pedido_id}: {error_type}: {error_msg}"
        )
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao deletar pedido: {error_msg}", 500)


@pedidos_bp.route("/exportar-planilha", methods=["POST"])
@requires_edit_auth  # qualquer cargo autenticado pode exportar (admin/vendedor/atendente/entregador/viewer)
def exportar_planilha():
    """
    Exporta vendas para Google Sheets
    CRÍTICO: Preservar esta funcionalidade exatamente como está
    """
    try:
        backend_dir = Path(__file__).parent.parent.parent
        script_path = backend_dir / "scripts" / "export" / "exportar_vendas_sheets.py"

        if not script_path.exists():
            return error_response("Script não encontrado", 500, details={"path": str(script_path)})

        # Importar e executar script (preservar lógica exata)
        import sys

        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        spec = importlib.util.spec_from_file_location("exportar_vendas_sheets", str(script_path))
        if spec is None or spec.loader is None:
            return error_response("Erro ao carregar módulo", 500)

        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(script_path)
        spec.loader.exec_module(module)

        # Nota: O script agora resolve credenciais automaticamente
        # via _resolve_credentials_path() em backend/user/config/ ou variável de ambiente

        if not hasattr(module, "exportar_vendas"):
            return error_response("Função exportar_vendas não encontrada", 500)

        resultado = module.exportar_vendas()

        if resultado:
            return success_response(message="Planilha atualizada com sucesso!")
        else:
            return error_response("Erro ao exportar. Verifique as credenciais do Google.", 500)

    except FileNotFoundError as e:
        return error_response(
            "Credenciais do Google não configuradas", 400, details={"error": str(e)}
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return error_response("Erro ao exportar planilha", 500, details={"error": str(e)})


@pedidos_bp.route("/batch-mark-paid", methods=["POST"])
@requires_any_role("admin", "vendedor")
def batch_mark_paid():
    """Marca todos os pedidos com pagamento Pendente/null como Pago"""
    try:
        from app import db
        from app.models import Pedido

        count = (
            Pedido.query.filter(
                (Pedido.status_pagamento.is_(None)) | (Pedido.status_pagamento == "Pendente")
            )
            .filter(Pedido.deleted_at.is_(None))
            .update(
                {"status_pagamento": "Pago", "updated_at": datetime_now_brazil()},
                synchronize_session="fetch",
            )
        )
        db.session.commit()

        # Meta CAPI: Purchase é disparado na criação do pedido; não há disparo em batch-mark-paid.

        return success_response(message=f"{count} pedidos marcados como Pago")
    except Exception as e:
        import traceback

        traceback.print_exc()
        return error_response("Erro ao marcar pedidos como pagos", 500, details={"error": str(e)})


@pedidos_bp.route("/batch-recalc-taxa", methods=["POST"])
@requires_any_role("admin")
def batch_recalc_taxa():
    """Recalcula taxa_entrega de todos os pedidos com distancia_km usando faixas atuais"""
    try:
        from app import db
        from app.models import Pedido
        from app.services.taxa_entrega import TaxaEntregaService

        service = TaxaEntregaService()
        pedidos = Pedido.query.filter(
            Pedido.distancia_km.isnot(None),
            Pedido.deleted_at.is_(None),
        ).all()

        count = 0
        for p in pedidos:
            nova_taxa = service.calcular_taxa(p.distancia_km)
            if nova_taxa != p.taxa_entrega:
                p.taxa_entrega = nova_taxa
                p.updated_at = datetime_now_brazil()
                count += 1

        db.session.commit()
        return success_response(
            message=f"{count} pedidos atualizados de {len(pedidos)} com distância"
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return error_response("Erro ao recalcular taxas", 500, details={"error": str(e)})


@pedidos_bp.route("/daily-freight", methods=["GET"])
@requires_edit_auth
def daily_freight():
    """Retorna lista de entregas e soma de taxa_entrega para uma data"""
    try:
        from datetime import date as date_type

        from app.models import Pedido

        date_str = request.args.get("date")
        if not date_str:
            date_str = date_type.today().isoformat()

        pedidos = Pedido.query.filter(
            Pedido.dia_entrega == date_str,
            Pedido.tipo_pedido == "Entrega",
            Pedido.deleted_at.is_(None),
        ).all()

        items = [
            {
                "id": p.id,
                "cliente": p.cliente,
                "endereco": p.endereco,
                "taxa_entrega": p.taxa_entrega or 0,
                "status": p.status,
            }
            for p in pedidos
        ]
        total = sum(i["taxa_entrega"] for i in items)

        return success_response(
            {"items": items, "total": total, "date": date_str, "count": len(items)}
        )
    except Exception as e:
        return error_response("Erro ao buscar frete do dia", 500, details={"error": str(e)})


@pedidos_bp.route("/freight-by-source", methods=["GET"])
@requires_edit_auth
def freight_by_source():
    """Média/total de frete agrupada por fonte para um intervalo de datas.

    Query params:
        start: data inicial (YYYY-MM-DD, inclusive). Default: hoje.
        end:   data final   (YYYY-MM-DD, inclusive). Default: hoje.
    """
    try:
        from datetime import date as date_type
        from datetime import datetime as dt

        from sqlalchemy import case, func

        from app import db
        from app.models import FontePedido, Pedido

        start_str = request.args.get("start") or date_type.today().isoformat()
        end_str = request.args.get("end") or start_str

        try:
            start_date = dt.strptime(start_str, "%Y-%m-%d").date()
            end_date = dt.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            return error_response("Datas inválidas (use YYYY-MM-DD)", 400)

        if end_date < start_date:
            start_date, end_date = end_date, start_date

        fonte_label = func.coalesce(
            FontePedido.nome,
            case((Pedido.fonte_pedido != "", Pedido.fonte_pedido), else_=None),
            "(sem fonte)",
        ).label("fonte")

        rows = (
            db.session.query(
                fonte_label,
                func.count(Pedido.id).label("total_pedidos"),
                func.avg(Pedido.taxa_entrega).label("media_taxa_entrega"),
                func.sum(Pedido.taxa_entrega).label("total_taxa_entrega"),
                func.count(Pedido.taxa_entrega).label("n_taxa_entrega"),
                func.avg(Pedido.frete_cobrado_cliente).label("media_frete_cobrado"),
                func.sum(Pedido.frete_cobrado_cliente).label("total_frete_cobrado"),
                func.count(Pedido.frete_cobrado_cliente).label("n_frete_cobrado"),
                func.avg(Pedido.frete_liquido_cliente).label("media_frete_liquido"),
                func.sum(Pedido.frete_liquido_cliente).label("total_frete_liquido"),
                func.count(Pedido.frete_liquido_cliente).label("n_frete_liquido"),
            )
            .outerjoin(FontePedido, Pedido.fonte_pedido_id == FontePedido.id)
            .filter(
                Pedido.deleted_at.is_(None),
                Pedido.dia_entrega >= start_date,
                Pedido.dia_entrega <= end_date,
            )
            .group_by(fonte_label)
            .order_by(func.count(Pedido.id).desc())
            .all()
        )

        def _f(v):
            return float(v) if v is not None else None

        items = [
            {
                "fonte": r.fonte or "(sem fonte)",
                "total_pedidos": int(r.total_pedidos or 0),
                "media_taxa_entrega": _f(r.media_taxa_entrega),
                "total_taxa_entrega": _f(r.total_taxa_entrega),
                "n_taxa_entrega": int(r.n_taxa_entrega or 0),
                "media_frete_cobrado": _f(r.media_frete_cobrado),
                "total_frete_cobrado": _f(r.total_frete_cobrado),
                "n_frete_cobrado": int(r.n_frete_cobrado or 0),
                "media_frete_liquido": _f(r.media_frete_liquido),
                "total_frete_liquido": _f(r.total_frete_liquido),
                "n_frete_liquido": int(r.n_frete_liquido or 0),
            }
            for r in rows
        ]

        return success_response(
            {
                "items": items,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "count": len(items),
            }
        )
    except Exception as e:
        return error_response("Erro ao calcular frete por fonte", 500, details={"error": str(e)})


@pedidos_bp.route("", methods=["POST"])
@requires_any_role("admin", "atendente", "vendedor")
def criar_pedido():
    """
    Cria novo pedido via API (usado pelo PWA)
    CRÍTICO: Preservar toda a lógica existente de api.py
    """
    try:
        import re
        from datetime import datetime

        from app import db
        from app.models import Cliente, FontePedido, Pedido

        data = request.get_json()

        if not data:
            return error_response("Nenhum dado fornecido", 400)

        # Extração de dados (preservar lógica exata)
        cliente = _clean_str(data.get("cliente"))
        telefone_cliente_raw = _clean_str(data.get("telefone_cliente", data.get("telefone", "")))
        # Remover formatação do telefone (máscara deve existir apenas no frontend)
        telefone_cliente = re.sub(r"[^\d]", "", telefone_cliente_raw)
        destinatario = _clean_str(data.get("destinatario"))
        tipo_pedido = data.get("tipo_pedido", "Entrega")
        fonte_pedido_id = data.get("fonte_pedido_id")
        fonte_pedido = _clean_str(data.get("fonte_pedido"))

        produto = _clean_str(data.get("produto"))
        flores_cor = _clean_str(data.get("flores_cor"))
        valor = _clean_str(data.get("valor"))
        horario = _clean_str(data.get("horario", data.get("hora_entrega", "")))
        dia_entrega_str = _clean_str(data.get("dia_entrega", data.get("data_entrega", "")))

        cep = _clean_str(data.get("cep"))
        rua = _clean_str(data.get("rua"))
        numero = _clean_str(data.get("numero"))
        bairro = _clean_str(data.get("bairro"))
        cidade = _clean_str(data.get("cidade"))
        endereco = _clean_str(data.get("endereco"))
        obs_entrega = _clean_str(data.get("obs_entrega"))
        delivery_details = _collect_delivery_details(data)

        mensagem = _clean_str(data.get("mensagem"))
        pagamento = _clean_str(data.get("pagamento"))
        parcelas_cartao_raw = data.get("parcelas_cartao")
        try:
            parcelas_cartao = (
                int(parcelas_cartao_raw) if parcelas_cartao_raw not in (None, "", 0) else None
            )
        except (ValueError, TypeError):
            parcelas_cartao = None
        observacoes = _clean_str(data.get("observacoes"))
        status_pagamento = _clean_str(data.get("status_pagamento"))
        codigo_whatsapp = _extract_whatsapp_token_from_payload(data)

        quantidade_raw = data.get("quantidade", 1)

        # Meta Pixel parameters (fbc vem já no formato fb.1.{ts}.{fbclid})
        fbc_raw = _clean_str(data.get("fbc"))
        fbp_raw = _clean_str(data.get("fbp"))
        fbc = fbc_raw or None
        fbp = fbp_raw or None

        # Validação de campos obrigatórios
        campos_obrigatorios = {
            "telefone_cliente": telefone_cliente,
            "destinatario": destinatario,
            "produto": produto,
            "horario": horario,
            "dia_entrega": dia_entrega_str,
        }

        campos_faltantes = [campo for campo, valor in campos_obrigatorios.items() if not valor]
        if campos_faltantes:
            return error_response(
                f'Campos obrigatórios ausentes: {", ".join(campos_faltantes)}',
                400,
                details={"campos_enviados": list(data.keys())},
            )

        # Conversão de quantidade
        try:
            if isinstance(quantidade_raw, str):
                quantidade_raw = quantidade_raw.strip()
            quantidade = (
                int(quantidade_raw) if quantidade_raw and str(quantidade_raw).strip() else 1
            )
            if quantidade < 0:
                quantidade = 1
        except (ValueError, TypeError):
            quantidade = 1

        # Validação de horário: aceita HH:MM ou intervalo HH:MM - HH:MM
        pattern_simples = r"^([01]?\d|2[0-3]):[0-5]\d$"
        pattern_intervalo = r"^([01]?\d|2[0-3]):[0-5]\d\s*-\s*([01]?\d|2[0-3]):[0-5]\d$"

        if not (re.match(pattern_simples, horario) or re.match(pattern_intervalo, horario)):
            return error_response(
                "Formato de horário inválido",
                400,
                details={
                    "horario_recebido": horario,
                    "formato_esperado": "HH:MM (ex: 14:30) ou intervalo HH:MM - HH:MM (ex: 08:00 - 10:00)",
                },
            )

        # Se for intervalo, validar que horário final é depois do inicial
        if " - " in horario:
            partes = horario.split(" - ")
            if len(partes) == 2:
                try:
                    h1, m1 = map(int, partes[0].strip().split(":"))
                    h2, m2 = map(int, partes[1].strip().split(":"))
                    minutos_inicial = h1 * 60 + m1
                    minutos_final = h2 * 60 + m2
                    if minutos_final <= minutos_inicial:
                        return error_response(
                            "O horário final deve ser depois do horário inicial",
                            400,
                            details={"horario_recebido": horario},
                        )
                except (ValueError, IndexError):
                    return error_response(
                        "Formato de intervalo inválido",
                        400,
                        details={"horario_recebido": horario},
                    )

        # Conversão de data
        try:
            if "/" in dia_entrega_str:
                dia_entrega = datetime.strptime(dia_entrega_str, "%d/%m/%Y").date()
            else:
                dia_entrega = datetime.strptime(dia_entrega_str, "%Y-%m-%d").date()
        except ValueError as e:
            return error_response(
                "Formato de data inválido",
                400,
                details={
                    "data_recebida": dia_entrega_str,
                    "formatos_aceitos": ["YYYY-MM-DD", "DD/MM/YYYY"],
                    "detalhes": str(e),
                },
            )

        # Gerenciar cliente_id
        cliente_id = _normalize_optional_id(data.get("cliente_id"))
        if not cliente_id and cliente and telefone_cliente:
            cliente_existente = Cliente.buscar_por_telefone(telefone_cliente)
            if cliente_existente:
                cliente_id = cliente_existente.id
            else:
                try:
                    novo_cliente = Cliente(
                        nome=cliente,
                        telefone=telefone_cliente,
                        email=None,
                        observacoes=None,
                    )
                    db.session.add(novo_cliente)
                    db.session.flush()
                    cliente_id = novo_cliente.id
                except Exception:
                    cliente_id = None

        try:
            cliente_id_int = int(cliente_id) if cliente_id is not None else None
        except (ValueError, TypeError):
            cliente_id_int = None

        # Processar fonte_pedido_id
        fonte_pedido_id_int = None
        if fonte_pedido_id:
            try:
                fonte_pedido_id_int = int(fonte_pedido_id)
            except (ValueError, TypeError):
                fonte_pedido_id_int = None
        elif fonte_pedido:
            fonte = FontePedido.query.filter_by(nome=fonte_pedido, ativo=True).first()
            if fonte:
                fonte_pedido_id_int = fonte.id

        # Determinar vendedor_id:
        # - vendedor (JWT ou Basic Auth): auto-atribuir o próprio ID
        # - admin: aceitar vendedor_id do body (opcional)
        current_user = getattr(request, "current_user", None)
        if current_user is None:
            _auth_hdr = request.headers.get("Authorization", "")
            if _auth_hdr.lower().startswith("bearer "):
                try:
                    from app.services.auth_service import decode_token, extract_bearer_token

                    _tok = extract_bearer_token(_auth_hdr)
                    current_user = decode_token(_tok) if _tok else None
                except Exception:
                    pass
        user_role = (current_user.get("role") if current_user else None) or getattr(
            request, "user_role", None
        )
        vendedor_id_final = None
        if user_role == "vendedor":
            vendedor_id_final = _get_current_vendedor_id()
        elif user_role == "admin":
            try:
                vendedor_id_final = int(data["vendedor_id"]) if data.get("vendedor_id") else None
            except (ValueError, TypeError):
                vendedor_id_final = None

        # INT-01: derivar slot_inicio (Time) do horário também no pedido manual, para
        # ordenação cronológica confiável e para entrar na ocupação do alocador (INT-02).
        from app.services.delivery_slot_allocator import derive_slot_inicio

        slot_inicio_manual = derive_slot_inicio(horario)

        # Criar pedido
        payment_snapshot = _build_payment_snapshot(data, valor, status_pagamento, pagamento)
        pedido = Pedido(
            cliente=cliente if cliente else None,
            telefone_cliente=telefone_cliente,
            destinatario=destinatario,
            tipo_pedido=tipo_pedido,
            fonte_pedido=fonte_pedido if fonte_pedido else None,
            fonte_pedido_id=fonte_pedido_id_int,
            produto=produto,
            flores_cor=flores_cor if flores_cor else None,
            valor=valor if valor else None,
            horario=horario,
            slot_inicio=slot_inicio_manual,
            dia_entrega=dia_entrega,
            cep=cep if cep else None,
            rua=rua if rua else None,
            numero=numero if numero else None,
            tipo_local=delivery_details["tipo_local"],
            nome_local=delivery_details["nome_local"],
            apto=delivery_details["apto"],
            bloco=delivery_details["bloco"],
            torre=delivery_details["torre"],
            andar=delivery_details["andar"],
            quadra=delivery_details["quadra"],
            lote=delivery_details["lote"],
            complemento=delivery_details["complemento"],
            bairro=bairro if bairro else None,
            cidade=cidade if cidade else None,
            endereco=endereco if endereco else None,
            obs_entrega=obs_entrega if obs_entrega else None,
            mensagem=mensagem if mensagem else None,
            pagamento=pagamento if pagamento else None,
            parcelas_cartao=parcelas_cartao,
            observacoes=observacoes if observacoes else None,
            status_pagamento=status_pagamento if status_pagamento else None,
            **payment_snapshot,
            status="agendado",
            quantidade=quantidade,
            cliente_id=cliente_id_int,
            fbc=fbc,
            fbp=fbp,
            codigo_whatsapp=codigo_whatsapp,
            vendedor_id=vendedor_id_final,
        )

        db.session.add(pedido)
        db.session.flush()  # gera pedido.id antes de vincular o lead
        _link_lead_by_whatsapp_code(codigo_whatsapp, telefone_cliente, pedido_id=pedido.id)
        _upsert_cliente_endereco_from_pedido(pedido)
        from app.services.taxa_cartao import aplicar_taxa_cartao_snapshot

        aplicar_taxa_cartao_snapshot(pedido)
        apply_commission_lifecycle(pedido, previous=None, actor_id=vendedor_id_final)
        db.session.commit()

        # Hook de Purchase: dispara CAPI no ato da criação do pedido (exceto fonte site/Nuvemshop)
        try:
            from app.utils.meta_capi_helper import create_outbox_for_new_order

            create_outbox_for_new_order(pedido)
        except Exception as e:
            print(f"[AVISO] Erro ao criar outbox para pedido #{pedido.id}: {e}")

        try:
            from app.utils.bling_helper import enqueue_bling_for_new_order

            enqueue_bling_for_new_order(pedido)
        except Exception as e:
            print(f"[AVISO] Erro ao criar outbox Bling para pedido #{pedido.id}: {e}")

        try:
            from app.utils.utmify_helper import send_utmify_if_purchase

            send_utmify_if_purchase(pedido, status_anterior=None, status_pagamento_anterior=None)
        except Exception as e:
            print(f"[AVISO] Erro ao enviar UTMify para pedido #{pedido.id}: {e}")

        # Inserir na tabela auxiliar da fonte (se houver)
        if fonte_pedido_id_int:
            try:
                from app.models.pedido_fonte import PedidoFonte

                PedidoFonte.adicionar_pedido(
                    pedido.id, fonte_pedido_id_int, valor if valor else None
                )
            except Exception:
                pass  # Não falhar se houver erro

        # Enviar push notification em background (não bloqueia a resposta)
        try:
            from flask import current_app

            from app.services.notification_service import (
                format_delivery_datetime,
                send_push_to_all_async,
            )

            # Formatar data/hora de entrega
            entrega_info = format_delivery_datetime(pedido.dia_entrega, pedido.horario)
            if entrega_info:
                body = f"#{pedido.id} - {destinatario} | {produto} | Entrega: {entrega_info}"
            else:
                body = f"#{pedido.id} - {destinatario} | {produto}"

            send_push_to_all_async(
                app=current_app._get_current_object(),
                title="Novo Pedido!",
                body=body,
                url="/",
            )
        except Exception:
            pass  # Best-effort: não falhar criação do pedido

        # Link público de acompanhamento (token assinado). Base via env, sem hardcode.
        track_url = build_track_url(pedido.id)

        return success_response(
            {
                "pedido_id": pedido.id,
                "pedido": pedido.to_dict(),
                "track_url": track_url,
            },
            message="Pedido criado com sucesso",
            status_code=201,
        )

    except Exception as e:
        from app import db

        db.session.rollback()
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao criar pedido: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>", methods=["PUT"])
@requires_any_role("admin", "atendente", "vendedor")
def atualizar_pedido(pedido_id):
    """
    Atualiza dados completos do pedido
    CRÍTICO: Preservar lógica de resetar distância quando endereço muda
    IMPORTANTE: Registra overrides para pedidos com external_ref (Nuvemshop)
    """
    try:
        from datetime import datetime

        from app import db
        from app.models import FontePedido

        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404, details={"pedido_id": pedido_id})

        previous_commission_snapshot = snapshot_commission_fields(pedido)
        data = request.get_json() or {}
        codigo_whatsapp = _extract_whatsapp_token_from_payload(data)

        # Verificar se pedido tem external_ref (importado de plataforma externa)
        external_ref = PedidoExternalRef.query.filter_by(pedido_id=pedido_id).first()
        has_external_ref = external_ref is not None

        # Lista de campos que foram alterados (para registro de override)
        changed_fields = []

        # Helper para rastrear mudanças
        def track_change(field_name, old_value, new_value):
            if old_value != new_value:
                changed_fields.append((field_name, new_value))

        # Atualizar campos (preservar lógica exata)
        if "cliente" in data:
            track_change("cliente", pedido.cliente, data["cliente"])
            pedido.cliente = data["cliente"]
        if "telefone_cliente" in data:
            telefone_raw = _clean_str(data["telefone_cliente"])
            new_telefone = re.sub(r"[^\d]", "", telefone_raw)
            track_change("telefone_cliente", pedido.telefone_cliente, new_telefone)
            pedido.telefone_cliente = new_telefone
        if "destinatario" in data:
            track_change("destinatario", pedido.destinatario, data["destinatario"])
            pedido.destinatario = data["destinatario"]
        if "tipo_pedido" in data:
            track_change("tipo_pedido", pedido.tipo_pedido, data["tipo_pedido"])
            pedido.tipo_pedido = data["tipo_pedido"]
        if "fonte_pedido_id" in data:
            try:
                new_fonte_id = int(data["fonte_pedido_id"]) if data["fonte_pedido_id"] else None
                track_change("fonte_pedido_id", pedido.fonte_pedido_id, new_fonte_id)
                pedido.fonte_pedido_id = new_fonte_id
            except (ValueError, TypeError):
                pedido.fonte_pedido_id = None
        elif "fonte_pedido" in data:
            fonte = FontePedido.query.filter_by(nome=data["fonte_pedido"], ativo=True).first()
            if fonte:
                track_change("fonte_pedido_id", pedido.fonte_pedido_id, fonte.id)
                pedido.fonte_pedido_id = fonte.id
            track_change("fonte_pedido", pedido.fonte_pedido, data["fonte_pedido"])
            pedido.fonte_pedido = data["fonte_pedido"]
        if "produto" in data:
            track_change("produto", pedido.produto, data["produto"])
            pedido.produto = data["produto"]
        if "flores_cor" in data:
            track_change("flores_cor", pedido.flores_cor, data["flores_cor"])
            pedido.flores_cor = data["flores_cor"]
        if "valor" in data:
            track_change("valor", pedido.valor, data["valor"])
            pedido.valor = data["valor"]
        if "horario" in data:
            track_change("horario", pedido.horario, data["horario"])
            pedido.horario = data["horario"]
            # INT-01: manter slot_inicio coerente com o horário editado.
            from app.services.delivery_slot_allocator import derive_slot_inicio

            pedido.slot_inicio = derive_slot_inicio(data["horario"])
        if "dia_entrega" in data:
            dia_entrega_str = data["dia_entrega"]
            if "/" in dia_entrega_str:
                new_dia = datetime.strptime(dia_entrega_str, "%d/%m/%Y").date()
            else:
                new_dia = datetime.strptime(dia_entrega_str, "%Y-%m-%d").date()
            track_change("dia_entrega", pedido.dia_entrega, new_dia)
            pedido.dia_entrega = new_dia

        # Verificar se endereço mudou (resetar distância)
        endereco_mudou = False
        campos_endereco = ["cep", "rua", "numero", "bairro", "cidade", "endereco"]
        for campo in campos_endereco:
            if campo in data and data[campo] != getattr(pedido, campo):
                track_change(campo, getattr(pedido, campo), data[campo])
                setattr(pedido, campo, data[campo])
                endereco_mudou = True

        delivery_details = _collect_delivery_details(data, pedido)
        for campo, new_value in delivery_details.items():
            if new_value != getattr(pedido, campo):
                track_change(campo, getattr(pedido, campo), new_value)
                setattr(pedido, campo, new_value)

        if endereco_mudou:
            pedido.distancia_km = None

        if "obs_entrega" in data:
            track_change("obs_entrega", pedido.obs_entrega, data["obs_entrega"])
            pedido.obs_entrega = data["obs_entrega"]
        if "mensagem" in data:
            track_change("mensagem", pedido.mensagem, data["mensagem"])
            pedido.mensagem = data["mensagem"]
        if "pagamento" in data:
            track_change("pagamento", pedido.pagamento, data["pagamento"])
            pedido.pagamento = data["pagamento"]
        if "parcelas_cartao" in data:
            raw = data["parcelas_cartao"]
            try:
                novas_parcelas = int(raw) if raw not in (None, "", 0) else None
            except (ValueError, TypeError):
                novas_parcelas = None
            track_change("parcelas_cartao", pedido.parcelas_cartao, novas_parcelas)
            pedido.parcelas_cartao = novas_parcelas
        if "observacoes" in data:
            track_change("observacoes", pedido.observacoes, data["observacoes"])
            pedido.observacoes = data["observacoes"]

        # Status anterior para hook (ANTES de atualizar)
        status_anterior = pedido.status
        status_pagamento_anterior = pedido.status_pagamento

        if "status_pagamento" in data:
            track_change("status_pagamento", pedido.status_pagamento, data["status_pagamento"])
            pedido.status_pagamento = data["status_pagamento"]

        if "status" in data:
            track_change("status", pedido.status, data["status"])
            pedido.status = data["status"]

        if "fbc" in data:
            new_fbc = _clean_str(data["fbc"]) or None
            track_change("fbc", pedido.fbc, new_fbc)
            pedido.fbc = new_fbc
        if "fbp" in data:
            new_fbp = _clean_str(data["fbp"]) or None
            track_change("fbp", pedido.fbp, new_fbp)
            pedido.fbp = new_fbp

        # Persiste o token do WhatsApp quando vier um (não apaga o existente se o payload
        # de edição não trouxer token). `codigo_whatsapp` já foi extraído acima.
        if codigo_whatsapp and codigo_whatsapp != pedido.codigo_whatsapp:
            track_change("codigo_whatsapp", pedido.codigo_whatsapp, codigo_whatsapp)
            pedido.codigo_whatsapp = codigo_whatsapp

        # Vendedor: admin pode reatribuir; vendedor vincula a si mesmo se ainda sem vendedor
        # Resolve current_user: tenta request.current_user (JWT via decorator),
        # senão decodifica o Bearer token diretamente (Basic Auth path não seta current_user)
        current_user = getattr(request, "current_user", None)
        if current_user is None:
            _auth_hdr = request.headers.get("Authorization", "")
            if _auth_hdr.lower().startswith("bearer "):
                try:
                    from app.services.auth_service import decode_token, extract_bearer_token

                    _tok = extract_bearer_token(_auth_hdr)
                    current_user = decode_token(_tok) if _tok else None
                except Exception:
                    pass
        user_role = (current_user.get("role") if current_user else None) or getattr(
            request, "user_role", None
        )
        if user_role == "admin" and "vendedor_id" in data:
            try:
                pedido.vendedor_id = int(data["vendedor_id"]) if data.get("vendedor_id") else None
            except (ValueError, TypeError):
                pass
        elif user_role == "vendedor" and pedido.vendedor_id is None:
            pedido.vendedor_id = _get_current_vendedor_id()

        if any(
            field in data
            for field in (
                "status_pagamento",
                "pagamento",
                "valor",
                "valor_entrada",
                "valor_restante",
                "forma_pagamento_entrada",
                "forma_pagamento_restante",
                "regra_pagamento",
                "percentual_entrada",
            )
        ):
            _apply_payment_snapshot(pedido, data)

        pedido.updated_at = datetime_now_brazil()

        # Registrar overrides para pedidos com external_ref (Nuvemshop)
        # Isso protege os campos editados manualmente de serem sobrescritos por webhooks
        if has_external_ref and changed_fields:
            actor = getattr(g, "user", None) or "admin"
            for field_name, field_value in changed_fields:
                PedidoManualOverride.set_override(
                    pedido_id=pedido_id,
                    field_name=field_name,
                    field_value=str(field_value) if field_value is not None else None,
                    edited_by=actor,
                )

        if codigo_whatsapp:
            _link_lead_by_whatsapp_code(
                codigo_whatsapp, pedido.telefone_cliente, pedido_id=pedido_id
            )

        actor_id = current_user.get("user_id") if current_user else None
        from app.services.taxa_cartao import aplicar_taxa_cartao_snapshot

        aplicar_taxa_cartao_snapshot(pedido)
        apply_commission_lifecycle(pedido, previous=previous_commission_snapshot, actor_id=actor_id)
        db.session.commit()

        # Meta CAPI: Purchase é disparado na criação do pedido, não em update.

        try:
            from app.utils.utmify_helper import send_utmify_if_purchase

            send_utmify_if_purchase(pedido, status_anterior, status_pagamento_anterior)
        except Exception as e:
            print(f"[AVISO] Erro ao enviar UTMify para pedido #{pedido_id}: {e}")

        return success_response(
            {"pedido": pedido.to_dict()}, message="Pedido atualizado com sucesso"
        )

    except Exception as e:
        from app import db

        db.session.rollback()
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao atualizar pedido: {str(e)}", 500)


@pedidos_bp.route("/por-data", methods=["GET"])
@requires_edit_auth
def get_pedidos_por_data():
    """Retorna contagem de pedidos por horário para uma data específica"""
    try:
        from datetime import datetime

        data_str = request.args.get("data")
        if not data_str:
            return error_response(
                'Parâmetro "data" é obrigatório',
                400,
                details={"formato_esperado": "YYYY-MM-DD (ex: 2025-12-20)"},
            )

        # Converter data
        try:
            if "/" in data_str:
                partes = data_str.split("/")
                if len(partes) == 3:
                    dia, mes, ano = partes
                    data_entrega = datetime.strptime(f"{ano}-{mes}-{dia}", "%Y-%m-%d").date()
                else:
                    return error_response("Formato de data inválido", 400)
            else:
                data_entrega = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError as e:
            return error_response(
                "Formato de data inválido",
                400,
                details={
                    "detalhes": str(e),
                    "formato_esperado": "YYYY-MM-DD ou DD/MM/YYYY",
                },
            )

        # Buscar pedidos do dia
        pedidos = pedido_repo.buscar_por_data(data_entrega, data_entrega, excluir_ocultos=True)

        # Agrupar por horário
        horarios = {}
        for pedido in pedidos:
            horario = pedido.horario.strip() if pedido.horario else ""
            if horario:
                horarios[horario] = horarios.get(horario, 0) + 1

        return success_response(
            {
                "data": data_str,
                "data_formatada": data_entrega.strftime("%Y-%m-%d"),
                "total_pedidos": len(pedidos),
                "horarios": horarios,
            }
        )

    except Exception as e:
        return error_response(f"Erro ao buscar pedidos por data: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/marcar-impresso", methods=["POST", "PUT", "OPTIONS"])
@requires_any_role("admin", "atendente", "vendedor")
def marcar_impresso(pedido_id):
    """Marca pedido como impresso"""
    try:
        from app import db

        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        pedido.impresso = True
        pedido.updated_at = datetime_now_brazil()
        db.session.commit()

        return success_response(
            {"pedido": pedido.to_dict()}, message="Pedido marcado como impresso"
        )

    except Exception as e:
        from app import db

        db.session.rollback()
        return error_response(f"Erro ao marcar como impresso: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/toggle-cartao-impresso", methods=["POST", "PUT", "OPTIONS"])
@requires_any_role("admin", "atendente", "vendedor")
def toggle_cartao_impresso(pedido_id):
    """Alterna a flag 'cartao_impresso' do pedido (cartão/cartinha já impresso)."""
    try:
        from app import db

        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        payload = request.get_json(silent=True) or {}
        if "cartao_impresso" in payload:
            pedido.cartao_impresso = bool(payload["cartao_impresso"])
        else:
            pedido.cartao_impresso = not bool(pedido.cartao_impresso)
        pedido.updated_at = datetime_now_brazil()
        db.session.commit()

        msg = "Cartão marcado como impresso" if pedido.cartao_impresso else "Cartão desmarcado"
        return success_response({"pedido": pedido.to_dict()}, message=msg)

    except Exception as e:
        from app import db

        db.session.rollback()
        return error_response(f"Erro ao alternar cartao_impresso: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/comprovante", methods=["GET"])
def obter_comprovante(pedido_id):
    """Gera comprovante de pedido (HTML)"""
    try:
        from flask import Response

        command = GerarComprovanteCommand(pedido_id)
        html = command.execute()

        return Response(html, mimetype="text/html")
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao gerar comprovante: {str(e)}", 500)


@pedidos_bp.route("/comprovante-lote", methods=["POST"])
def obter_comprovante_lote():
    """Gera comprovante em lote (HTML A4). Moldura `layout` = 1, 2 ou 4 por folha."""
    try:
        from flask import Response

        payload = request.get_json(silent=True) or {}
        pedido_ids = payload.get("pedido_ids", [])

        if not isinstance(pedido_ids, list) or not pedido_ids:
            return error_response("Informe ao menos 1 pedido em 'pedido_ids'", 400)

        try:
            pedido_ids = [int(pid) for pid in pedido_ids]
        except (TypeError, ValueError):
            return error_response("IDs de pedido inválidos", 400)

        if len(pedido_ids) > MAX_PEDIDOS_POR_LOTE:
            return error_response(f"Máximo de {MAX_PEDIDOS_POR_LOTE} pedidos por lote", 400)

        try:
            layout = int(payload.get("layout", 4))
        except (TypeError, ValueError):
            layout = 4

        command = GerarComprovanteLoteCommand(pedido_ids, layout=layout)
        html = command.execute()
        return Response(html, mimetype="text/html")
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao gerar comprovante em lote: {str(e)}", 500)


@pedidos_bp.route("/ocultar-concluidos", methods=["POST"])
@requires_any_role("admin", "vendedor")
def ocultar_concluidos():
    """Oculta todos os pedidos concluídos do painel"""
    try:
        print("[OCULTAR_CONCLUIDOS] Iniciando ocultação de pedidos concluídos...")
        count = pedido_repo.ocultar_concluidos()
        print(f"[OCULTAR_CONCLUIDOS] {count} pedido(s) concluído(s) ocultado(s) com sucesso")

        return success_response(
            {"count": count},
            message=f"{count} pedido(s) concluído(s) ocultado(s) do painel",
        )
    except Exception as e:
        from app import db

        print(f"[OCULTAR_CONCLUIDOS] Erro ao ocultar pedidos concluídos: {str(e)}")
        import traceback

        traceback.print_exc()
        db.session.rollback()
        return error_response(f"Erro ao ocultar pedidos concluídos: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/restore", methods=["POST"])
@requires_role("admin")
def restaurar_pedido(pedido_id):
    """Restaura pedido soft-deleted (P0.3)"""
    try:
        from app import db

        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        if not pedido.is_deleted:
            return error_response("Pedido não está deletado", 400)

        # Obter actor (usuário) se disponível
        actor = "system"  # TODO: extrair de autenticação se disponível

        # Executar restore via repository (já registra auditoria)
        pedido_restaurado = pedido_repo.restore_pedido(pedido_id, actor=actor)

        if pedido_restaurado:
            actor_id = None
            current = getattr(request, "current_user", None)
            if current:
                actor_id = current.get("user_id")

            # Se o pedido restaurado já estiver pago, reexecuta o lifecycle para
            # recompor a comissão que pode ter sido voidada no soft delete.
            apply_commission_lifecycle(pedido_restaurado, previous=None, actor_id=actor_id)
            pedido_restaurado.updated_at = datetime_now_brazil()
            db.session.commit()

            return success_response(
                {"pedido": pedido_restaurado.to_dict()},
                message="Pedido restaurado com sucesso",
            )
        else:
            return error_response("Falha ao restaurar pedido", 500)

    except Exception as e:
        from app import db

        db.session.rollback()
        return error_response(f"Erro ao restaurar pedido: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/meta-outbox", methods=["GET"])
@requires_any_role("admin", "atendente")
def verificar_outbox_pedido(pedido_id):
    """Verifica se existe registro na outbox Meta CAPI para um pedido"""
    try:
        from app.models.meta_capi_outbox import MetaCapiOutbox

        entry = MetaCapiOutbox.query.filter_by(order_id=pedido_id).first()
        if entry:
            return success_response(
                {
                    "exists": True,
                    "outbox": entry.to_dict(),
                },
                message="Outbox encontrada",
            )
        else:
            return success_response(
                {"exists": False},
                message="Nenhuma outbox encontrada para este pedido",
            )
    except Exception as e:
        return error_response(f"Erro ao verificar outbox: {str(e)}", 500)


@pedidos_bp.route("/meta-outbox/stats", methods=["GET"])
@requires_any_role("admin", "atendente")
def estatisticas_outbox():
    """Retorna estatísticas da outbox Meta CAPI"""
    try:
        from app.models.meta_capi_outbox import MetaCapiOutbox

        total = MetaCapiOutbox.query.count()
        pending = MetaCapiOutbox.query.filter_by(status="pending").count()
        sent = MetaCapiOutbox.query.filter_by(status="sent").count()
        failed = MetaCapiOutbox.query.filter_by(status="failed").count()

        return success_response(
            {
                "total": total,
                "pending": pending,
                "sent": sent,
                "failed": failed,
            },
            message="Estatísticas da outbox",
        )
    except Exception as e:
        return error_response(f"Erro ao obter estatísticas: {str(e)}", 500)


@pedidos_bp.route("/meta-outbox/criar-faltantes", methods=["POST"])
@requires_any_role("admin")
def criar_outbox_faltantes():
    """
    Cria outboxes faltantes para pedidos pagos que ainda não têm outbox (backfill)

    Body opcional:
    {
        "limit": 100,  // Limite de pedidos para processar (opcional)
        "dry_run": false  // Se true, apenas mostra o que seria criado (opcional)
    }
    """
    try:
        from sqlalchemy import func

        from app.models.meta_capi_outbox import MetaCapiOutbox
        from app.models.pedido import Pedido
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        data = request.get_json() or {}
        limit = data.get("limit")
        dry_run = data.get("dry_run", False)

        if dry_run:
            # Modo dry-run: apenas contar
            query = (
                Pedido.query.filter(
                    func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
                    Pedido.deleted_at.is_(None),
                )
                .outerjoin(MetaCapiOutbox, Pedido.id == MetaCapiOutbox.order_id)
                .filter(MetaCapiOutbox.id.is_(None))
            )
            if limit:
                query = query.limit(limit)
            total_encontrados = query.count()

            return success_response(
                {
                    "dry_run": True,
                    "total_encontrados": total_encontrados,
                    "criados": 0,
                    "message": f"Encontrados {total_encontrados} pedidos sem outbox (dry-run)",
                },
                message="Dry-run: nenhuma outbox foi criada",
            )

        # Modo real: criar outboxes
        query = (
            Pedido.query.filter(
                func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
                Pedido.deleted_at.is_(None),
            )
            .outerjoin(MetaCapiOutbox, Pedido.id == MetaCapiOutbox.order_id)
            .filter(MetaCapiOutbox.id.is_(None))
            .order_by(Pedido.updated_at.desc())
        )

        if limit:
            query = query.limit(limit)

        pedidos_sem_outbox = query.all()

        outbox_repo = MetaCapiOutboxRepository()
        criados = 0
        erros = 0
        erros_detalhes = []

        for pedido in pedidos_sem_outbox:
            try:
                outbox = outbox_repo.create_from_pedido(pedido)
                if outbox:
                    criados += 1
            except Exception as e:
                erros += 1
                erros_detalhes.append(f"Pedido #{pedido.id}: {str(e)}")

        return success_response(
            {
                "total_encontrados": len(pedidos_sem_outbox),
                "criados": criados,
                "erros": erros,
                "erros_detalhes": erros_detalhes if erros > 0 else None,
            },
            message=f"Processados {len(pedidos_sem_outbox)} pedidos: {criados} outboxes criadas, {erros} erros",
        )

    except Exception as e:
        return error_response(f"Erro ao criar outboxes faltantes: {str(e)}", 500)


@pedidos_bp.route("/meta-outbox/reset-failed", methods=["POST"])
@requires_any_role("admin")
def reset_failed_outbox():
    """
    Reseta entradas failed da outbox Meta CAPI para pending (para retry).
    Útil após corrigir credenciais META_PIXEL_ID / META_CAPI_ACCESS_TOKEN.

    Body opcional:
    {
        "only_permanent": true  // Se true (default), reseta apenas error_type="permanent"
    }
    """
    try:
        from app import db
        from app.models.meta_capi_outbox import MetaCapiOutbox

        data = request.get_json() or {}
        only_permanent = data.get("only_permanent", True)

        q = MetaCapiOutbox.query.filter_by(status="failed")
        if only_permanent:
            q = q.filter_by(error_type="permanent")

        entries = q.all()
        for entry in entries:
            entry.status = "pending"
            entry.attempts = 0
            entry.last_error = None
            entry.error_type = None
            entry.updated_at = datetime_now_brazil()

        db.session.commit()
        return success_response(
            {"reset_count": len(entries)},
            message=f"{len(entries)} entradas resetadas para retry",
        )
    except Exception as e:
        return error_response(f"Erro ao resetar outboxes: {str(e)}", 500)


@pedidos_bp.route("/deleted", methods=["GET"])
@requires_edit_auth
def listar_deletados():
    """Lista pedidos soft-deleted (P0.3)"""
    try:
        pedidos_deletados = pedido_repo.buscar_deletados()
        pedidos_data = [p.to_dict() for p in pedidos_deletados]

        return success_response({"pedidos": pedidos_data, "total": len(pedidos_data)})
    except Exception as e:
        return error_response(f"Erro ao listar pedidos deletados: {str(e)}", 500)
