# -*- coding: utf-8 -*-
"""Credenciais OAuth da integracao Bling."""

from app import db
from app.models.pedido import datetime_now_brazil


class BlingCredential(db.Model):
    __tablename__ = "bling_credentials"

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.String(50), nullable=False, unique=True, index=True, default="default")
    access_token_encrypted = db.Column(db.Text, nullable=True)
    refresh_token_encrypted = db.Column(db.Text, nullable=True)
    token_type = db.Column(db.String(30), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    scopes = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    raw_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime_now_brazil, onupdate=datetime_now_brazil)

    def to_dict(self):
        return {
            "id": self.id,
            "store_id": self.store_id,
            "connected": bool(self.active and self.refresh_token_encrypted),
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scopes": self.scopes,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
