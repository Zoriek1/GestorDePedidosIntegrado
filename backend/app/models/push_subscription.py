# -*- coding: utf-8 -*-
"""
Modelo para armazenar inscrições de Push Notification (Web Push / VAPID).

Cada dispositivo que aceita notificações gera um endpoint único.
"""
from app import db
from app.models.pedido import datetime_now_brazil


class PushSubscription(db.Model):
    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    # Pedido associado (inscrição do CLIENTE, opt-in na tela de acompanhamento).
    # NULL = inscrição da EQUIPE (broadcast de novos pedidos). Os dois públicos são
    # separados por este campo para que o aviso de um não vaze para o outro.
    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(db.DateTime, default=datetime_now_brazil)

    def to_dict(self):
        return {
            "endpoint": self.endpoint,
            "p256dh": self.p256dh,
            "auth": self.auth,
            "pedido_id": self.pedido_id,
        }

    def __repr__(self):
        return f"<PushSubscription endpoint={self.endpoint[:40]}...>"
