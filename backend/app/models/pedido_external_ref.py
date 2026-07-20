# -*- coding: utf-8 -*-
"""
Vinculo entre pedido interno e fonte externa (ex: Nuvemshop).
"""

from sqlalchemy import Index, text

from app import db
from app.models.pedido import datetime_now_brazil
from app.services.tenant_scope import TenantScoped


class PedidoExternalRef(TenantScoped, db.Model):
    __tablename__ = "pedido_external_refs"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), index=True, nullable=False)
    store_id = db.Column(db.String(50), index=True, nullable=False)
    external_order_id = db.Column(db.String(80), index=True, nullable=False)
    external_order_number = db.Column(db.String(50), nullable=True)
    order_token = db.Column(db.String(100), nullable=True)

    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), index=True, nullable=False)

    schedule_pending = db.Column(db.Boolean, default=False, nullable=False)

    # Rastreamento da origem do agendamento
    agendamento_source = db.Column(
        db.String(50),
        nullable=True,
        comment="Origem do agendamento: custom_fields, attributes, extra, shipping_option, fallback",
    )
    needs_review = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="True se agendamento veio de fallback e precisa revisão",
    )

    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime_now_brazil, onupdate=datetime_now_brazil)

    __table_args__ = (
        db.UniqueConstraint(
            "store_ref_id",
            "provider",
            "store_id",
            "external_order_id",
            name="uq_pedido_external_tenant_provider_store_order",
        ),
        Index(
            "uq_pedido_external_legacy_provider_store_order",
            "provider",
            "store_id",
            "external_order_id",
            unique=True,
            sqlite_where=text("store_ref_id IS NULL"),
            postgresql_where=text("store_ref_id IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PedidoExternalRef {self.provider} store={self.store_id} "
            f"order={self.external_order_id} pedido_id={self.pedido_id}>"
        )
