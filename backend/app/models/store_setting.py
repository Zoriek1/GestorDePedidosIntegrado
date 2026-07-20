# -*- coding: utf-8 -*-
"""Configuracoes e credenciais de integracao pertencentes a uma loja."""

from app import db
from app.models.pedido import datetime_now_brazil
from app.utils.crypto import decrypt_secret, encrypt_secret

STORE_SETTINGS_PURPOSE = b":store-settings"
SECRET_FIELDS = {
    "meta_capi_access_token": "meta_capi_access_token_encrypted",
    "ga4_api_secret": "ga4_api_secret_encrypted",
    "utmify_api_token": "utmify_api_token_encrypted",
}


class StoreSetting(db.Model):
    __tablename__ = "store_settings"

    id = db.Column(db.Integer, primary_key=True)
    store_ref_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "stores.id",
            name="fk_store_settings_store_ref_id_stores",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    marketing_dispatch_enabled = db.Column(db.Boolean, nullable=False, default=False)
    meta_pixel_id = db.Column(db.String(50), nullable=True)
    meta_capi_access_token_encrypted = db.Column(db.Text, nullable=True)

    ga4_measurement_id = db.Column(db.String(30), nullable=True)
    ga4_api_secret_encrypted = db.Column(db.Text, nullable=True)
    ga4_validate_only = db.Column(db.Boolean, nullable=False, default=False)

    google_datamanager_enabled = db.Column(db.Boolean, nullable=False, default=False)
    google_ads_customer_id = db.Column(db.String(30), nullable=True)
    google_ads_conversion_action_id = db.Column(db.String(80), nullable=True)
    utmify_enabled = db.Column(db.Boolean, nullable=False, default=False)
    utmify_api_token_encrypted = db.Column(db.Text, nullable=True)
    utmify_platform = db.Column(db.String(80), nullable=True)
    utmify_is_test = db.Column(db.Boolean, nullable=False, default=False)

    endereco_floricultura = db.Column(db.String(255), nullable=True)
    loja_cep = db.Column(db.String(9), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime_now_brazil)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime_now_brazil,
        onupdate=datetime_now_brazil,
    )

    def set_secret(self, field: str, value: str | None) -> None:
        encrypted_field = SECRET_FIELDS.get(field)
        if not encrypted_field:
            raise ValueError(f"Campo secreto desconhecido: {field}")
        setattr(self, encrypted_field, encrypt_secret(value, STORE_SETTINGS_PURPOSE))

    def get_secret(self, field: str) -> str | None:
        encrypted_field = SECRET_FIELDS.get(field)
        if not encrypted_field:
            raise ValueError(f"Campo secreto desconhecido: {field}")
        return decrypt_secret(getattr(self, encrypted_field), STORE_SETTINGS_PURPOSE)
