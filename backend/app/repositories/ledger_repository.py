# -*- coding: utf-8 -*-
"""
LedgerRepository — CRUD e queries do ledger de recebíveis (double-entry)
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func

from app import db
from app.models.fonte_pedido import FontePedido
from app.models.ledger_entry import LedgerEntry
from app.models.pedido import Pedido
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

    @staticmethod
    def _competencia_key(competence_date: date, competencia_tipo: str) -> str:
        if competencia_tipo == "mensal":
            return competence_date.strftime("%Y-%m")
        iso = competence_date.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    @staticmethod
    def _coerce_date(value: Any, fallback: date) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return fallback

    @staticmethod
    def _coerce_float(value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0

    def get_pending_sections(
        self,
        user_id: int,
        competencia_tipo: str = "semanal",
        competencia: Optional[str] = None,
        include_quitados: bool = False,
    ) -> Dict[str, Any]:
        """
        Retorna comissões de pedidos seccionadas por status de UI:
          - atrasado: status='active' e data de competência < hoje
          - a_receber: status='active' e na competência selecionada
          - quitado: status='settled' (somente se include_quitados=True)

        Regras:
          - somente CREDIT de comissão com pedido_id
          - atrasados sempre retornam (independem da competência)
          - quitados não entram no payload padrão
        """
        competencia_tipo = (competencia_tipo or "semanal").strip().lower()
        if competencia_tipo not in {"semanal", "mensal"}:
            competencia_tipo = "semanal"

        today = today_brazil()
        if not competencia:
            competencia = self._competencia_key(today, competencia_tipo)

        query = (
            db.session.query(
                LedgerEntry.id.label("ledger_entry_id"),
                LedgerEntry.user_id,
                LedgerEntry.pedido_id,
                LedgerEntry.amount,
                LedgerEntry.category,
                LedgerEntry.week_ref,
                LedgerEntry.due_date,
                LedgerEntry.status.label("ledger_status"),
                LedgerEntry.created_at,
                Pedido.cliente,
                Pedido.dia_entrega,
                Pedido.fonte_pedido,
                FontePedido.nome.label("fonte_nome"),
            )
            .join(Pedido, Pedido.id == LedgerEntry.pedido_id)
            .outerjoin(FontePedido, FontePedido.id == Pedido.fonte_pedido_id)
            .filter(
                LedgerEntry.user_id == user_id,
                LedgerEntry.type == "CREDIT",
                LedgerEntry.voided.is_(False),
                LedgerEntry.category.like("comissao_%"),
                LedgerEntry.pedido_id.isnot(None),
            )
        )
        if not include_quitados:
            query = query.filter(LedgerEntry.status == "active")

        rows = query.all()

        classified = []
        competencias_a_receber = set()

        for row in rows:
            competence_date = (
                row.due_date
                or row.week_ref
                or self._coerce_date(row.created_at, today)
            )
            competencia_key = self._competencia_key(competence_date, competencia_tipo)

            if row.ledger_status == "settled":
                status_ui = "quitado"
            elif competence_date < today:
                status_ui = "atrasado"
            else:
                status_ui = "a_receber"

            if status_ui == "a_receber":
                competencias_a_receber.add(competencia_key)

            classified.append(
                {
                    "ledger_entry_id": row.ledger_entry_id,
                    "pedido_id": row.pedido_id,
                    "cliente": row.cliente,
                    "fonte": row.fonte_nome or row.fonte_pedido,
                    "dia_entrega": row.dia_entrega.isoformat() if row.dia_entrega else None,
                    "due_date": row.due_date.isoformat() if row.due_date else None,
                    "week_ref": row.week_ref.isoformat() if row.week_ref else None,
                    "amount": self._coerce_float(row.amount),
                    "category": row.category,
                    "status": status_ui,
                    "competencia": competencia_key,
                    "_competence_date": competence_date,
                }
            )

        scoped = []
        for item in classified:
            if item["status"] == "atrasado":
                scoped.append(item)
                continue
            if item["status"] == "a_receber" and item["competencia"] == competencia:
                scoped.append(item)
                continue
            if include_quitados and item["status"] == "quitado":
                scoped.append(item)

        sections: Dict[str, Dict[str, Any]] = {
            "atrasado": {"total": 0.0, "total_pedidos": 0, "pedidos": []},
            "a_receber": {"total": 0.0, "total_pedidos": 0, "pedidos": []},
            "quitado": {"total": 0.0, "total_pedidos": 0, "pedidos": []},
        }

        scoped_sorted = sorted(
            scoped,
            key=lambda x: (x["_competence_date"], x["ledger_entry_id"]),
        )

        for item in scoped_sorted:
            sec = sections[item["status"]]
            sec["total"] = round(sec["total"] + item["amount"], 2)
            sec["total_pedidos"] += 1
            payload_item = {k: v for k, v in item.items() if not k.startswith("_")}
            sec["pedidos"].append(payload_item)

        if not include_quitados:
            sections["quitado"] = {"total": 0.0, "total_pedidos": 0, "pedidos": []}

        competencias_disponiveis = sorted(competencias_a_receber, reverse=True)

        return {
            "competencia_tipo": competencia_tipo,
            "competencia": competencia,
            "competencias_disponiveis": competencias_disponiveis,
            "atrasado": sections["atrasado"],
            "a_receber": sections["a_receber"],
            "quitado": sections["quitado"],
        }

    def get_pending(self, user_id: int) -> List[LedgerEntry]:
        """
        Retorna CREDITs active com foco na semana corrente:
        - Todos os atrasados (due_date < hoje)
        - Itens de hoje (due_date == hoje)
        - Itens sem due_date
        - Futuros desta semana (hoje < due_date < próxima segunda)

        Valores agendados para a próxima semana ou além NÃO entram aqui — eles
        aparecem em outras telas (extrato/períodos), mas não devem somar no
        "A Receber" desta semana.
        """
        from datetime import timedelta

        today = today_brazil()
        # Próxima segunda-feira (limite superior exclusivo do "current week")
        next_monday = today + timedelta(days=(7 - today.weekday()))

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
        future_this_week = [
            e
            for e in all_active
            if e.due_date is not None and today < e.due_date < next_monday
        ]

        selected = overdue + due_today + without_due + future_this_week
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
