# -*- coding: utf-8 -*-
"""
LedgerService — geração de créditos fixos, cálculo de saldo e lançamentos manuais
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional


def get_monday(ref_date: Optional[date] = None) -> date:
    """Retorna a segunda-feira da semana fornecida (ou da semana atual)."""
    if ref_date is None:
        ref_date = date.today()
    return ref_date - timedelta(days=ref_date.weekday())


def _compute_due_date(monday: date, payment_day: Optional[int]) -> Optional[date]:
    """
    Calcula a data de vencimento a partir da segunda-feira da semana.
    payment_day: 0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex, 5=Sáb, 6=Dom
    Se payment_day for None, retorna None.
    """
    if payment_day is None:
        return None
    return monday + timedelta(days=payment_day)


def generate_weekly_credits(week_ref: date, created_by: int) -> dict:
    """
    Gera créditos fixos semanais para todos os vendedores ativos.
    Idempotente: não cria duplicatas para a mesma semana+categoria.
    Define status='pendente' e due_date a partir de payment_day do PayrollConfig.

    Returns:
        {"created": int, "skipped": int}
    """
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

            # Idempotência
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
                status="pendente",
                created_by=created_by,
            )
            db.session.add(entry)
            created += 1

    db.session.commit()
    print(f"[LEDGER] generate_weekly_credits week={monday}: {created} criados, {skipped} pulados")
    return {"created": created, "skipped": skipped}


def generate_calendar(n_weeks: int, created_by: int, from_week: Optional[date] = None) -> dict:
    """
    Gera créditos fixos semanais para as próximas n_weeks semanas a partir de from_week
    (padrão: semana atual).
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


def get_period_summary(user_id: int) -> dict:
    """
    Retorna recebíveis agrupados por período de pagamento (semana).

    Cada período contém:
    - week_ref: segunda-feira da semana (YYYY-MM-DD)
    - pgt_day: data prevista de pagamento (due_date do período)
    - total_credit: soma de créditos do período
    - confirmed: soma confirmada
    - pending: soma pendente (inclui atrasado)
    - is_overdue: True se pgt_day < hoje e ainda há pendente
    - status: "atrasado" | "pendente" | "confirmado" | "futuro"
    - entries: lista de lançamentos do período
    """
    from collections import defaultdict

    from app.models.ledger_entry import LedgerEntry
    from app.repositories.user_repository import UserRepository

    today = date.today()

    # Buscar payment_day do vendedor
    user_repo = UserRepository()
    payroll_configs = user_repo.get_payroll_configs(user_id)
    semanal_config = next(
        (c for c in payroll_configs if c.frequency == "semanal" and c.payment_day is not None),
        None,
    )

    # Todos os lançamentos do vendedor ordenados por semana
    entries = (
        LedgerEntry.query.filter_by(user_id=user_id)
        .order_by(LedgerEntry.week_ref.desc(), LedgerEntry.created_at.asc())
        .all()
    )

    # Agrupar por week_ref
    weeks: dict = defaultdict(lambda: {
        "entries": [],
        "total_credit": 0.0,
        "total_debit": 0.0,
        "confirmed": 0.0,
        "pending": 0.0,
        "pgt_day": None,
    })

    for entry in entries:
        key = entry.week_ref.isoformat() if entry.week_ref else "sem_semana"
        group = weeks[key]
        group["entries"].append(entry.to_dict())

        # Calcular pgt_day do grupo a partir do semanal_config se ainda não definido
        if group["pgt_day"] is None:
            if entry.due_date:
                group["pgt_day"] = entry.due_date.isoformat()
            elif entry.week_ref and semanal_config:
                pgt = entry.week_ref + timedelta(days=semanal_config.payment_day)
                group["pgt_day"] = pgt.isoformat()

        if entry.type == "CREDIT":
            group["total_credit"] = round(group["total_credit"] + entry.amount, 2)
            if entry.status == "confirmado":
                group["confirmed"] = round(group["confirmed"] + entry.amount, 2)
            else:
                group["pending"] = round(group["pending"] + entry.amount, 2)
        else:
            group["total_debit"] = round(group["total_debit"] + entry.amount, 2)

    # Montar resultado com status calculado
    result = []
    for week_key, group in sorted(weeks.items(), reverse=True):
        pgt_day_date = date.fromisoformat(group["pgt_day"]) if group["pgt_day"] else None
        has_pending = group["pending"] > 0
        is_overdue = pgt_day_date is not None and pgt_day_date < today and has_pending

        if is_overdue:
            status = "atrasado"
        elif has_pending and pgt_day_date and pgt_day_date >= today:
            status = "pendente"
        elif has_pending:
            status = "pendente"
        elif group["confirmed"] > 0:
            status = "confirmado"
        else:
            status = "futuro"

        result.append({
            "week_ref": week_key,
            "pgt_day": group["pgt_day"],
            "total_credit": group["total_credit"],
            "total_debit": group["total_debit"],
            "confirmed": group["confirmed"],
            "pending": group["pending"],
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
    Cria lançamento manual no ledger (pagamento, adiantamento, bônus, ajuste).
    DEBITs são criados já como 'confirmado'; CREDITs manuais como 'confirmado' também
    (admin está lançando manualmente — não precisa de confirmação do funcionário).

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
        status="confirmado",
        created_by=created_by,
    )
    db.session.add(entry)
    db.session.commit()
    return entry.to_dict()
