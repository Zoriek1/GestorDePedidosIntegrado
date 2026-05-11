# -*- coding: utf-8 -*-
"""
DeliveryCreditService — gera CREDIT no ledger do entregador ao finalizar entrega.

Espelha commission_service.generate_commission, mas:
- Usa delivery_pedido_id (não pedido_id) para idempotência, deixando a comissão
  do vendedor (pedido_id) conviver no mesmo pedido sem conflito de índice.
- amount = pedido.taxa_entrega (não percentual).
- category = "taxa_entrega".
"""
from __future__ import annotations

from datetime import date, datetime


def _resolve_reference_date(pedido) -> date:
    """delivery_completed_at → paid_at → created_at → today (Brazil)."""
    for attr in ("delivery_completed_at", "paid_at", "created_at"):
        v = getattr(pedido, attr, None)
        if v:
            return v.date() if isinstance(v, datetime) else v
    from app.utils.date_utils import today_brazil

    return today_brazil()


def generate_delivery_credit(
    pedido, entregador_id: int, reference_date: date | None = None
) -> None:
    """
    Gera o CREDIT de taxa_entrega no ledger do entregador.
    Idempotente: se já existe CREDIT ativo para o pedido (delivery_pedido_id), não duplica.
    """
    from flask import current_app

    from app import db
    from app.models.ledger_entry import LedgerEntry
    from app.repositories.ledger_repository import LedgerRepository
    from app.repositories.user_repository import UserRepository
    from app.services.commission_service import get_due_date_for_commission, get_monday

    ledger_repo = LedgerRepository()
    user_repo = UserRepository()

    if not entregador_id:
        return

    if ledger_repo.get_active_by_delivery_pedido_id(pedido.id):
        return

    taxa = float(getattr(pedido, "taxa_entrega", None) or 0.0)
    if taxa <= 0:
        current_app.logger.info(
            "[TAXA_ENTREGA] Pedido #%s sem taxa_entrega — CREDIT pulado", pedido.id
        )
        return

    ref_date = reference_date or _resolve_reference_date(pedido)
    week_ref = get_monday(ref_date)

    payroll_configs = user_repo.get_payroll_configs(entregador_id)
    semanal_config = next(
        (c for c in payroll_configs if c.frequency == "semanal" and c.payment_day is not None),
        None,
    )
    due_date = (
        get_due_date_for_commission(ref_date, semanal_config.payment_day)
        if semanal_config
        else ref_date
    )

    entry = LedgerEntry(
        user_id=entregador_id,
        type="CREDIT",
        category="taxa_entrega",
        amount=round(taxa, 2),
        description=f"Taxa de entrega — Pedido #{pedido.id}",
        delivery_pedido_id=pedido.id,
        week_ref=week_ref,
        due_date=due_date,
        status="active",
        created_by=entregador_id,
    )
    db.session.add(entry)
    db.session.flush()
    current_app.logger.info(
        "[TAXA_ENTREGA] Pedido #%s: R$%.2f → entregador %s",
        pedido.id, taxa, entregador_id,
    )


def void_delivery_credit(pedido, reason: str) -> bool:
    """
    Marca o CREDIT de taxa_entrega ativo como voided (sem DEBIT contrário).
    Usado em status_regression, soft_delete, edit_estorno.
    Returns: True se voidou algo.
    """
    from flask import current_app

    from app import db
    from app.repositories.ledger_repository import LedgerRepository

    existing = LedgerRepository().get_active_by_delivery_pedido_id(pedido.id)
    if not existing:
        return False

    existing.voided = True
    existing.void_reason = reason
    db.session.flush()
    current_app.logger.info(
        "[TAXA_ENTREGA] Pedido #%s: CREDIT R$%.2f voidado (reason=%s)",
        pedido.id, float(existing.amount), reason,
    )
    return True


def void_and_recreate_delivery_credit(pedido, entregador_id: int) -> None:
    """
    Estorna o CREDIT atual de taxa_entrega e cria um novo com os valores atuais.
    Usado quando taxa_entrega muda em pedido já finalizado.
    """
    void_delivery_credit(pedido, reason="edit_estorno")
    generate_delivery_credit(pedido, entregador_id)
