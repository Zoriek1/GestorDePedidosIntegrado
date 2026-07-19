# -*- coding: utf-8 -*-
"""Outbox idempotente para conversoes GA4 e Google Ads Data Manager."""

from app import db
from app.models.pedido import datetime_now_brazil


class MarketingConversionOutbox(db.Model):
    __tablename__ = "marketing_conversion_outbox"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False, index=True)
    destino = db.Column(db.String(30), nullable=False, index=True)
    evento = db.Column(db.String(80), nullable=False)
    transaction_id = db.Column(db.String(100), nullable=False, index=True)
    event_time = db.Column(db.DateTime, nullable=False)
    payload_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    request_id = db.Column(db.String(255), nullable=True, index=True)
    last_http_status = db.Column(db.Integer, nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime_now_brazil)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime_now_brazil)

    __table_args__ = (
        db.UniqueConstraint(
            "pedido_id", "destino", "evento", name="uq_marketing_outbox_pedido_destino_evento"
        ),
    )

    pedido = db.relationship("Pedido", foreign_keys=[pedido_id])
    lead = db.relationship("Lead", foreign_keys=[lead_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pedido_id": self.pedido_id,
            "lead_id": self.lead_id,
            "destino": self.destino,
            "evento": self.evento,
            "transaction_id": self.transaction_id,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "status": self.status,
            "attempts": self.attempts,
            "request_id": self.request_id,
            "last_http_status": self.last_http_status,
            "last_error": self.last_error,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
