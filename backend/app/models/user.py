# -*- coding: utf-8 -*-
"""
Models de Usuário, Configuração de Remuneração e Comissão
Parte do módulo de Recebíveis
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


class User(db.Model):
    """Usuário do sistema com suporte a múltiplos roles"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, comment="Nome de exibição")
    email = db.Column(
        db.String(200), unique=True, nullable=False, index=True, comment="Email de login"
    )
    # Multi-tenant (Fase A): loja à qual o usuário pertence. Nullable durante o rollout;
    # NOT NULL e unique composto (store_ref_id, email) ficam para fase posterior.
    store_ref_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "stores.id",
            name="fk_users_store_ref_id_stores",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
        comment="Loja (tenant) do usuário; resolve identidade autenticada",
    )
    password_hash = db.Column(db.String(256), nullable=False, comment="bcrypt hash")
    role = db.Column(
        db.String(20),
        nullable=False,
        default="vendedor",
        comment="admin | vendedor | atendente | entregador | viewer",
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True, comment="Soft-disable")
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime_now_brazil, onupdate=datetime_now_brazil, nullable=False
    )

    # Relationships
    payroll_configs = db.relationship(
        "PayrollConfig", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    commission_configs = db.relationship(
        "CommissionConfig", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    ledger_entries = db.relationship(
        "LedgerEntry",
        foreign_keys="LedgerEntry.user_id",
        backref="user",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<User #{self.id} {self.email} ({self.role})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "store_ref_id": self.store_ref_id,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }


class PayrollConfig(db.Model):
    """Configuração de remuneração fixa por vendedor"""

    __tablename__ = "payroll_config"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category = db.Column(
        db.String(50),
        nullable=False,
        comment="fixo_semanal | fixo_mensal | almoco | transporte | custom",
    )
    label = db.Column(db.String(100), nullable=False, comment="Nome de exibição")
    amount = db.Column(db.Float, nullable=False, comment="Valor em R$")
    frequency = db.Column(db.String(20), nullable=False, comment="semanal | mensal")
    payment_day = db.Column(
        db.Integer,
        nullable=True,
        comment="Dia de pagamento: 0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex, 5=Sáb, 6=Dom (só p/ semanal)",
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            "payment_day IS NULL OR (payment_day BETWEEN 0 AND 6)",
            name="ck_payroll_payment_day_range",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category,
            "label": self.label,
            "amount": self.amount,
            "frequency": self.frequency,
            "payment_day": self.payment_day,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }


class CommissionConfig(db.Model):
    """Configuração de comissão por fonte de pedido por vendedor"""

    __tablename__ = "commission_config"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    fonte_pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("fontes_pedido.id"),
        nullable=True,
        index=True,
        comment="Fonte real vinculada à configuração (preferencial)",
    )
    source = db.Column(
        db.String(50),
        nullable=False,
        comment="whatsapp | site | balcao | indicacao | lucro_bruto",
    )
    rate = db.Column(db.Float, nullable=False, comment="Percentual como decimal (0.03 = 3%)")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    fonte_pedido = db.relationship("FontePedido", lazy="joined")

    __table_args__ = (
        db.CheckConstraint("rate >= 0", name="ck_commission_rate_nonneg"),
        db.Index(
            "ux_comm_user_fonte_active",
            "user_id",
            "fonte_pedido_id",
            unique=True,
            sqlite_where=db.text("is_active = 1 AND fonte_pedido_id IS NOT NULL"),
        ),
        db.Index(
            "ux_comm_user_source_active",
            "user_id",
            "source",
            unique=True,
            sqlite_where=db.text("is_active = 1 AND fonte_pedido_id IS NULL AND source <> ''"),
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "fonte_pedido_id": self.fonte_pedido_id,
            "fonte_nome": self.fonte_pedido.nome if self.fonte_pedido else None,
            "source": self.source,
            "rate": self.rate,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }
