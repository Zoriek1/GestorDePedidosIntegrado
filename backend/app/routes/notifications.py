# -*- coding: utf-8 -*-
"""
Rotas de Push Notifications.

Endpoints:
  GET  /api/notifications/vapid-public-key  — Retorna a chave pública VAPID.
  POST /api/notifications/subscribe         — Salva (ou atualiza) uma inscrição.
  POST /api/notifications/test              — Envia notificação de teste (admin).
"""
import logging

from flask import Blueprint, request

from app import db
from app.config import Config
from app.middleware import requires_role
from app.models.push_subscription import PushSubscription
from app.schemas.common import error_response, success_response

logger = logging.getLogger(__name__)

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.route("/vapid-public-key", methods=["GET"])
def get_vapid_public_key():
    """Retorna a chave pública VAPID para o frontend se inscrever."""
    key = Config.VAPID_PUBLIC_KEY
    if not key:
        return error_response("VAPID_PUBLIC_KEY não configurada no servidor", 500)
    return success_response({"publicKey": key})


@notifications_bp.route("/subscribe", methods=["POST"])
def subscribe():
    """
    Salva uma inscrição de push notification.

    Body esperado:
    {
        "endpoint": "https://fcm.googleapis.com/...",
        "keys": {
            "p256dh": "...",
            "auth": "..."
        }
    }
    """
    data = request.get_json() or {}

    endpoint = (data.get("endpoint") or "").strip()
    keys = data.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth = (keys.get("auth") or "").strip()

    if not endpoint or not p256dh or not auth:
        return error_response("Campos obrigatórios: endpoint, keys.p256dh, keys.auth", 400)

    # Upsert: atualiza se o endpoint já existe, senão cria.
    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        existing.p256dh = p256dh
        existing.auth = auth
        db.session.commit()
        logger.info("[Push] Subscription atualizada: %s...", endpoint[:60])
        return success_response({"status": "updated"})

    sub = PushSubscription(endpoint=endpoint, p256dh=p256dh, auth=auth)
    db.session.add(sub)
    db.session.commit()
    logger.info("[Push] Nova subscription: %s...", endpoint[:60])
    return success_response({"status": "created"}, status_code=201)


def _read_subscription_payload():
    """Lê e valida o corpo {endpoint, keys:{p256dh, auth}}. Retorna (data, erro)."""
    data = request.get_json() or {}
    endpoint = (data.get("endpoint") or "").strip()
    keys = data.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth = (keys.get("auth") or "").strip()
    if not endpoint or not p256dh or not auth:
        return None, error_response("Campos obrigatórios: endpoint, keys.p256dh, keys.auth", 400)
    return {"endpoint": endpoint, "p256dh": p256dh, "auth": auth}, None


@notifications_bp.route("/track/<token>/subscribe", methods=["POST"])
def subscribe_track(token):
    """
    Inscrição pública (CLIENTE) para avisos de status de um pedido específico.

    Sem auth por design — o token assinado de acompanhamento é a credencial. A
    inscrição fica vinculada ao pedido (``pedido_id``), separada do broadcast da equipe.

    NOTA: ``endpoint`` é único por dispositivo; se o mesmo dispositivo se inscrever em
    outro pedido, a inscrição passa a apontar para o pedido mais recente.
    """
    from app.services.track_token import parse_track_token

    pedido_id = parse_track_token(token)
    if pedido_id is None:
        return error_response("Pedido não encontrado", 404)

    payload, err = _read_subscription_payload()
    if err:
        return err

    existing = PushSubscription.query.filter_by(endpoint=payload["endpoint"]).first()
    if existing:
        existing.p256dh = payload["p256dh"]
        existing.auth = payload["auth"]
        existing.pedido_id = pedido_id
        db.session.commit()
        logger.info("[Push] Inscrição de cliente atualizada (pedido %s)", pedido_id)
        return success_response({"status": "updated"})

    sub = PushSubscription(
        endpoint=payload["endpoint"],
        p256dh=payload["p256dh"],
        auth=payload["auth"],
        pedido_id=pedido_id,
    )
    db.session.add(sub)
    db.session.commit()
    logger.info("[Push] Nova inscrição de cliente (pedido %s)", pedido_id)
    return success_response({"status": "created"}, status_code=201)


@notifications_bp.route("/track/<token>/unsubscribe", methods=["POST"])
def unsubscribe_track(token):
    """Cancela a inscrição de avisos do cliente para um pedido (por endpoint)."""
    from app.services.track_token import parse_track_token

    pedido_id = parse_track_token(token)
    if pedido_id is None:
        return error_response("Pedido não encontrado", 404)

    data = request.get_json() or {}
    endpoint = (data.get("endpoint") or "").strip()
    if not endpoint:
        return error_response("Campo obrigatório: endpoint", 400)

    removed = PushSubscription.query.filter_by(endpoint=endpoint, pedido_id=pedido_id).delete()
    db.session.commit()
    return success_response({"status": "deleted", "removed": removed})


@notifications_bp.route("/test", methods=["POST"])
@requires_role("admin")
def test_notification():
    """Envia uma notificação de teste para todos os dispositivos inscritos."""
    from app.services.notification_service import send_push_to_all

    result = send_push_to_all(
        title="Teste de Notificação",
        body="Se você está lendo isso, as notificações estão funcionando!",
        url="/",
    )
    return success_response(result)
