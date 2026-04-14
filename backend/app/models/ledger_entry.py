# -*- coding: utf-8 -*-
"""
Model de Lançamento no Ledger de Recebíveis
Conta corrente entre vendedor e empresa
"""
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from app import db

TIMEZONE_BRASIL = ZoneInfo("America/Sao_Paulo")


def datetime_now_brazil():
    return datetime.now(TIMEZONE_BRASIL)


# Categorias válidas
CREDIT_CATEGORIES = {
    "fixo_semanal",
    "fixo_mensal",
    "almoco",
    "transporte",
    "comissao_whatsapp",
    "comissao_site",
    "comissao_balcao",
    "comissao_indicacao",
    "comissao_lucro",
    "custom_credit",
}
DEBIT_CATEGORIES = {
    "pagamento",
    "adiantamento",
    "ajuste_debito",
}
ALL_CATEGORIES = CREDIT_CATEGORIES | DEBIT_CATEGORIES


class LedgerEntry(db.Model):
    """Lançamento no ledger de recebíveis do vendedor"""

    __tablename__ = "ledger_entry"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="Vendedor dono do saldo",
    )
    type = db.Column(db.String(10), nullable=False, comment="CREDIT | DEBIT")
    category = db.Column(db.String(50), nullable=False, comment="Ver CREDIT/DEBIT_CATEGORIES")
    amount = db.Column(db.Float, nullable=False, comment="Sempre positivo")
    description = db.Column(db.Text, nullable=True, comment="Anotação livre")
    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=True,
        unique=True,  # Idempotência: um pedido gera no máximo uma comissão
        comment="Só para comissões — UNIQUE garante idempotência",
    )
    week_ref = db.Column(
        db.Date,
        nullable=False,
        index=True,
        comment="Segunda-feira da semana de referência",
    )
    due_date = db.Column(
        db.Date,
        nullable=True,
        comment="Data prevista de pagamento (semana + payment_day)",
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pendente",
        comment="pendente | confirmado — funcionário confirma recebimento",
    )
    confirmed_at = db.Column(db.DateTime, nullable=True, comment="Quando o funcionário confirmou")
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        comment="Quem lançou",
    )

    # Índice composto para consultas por semana
    __table_args__ = (
        db.Index("ix_ledger_user_week", "user_id", "week_ref"),
    )

    def __repr__(self):
        return f"<LedgerEntry #{self.id} {self.type} {self.category} R${self.amount:.2f}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "category": self.category,
            "amount": round(self.amount, 2),
            "description": self.description or "",
            "pedido_id": self.pedido_id,
            "week_ref": self.week_ref.strftime("%Y-%m-%d") if self.week_ref else "",
            "due_date": self.due_date.strftime("%Y-%m-%d") if self.due_date else None,
            "status": self.status,
            "confirmed_at": self.confirmed_at.strftime("%Y-%m-%d %H:%M:%S") if self.confirmed_at else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "created_by": self.created_by,
        }
