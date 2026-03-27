# -*- coding: utf-8 -*-
"""
Outbox para eventos Meta CAPI do funil de leads (Contact + Lead).
"""

from app import db
from app.models.pedido import datetime_now_brazil


class MetaCapiLeadOutbox(db.Model):
    """
    Fila de envio Contact/Lead para Meta CAPI, com retry.
    Um registro por estágio por lead (contact | lead).
    """

    __tablename__ = "meta_capi_lead_outbox"
    __table_args__ = (
        db.UniqueConstraint("lead_id", "funnel_stage", name="uq_meta_capi_lead_outbox_lead_stage"),
    )

    id = db.Column(db.Integer, primary_key=True)

    lead_id = db.Column(
        db.Integer,
        db.ForeignKey("leads.id"),
        nullable=False,
        index=True,
    )

    funnel_stage = db.Column(
        db.String(20),
        nullable=False,
        index=True,
        comment="contact | lead",
    )

    event_id = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    event_time = db.Column(db.DateTime, nullable=False)

    payload_json = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True,
    )

    attempts = db.Column(db.Integer, nullable=False, default=0)

    last_error = db.Column(db.Text, nullable=True)

    error_type = db.Column(db.String(20), nullable=True, index=True)

    sent_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)

    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime_now_brazil)

    lead = db.relationship("Lead", backref="meta_capi_lead_outbox_entries", foreign_keys=[lead_id])
