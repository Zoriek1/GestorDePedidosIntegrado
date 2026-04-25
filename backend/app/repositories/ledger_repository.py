# -*- coding: utf-8 -*-
"""
LedgerRepository — CRUD e queries do ledger de recebíveis (double-entry)
"""
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import case, func

from app import db
from app.models.ledger_entry import LedgerEntry
from app.repositories.base_repository import BaseRepository
from app.utils.date_utils import today_brazil


class LedgerRepository(BaseRepository[LedgerEntry]):
    def __init__(self):
        super().__init__(LedgerEntry)

    # ------------------------------------------------------------------
    # Idempotência
    # ------------------------------------------------------------------

    def get_active_by_pedido_id(self, pedido_id: int) -> Optional[LedgerEntry]:
        """Retorna a comissão CREDIT ainda ativa (não voidada e não quitada) de um pedido."""
        return (
            LedgerEntry.query.filter(
                LedgerEntry.pedido_id == pedido_id,
                LedgerEntry.type == "CREDIT",
                LedgerEntry.status == "active",
                LedgerEntry.voided.is_(False),
            )
            .order_by(LedgerEntry.id.desc())
            .first()
        )

    # Alias para retrocompatibilidade interna: qualquer CREDIT histórico
    # ainda válido para o pedido, mesmo que já tenha sido quitado.
    def get_by_pedido_id(self, pedido_id: int) -> Optional[LedgerEntry]:
        return (
            LedgerEntry.query.filter(
                LedgerEntry.pedido_id == pedido_id,
                LedgerEntry.type == "CREDIT",
                LedgerEntry.voided.is_(False),
            )
            .order_by(LedgerEntry.id.desc())
            .first()
        )

    def get_by_week_and_category(
        self, user_id: int, week_ref: date, category: str
    ) -> Optional[LedgerEntry]:
        """Verifica se já existe lançamento fixo para a semana+categoria."""
        return LedgerEntry.query.filter_by(
            user_id=user_id, week_ref=week_ref, category=category, voided=False
        ).first()

    # ------------------------------------------------------------------
    # Saldo — lógica double-entry simplificada
    # ------------------------------------------------------------------

    def get_balance(self, user_id: int) -> dict:
        """
        Contas a receber (semântica operacional):
          active_total     = Σ(CREDIT WHERE status='active' AND voided=FALSE)
          overdue          = active_total WHERE due_date < hoje
          due_today        = active_total WHERE due_date == hoje
          upcoming         = active_total WHERE due_date > hoje (ou sem due_date)
          balance          = active_total
        """
        today = today_brazil()

        base_active = (
            db.session.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .filter(
                LedgerEntry.user_id == user_id,
                LedgerEntry.type == "CREDIT",
                LedgerEntry.status == "active",
                LedgerEntry.voided.is_(False),
            )
        )

        active_total = float(base_active.scalar())

        overdue = float(
            base_active.filter(LedgerEntry.due_date < today).scalar()
        )
        due_today = float(
            base_active.filter(LedgerEntry.due_date == today).scalar()
        )
        upcoming = float(
            base_active.filter(
                (LedgerEntry.due_date > today) | LedgerEntry.due_date.is_(None)
            ).scalar()
        )

        # ajuste_debito é puramente contábil (estorno por edição de pedido); o void
        # do CREDIT já remove o valor do saldo, então não conta como pagamento.
        total_debits = float(
            db.session.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .filter(
                LedgerEntry.user_id == user_id,
                LedgerEntry.type == "DEBIT",
                LedgerEntry.voided.is_(False),
                LedgerEntry.category != "ajuste_debito",
            )
            .scalar()
        )

        return {
            "total_credits": round(active_total, 2),
            "overdue_credits": round(overdue, 2),
            "due_today_credits": round(due_today, 2),
            "upcoming_credits": round(upcoming, 2),
            "total_debits": round(total_debits, 2),
            "balance": round(active_total, 2),
        }

    def get_all_balances(self) -> List[dict]:
        """
        Resumo de saldo de todos os vendedores ativos — query única com GROUP BY.
        Evita N+1 do loop anterior.
        """
        from app.models.user import User

        today = today_brazil()

        rows = (
            db.session.query(
                LedgerEntry.user_id,
                func.sum(
                    case(
                        (
                            (LedgerEntry.type == "CREDIT")
                            & (LedgerEntry.status == "active")
                            & ~LedgerEntry.voided,
                            LedgerEntry.amount,
                        ),
                        else_=0,
                    )
                ).label("active_total"),
                func.sum(
                    case(
                        (
                            (LedgerEntry.type == "DEBIT")
                            & ~LedgerEntry.voided
                            & (LedgerEntry.category != "ajuste_debito"),
                            LedgerEntry.amount,
                        ),
                        else_=0,
                    )
                ).label("total_debits"),
                func.sum(
                    case(
                        (
                            (LedgerEntry.type == "CREDIT")
                            & (LedgerEntry.status == "active")
                            & ~LedgerEntry.voided
                            & (LedgerEntry.due_date < today),
                            LedgerEntry.amount,
                        ),
                        else_=0,
                    )
                ).label("overdue"),
            )
            .group_by(LedgerEntry.user_id)
            .all()
        )

        balances_by_user = {
            r.user_id: {
                "total_credits": round(float(r.active_total), 2),
                "overdue_credits": round(float(r.overdue), 2),
                "total_debits": round(float(r.total_debits), 2),
                "balance": round(float(r.active_total), 2),
            }
            for r in rows
        }

        vendedores = User.query.filter_by(is_active=True).all()
        result = []
        for v in vendedores:
            bal = balances_by_user.get(v.id, {
                "total_credits": 0.0,
                "overdue_credits": 0.0,
                "total_debits": 0.0,
                "balance": 0.0,
            })
            result.append({"user": v.to_dict(), **bal})
        return result

    # ------------------------------------------------------------------
    # Pagamentos pendentes (CREDITs active)
    # ------------------------------------------------------------------

    def get_pending(self, user_id: int) -> List[LedgerEntry]:
        """
        Retorna CREDITs active com foco operacional:
        - Todos os atrasados (due_date < hoje)
        - Itens de hoje (due_date == hoje)
        - Itens sem due_date
        - Dos futuros, somente o próximo dia de pagamento (menor due_date > hoje)
        """
        today = today_brazil()
        all_active = (
            LedgerEntry.query.filter(
                LedgerEntry.user_id == user_id,
                LedgerEntry.type == "CREDIT",
                LedgerEntry.status == "active",
                LedgerEntry.voided.is_(False),
            )
            .order_by(LedgerEntry.due_date.asc().nullsfirst(), LedgerEntry.week_ref.asc())
            .all()
        )
        if not all_active:
            return []

        overdue = [e for e in all_active if e.due_date is not None and e.due_date < today]
        due_today = [e for e in all_active if e.due_date == today]
        without_due = [e for e in all_active if e.due_date is None]
        future = [e for e in all_active if e.due_date is not None and e.due_date > today]

        next_due = min((e.due_date for e in future), default=None)
        next_future = [e for e in future if e.due_date == next_due] if next_due else []

        selected = overdue + due_today + without_due + next_future
        return sorted(
            selected,
            key=lambda e: (
                e.due_date or date.min,
                e.week_ref or date.min,
                e.created_at or datetime.min,
            ),
        )

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
        query = LedgerEntry.query.filter(
            LedgerEntry.user_id == user_id,
            LedgerEntry.voided.is_(False),
        )

        if week_ref:
            query = query.filter(LedgerEntry.week_ref == week_ref)
        if category:
            query = query.filter(LedgerEntry.category == category)
        if from_date:
            query = query.filter(LedgerEntry.week_ref >= from_date)
        if to_date:
            query = query.filter(LedgerEntry.week_ref <= to_date)

        return query.order_by(LedgerEntry.week_ref.desc(), LedgerEntry.created_at.desc()).all()
