# -*- coding: utf-8 -*-
"""
LedgerService — geração de créditos fixos, saldo e quitação em lote (double-entry)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from app.utils.date_utils import get_monday


def _compute_due_date(monday: date, payment_day: Optional[int]) -> Optional[date]:
    """
    Calcula a data de vencimento a partir da segunda-feira da semana.
    payment_day: 0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex, 5=Sáb, 6=Dom
    """
    if payment_day is None:
        return None
    return monday + timedelta(days=payment_day)


def generate_weekly_credits(week_ref: date, created_by: int) -> dict:
    """
    Gera créditos fixos semanais para todos os vendedores ativos.
    Idempotente: não cria duplicatas para a mesma semana+categoria.
    Define status='active' e due_date a partir de payment_day do PayrollConfig.

    Returns:
        {"created": int, "skipped": int}
    """
    from flask import current_app

    from app import db
    from app.models.ledger_entry import LedgerEntry
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

            if ledger_repo.get_by_week_and_category(vendedor.id, monday, config.category):
                skipped += 1
                continue

            due_date = _compute_due_date(monday, config.payment_day)

            entry = LedgerEntry(
                user_id=vendedor.id,
                type="CREDIT",
                category=config.category,
                amount=config.amount,
                description=config.label,
                week_ref=monday,
                due_date=due_date,
                status="active",
                created_by=created_by,
            )
            db.session.add(entry)
            created += 1

    db.session.commit()
    current_app.logger.info(
        "[LEDGER] generate_weekly_credits week=%s: %s criados, %s pulados",
        monday, created, skipped,
    )
    return {"created": created, "skipped": skipped}


def generate_calendar(n_weeks: int, created_by: int, from_week: Optional[date] = None) -> dict:
    """
    Gera créditos fixos semanais para as próximas n_weeks semanas a partir de from_week.
    Retorna {"weeks": [...], "total_created": int, "total_skipped": int}.
    """
    if n_weeks < 1 or n_weeks > 52:
        raise ValueError("n_weeks deve estar entre 1 e 52")

    monday = get_monday(from_week)
    total_created = 0
    total_skipped = 0
    weeks: List[str] = []

    for i in range(n_weeks):
        week = monday + timedelta(weeks=i)
        result = generate_weekly_credits(week_ref=week, created_by=created_by)
        total_created += result["created"]
        total_skipped += result["skipped"]
        weeks.append(week.strftime("%Y-%m-%d"))

    return {
        "weeks": weeks,
        "total_created": total_created,
        "total_skipped": total_skipped,
    }


def get_balance(user_id: int) -> dict:
    """Retorna saldo devedor do vendedor."""
    from app.repositories.ledger_repository import LedgerRepository

    return LedgerRepository().get_balance(user_id)


def settle_user_credits(user_id: int, settled_by: int) -> dict:
    """
    Quitação em lote (double-entry): cria um DEBIT = SUM(CREDITs active)
    e marca todos os CREDITs active como settled, apontando para o DEBIT.

    Idempotente: retorna {"settled": 0, "amount": 0} se não há CREDITs active.
    Usa UPDATE condicional atômico para evitar race condition (2 cliques).

    Returns:
        {"settled": int, "amount": float, "debit_id": int | None}
    """
    from flask import current_app

    from app import db
    from app.models.ledger_entry import LedgerEntry
    from app.utils.date_utils import get_monday

    today = date.today()
    week_ref = get_monday(today)

    # 1. Somar CREDITs active em uma única query
    from sqlalchemy import func

    total_row = (
        db.session.query(func.sum(LedgerEntry.amount), func.count(LedgerEntry.id))
        .filter(
            LedgerEntry.user_id == user_id,
            LedgerEntry.type == "CREDIT",
            LedgerEntry.status == "active",
            LedgerEntry.voided.is_(False),
        )
        .one()
    )
    total_amount = float(total_row[0] or 0)
    count = int(total_row[1] or 0)

    if total_amount <= 0 or count == 0:
        return {"settled": 0, "amount": 0.0, "debit_id": None}

    # 2. Criar DEBIT de pagamento já settled
    from app.models.ledger_entry import datetime_now_brazil

    now = datetime_now_brazil()
    debit = LedgerEntry(
        user_id=user_id,
        type="DEBIT",
        category="pagamento",
        amount=round(total_amount, 2),
        description=f"Quitação em lote — {count} lançamento(s)",
        week_ref=week_ref,
        status="settled",
        settled_at=now,
        created_by=settled_by,
    )
    db.session.add(debit)
    db.session.flush()  # gera debit.id sem commit
    debit_id = debit.id

    # 3. Marcar todos os CREDITs active como settled (UPDATE atômico)
    updated = (
        db.session.query(LedgerEntry)
        .filter(
            LedgerEntry.user_id == user_id,
            LedgerEntry.type == "CREDIT",
            LedgerEntry.status == "active",
            LedgerEntry.voided.is_(False),
        )
        .update(
            {"status": "settled", "settled_at": now, "settled_by_id": debit_id},
            synchronize_session="fetch",
        )
    )

    db.session.commit()

    current_app.logger.info(
        "[LEDGER] settle user=%s: %s créditos quitados, total R$%.2f, DEBIT #%s",
        user_id, updated, total_amount, debit_id,
    )
    return {"settled": updated, "amount": round(total_amount, 2), "debit_id": debit_id}


def get_period_summary(user_id: int) -> dict:
    """
    Retorna recebíveis agrupados por período de pagamento (semana).
    """
    from collections import defaultdict

    from app.models.ledger_entry import LedgerEntry
    from app.repositories.user_repository import UserRepository

    today = date.today()

    user_repo = UserRepository()
    payroll_configs = user_repo.get_payroll_configs(user_id)
    semanal_config = next(
        (c for c in payroll_configs if c.frequency == "semanal" and c.payment_day is not None),
        None,
    )

    entries = (
        LedgerEntry.query.filter_by(user_id=user_id)
        .filter(LedgerEntry.voided.is_(False))
        .order_by(LedgerEntry.week_ref.desc(), LedgerEntry.created_at.asc())
        .all()
    )

    weeks: dict = defaultdict(lambda: {
        "entries": [],
        "total_credit": 0.0,
        "total_debit": 0.0,
        "settled": 0.0,
        "active": 0.0,
        "pgt_day": None,
    })

    for entry in entries:
        key = entry.week_ref.isoformat() if entry.week_ref else "sem_semana"
        group = weeks[key]
        group["entries"].append(entry.to_dict())

        if group["pgt_day"] is None:
            if entry.due_date:
                group["pgt_day"] = entry.due_date.isoformat()
            elif entry.week_ref and semanal_config:
                pgt = entry.week_ref + timedelta(days=semanal_config.payment_day)
                group["pgt_day"] = pgt.isoformat()

        if entry.type == "CREDIT":
            group["total_credit"] = round(group["total_credit"] + float(entry.amount), 2)
            if entry.status == "settled":
                group["settled"] = round(group["settled"] + float(entry.amount), 2)
            else:
                group["active"] = round(group["active"] + float(entry.amount), 2)
        else:
            group["total_debit"] = round(group["total_debit"] + float(entry.amount), 2)

    result = []
    for week_key, group in sorted(weeks.items(), reverse=True):
        pgt_day_date = date.fromisoformat(group["pgt_day"]) if group["pgt_day"] else None
        has_active = group["active"] > 0
        is_overdue = pgt_day_date is not None and pgt_day_date < today and has_active

        if is_overdue:
            status = "atrasado"
        elif has_active and pgt_day_date and pgt_day_date >= today:
            status = "pendente"
        elif has_active:
            status = "pendente"
        elif group["settled"] > 0:
            status = "quitado"
        else:
            status = "futuro"

        result.append({
            "week_ref": week_key,
            "pgt_day": group["pgt_day"],
            "total_credit": group["total_credit"],
            "total_debit": group["total_debit"],
            "settled": group["settled"],
            "active": group["active"],
            "is_overdue": is_overdue,
            "status": status,
            "entries": group["entries"],
        })

    return {
        "periods": result,
        "today": today.isoformat(),
    }


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
    Cria lançamento manual no ledger (adiantamento, bônus, ajuste).
    Entradas manuais do admin nascem como 'settled' (não precisam de confirmação).
    """
    from app import db
    from app.models.ledger_entry import ALL_CATEGORIES, LedgerEntry, datetime_now_brazil

    if entry_type not in ("CREDIT", "DEBIT"):
        raise ValueError("type deve ser CREDIT ou DEBIT")
    if category not in ALL_CATEGORIES:
        raise ValueError(f"category '{category}' inválida")
    if amount <= 0:
        raise ValueError("amount deve ser positivo")

    monday = get_monday(week_ref)
    now = datetime_now_brazil()
    # CREDITs manuais nascem 'active' (ainda a receber pelo vendedor).
    # DEBITs manuais (adiantamento, ajuste) são imediatamente 'settled'.
    status = "active" if entry_type == "CREDIT" else "settled"
    entry = LedgerEntry(
        user_id=user_id,
        type=entry_type,
        category=category,
        amount=round(amount, 2),
        description=description,
        week_ref=monday,
        status=status,
        settled_at=now if status == "settled" else None,
        created_by=created_by,
    )
    db.session.add(entry)
    db.session.commit()
    return entry.to_dict()
