# -*- coding: utf-8 -*-
"""
Modelo de Lead UTM — rastreia cliques vindos da landing page (lpb.planteumaflor.com)
"""

from app import db
from app.models.pedido import datetime_now_brazil


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    # Chave de deduplicação (evita recontagem por retries/duplo clique)
    dedup_key = db.Column(db.String(64), unique=True, index=True, nullable=False)
    event = db.Column(db.String(50), index=True)
    url = db.Column(db.Text)
    referrer = db.Column(db.Text)
    utm_source = db.Column(db.String(100), index=True)
    utm_medium = db.Column(db.String(100))
    utm_campaign = db.Column(db.String(100), index=True)
    utm_content = db.Column(db.String(100))
    utm_term = db.Column(db.String(100))
    src = db.Column(db.String(100))
    sck = db.Column(db.String(200))
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "dedup_key": self.dedup_key,
            "event": self.event,
            "url": self.url,
            "referrer": self.referrer,
            "utm_source": self.utm_source,
            "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign,
            "utm_content": self.utm_content,
            "utm_term": self.utm_term,
            "src": self.src,
            "sck": self.sck,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
