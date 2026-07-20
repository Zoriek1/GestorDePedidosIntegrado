# -*- coding: utf-8 -*-
"""
Modelo de Lead UTM — rastreia cliques vindos da landing page (lpb.planteumaflor.com)

Dados de atribuição (UTMs, fbclid/fbp, referrer, IP) ficam SOMENTE nesta tabela.
Para consultar a origem de um pedido criado a partir de um lead, cruze pelo campo
``phone`` (telefone) e/ou ``fbclid`` entre as tabelas ``leads`` e ``pedidos``.

Consulta útil (SQL):
    SELECT l.id, l.phone, l.utm_source, l.utm_campaign, l.fbclid, l.created_at
    FROM leads l
    WHERE l.phone = '<telefone_do_pedido>'
    ORDER BY l.created_at DESC;
"""

from app import db
from app.models.pedido import datetime_now_brazil
from app.services.tenant_scope import TenantScoped


class Lead(TenantScoped, db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    # Chave de deduplicação (evita recontagem por retries/duplo clique)
    dedup_key = db.Column(db.String(64), index=True, nullable=False)
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
    phone = db.Column(db.String(30), index=True, nullable=True)
    token_rastreio = db.Column(db.String(64), index=True, nullable=True)
    token_valido = db.Column(db.Boolean, nullable=True)
    status = db.Column(db.String(50), index=True, nullable=True, default="pendente_whatsapp")
    # Subestado operacional do lead confirmado (`status='whatsapp_iniciado'`), marcado
    # pelo operador: aguardando_resposta | orcamento_enviado | sem_resposta. Etiqueta
    # pura — não dispara evento Meta nem entra no _aggregate_lead_stats.
    situacao = db.Column(db.String(30), index=True, nullable=True)
    fbclid = db.Column(db.String(255), index=True)
    fbp = db.Column(db.String(255))
    gclid = db.Column(db.String(255), index=True)
    gbraid = db.Column(db.String(255), index=True)
    wbraid = db.Column(db.String(255), index=True)
    ga_client_id = db.Column(db.String(255), index=True)
    ga_session_id = db.Column(db.String(100))
    ga_session_started_at = db.Column(db.DateTime, nullable=True)
    first_landing_url = db.Column(db.Text)
    session_referrer = db.Column(db.Text)
    cta_location = db.Column(db.String(100))
    product_id = db.Column(db.String(100))
    product_name = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, index=True)
    # Meta Pixel/CAPI: mesmo event_id por estágio para dedup browser+servidor
    meta_event_id_contact = db.Column(db.String(100), nullable=True, index=True)
    meta_event_id_lead = db.Column(db.String(100), nullable=True, index=True)
    client_user_agent = db.Column(db.String(512), nullable=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=True, index=True)
    # Followup: rastreia o último contato manual com um Lead Confirmado.
    # NULL = nunca foi feito followup. Preenchido = quem fez e quando. Permite
    # filtrar "confirmados sem followup há X dias" sem migrations futuras.
    followup_feito_em = db.Column(db.DateTime, nullable=True)
    followup_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    # Atribuição: utm_* deste lead refletem o ÚLTIMO toque pago (last non-direct).
    # first_touch_id congela o toque que descobriu o lead; last_touch_id segue
    # o toque pago mais recente. Toques diretos viram histórico mas não mexem em last.
    first_touch_id = db.Column(
        db.Integer,
        db.ForeignKey("lead_touchpoints.id", use_alter=True, name="fk_leads_first_touch"),
        nullable=True,
    )
    last_touch_id = db.Column(
        db.Integer,
        db.ForeignKey("lead_touchpoints.id", use_alter=True, name="fk_leads_last_touch"),
        nullable=True,
    )

    first_touch = db.relationship(
        "LeadTouchpoint",
        foreign_keys=[first_touch_id],
        post_update=True,
        lazy="joined",
    )
    last_touch = db.relationship(
        "LeadTouchpoint",
        foreign_keys=[last_touch_id],
        post_update=True,
        lazy="joined",
    )

    __table_args__ = (
        db.UniqueConstraint("store_ref_id", "dedup_key", name="uq_leads_store_dedup_key"),
    )

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
            "phone": self.phone,
            "token_rastreio": self.token_rastreio,
            "token_valido": self.token_valido,
            "status": self.status,
            "situacao": self.situacao,
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
            "first_landing_url": self.first_landing_url,
            "session_referrer": self.session_referrer,
            "cta_location": self.cta_location,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "meta_event_id_contact": self.meta_event_id_contact,
            "meta_event_id_lead": self.meta_event_id_lead,
            "pedido_id": self.pedido_id,
            "followup_feito_em": self.followup_feito_em.isoformat() if self.followup_feito_em else None,
            "followup_por": self.followup_por,
            "first_touch_id": self.first_touch_id,
            "last_touch_id": self.last_touch_id,
            "first_touch": self.first_touch.to_dict() if self.first_touch else None,
            "last_touch": self.last_touch.to_dict() if self.last_touch else None,
        }
