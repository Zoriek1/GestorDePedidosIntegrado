# -*- coding: utf-8 -*-
"""
Histórico de toques (touchpoints) por lead — atribuição last non-direct.

Cada hit em /api/leads cria uma linha aqui com a UTM bag inteira do toque.
Lead.utm_* mantém o ÚLTIMO TOQUE PAGO (last non-direct). Toques diretos /
orgânicos viram parte do histórico mas não atualizam o lead — quem esquentou
a venda continua com o crédito.

is_paid é derivado na escrita pela presença de fbclid, utm_id, ou utm_medium
em PAID_MEDIUMS.
"""
from app import db
from app.models.pedido import datetime_now_brazil

PAID_MEDIUMS = frozenset({"paid_social", "paidsocial", "cpc", "ppc", "paid", "ads", "paidsearch"})


def derive_is_paid(
    *,
    utm_medium: str | None,
    fbclid: str | None,
    utm_id: str | None,
) -> bool:
    if fbclid:
        return True
    if utm_id:
        return True
    if utm_medium and utm_medium.strip().lower() in PAID_MEDIUMS:
        return True
    return False


class LeadTouchpoint(db.Model):
    __tablename__ = "lead_touchpoints"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(
        db.Integer,
        db.ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    utm_source = db.Column(db.String(100))
    utm_medium = db.Column(db.String(100))
    utm_campaign = db.Column(db.String(100))
    utm_content = db.Column(db.String(100))
    utm_term = db.Column(db.String(100))
    utm_id = db.Column(db.String(100))
    src = db.Column(db.String(100))
    placement = db.Column(db.String(100))
    sck = db.Column(db.String(200))
    fbclid = db.Column(db.String(255))
    fbp = db.Column(db.String(255))
    referrer = db.Column(db.Text)
    url = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    client_user_agent = db.Column(db.String(512))
    is_paid = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, index=True, nullable=False)

    __table_args__ = (db.Index("ix_lead_touchpoints_lead_created", "lead_id", "created_at"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "utm_source": self.utm_source,
            "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign,
            "utm_content": self.utm_content,
            "utm_term": self.utm_term,
            "utm_id": self.utm_id,
            "src": self.src,
            "placement": self.placement,
            "sck": self.sck,
            "fbclid": self.fbclid,
            "fbp": self.fbp,
            "referrer": self.referrer,
            "url": self.url,
            "ip_address": self.ip_address,
            "is_paid": bool(self.is_paid),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
