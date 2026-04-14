# -*- coding: utf-8 -*-
"""
LedgerRepository — CRUD e queries do ledger de recebíveis
"""
from datetime import date
from typing import List, Optional

from sqlalchemy import func

from app import db
from app.models.ledger_entry import LedgerEntry
from app.repositories.base_repository import BaseRepository


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
        """Retorna saldo devedor (quanto a empresa deve ao vendedor)."""
        credits = (
            db.session.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .filter(LedgerEntry.user_id == user_id, LedgerEntry.type == "CREDIT")
            .scalar()
        )
        debits = (
            db.session.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .filter(LedgerEntry.user_id == user_id, LedgerEntry.type == "DEBIT")
            .scalar()
        )
        return {
            "total_credits": round(float(credits), 2),
            "total_debits": round(float(debits), 2),
            "balance": round(float(credits) - float(debits), 2),
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
