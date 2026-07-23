# -*- coding: utf-8 -*-
"""Logs auditaveis da integracao Mercado Pago Point."""

import json

from app import db
from app.models.pedido import datetime_now_brazil


class MercadoPagoIntegrationLog(db.Model):
    __tablename__ = "mercado_pago_integration_logs"

    id = db.Column(db.Integer, primary_key=True)
    outbox_id = db.Column(
        db.Integer,
        db.ForeignKey("mercado_pago_outbox.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    level = db.Column(db.String(20), nullable=False, default="info", index=True)
    step = db.Column(db.String(60), nullable=True, index=True)
    message = db.Column(db.Text, nullable=False)
    request_json = db.Column(db.Text, nullable=True)
    response_json = db.Column(db.Text, nullable=True)
    status_code = db.Column(db.Integer, nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime_now_brazil, nullable=False, index=True
    )

    outbox = db.relationship(
        "MercadoPagoOutbox", backref="logs", foreign_keys=[outbox_id]
    )

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
            "outbox_id": self.outbox_id,
            "level": self.level,
            "step": self.step,
            "message": self.message,
            "request": self._json_value(self.request_json),
            "response": self._json_value(self.response_json),
            "status_code": self.status_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
