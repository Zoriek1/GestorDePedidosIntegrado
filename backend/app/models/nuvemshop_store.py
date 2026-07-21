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
    store_ref_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "stores.id",
            name="fk_nuvemshop_stores_store_ref_id_stores",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )
    access_token = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    default_vendedor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    installed_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    uninstalled_at = db.Column(db.DateTime, nullable=True)
    default_vendedor = db.relationship("User", foreign_keys=[default_vendedor_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<NuvemshopStore #{self.store_id} active={self.active}>"

    @property
    def decrypted_token(self) -> str | None:
        from app.integrations.nuvemshop.token_service import decrypt_token
        return decrypt_token(self.access_token)
