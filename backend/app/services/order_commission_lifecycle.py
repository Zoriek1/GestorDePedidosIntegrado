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
from app.services.delivery_credit_service import (
    generate_delivery_credit,
    void_and_recreate_delivery_credit,
    void_delivery_credit,
)

SENSITIVE_FIELDS = (
    "vendedor_id",
    "fonte_pedido_id",
    "valor",
    "tipo_pedido",
    "taxa_entrega",
    "taxa_cartao_valor",
)
DELIVERY_SENSITIVE_FIELDS = ("entregador_id", "taxa_entrega")


def snapshot_commission_fields(pedido) -> dict[str, Any]:
    """Captura os campos usados para detectar mudanças que exigem estorno."""
    return {
        "status": getattr(pedido, "status", None),
        "status_pagamento": getattr(pedido, "status_pagamento", None),
        "vendedor_id": getattr(pedido, "vendedor_id", None),
        "entregador_id": getattr(pedido, "entregador_id", None),
        "fonte_pedido_id": getattr(pedido, "fonte_pedido_id", None),
        "valor": getattr(pedido, "valor", None),
        "tipo_pedido": getattr(pedido, "tipo_pedido", None),
        "taxa_entrega": getattr(pedido, "taxa_entrega", None),
        "taxa_cartao_valor": getattr(pedido, "taxa_cartao_valor", None),
        "delivery_completed_at": getattr(pedido, "delivery_completed_at", None),
    }


def _is_paid_status(value: str | None) -> bool:
    return (value or "").strip().lower() in ("pago", "parcial")


def _sensitive_fields_changed(previous: dict[str, Any], pedido) -> bool:
    for field in SENSITIVE_FIELDS:
        if previous.get(field) != getattr(pedido, field, None):
            return True
    return False


def apply_commission_lifecycle(
    pedido, previous: dict[str, Any] | None = None, actor_id: int | None = None
) -> dict:
    """
    Aplica regras de comissão para create/update/status.

    Também aciona o lifecycle do CREDIT de taxa_entrega (entregador) ao final,
    para que toda mudança no pedido propague para o ledger do entregador sem
    exigir que cada callsite saiba dos dois fluxos.

    Retorna dicionário com flags de ações executadas (mantém shape original).
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
        result = {
            "transitioning_to_paid": False,
            "transitioning_from_paid": True,
            "voided_and_recreated": False,
            "voided": voided,
            "generated": False,
        }
        apply_delivery_credit_lifecycle(pedido, previous=previous)
        return result

    vendedor_id = getattr(pedido, "vendedor_id", None) or actor_id
    if not vendedor_id:
        result = {
            "transitioning_to_paid": transitioning_to_paid,
            "transitioning_from_paid": transitioning_from_paid,
            "voided_and_recreated": False,
            "voided": False,
            "generated": False,
        }
        apply_delivery_credit_lifecycle(pedido, previous=previous)
        return result

    if previous and has_active_commission and _sensitive_fields_changed(previous, pedido):
        void_and_recreate_commission(pedido, vendedor_id)
        result = {
            "transitioning_to_paid": transitioning_to_paid,
            "transitioning_from_paid": transitioning_from_paid,
            "voided_and_recreated": True,
            "voided": False,
            "generated": True,
        }
        apply_delivery_credit_lifecycle(pedido, previous=previous)
        return result

    # Pedido pago/parcial que ainda nao tem nenhuma comissao historica valida:
    # cobre create ja pago, update Pendente->Pago e atribuicao tardia de vendedor.
    if is_paid_now and not has_any_commission:
        generate_commission(pedido, vendedor_id)
        result = {
            "transitioning_to_paid": transitioning_to_paid,
            "transitioning_from_paid": transitioning_from_paid,
            "voided_and_recreated": False,
            "voided": False,
            "generated": True,
        }
        apply_delivery_credit_lifecycle(pedido, previous=previous)
        return result

    result = {
        "transitioning_to_paid": False,
        "transitioning_from_paid": False,
        "voided_and_recreated": False,
        "voided": False,
        "generated": False,
    }
    apply_delivery_credit_lifecycle(pedido, previous=previous)
    return result


def apply_delivery_credit_lifecycle(pedido, previous: dict[str, Any] | None = None) -> dict:
    """
    Espelha o lifecycle de comissão, porém para o CREDIT de taxa_entrega do entregador.

    Regras:
    - status regredindo de 'concluido' para outro → void.
    - entregador_id mudou em pedido já com CREDIT ativo → void+recreate (se houver entregador novo).
    - taxa_entrega mudou em pedido já com CREDIT ativo → void+recreate.
    - delivery_completed_at definido pela 1ª vez + entregador_id presente + taxa_entrega > 0 → generate.
    """
    previous = previous or {}
    repo = LedgerRepository()

    prev_status = (previous.get("status") or "").lower()
    curr_status = (getattr(pedido, "status", None) or "").lower()
    entregador_id = getattr(pedido, "entregador_id", None)
    has_active = repo.get_active_by_delivery_pedido_id(pedido.id) is not None

    # Regressão de status (concluido → algo) voida o CREDIT.
    if prev_status == "concluido" and curr_status != "concluido" and has_active:
        voided = void_delivery_credit(pedido, reason="status_regression")
        return {"voided": voided, "generated": False, "voided_and_recreated": False}

    # entregador_id ou taxa_entrega mudaram em pedido já creditado.
    if previous and has_active:
        changed = any(
            previous.get(f) != getattr(pedido, f, None) for f in DELIVERY_SENSITIVE_FIELDS
        )
        if changed:
            if entregador_id:
                void_and_recreate_delivery_credit(pedido, entregador_id)
                return {"voided": False, "generated": True, "voided_and_recreated": True}
            void_delivery_credit(pedido, reason="edit_estorno")
            return {"voided": True, "generated": False, "voided_and_recreated": False}

    # 1ª geração: pedido finalizado com entregador + taxa > 0.
    if (
        curr_status == "concluido"
        and entregador_id
        and getattr(pedido, "delivery_completed_at", None)
        and not has_active
    ):
        generate_delivery_credit(pedido, entregador_id)
        return {"voided": False, "generated": True, "voided_and_recreated": False}

    return {"voided": False, "generated": False, "voided_and_recreated": False}
