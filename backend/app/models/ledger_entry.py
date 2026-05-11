# -*- coding: utf-8 -*-
"""
Model de Lançamento no Ledger de Recebíveis
Conta corrente entre vendedor e empresa — double-entry clássico
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
    "taxa_entrega",
}
DEBIT_CATEGORIES = {
    "pagamento",
    "adiantamento",
    "ajuste_debito",
}
ALL_CATEGORIES = CREDIT_CATEGORIES | DEBIT_CATEGORIES


class LedgerEntry(db.Model):
    """
    Lançamento no ledger de recebíveis do vendedor.

    Double-entry: todo pagamento gera um DEBIT que quita um lote de CREDITs active.
    CREDIT nasce com status='active'; vira 'settled' quando o DEBIT de quitação é criado.
    DEBIT nasce diretamente com status='settled'.
    """

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
    amount = db.Column(db.Numeric(12, 2), nullable=False, comment="Sempre positivo")
    description = db.Column(db.Text, nullable=True, comment="Anotação livre")
    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=True,
        # UNIQUE removido — substituído por índice parcial WHERE voided=0 no migration script
        comment="Só para comissões — índice parcial garante idempotência por pedido ativo",
    )
    delivery_pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=True,
        comment="Só para CREDIT de taxa_entrega — idempotência por pedido entregue (entregador)",
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
        default="active",
        comment="active | settled",
    )
    settled_at = db.Column(db.DateTime, nullable=True, comment="Quando foi quitado")
    settled_by_id = db.Column(
        db.Integer,
        db.ForeignKey("ledger_entry.id"),
        nullable=True,
        comment="DEBIT que quitou este CREDIT (NULL para DEBITs ou CREDITs ainda active)",
    )
    voided = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="TRUE quando estornado por edição de pedido",
    )
    void_reason = db.Column(
        db.String(50),
        nullable=True,
        comment="Motivo do void: status_regression, soft_delete, edit_estorno",
    )
    commission_rate = db.Column(
        db.Numeric(5, 4),
        nullable=True,
        comment="Snapshot da rate usada (CREDIT de comissão); preserva config histórica",
    )
    commission_source = db.Column(
        db.String(50),
        nullable=True,
        comment="Snapshot do source usado (CREDIT de comissão)",
    )
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        comment="Quem lançou",
    )

    __table_args__ = (
        db.Index("ix_ledger_user_week", "user_id", "week_ref"),
        db.Index(
            "uq_ledger_pedido_active",
            "pedido_id",
            unique=True,
            sqlite_where=db.text("voided=0 AND pedido_id IS NOT NULL"),
            postgresql_where=db.text("voided = FALSE AND pedido_id IS NOT NULL"),
        ),
        db.Index(
            "uq_ledger_delivery_pedido_active",
            "delivery_pedido_id",
            unique=True,
            sqlite_where=db.text("voided=0 AND delivery_pedido_id IS NOT NULL"),
            postgresql_where=db.text("voided = FALSE AND delivery_pedido_id IS NOT NULL"),
        ),
        db.Index(
            "uq_ledger_weekly_active",
            "user_id",
            "week_ref",
            "category",
            unique=True,
            sqlite_where=db.text(
                "voided=0 AND week_ref IS NOT NULL "
                "AND category IN ('fixo_semanal','almoco','transporte')"
            ),
            postgresql_where=db.text(
                "voided = FALSE AND week_ref IS NOT NULL "
                "AND category IN ('fixo_semanal','almoco','transporte')"
            ),
        ),
        db.CheckConstraint("type IN ('CREDIT', 'DEBIT')", name="ck_ledger_type"),
        db.CheckConstraint("status IN ('active', 'settled')", name="ck_ledger_status"),
        db.CheckConstraint("amount > 0", name="ck_ledger_amount_positive"),
    )

    def __repr__(self):
        return f"<LedgerEntry #{self.id} {self.type} {self.category} R${self.amount}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "category": self.category,
            "amount": float(self.amount),
            "description": self.description or "",
            "pedido_id": self.pedido_id,
            "delivery_pedido_id": self.delivery_pedido_id,
            "week_ref": self.week_ref.strftime("%Y-%m-%d") if self.week_ref else "",
            "due_date": self.due_date.strftime("%Y-%m-%d") if self.due_date else None,
            "status": self.status,
            "settled_at": self.settled_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.settled_at
            else None,
            "settled_by_id": self.settled_by_id,
            "voided": self.voided,
            "void_reason": self.void_reason,
            "commission_rate": float(self.commission_rate) if self.commission_rate is not None else None,
            "commission_source": self.commission_source,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "created_by": self.created_by,
        }
