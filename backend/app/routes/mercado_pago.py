# -*- coding: utf-8 -*-
"""Rotas da integracao Mercado Pago Point."""

import logging

from flask import Blueprint, request

from app.integrations.mercado_pago.errors import (
    MercadoPagoConfigError,
    MercadoPagoError,
    MercadoPagoValidationError,
)
from app.integrations.mercado_pago.service import MercadoPagoService
from app.middleware import requires_any_role, requires_role
from app.models.mercado_pago_integration_log import MercadoPagoIntegrationLog
from app.models.mercado_pago_outbox import MercadoPagoOutbox
from app.schemas.common import error_response, success_response

mercado_pago_bp = Blueprint("mercado_pago", __name__, url_prefix="/api/integrations/mercadopago")
logger = logging.getLogger(__name__)


def _service() -> MercadoPagoService:
    from flask import g

    return MercadoPagoService(store_ref_id=getattr(g, "tenant_store_id", None))


def _handle_error(exc: Exception):
    if isinstance(exc, MercadoPagoValidationError):
        return error_response(str(exc), 400)
    if isinstance(exc, MercadoPagoConfigError):
        return error_response(str(exc), 400)
    if isinstance(exc, MercadoPagoError):
        return error_response(str(exc), 502, details=exc.details)
    logger.exception("Erro inesperado na integracao Mercado Pago")
    return error_response(f"Erro na integracao Mercado Pago: {type(exc).__name__}", 500)


# ---------------------------------------------------------------------------
# Webhook (PUBLICO - chamado pelo Mercado Pago, sem JWT)
# ---------------------------------------------------------------------------
@mercado_pago_bp.route("/webhook", methods=["POST"])
def mp_webhook():
    try:
        raw_body = request.get_data()
        headers = {k: v for k, v in request.headers if k.lower().startswith("x-")}
        result = _service().handle_webhook(raw_body, headers)
        return success_response(result)
    except MercadoPagoValidationError as exc:
        return error_response(str(exc), 401)
    except Exception as exc:
        logger.exception("Erro no webhook Mercado Pago")
        return error_response(f"Erro: {type(exc).__name__}", 500)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
@mercado_pago_bp.route("/status", methods=["GET"])
@requires_role("admin")
def mp_status():
    try:
        return success_response(_service().status())
    except Exception as exc:
        return _handle_error(exc)


# ---------------------------------------------------------------------------
# Setup (criar webhook MP + contato Bling)
# ---------------------------------------------------------------------------
@mercado_pago_bp.route("/setup", methods=["POST"])
@requires_role("admin")
def mp_setup():
    try:
        result = _service().setup_integration()
        return success_response(result, message="Integracao MP Point configurada")
    except Exception as exc:
        return _handle_error(exc)


# ---------------------------------------------------------------------------
# Config (credenciais mascaradas)
# ---------------------------------------------------------------------------
@mercado_pago_bp.route("/config", methods=["GET"])
@requires_role("admin")
def mp_config():
    try:
        from app.services.integration_settings_service import (
            default_store,
            get_settings,
            serialize_settings,
        )

        store = default_store()
        settings = get_settings(store.id)
        return success_response(serialize_settings(store, settings))
    except Exception as exc:
        return _handle_error(exc)


# ---------------------------------------------------------------------------
# Process pending (trigger manual do worker)
# ---------------------------------------------------------------------------
@mercado_pago_bp.route("/process-pending", methods=["POST"])
@requires_role("admin")
def mp_process_pending():
    limit = request.args.get("limit", type=int) or 20
    try:
        return success_response(_service().process_pending(limit=limit))
    except Exception as exc:
        return _handle_error(exc)


# ---------------------------------------------------------------------------
# Retry outbox
# ---------------------------------------------------------------------------
@mercado_pago_bp.route("/outbox/<int:outbox_id>/retry", methods=["POST"])
@requires_role("admin")
def mp_retry_outbox(outbox_id: int):
    try:
        outbox = MercadoPagoOutbox.query.get_or_404(outbox_id)
        outbox.status = "pending"
        outbox.step = "pending"

        outbox.next_retry_at = None
        outbox.error_message = None
        outbox.error_code = None
        from app import db

        db.session.commit()
        result = _service().process_outbox(outbox)
        return success_response(result, message="Retry MP processado")
    except Exception as exc:
        return _handle_error(exc)


# ---------------------------------------------------------------------------
# Outbox logs
# ---------------------------------------------------------------------------
@mercado_pago_bp.route("/outbox/<int:outbox_id>/logs", methods=["GET"])
@requires_any_role("admin", "atendente")
def mp_outbox_logs(outbox_id: int):
    logs = (
        MercadoPagoIntegrationLog.query.filter_by(outbox_id=outbox_id)
        .order_by(MercadoPagoIntegrationLog.created_at.asc())
        .all()
    )
    return success_response({"logs": [log.to_dict() for log in logs]})


# ---------------------------------------------------------------------------
# Outbox list
# ---------------------------------------------------------------------------
@mercado_pago_bp.route("/outbox", methods=["GET"])
@requires_any_role("admin", "atendente")
def mp_outbox_list():
    status = request.args.get("status")
    query = MercadoPagoOutbox.query
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(MercadoPagoOutbox.created_at.desc()).limit(50).all()
    return success_response({"outbox": [item.to_dict() for item in items]})
