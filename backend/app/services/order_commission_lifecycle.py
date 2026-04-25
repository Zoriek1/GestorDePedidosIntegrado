# -*- coding: utf-8 -*-
"""
Regras de ciclo de vida de comissão para pedidos.
Centraliza gatilhos de create/update/status em um único ponto.
"""
from __future__ import annotations

from typing import Any

from app.repositories.ledger_repository import LedgerRepository
from app.services.commission_service import (
    generate_commission,
    void_active_commission,
    void_and_recreate_commission,
)

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
    was_paid = _is_paid_status(prev_status_pagamento)
    is_paid_now = _is_paid_status(curr_status_pagamento)
    transitioning_to_paid = is_paid_now and not was_paid
    transitioning_from_paid = was_paid and not is_paid_now

    if transitioning_to_paid and not getattr(pedido, "paid_at", None):
        pedido.paid_at = datetime_now_brazil()

    repo = LedgerRepository()
    has_active_commission = repo.get_active_by_pedido_id(pedido.id) is not None
    has_any_commission = repo.get_by_pedido_id(pedido.id) is not None

    # Regressão Pago/Parcial → não pago: voida o CREDIT ativo (sem DEBIT, pois
    # não houve pagamento real) e sai. Não exige vendedor_id.
    if transitioning_from_paid and has_active_commission:
        voided = void_active_commission(pedido, reason="status_regression")
        return {
            "transitioning_to_paid": False,
            "transitioning_from_paid": True,
            "voided_and_recreated": False,
            "voided": voided,
            "generated": False,
        }

    vendedor_id = getattr(pedido, "vendedor_id", None) or actor_id
    if not vendedor_id:
        return {
            "transitioning_to_paid": transitioning_to_paid,
            "transitioning_from_paid": transitioning_from_paid,
            "voided_and_recreated": False,
            "voided": False,
            "generated": False,
        }

    if previous and has_active_commission and _sensitive_fields_changed(previous, pedido):
        void_and_recreate_commission(pedido, vendedor_id)
        return {
            "transitioning_to_paid": transitioning_to_paid,
            "transitioning_from_paid": transitioning_from_paid,
            "voided_and_recreated": True,
            "voided": False,
            "generated": True,
        }

    # Pedido pago/parcial que ainda nao tem nenhuma comissao historica valida:
    # cobre create ja pago, update Pendente->Pago e atribuicao tardia de vendedor.
    if is_paid_now and not has_any_commission:
        generate_commission(pedido, vendedor_id)
        return {
            "transitioning_to_paid": transitioning_to_paid,
            "transitioning_from_paid": transitioning_from_paid,
            "voided_and_recreated": False,
            "voided": False,
            "generated": True,
        }

    return {
        "transitioning_to_paid": False,
        "transitioning_from_paid": False,
        "voided_and_recreated": False,
        "voided": False,
        "generated": False,
    }
