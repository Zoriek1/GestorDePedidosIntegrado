# -*- coding: utf-8 -*-
"""
Outbox unificado para eventos de marketing (Meta CAPI + GA4).

Substitui progressivamente:
  - meta_capi_outbox (Purchase)
  - meta_capi_lead_outbox (Contact/Lead/Disqualified)
  - marketing_conversion_outbox (GA4 Purchase)

Dual-write: as tabelas antigas continuam sendo lidas pelo worker até esvaziarem.
"""

from app import db
from app.models.pedido import datetime_now_brazil
from app.services.tenant_scope import TenantScoped


class EventsOutbox(TenantScoped, db.Model):
    __tablename__ = "events_outbox"

    id = db.Column(db.Integer, primary_key=True)

    lead_id = db.Column(
        db.Integer, db.ForeignKey("leads.id"), nullable=True, index=True
    )
    pedido_id = db.Column(
        db.Integer, db.ForeignKey("pedidos.id"), nullable=True, index=True
    )

    destino = db.Column(db.String(30), nullable=False, index=True)
    evento = db.Column(db.String(80), nullable=False)
    dedup_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    event_time = db.Column(db.DateTime, nullable=False)
    payload_json = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    error_type = db.Column(db.String(20), nullable=True, index=True)
    last_error = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime_now_brazil)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime_now_brazil)

    pedido = db.relationship("Pedido", foreign_keys=[pedido_id])
    lead = db.relationship("Lead", foreign_keys=[lead_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "pedido_id": self.pedido_id,
            "destino": self.destino,
            "evento": self.evento,
            "dedup_key": self.dedup_key,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "status": self.status,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
