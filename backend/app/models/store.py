# -*- coding: utf-8 -*-
"""Identidade interna das lojas (tenants) da aplicacao."""

from app import db
from app.models.pedido import datetime_now_brazil


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(60), nullable=False, unique=True, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime_now_brazil)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime_now_brazil,
        onupdate=datetime_now_brazil,
    )

    def __repr__(self) -> str:
        return f"<Store #{self.id} slug={self.slug!r}>"
