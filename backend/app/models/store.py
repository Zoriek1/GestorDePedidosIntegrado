# -*- coding: utf-8 -*-
"""Identidade interna das lojas (tenants) da aplicacao."""

from app import db
from app.models.pedido import datetime_now_brazil


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(60), nullable=False, unique=True, index=True)
    # Dominio de e-mail da loja: resolve o tenant no login (maria@floriculturax.com
    # -> loja X). Nullable enquanto houver loja sem dominio proprio; nesse caso o
    # login cai na busca global (compat). Sempre gravado em minusculas.
    email_domain = db.Column(db.String(120), nullable=True, unique=True, index=True)
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
