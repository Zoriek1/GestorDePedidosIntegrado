# -*- coding: utf-8 -*-
"""Helpers para enfileirar integracao Bling sem bloquear o pedido."""

import logging

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.bling_credential import BlingCredential
from app.models.bling_outbox import BlingOutbox
from app.models.pedido import Pedido

logger = logging.getLogger(__name__)


def enqueue_bling_for_new_order(pedido: Pedido) -> bool:
    """Cria outbox Bling para pedido novo quando a integracao esta pronta.

    Nao chama a API do Bling aqui. O bling-worker processa a fila em segundo
    plano, e falhas de mapeamento/API ficam registradas no proprio outbox.
    """
    if not current_app.config.get("BLING_ENABLED"):
        return False

    store_id = current_app.config.get("BLING_STORE_ID") or "default"
    credential = BlingCredential.query.filter_by(store_id=store_id, active=True).first()
    if not credential or not credential.refresh_token_encrypted:
        logger.info("bling.skip_enqueue pedido_id=%s reason=not_connected", pedido.id)
        return False

    existing = BlingOutbox.query.filter_by(
        pedido_id=pedido.id,
        operation="send_order",
    ).first()
    if existing:
        logger.info(
            "bling.skip_enqueue pedido_id=%s reason=already_enqueued outbox_id=%s",
            pedido.id,
            existing.id,
        )
        return False

    outbox = BlingOutbox(
        pedido_id=pedido.id,
        operation="send_order",
        status="pending",
        step="pending",
    )
    db.session.add(outbox)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        logger.info("bling.skip_enqueue pedido_id=%s reason=unique_conflict", pedido.id)
        return False

    logger.info("bling.enqueued pedido_id=%s outbox_id=%s", pedido.id, outbox.id)
    return True


def enqueue_bling_cancel_for_order(pedido: Pedido) -> bool:
    """Enfileira o cancelamento da venda no Bling quando o pedido e excluido.

    So enfileira se o pedido realmente foi enviado ao Bling (tem venda criada);
    caso contrario nao ha o que cancelar. O bling-worker processa a fila.
    """
    if not current_app.config.get("BLING_ENABLED"):
        return False

    store_id = current_app.config.get("BLING_STORE_ID") or "default"
    credential = BlingCredential.query.filter_by(store_id=store_id, active=True).first()
    if not credential or not credential.refresh_token_encrypted:
        return False

    # Só cancela se o pedido foi enviado: precisa existir venda no Bling.
    sent = (
        BlingOutbox.query.filter_by(pedido_id=pedido.id, operation="send_order")
        .order_by(BlingOutbox.id.desc())
        .first()
    )
    has_order = bool(sent and sent.bling_order_id) or _has_external_ref(
        pedido.id, pedido.store_ref_id, store_id
    )
    if not has_order:
        logger.info("bling.skip_cancel pedido_id=%s reason=not_sent", pedido.id)
        return False

    existing = BlingOutbox.query.filter_by(
        pedido_id=pedido.id,
        operation="cancel_order",
    ).first()
    if existing and existing.status == "completed":
        return False
    if existing:
        existing.status = "pending"
        existing.error_code = None
        existing.error_message = None
        existing.next_retry_at = None
        db.session.commit()
        logger.info("bling.cancel_requeued pedido_id=%s outbox_id=%s", pedido.id, existing.id)
        return True

    outbox = BlingOutbox(
        pedido_id=pedido.id,
        operation="cancel_order",
        status="pending",
        step="pending",
    )
    db.session.add(outbox)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return False

    logger.info("bling.cancel_enqueued pedido_id=%s outbox_id=%s", pedido.id, outbox.id)
    return True


def _has_external_ref(pedido_id: int, store_ref_id: int | None, store_id: str) -> bool:
    from app.models.pedido_external_ref import PedidoExternalRef

    return (
        PedidoExternalRef.query.filter_by(
            store_ref_id=store_ref_id,
            provider="bling",
            store_id=store_id,
            pedido_id=pedido_id,
        ).first()
        is not None
    )
