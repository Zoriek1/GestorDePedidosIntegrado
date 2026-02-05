# -*- coding: utf-8 -*-
"""
Modelo para armazenar tokens e dados da loja Nuvemshop.
"""

from app import db
from app.models.pedido import datetime_now_brazil


class NuvemshopStore(db.Model):
    __tablename__ = "nuvemshop_stores"

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.String(50), unique=True, index=True, nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    installed_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    uninstalled_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<NuvemshopStore #{self.store_id} active={self.active}>"
