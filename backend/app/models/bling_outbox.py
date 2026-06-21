# -*- coding: utf-8 -*-
"""Outbox da integracao Bling."""

import json

from app import db
from app.models.pedido import datetime_now_brazil


class BlingOutbox(db.Model):
    __tablename__ = "bling_outbox"
    __table_args__ = (
        # No maximo 1 outbox por pedido/operacao: fecha o caminho de duplo-insert
        # concorrente (envio manual + worker criando o mesmo pedido no Bling).
        db.UniqueConstraint(
            "pedido_id", "operation", name="uq_bling_outbox_pedido_operation"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False, index=True)
    operation = db.Column(db.String(50), nullable=False, default="send_order", index=True)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    step = db.Column(db.String(60), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=5)
    next_retry_at = db.Column(db.DateTime, nullable=True, index=True)
    payload_json = db.Column(db.Text, nullable=True)
    response_json = db.Column(db.Text, nullable=True)
    error_code = db.Column(db.String(80), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    bling_order_id = db.Column(db.String(80), nullable=True, index=True)
    bling_order_number = db.Column(db.String(80), nullable=True)
    bling_receivable_ids_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime_now_brazil, onupdate=datetime_now_brazil)
    finished_at = db.Column(db.DateTime, nullable=True)

    pedido = db.relationship("Pedido", backref="bling_outbox_entries", foreign_keys=[pedido_id])

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
            "pedido_id": self.pedido_id,
            "operation": self.operation,
            "status": self.status,
            "step": self.step,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "payload": self._json_value(self.payload_json),
            "response": self._json_value(self.response_json),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "bling_order_id": self.bling_order_id,
            "bling_order_number": self.bling_order_number,
            "bling_receivable_ids": self._json_value(self.bling_receivable_ids_json) or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
