# -*- coding: utf-8 -*-
"""Outbox da integracao Mercado Pago Point."""

import json

from app import db
from app.models.pedido import datetime_now_brazil
from app.services.tenant_scope import TenantScoped


class MercadoPagoOutbox(TenantScoped, db.Model):
    __tablename__ = "mercado_pago_outbox"
    __table_args__ = (
        db.UniqueConstraint("mp_payment_id", name="uq_mp_outbox_mp_payment_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    mp_payment_id = db.Column(db.String(80), nullable=False, index=True)
    mp_notification_id = db.Column(db.String(80), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    step = db.Column(db.String(60), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=5)
    next_retry_at = db.Column(db.DateTime, nullable=True, index=True)
    raw_webhook_json = db.Column(db.Text, nullable=True)
    payment_json = db.Column(db.Text, nullable=True)
    bling_contact_id = db.Column(db.String(80), nullable=True)
    bling_receivable_id = db.Column(db.String(80), nullable=True)
    error_code = db.Column(db.String(80), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime_now_brazil, onupdate=datetime_now_brazil
    )
    finished_at = db.Column(db.DateTime, nullable=True)

    def _json_value(self, raw):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def to_dict(self):
        return {
            "id": self.id,
            "mp_payment_id": self.mp_payment_id,
            "mp_notification_id": self.mp_notification_id,
            "status": self.status,
            "step": self.step,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "raw_webhook": self._json_value(self.raw_webhook_json),
            "payment": self._json_value(self.payment_json),
            "bling_contact_id": self.bling_contact_id,
            "bling_receivable_id": self.bling_receivable_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
