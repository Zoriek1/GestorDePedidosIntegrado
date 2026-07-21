# -*- coding: utf-8 -*-
"""
Modelo para armazenar entregas de webhooks Nuvemshop.
"""

from app import db
from app.models.pedido import datetime_now_brazil


class NuvemshopWebhookDelivery(db.Model):
    __tablename__ = "nuvemshop_webhook_deliveries"

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.String(50), index=True, nullable=False)
    store_ref_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id", name="fk_nuvemshop_deliveries_store_ref_id_stores"),
        nullable=True,
        index=True,
    )
    event = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.String(80), index=True, nullable=True)

    raw_body = db.Column(db.Text, nullable=False)
    headers_json = db.Column(db.Text, nullable=True)
    order_json = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default="pending", nullable=False)
    last_error = db.Column(db.Text, nullable=True)

    received_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    processed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<NuvemshopWebhookDelivery #{self.id} event={self.event} status={self.status}>"
