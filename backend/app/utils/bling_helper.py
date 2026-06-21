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
