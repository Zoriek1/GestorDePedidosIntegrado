# -*- coding: utf-8 -*-
"""
LedgerService — geração de créditos fixos, cálculo de saldo e lançamentos manuais
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


def get_monday(ref_date: Optional[date] = None) -> date:
    """Retorna a segunda-feira da semana fornecida (ou da semana atual)."""
    if ref_date is None:
        ref_date = date.today()
    return ref_date - timedelta(days=ref_date.weekday())


def generate_weekly_credits(week_ref: date, created_by: int) -> dict:
    """
    Gera créditos fixos semanais para todos os vendedores ativos.
    Idempotente: não cria duplicatas para a mesma semana+categoria.

    Returns:
        {"created": int, "skipped": int}
    """
    from app import db
    from app.models.ledger_entry import LedgerEntry
    from app.models.user import User
    from app.repositories.ledger_repository import LedgerRepository
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository()
    ledger_repo = LedgerRepository()

    monday = get_monday(week_ref)
    vendedores = user_repo.get_active_by_role("vendedor")

    created = 0
    skipped = 0

    for vendedor in vendedores:
        configs = user_repo.get_payroll_configs(vendedor.id)

        for config in configs:
            if config.frequency != "semanal":
                continue

            # Idempotência
            if ledger_repo.get_by_week_and_category(vendedor.id, monday, config.category):
                skipped += 1
                continue

            entry = LedgerEntry(
                user_id=vendedor.id,
                type="CREDIT",
                category=config.category,
                amount=config.amount,
                description=config.label,
                week_ref=monday,
                created_by=created_by,
            )
            db.session.add(entry)
            created += 1

    db.session.commit()
    print(f"[LEDGER] generate_weekly_credits week={monday}: {created} criados, {skipped} pulados")
    return {"created": created, "skipped": skipped}


def get_balance(user_id: int) -> dict:
    """Retorna saldo devedor do vendedor."""
    from app.repositories.ledger_repository import LedgerRepository

    return LedgerRepository().get_balance(user_id)


def create_manual_entry(
    user_id: int,
    entry_type: str,
    category: str,
    amount: float,
    week_ref: date,
    created_by: int,
    description: Optional[str] = None,
) -> dict:
    """
    Cria lançamento manual no ledger (pagamento, adiantamento, bônus, ajuste).

    Returns:
        LedgerEntry.to_dict()
    """
    from app import db
    from app.models.ledger_entry import ALL_CATEGORIES, LedgerEntry

    if entry_type not in ("CREDIT", "DEBIT"):
        raise ValueError("type deve ser CREDIT ou DEBIT")
    if category not in ALL_CATEGORIES:
        raise ValueError(f"category '{category}' inválida")
    if amount <= 0:
        raise ValueError("amount deve ser positivo")

    monday = get_monday(week_ref)
    entry = LedgerEntry(
        user_id=user_id,
        type=entry_type,
        category=category,
        amount=round(amount, 2),
        description=description,
        week_ref=monday,
        created_by=created_by,
    )
    db.session.add(entry)
    db.session.commit()
    return entry.to_dict()
