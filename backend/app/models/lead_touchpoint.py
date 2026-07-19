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
    gclid: str | None = None,
    gbraid: str | None = None,
    wbraid: str | None = None,
) -> bool:
    if fbclid or gclid or gbraid or wbraid:
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
    gclid = db.Column(db.String(255))
    gbraid = db.Column(db.String(255))
    wbraid = db.Column(db.String(255))
    ga_client_id = db.Column(db.String(255))
    ga_session_id = db.Column(db.String(100))
    ga_session_started_at = db.Column(db.DateTime, nullable=True)
    referrer = db.Column(db.Text)
    url = db.Column(db.Text)
    # Camada de sessão da LP (sessionStorage): primeira URL e referrer DESTA sessão.
    # Diagnóstico de perda de UTM — distingue "URL tinha utm mas campanha veio branca"
    # (storage sandboxed em webview) de teoria Apple/iOS. Ver rota /api/leads.
    first_landing_url = db.Column(db.Text)
    session_referrer = db.Column(db.Text)
    cta_location = db.Column(db.String(100))
    product_id = db.Column(db.String(100))
    product_name = db.Column(db.String(255))
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
            "gclid": self.gclid,
            "gbraid": self.gbraid,
            "wbraid": self.wbraid,
            "ga_client_id": self.ga_client_id,
            "ga_session_id": self.ga_session_id,
            "ga_session_started_at": (
                self.ga_session_started_at.isoformat() if self.ga_session_started_at else None
            ),
            "referrer": self.referrer,
            "url": self.url,
            "first_landing_url": self.first_landing_url,
            "session_referrer": self.session_referrer,
            "cta_location": self.cta_location,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "ip_address": self.ip_address,
            "is_paid": bool(self.is_paid),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
