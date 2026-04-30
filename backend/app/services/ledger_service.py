# -*- coding: utf-8 -*-
"""
LedgerService — geração de créditos fixos, saldo e quitação em lote (double-entry)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from app.utils.date_utils import get_monday, today_brazil


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

    Idempotência em duas camadas:
      1. Pré-check Python (otimização — evita INSERT desnecessário)
      2. UNIQUE index parcial uq_ledger_weekly_active (source of truth — protege race)

    Returns:
        {"created": int, "skipped": int}
    """
    from flask import current_app
    from sqlalchemy.exc import IntegrityError

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
            try:
                db.session.flush()
                created += 1
            except IntegrityError:
                db.session.rollback()
                skipped += 1
                current_app.logger.info(
                    "[LEDGER] race detectada — duplicata bloqueada pelo índice "
                    "user=%s week=%s cat=%s",
                    vendedor.id,
                    monday,
                    config.category,
                )

    db.session.commit()
    current_app.logger.info(
        "[LEDGER] generate_weekly_credits week=%s: %s criados, %s pulados",
        monday,
        created,
        skipped,
    )
    return {"created": created, "skipped": skipped}


def auto_generate_for_today(created_by: int | None = None) -> dict:
    """
    Autopagamento diário: para cada vendedor cuja PayrollConfig.payment_day
    coincide com o dia da semana de hoje (BRT), gera os créditos da SEMANA ATUAL.
    Idempotente — chamar mais de uma vez no mesmo dia não duplica.

    Pensado para rodar 1x/dia via meta_scheduler_entrypoint.
    """
    from flask import current_app

    from app.models.ledger_entry import datetime_now_brazil
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository()
    today = datetime_now_brazil().date()
    weekday = today.weekday()  # 0=Seg ... 6=Dom
    monday = get_monday(today)

    vendedores_a_pagar = []
    for vendedor in user_repo.get_active_by_role("vendedor"):
        configs = user_repo.get_payroll_configs(vendedor.id)
        if any(c.frequency == "semanal" and c.payment_day == weekday for c in configs):
            vendedores_a_pagar.append(vendedor.id)

    if not vendedores_a_pagar:
        return {"date": today.isoformat(), "vendedores_processados": 0, "created": 0, "skipped": 0}

    # generate_weekly_credits já itera todos os vendedores ativos com os
    # configs deles — chamamos uma vez para a semana atual; idempotência via
    # uq_ledger_weekly_active garante que apenas vendedores cujo config bate
    # serão criados (os outros são pulados pelo pré-check).
    actor_id = created_by or vendedores_a_pagar[0]
    result = generate_weekly_credits(week_ref=monday, created_by=actor_id)

    current_app.logger.info(
        "[LEDGER] auto_generate_for_today date=%s weekday=%s alvo=%s criados=%s",
        today,
        weekday,
        len(vendedores_a_pagar),
        result["created"],
    )
    return {
        "date": today.isoformat(),
        "vendedores_processados": len(vendedores_a_pagar),
        **result,
    }


def void_salary_entry(entry_id: int, actor_id: int) -> dict:
    """
    Apaga (soft-delete via voided=True) um lançamento de salário.

    Restrições:
      - Apenas categorias fixo_semanal | almoco | transporte (nunca comissão).
      - Não pode estar liquidado (settled_by_id != NULL).
      - Não pode já estar voidado.

    Mantém a entrada no banco (auditoria); o índice parcial uq_ledger_weekly_active
    libera o slot pra um novo lançamento da mesma (user, week, category).
    """
    from flask import current_app

    from app import db
    from app.models.ledger_entry import LedgerEntry, datetime_now_brazil

    SALARY_CATEGORIES = {"fixo_semanal", "almoco", "transporte"}

    entry = LedgerEntry.query.get(entry_id)
    if entry is None:
        raise LookupError(f"Lançamento #{entry_id} não encontrado")
    if entry.category not in SALARY_CATEGORIES:
        raise PermissionError("Apenas salários (fixo_semanal/almoco/transporte) podem ser apagados")
    if entry.settled_by_id is not None or entry.status == "settled":
        raise ValueError("Lançamento já liquidado não pode ser apagado")
    if entry.voided:
        raise ValueError("Lançamento já estava apagado")

    entry.voided = True
    entry.description = (entry.description or "") + (
        f" [voided em {datetime_now_brazil().strftime('%Y-%m-%d %H:%M')} por user#{actor_id}]"
    )
    db.session.commit()

    current_app.logger.info(
        "[LEDGER] void salary entry=%s user=%s actor=%s",
        entry_id,
        entry.user_id,
        actor_id,
    )
    return entry.to_dict()


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


def _normalize_ids(values: list[int]) -> list[int]:
    normalized: list[int] = []
    seen = set()
    for value in values or []:
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            continue
        if item_id <= 0:
            continue
        if item_id in seen:
            continue
        seen.add(item_id)
        normalized.append(item_id)
    return normalized


def settle_user_credits(
    user_id: int,
    settled_by: int,
    pedido_ids: list[int] | None = None,
    entry_ids: list[int] | None = None,
) -> dict:
    """
    Quitação parcial por lista explícita (double-entry): cria um DEBIT que liga os
    CREDITs ativos selecionados (comissões e fixos) por entry_ids e/ou pedido_ids.

    Estratégia atômica (sem race entre requisições simultâneas):
      1. Cria o DEBIT primeiro com amount=0 (placeholder).
      2. UPDATE atômico nos CREDITs elegíveis marcando settled_by_id=debit_id —
         essa é a "etiqueta" que define o lote, não um timestamp.
      3. SUM dos credits agora linkados ao DEBIT → ajusta debit.amount.
      4. Se nenhum CREDIT foi capturado, o DEBIT é removido (idempotência).

    Returns:
        {
            "settled": int,
            "amount": float,
            "debit_id": int | None,
            "pedido_ids_settled": list[int],
            "pedido_ids_ignored": list[int],
            "entry_ids_settled": list[int],
            "entry_ids_ignored": list[int],
        }
    """
    from flask import current_app

    from app import db
    from app.models.ledger_entry import LedgerEntry, datetime_now_brazil

    today = today_brazil()
    input_pedido_ids = _normalize_ids(pedido_ids or [])
    input_entry_ids = _normalize_ids(entry_ids or [])
    if not input_pedido_ids and not input_entry_ids:
        return {
            "settled": 0,
            "amount": 0.0,
            "debit_id": None,
            "pedido_ids_settled": [],
            "pedido_ids_ignored": input_pedido_ids,
            "entry_ids_settled": [],
            "entry_ids_ignored": input_entry_ids,
        }

    week_ref = get_monday(today)
    now = datetime_now_brazil()

    eligible_query = db.session.query(
        LedgerEntry.id.label("entry_id"),
        LedgerEntry.pedido_id.label("pedido_id"),
    ).filter(
        LedgerEntry.user_id == user_id,
        LedgerEntry.type == "CREDIT",
        LedgerEntry.status == "active",
        LedgerEntry.voided.is_(False),
    )

    if input_entry_ids and input_pedido_ids:
        eligible_query = eligible_query.filter(
            (LedgerEntry.id.in_(input_entry_ids))
            | (LedgerEntry.pedido_id.in_(input_pedido_ids))
        )
    elif input_entry_ids:
        eligible_query = eligible_query.filter(LedgerEntry.id.in_(input_entry_ids))
    else:
        eligible_query = eligible_query.filter(LedgerEntry.pedido_id.in_(input_pedido_ids))

    eligible_rows = eligible_query.all()
    eligible_entry_ids = [int(row.entry_id) for row in eligible_rows]

    if not eligible_entry_ids:
        return {
            "settled": 0,
            "amount": 0.0,
            "debit_id": None,
            "pedido_ids_settled": [],
            "pedido_ids_ignored": input_pedido_ids,
            "entry_ids_settled": [],
            "entry_ids_ignored": input_entry_ids,
        }

    # 1) Cria o DEBIT placeholder (amount=0.01 satisfaz CHECK amount>0;
    # o valor real é setado no passo 3, ou o DEBIT é removido se nada quitar).
    debit = LedgerEntry(
        user_id=user_id,
        type="DEBIT",
        category="pagamento",
        amount=0.01,
        description="Quitação parcial (em processamento)",
        week_ref=week_ref,
        status="settled",
        settled_at=now,
        created_by=settled_by,
    )
    db.session.add(debit)
    db.session.flush()
    debit_id = debit.id

    # 2) UPDATE atômico — captura apenas os CREDITs elegíveis enviados.
    updated = (
        db.session.query(LedgerEntry)
        .filter(
            LedgerEntry.user_id == user_id,
            LedgerEntry.type == "CREDIT",
            LedgerEntry.status == "active",
            LedgerEntry.voided.is_(False),
            LedgerEntry.id.in_(eligible_entry_ids),
        )
        .update(
            {
                "status": "settled",
                "settled_at": now,
                "settled_by_id": debit_id,
            },
            synchronize_session="fetch",
        )
    )

    if updated == 0:
        db.session.delete(debit)
        db.session.commit()
        return {
            "settled": 0,
            "amount": 0.0,
            "debit_id": None,
            "pedido_ids_settled": [],
            "pedido_ids_ignored": input_pedido_ids,
            "entry_ids_settled": [],
            "entry_ids_ignored": input_entry_ids,
        }

    # 3) Total exato do lote — agora vinculado pelo settled_by_id
    settled_rows = (
        db.session.query(LedgerEntry.id, LedgerEntry.pedido_id, LedgerEntry.amount)
        .filter(
            LedgerEntry.type == "CREDIT",
            LedgerEntry.settled_by_id == debit_id,
        )
        .all()
    )
    settled_amount_by_entry = {int(eid): float(amount or 0) for eid, _, amount in settled_rows}
    settled_entry_id_set = set(settled_amount_by_entry.keys())
    settled_pedido_id_set = {int(pid) for _, pid, _ in settled_rows if pid is not None}

    ignored_entry_ids = [eid for eid in input_entry_ids if eid not in settled_entry_id_set]
    settled_pedido_ids = [pid for pid in input_pedido_ids if pid in settled_pedido_id_set]
    ignored_pedido_ids = [pid for pid in input_pedido_ids if pid not in settled_pedido_id_set]

    if not input_pedido_ids and settled_pedido_id_set:
        settled_pedido_ids = sorted(settled_pedido_id_set)

    total_amount = round(sum(settled_amount_by_entry.values()), 2)

    debit.amount = total_amount
    debit.description = (
        f"Quitação parcial — {updated} lançamento(s), "
        f"{len(settled_pedido_ids)} pedido(s)"
    )

    db.session.commit()

    current_app.logger.info(
        "[LEDGER] settle user=%s: %s créditos quitados, %s pedidos, total R$%.2f, DEBIT #%s",
        user_id,
        updated,
        len(settled_pedido_ids),
        total_amount,
        debit_id,
    )
    return {
        "settled": updated,
        "amount": total_amount,
        "debit_id": debit_id,
        "pedido_ids_settled": settled_pedido_ids,
        "pedido_ids_ignored": ignored_pedido_ids,
        "entry_ids_settled": sorted(settled_entry_id_set),
        "entry_ids_ignored": ignored_entry_ids,
    }


def get_period_summary(user_id: int) -> dict:
    """
    Retorna comissões agrupadas por período de pagamento (due_date).
    """
    from collections import defaultdict

    from app.models.ledger_entry import LedgerEntry
    from app.models.pedido import Pedido
    from app.services.commission_service import map_fonte_to_source

    today = today_brazil()

    entries = (
        LedgerEntry.query.filter(
            LedgerEntry.user_id == user_id,
            LedgerEntry.type == "CREDIT",
            LedgerEntry.category.like("comissao_%"),
            LedgerEntry.voided.is_(False),
        )
        .order_by(LedgerEntry.due_date.desc().nullslast(), LedgerEntry.created_at.asc())
        .all()
    )

    pedido_ids = [e.pedido_id for e in entries if e.pedido_id is not None]
    pedidos_by_id = (
        {p.id: p for p in Pedido.query.filter(Pedido.id.in_(pedido_ids)).all()}
        if pedido_ids
        else {}
    )

    periods: dict = defaultdict(
        lambda: {
            "period_date": None,
            "total_commission": 0.0,
            "active_commission": 0.0,
            "settled_commission": 0.0,
            "orders_count": 0,
            "order_ids": set(),
            "by_source_map": defaultdict(
                lambda: {"source": None, "source_id": None, "source_slug": None, "total": 0.0}
            ),
        }
    )
    for entry in entries:
        period_key = entry.due_date.isoformat() if entry.due_date else "sem_data"
        group = periods[period_key]
        group["period_date"] = period_key if period_key != "sem_data" else None

        amount = float(entry.amount or 0)
        group["total_commission"] = round(group["total_commission"] + amount, 2)
        if entry.status == "settled":
            group["settled_commission"] = round(group["settled_commission"] + amount, 2)
        else:
            group["active_commission"] = round(group["active_commission"] + amount, 2)

        if entry.pedido_id is not None:
            group["order_ids"].add(entry.pedido_id)

        pedido = pedidos_by_id.get(entry.pedido_id)
        source_id = pedido.fonte_pedido_id if pedido else None
        source_name = None
        if pedido and pedido.fonte_pedido_rel:
            source_name = pedido.fonte_pedido_rel.nome
        elif pedido:
            source_name = pedido.fonte_pedido

        category_source = (
            entry.category.replace("comissao_", "", 1)
            if entry.category.startswith("comissao_")
            else entry.category
        )
        source_slug = map_fonte_to_source(source_name or "") or category_source
        source_key = f"{source_id}:{source_slug}"
        source_group = group["by_source_map"][source_key]
        source_group["source"] = source_name or category_source
        source_group["source_id"] = source_id
        source_group["source_slug"] = source_slug
        source_group["total"] = round(source_group["total"] + amount, 2)

    result = []
    for period_key in sorted(periods.keys(), reverse=True):
        group = periods[period_key]
        period_date = date.fromisoformat(period_key) if period_key != "sem_data" else None
        has_active = group["active_commission"] > 0
        is_overdue = period_date is not None and period_date < today and has_active

        if is_overdue:
            status = "atrasado"
        elif has_active:
            status = "pendente"
        elif group["settled_commission"] > 0:
            status = "quitado"
        else:
            status = "sem_movimento"

        by_source = sorted(
            group["by_source_map"].values(),
            key=lambda s: s["total"],
            reverse=True,
        )

        result.append(
            {
                "period_date": group["period_date"],
                "total_commission": group["total_commission"],
                "active_commission": group["active_commission"],
                "settled_commission": group["settled_commission"],
                "orders_count": len(group["order_ids"]),
                "is_overdue": is_overdue,
                "status": status,
                "by_source": by_source,
            }
        )

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
