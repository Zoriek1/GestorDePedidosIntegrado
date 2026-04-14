# -*- coding: utf-8 -*-
"""
LedgerRepository — CRUD e queries do ledger de recebíveis
"""
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import func

from app import db
from app.models.ledger_entry import LedgerEntry
from app.repositories.base_repository import BaseRepository

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

TIMEZONE_BRASIL = ZoneInfo("America/Sao_Paulo")


class LedgerRepository(BaseRepository[LedgerEntry]):
    def __init__(self):
        super().__init__(LedgerEntry)

    # ------------------------------------------------------------------
    # Idempotência
    # ------------------------------------------------------------------

    def get_by_pedido_id(self, pedido_id: int) -> Optional[LedgerEntry]:
        """Verifica se já existe entry para esse pedido (previne comissão duplicada)."""
        return LedgerEntry.query.filter_by(pedido_id=pedido_id).first()

    def get_by_week_and_category(
        self, user_id: int, week_ref: date, category: str
    ) -> Optional[LedgerEntry]:
        """Verifica se já existe lançamento fixo para a semana+categoria (previne duplicação)."""
        return LedgerEntry.query.filter_by(
            user_id=user_id, week_ref=week_ref, category=category
        ).first()

    # ------------------------------------------------------------------
    # Saldo
    # ------------------------------------------------------------------

    def get_balance(self, user_id: int) -> dict:
        """
        Retorna saldo devedor separando:
        - confirmed_credits: créditos já confirmados (recebidos)
        - overdue_credits: pendentes com due_date < hoje (atrasados)
        - pending_credits: pendentes do dia (due_date == hoje) ou sem due_date
        - total_debits: débitos (pagamentos realizados)
        - balance: total_credits - total_debits
        """
        today = date.today()

        confirmed_credits = (
            db.session.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .filter(
                LedgerEntry.user_id == user_id,
                LedgerEntry.type == "CREDIT",
                LedgerEntry.status == "confirmado",
            )
            .scalar()
        )

        # Atrasado: pendente e due_date já passou
        overdue_credits = (
            db.session.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .filter(
                LedgerEntry.user_id == user_id,
                LedgerEntry.type == "CREDIT",
                LedgerEntry.status == "pendente",
                LedgerEntry.due_date < today,
            )
            .scalar()
        )

        # Pendente do dia: due_date == hoje ou sem due_date
        pending_credits = (
            db.session.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .filter(
                LedgerEntry.user_id == user_id,
                LedgerEntry.type == "CREDIT",
                LedgerEntry.status == "pendente",
                (LedgerEntry.due_date == today) | (LedgerEntry.due_date.is_(None)),
            )
            .scalar()
        )

        debits = (
            db.session.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .filter(LedgerEntry.user_id == user_id, LedgerEntry.type == "DEBIT")
            .scalar()
        )

        total_credits = float(confirmed_credits) + float(overdue_credits) + float(pending_credits)
        return {
            "total_credits": round(total_credits, 2),
            "confirmed_credits": round(float(confirmed_credits), 2),
            "overdue_credits": round(float(overdue_credits), 2),
            "pending_credits": round(float(pending_credits), 2),
            "total_debits": round(float(debits), 2),
            "balance": round(total_credits - float(debits), 2),
        }

    def get_all_balances(self) -> List[dict]:
        """Resumo de saldo de todos os vendedores (para o admin)."""
        from app.models.user import User

        vendedores = User.query.filter_by(is_active=True).all()
        result = []
        for v in vendedores:
            bal = self.get_balance(v.id)
            result.append({"user": v.to_dict(), **bal})
        return result

    # ------------------------------------------------------------------
    # Pagamentos pendentes (a confirmar pelo funcionário)
    # ------------------------------------------------------------------

    def get_pending(self, user_id: int) -> List[LedgerEntry]:
        """
        Retorna CREDITs pendentes com foco operacional:
        - Todos os atrasados (due_date < hoje)
        - Itens de hoje (due_date == hoje)
        - Itens sem due_date
        - Dos futuros, somente o próximo dia de pagamento (menor due_date > hoje)
        """
        today = date.today()
        all_pending = (
            LedgerEntry.query.filter_by(user_id=user_id, type="CREDIT", status="pendente")
            .order_by(LedgerEntry.due_date.asc().nullsfirst(), LedgerEntry.week_ref.asc())
            .all()
        )
        if not all_pending:
            return []

        overdue = [e for e in all_pending if e.due_date is not None and e.due_date < today]
        due_today = [e for e in all_pending if e.due_date == today]
        without_due_date = [e for e in all_pending if e.due_date is None]
        future = [e for e in all_pending if e.due_date is not None and e.due_date > today]

        next_future_due_date = min((e.due_date for e in future), default=None)
        next_future = [e for e in future if e.due_date == next_future_due_date] if next_future_due_date else []

        selected = overdue + due_today + without_due_date + next_future

        # Preserva ordenação por due_date, week_ref e created_at.
        return sorted(
            selected,
            key=lambda e: (
                e.due_date or date.min,
                e.week_ref or date.min,
                e.created_at or datetime.min,
            ),
        )

    def confirm_entry(self, entry_id: int, user_id: int, is_admin: bool) -> Optional[LedgerEntry]:
        """
        Marca entry como confirmada.
        - Vendedor só pode confirmar as próprias entries.
        - Admin pode confirmar qualquer entry.
        """
        entry = LedgerEntry.query.get(entry_id)
        if not entry:
            return None
        if not is_admin and entry.user_id != user_id:
            return None
        if entry.status == "confirmado":
            return entry  # idempotente
        entry.status = "confirmado"
        entry.confirmed_at = datetime.now(TIMEZONE_BRASIL)
        db.session.commit()
        return entry

    # ------------------------------------------------------------------
    # Extrato
    # ------------------------------------------------------------------

    def get_entries(
        self,
        user_id: int,
        week_ref: Optional[date] = None,
        category: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[LedgerEntry]:
        query = LedgerEntry.query.filter_by(user_id=user_id)

        if week_ref:
            query = query.filter(LedgerEntry.week_ref == week_ref)
        if category:
            query = query.filter(LedgerEntry.category == category)
        if from_date:
            query = query.filter(LedgerEntry.week_ref >= from_date)
        if to_date:
            query = query.filter(LedgerEntry.week_ref <= to_date)

        return query.order_by(LedgerEntry.week_ref.desc(), LedgerEntry.created_at.desc()).all()
