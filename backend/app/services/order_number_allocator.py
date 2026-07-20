# -*- coding: utf-8 -*-
"""Alocação monotônica de número de pedido por empresa."""

from sqlalchemy import func

from app import db
from app.models.pedido import Pedido
from app.models.store import Store


def allocate_order_number(store_ref_id: int | None) -> int | None:
    """Retorna o próximo número da empresa, serializando no PostgreSQL."""
    if store_ref_id is None:
        return None

    # A linha da Store funciona como mutex por tenant no PostgreSQL. No SQLite,
    # a serialização da escrita e a unique composta são a proteção final.
    db.session.query(Store.id).filter(Store.id == store_ref_id).with_for_update().one()
    current = (
        db.session.query(func.max(Pedido.numero_pedido))
        .execution_options(include_all_tenants=True)
        .filter(Pedido.store_ref_id == store_ref_id)
        .scalar()
    )
    return int(current or 0) + 1
