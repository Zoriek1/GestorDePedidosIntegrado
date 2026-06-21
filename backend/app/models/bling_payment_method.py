# -*- coding: utf-8 -*-
"""Cache read-only de formas de pagamento do Bling."""

from app import db
from app.models.pedido import datetime_now_brazil


class BlingPaymentMethod(db.Model):
    __tablename__ = "bling_payment_methods"

    id = db.Column(db.Integer, primary_key=True)
    bling_id = db.Column(db.String(80), nullable=False, unique=True, index=True)
    nome = db.Column(db.String(160), nullable=False, index=True)
    tipo = db.Column(db.String(120), nullable=True)
    finalidade = db.Column(db.String(80), nullable=True)
    destino = db.Column(db.String(120), nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    raw_json = db.Column(db.Text, nullable=True)
    synced_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime_now_brazil, onupdate=datetime_now_brazil)

    def to_dict(self):
        return {
            "id": self.id,
            "bling_id": self.bling_id,
            "nome": self.nome,
            "tipo": self.tipo,
            "finalidade": self.finalidade,
            "destino": self.destino,
            "ativo": self.ativo,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
