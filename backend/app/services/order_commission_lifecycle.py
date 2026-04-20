# -*- coding: utf-8 -*-
"""
Regras de ciclo de vida de comissão para pedidos.
Centraliza gatilhos de create/update/status em um único ponto.
"""
from __future__ import annotations

from typing import Any

from app.repositories.ledger_repository import LedgerRepository
from app.services.commission_service import generate_commission, void_and_recreate_commission


SENSITIVE_FIELDS = ("vendedor_id", "fonte_pedido_id", "valor", "tipo_pedido", "taxa_entrega")


def snapshot_commission_fields(pedido) -> dict[str, Any]:
    """Captura os campos usados para detectar mudanças que exigem estorno."""
    return {
        "status_pagamento": getattr(pedido, "status_pagamento", None),
        "vendedor_id": getattr(pedido, "vendedor_id", None),
        "fonte_pedido_id": getattr(pedido, "fonte_pedido_id", None),
        "valor": getattr(pedido, "valor", None),
        "tipo_pedido": getattr(pedido, "tipo_pedido", None),
        "taxa_entrega": getattr(pedido, "taxa_entrega", None),
    }


def _is_paid_status(value: str | None) -> bool:
    return (value or "").strip().lower() in ("pago", "parcial")


def _sensitive_fields_changed(previous: dict[str, Any], pedido) -> bool:
    for field in SENSITIVE_FIELDS:
        if previous.get(field) != getattr(pedido, field, None):
            return True
    return False


def apply_commission_lifecycle(pedido, previous: dict[str, Any] | None = None, actor_id: int | None = None) -> dict:
    """
    Aplica regras de comissão para create/update/status.

    Retorna dicionário com flags de ações executadas.
    """
    from app.models.pedido import datetime_now_brazil

    previous = previous or {}

    prev_status_pagamento = previous.get("status_pagamento")
    curr_status_pagamento = getattr(pedido, "status_pagamento", None)
    transitioning_to_paid = _is_paid_status(curr_status_pagamento) and not _is_paid_status(
        prev_status_pagamento
    )

    if transitioning_to_paid and not getattr(pedido, "paid_at", None):
        pedido.paid_at = datetime_now_brazil()

    vendedor_id = getattr(pedido, "vendedor_id", None) or actor_id
    if not vendedor_id:
        return {
            "transitioning_to_paid": transitioning_to_paid,
            "voided_and_recreated": False,
            "generated": False,
        }

    repo = LedgerRepository()
    has_active_commission = repo.get_active_by_pedido_id(pedido.id) is not None

    if previous and has_active_commission and _sensitive_fields_changed(previous, pedido):
        void_and_recreate_commission(pedido, vendedor_id)
        return {
            "transitioning_to_paid": transitioning_to_paid,
            "voided_and_recreated": True,
            "generated": True,
        }

    if transitioning_to_paid:
        generate_commission(pedido, vendedor_id)
        return {
            "transitioning_to_paid": True,
            "voided_and_recreated": False,
            "generated": True,
        }

    return {
        "transitioning_to_paid": False,
        "voided_and_recreated": False,
        "generated": False,
    }

