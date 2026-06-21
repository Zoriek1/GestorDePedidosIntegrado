# -*- coding: utf-8 -*-
"""Logs auditaveis da integracao Bling."""

import json

from app import db
from app.models.pedido import datetime_now_brazil


class BlingIntegrationLog(db.Model):
    __tablename__ = "bling_integration_logs"

    id = db.Column(db.Integer, primary_key=True)
    outbox_id = db.Column(db.Integer, db.ForeignKey("bling_outbox.id"), nullable=True, index=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=True, index=True)
    level = db.Column(db.String(20), nullable=False, default="info", index=True)
    step = db.Column(db.String(60), nullable=True, index=True)
    message = db.Column(db.Text, nullable=False)
    request_json = db.Column(db.Text, nullable=True)
    response_json = db.Column(db.Text, nullable=True)
    status_code = db.Column(db.Integer, nullable=True)
    error_code = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False, index=True)

    outbox = db.relationship("BlingOutbox", backref="logs", foreign_keys=[outbox_id])

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
            "pedido_id": self.pedido_id,
            "level": self.level,
            "step": self.step,
            "message": self.message,
            "request": self._json_value(self.request_json),
            "response": self._json_value(self.response_json),
            "status_code": self.status_code,
            "error_code": self.error_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
