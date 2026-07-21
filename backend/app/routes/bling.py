# -*- coding: utf-8 -*-
"""Rotas da integracao Bling API v3."""

import logging

from flask import Blueprint, g, redirect, request

from app import db
from app.integrations.bling.errors import BlingIntegrationError
from app.integrations.bling.service import BlingIntegrationService
from app.integrations.bling.token_service import BlingTokenService
from app.middleware import requires_any_role, requires_role
from app.models.bling_integration_log import BlingIntegrationLog
from app.schemas.common import error_response, success_response
from app.services.oauth_state import sign_state, verify_state
from app.services.tenancy import is_multi_store

bling_bp = Blueprint("bling", __name__, url_prefix="/api/integrations/bling")
logger = logging.getLogger(__name__)


def _service() -> BlingIntegrationService:
    return BlingIntegrationService(store_ref_id=getattr(g, "tenant_store_id", None))


def _front_url(path: str) -> str:
    from app.config import Config

    base = (
        getattr(Config, "PUBLIC_BASE_URL", "")
        or getattr(Config, "NUVEMSHOP_PUBLIC_BASE_URL", "")
        or ""
    ).rstrip("/")
    return f"{base}{path}" if base else path


def _handle_error(exc: Exception):
    if isinstance(exc, BlingIntegrationError):
        return error_response(str(exc), 400, details=exc.details)
    logger.exception("Erro inesperado na integracao Bling")
    return error_response(f"Erro na integracao Bling: {type(exc).__name__}", 500)


@bling_bp.route("/install", methods=["GET"])
@requires_role("admin")
def bling_install():
    try:
        # State assinado amarra o fluxo à loja autenticada (Fase B). Fallback ao
        # state estático apenas quando não há loja no contexto (single-tenant legado).
        store = getattr(g, "current_store", None)
        state = sign_state(store.id, "bling") if store else "gestor-bling"
        url = BlingTokenService.build_authorize_url(state=state)
        if request.args.get("redirect", "").lower() == "true":
            return redirect(url)
        return success_response({"authorize_url": url})
    except Exception as exc:
        return _handle_error(exc)


@bling_bp.route("/oauth/callback", methods=["GET"])
def bling_oauth_callback():
    code = request.args.get("code")
    if not code:
        return error_response("Parametro code ausente", 400)

    # Resolve o tenant pelo state assinado. No modo multi-tenant, state ausente/
    # inválido falha fechado; no single-tenant cai na loja default (compat).
    verified = verify_state(request.args.get("state"), "bling")
    store_ref_id = verified["srid"] if verified else None
    if store_ref_id is None and is_multi_store():
        return error_response("State OAuth inválido ou ausente", 400)

    try:
        BlingTokenService.exchange_code(code, store_ref_id=store_ref_id)
        return redirect(_front_url("/integracoes/bling?bling=connected"))
    except Exception as exc:
        return _handle_error(exc)


@bling_bp.route("/disconnect", methods=["DELETE"])
@requires_role("admin")
def bling_disconnect():
    """Desconecta o Bling localmente (nao revoga no provedor)."""
    from app.models.bling_credential import BlingCredential
    from app.models.pedido import datetime_now_brazil

    store_ref_id = getattr(g, "tenant_store_id", None)
    try:
        cred = BlingCredential.query.filter_by(store_ref_id=store_ref_id).first()
        if cred:
            cred.active = False
            cred.access_token_encrypted = None
            cred.refresh_token_encrypted = None
            cred.updated_at = datetime_now_brazil()
            db.session.commit()
        return success_response(message="Bling desconectado")
    except Exception:
        db.session.rollback()
        logger.exception("Erro ao desconectar Bling")
        return error_response("Erro ao desconectar Bling", 500)


@bling_bp.route("/status", methods=["GET"])
@requires_role("admin")
def bling_status():
    try:
        return success_response(_service().status())
    except Exception as exc:
        return _handle_error(exc)


@bling_bp.route("/sync-config", methods=["POST"])
@requires_role("admin")
def bling_sync_config():
    try:
        result = _service().sync_config()
        return success_response(result, message="Configuracao Bling sincronizada")
    except Exception as exc:
        return _handle_error(exc)


@bling_bp.route("/config", methods=["GET"])
@requires_role("admin")
def bling_config():
    try:
        return success_response(_service().list_config())
    except Exception as exc:
        return _handle_error(exc)


@bling_bp.route("/mappings/<int:mapping_id>", methods=["PUT"])
@requires_role("admin")
def bling_update_mapping(mapping_id: int):
    try:
        mapping = _service().save_mapping(mapping_id, request.get_json() or {})
        return success_response({"mapping": mapping.to_dict()}, message="Mapeamento salvo")
    except Exception as exc:
        return _handle_error(exc)


@bling_bp.route("/pedidos/<int:pedido_id>/preview", methods=["POST", "GET"])
@requires_any_role("admin", "atendente", "vendedor")
def bling_preview_pedido(pedido_id: int):
    try:
        return success_response(_service().preview_order(pedido_id))
    except Exception as exc:
        return _handle_error(exc)


@bling_bp.route("/pedidos/<int:pedido_id>/send", methods=["POST"])
@requires_any_role("admin", "atendente")
def bling_send_pedido(pedido_id: int):
    try:
        result = _service().send_order(pedido_id)
        return success_response(result, message="Envio Bling processado")
    except Exception as exc:
        return _handle_error(exc)


@bling_bp.route("/outbox/<int:outbox_id>/retry", methods=["POST"])
@requires_any_role("admin", "atendente")
def bling_retry_outbox(outbox_id: int):
    try:
        result = _service().retry_outbox(outbox_id)
        return success_response(result, message="Retry Bling processado")
    except Exception as exc:
        return _handle_error(exc)


@bling_bp.route("/outbox/<int:outbox_id>/logs", methods=["GET"])
@requires_any_role("admin", "atendente", "vendedor")
def bling_outbox_logs(outbox_id: int):
    logs = (
        BlingIntegrationLog.query.filter_by(outbox_id=outbox_id)
        .order_by(BlingIntegrationLog.created_at.asc())
        .all()
    )
    return success_response({"logs": [log.to_dict() for log in logs]})


@bling_bp.route("/process-pending", methods=["POST"])
@requires_role("admin")
def bling_process_pending():
    limit = request.args.get("limit", type=int) or 20
    try:
        return success_response(_service().process_pending(limit=limit))
    except Exception as exc:
        return _handle_error(exc)
