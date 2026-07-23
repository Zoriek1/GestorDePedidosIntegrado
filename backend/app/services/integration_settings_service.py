# -*- coding: utf-8 -*-
"""Leitura, validacao e serializacao das integracoes configuradas por loja."""

import logging
import re
from typing import Any

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.store import Store
from app.models.store_setting import SECRET_FIELDS, StoreSetting

logger = logging.getLogger(__name__)

MASK_PREFIX = "********"
DEFAULT_STORE_SLUG = "default"

STRING_FIELDS = {
    "meta_pixel_id": 50,
    "ga4_measurement_id": 30,
    "google_ads_customer_id": 30,
    "google_ads_conversion_action_id": 80,
    "utmify_platform": 80,
    "endereco_floricultura": 255,
    "loja_cep": 9,
}
BOOLEAN_FIELDS = {
    "marketing_dispatch_enabled",
    "ga4_validate_only",
    "google_datamanager_enabled",
    "utmify_enabled",
    "utmify_is_test",
    "mercado_pago_enabled",
}
ALLOWED_FIELDS = set(STRING_FIELDS) | BOOLEAN_FIELDS | set(SECRET_FIELDS)


# =============================================================================
# F6/E0 — Grid de Integracoes por canal
# =============================================================================
# Cada canal agrupa campos do store_settings. O frontend renderiza 1 card por
# canal com save/validate por campo. Nuvemshop e Bling nao entram aqui porque
# usam OAuth e resolvem status por outros endpoints.
CHANNELS: dict[str, dict[str, list[str]]] = {
    "meta_capi": {
        "fields": ["meta_pixel_id", "meta_capi_access_token"],
        "required": ["meta_pixel_id", "meta_capi_access_token"],
    },
    "ga4": {
        "fields": ["ga4_measurement_id", "ga4_api_secret", "ga4_validate_only"],
        "required": ["ga4_measurement_id", "ga4_api_secret"],
    },
    "google_ads": {
        "fields": [
            "google_ads_customer_id",
            "google_ads_conversion_action_id",
            "google_datamanager_enabled",
        ],
        "required": ["google_ads_customer_id", "google_ads_conversion_action_id"],
    },
    "utmify": {
        "fields": ["utmify_api_token", "utmify_platform", "utmify_is_test", "utmify_enabled"],
        "required": ["utmify_api_token", "utmify_platform"],
    },
    "dados_operacionais": {
        "fields": ["endereco_floricultura", "loja_cep"],
        "required": ["loja_cep"],
    },
    "mercado_pago": {
        "fields": [
            "mercado_pago_access_token",
            "mercado_pago_public_key",
            "mercado_pago_webhook_secret",
        ],
        "required": ["mercado_pago_access_token"],
    },
}

# Conjunto canonico de channels suportados (inclui OAuth, mas esses nao tem
# save por campo — o status vem do store OAuth/credential).
ALL_CHANNELS = set(CHANNELS) | {"nuvemshop", "bling", "mercado_pago"}


def channel_fields(channel: str) -> list[str]:
    """Lista de campos que pertencem ao canal (vazio se OAuth-only)."""
    return list(CHANNELS.get(channel, {}).get("fields", []))


def channel_required(channel: str) -> list[str]:
    """Campos obrigatorios para o canal ser considerado configurado."""
    return list(CHANNELS.get(channel, {}).get("required", []))


def is_known_channel(channel: str) -> bool:
    return channel in ALL_CHANNELS


def channel_supports_patch(channel: str) -> bool:
    """Apenas canais com campos salvos no store_settings aceitam PATCH."""
    return channel in CHANNELS


def default_store() -> Store:
    store = Store.query.filter_by(slug=DEFAULT_STORE_SLUG).first()
    if not store:
        raise RuntimeError("Loja default ausente; execute add_store_foundation.py")
    return store


def get_settings(store_ref_id: int) -> StoreSetting | None:
    return StoreSetting.query.filter_by(store_ref_id=store_ref_id).first()


def get_or_create_settings(store_ref_id: int) -> StoreSetting:
    settings = get_settings(store_ref_id)
    if settings:
        return settings
    settings = StoreSetting(store_ref_id=store_ref_id)
    db.session.add(settings)
    return settings


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    suffix = value[-4:] if len(value) >= 4 else value
    return f"{MASK_PREFIX}{suffix}"


def is_masked(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("****")


def serialize_settings(store: Store, settings: StoreSetting | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "store": {"id": store.id, "name": store.name, "slug": store.slug},
        "configured": settings is not None,
    }
    for field in STRING_FIELDS:
        payload[field] = getattr(settings, field, None) if settings else None
    for field in BOOLEAN_FIELDS:
        payload[field] = bool(getattr(settings, field, False)) if settings else False
    for field in SECRET_FIELDS:
        secret = settings.get_secret(field) if settings else None
        payload[field] = _mask(secret)
        payload[f"has_{field}"] = bool(secret)
    return payload


def update_settings(settings: StoreSetting, data: dict[str, Any]) -> None:
    unknown = sorted(set(data) - ALLOWED_FIELDS)
    if unknown:
        raise ValueError(f"Campos desconhecidos: {', '.join(unknown)}")

    for field, max_length in STRING_FIELDS.items():
        if field not in data:
            continue
        raw = data[field]
        if raw is not None and not isinstance(raw, str):
            raise ValueError(f"{field} deve ser texto ou null")
        value = raw.strip() if isinstance(raw, str) else None
        value = value or None
        if value and len(value) > max_length:
            raise ValueError(f"{field} excede {max_length} caracteres")
        if field == "loja_cep" and value and not re.fullmatch(r"\d{5}-?\d{3}", value):
            raise ValueError("loja_cep deve estar no formato 00000-000")
        if field == "loja_cep" and value and "-" not in value:
            value = f"{value[:5]}-{value[5:]}"
        setattr(settings, field, value)

    for field in BOOLEAN_FIELDS:
        if field not in data:
            continue
        if not isinstance(data[field], bool):
            raise ValueError(f"{field} deve ser booleano")
        setattr(settings, field, data[field])

    for field in SECRET_FIELDS:
        if field not in data or is_masked(data[field]):
            continue
        raw = data[field]
        if raw is not None and not isinstance(raw, str):
            raise ValueError(f"{field} deve ser texto ou null")
        value = raw.strip() if isinstance(raw, str) else None
        settings.set_secret(field, value or None)


def settings_from_environment(store_ref_id: int) -> StoreSetting:
    """Cria o snapshot inicial do tenant default a partir do config legado."""
    settings = StoreSetting(
        store_ref_id=store_ref_id,
        marketing_dispatch_enabled=bool(current_app.config.get("MARKETING_DISPATCH_ENABLED")),
        meta_pixel_id=current_app.config.get("META_PIXEL_ID") or None,
        ga4_measurement_id=current_app.config.get("GA4_MEASUREMENT_ID") or None,
        ga4_validate_only=bool(current_app.config.get("GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY")),
        google_datamanager_enabled=bool(current_app.config.get("GOOGLE_DATAMANAGER_ENABLED")),
        google_ads_customer_id=current_app.config.get("GOOGLE_ADS_CUSTOMER_ID") or None,
        google_ads_conversion_action_id=(
            current_app.config.get("GOOGLE_ADS_CONVERSION_ACTION_ID") or None
        ),
        utmify_enabled=bool(current_app.config.get("UTMIFY_ENABLED")),
        utmify_platform=current_app.config.get("UTMIFY_PLATFORM") or None,
        utmify_is_test=bool(current_app.config.get("UTMIFY_IS_TEST")),
        endereco_floricultura=current_app.config.get("ENDERECO_FLORICULTURA") or None,
        loja_cep=current_app.config.get("LOJA_CEP") or None,
    )
    for field, config_key in {
        "meta_capi_access_token": "META_CAPI_ACCESS_TOKEN",
        "ga4_api_secret": "GA4_API_SECRET",
        "utmify_api_token": "UTMIFY_API_TOKEN",
        "mercado_pago_access_token": "MERCADO_PAGO_ACCESS_TOKEN",
        "mercado_pago_public_key": "MERCADO_PAGO_PUBLIC_KEY",
        "mercado_pago_webhook_secret": "MERCADO_PAGO_WEBHOOK_SECRET",
    }.items():
        settings.set_secret(field, current_app.config.get(config_key) or None)
    settings.mercado_pago_enabled = bool(current_app.config.get("MERCADO_PAGO_ENABLED"))
    return settings


def _environment_runtime_config() -> dict[str, Any]:
    return {
        key: current_app.config.get(key)
        for key in (
            "MARKETING_DISPATCH_ENABLED",
            "META_PIXEL_ID",
            "META_CAPI_ACCESS_TOKEN",
            "GA4_MEASUREMENT_ID",
            "GA4_API_SECRET",
            "GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY",
            "GOOGLE_DATAMANAGER_ENABLED",
            "GOOGLE_ADS_CUSTOMER_ID",
            "GOOGLE_ADS_CONVERSION_ACTION_ID",
            "GOOGLE_DATAMANAGER_CREDENTIALS_JSON",
            "UTMIFY_ENABLED",
            "UTMIFY_API_TOKEN",
            "UTMIFY_PLATFORM",
            "UTMIFY_IS_TEST",
            "ENDERECO_FLORICULTURA",
            "LOJA_CEP",
            "MERCADO_PAGO_ENABLED",
            "MERCADO_PAGO_ACCESS_TOKEN",
            "MERCADO_PAGO_PUBLIC_KEY",
            "MERCADO_PAGO_WEBHOOK_SECRET",
        )
    }


def _disabled_runtime_config() -> dict[str, Any]:
    config = _environment_runtime_config()
    for key in (
        "MARKETING_DISPATCH_ENABLED",
        "GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY",
        "GOOGLE_DATAMANAGER_ENABLED",
        "UTMIFY_ENABLED",
        "UTMIFY_IS_TEST",
        "MERCADO_PAGO_ENABLED",
    ):
        config[key] = False
    for key in (
        "META_PIXEL_ID",
        "META_CAPI_ACCESS_TOKEN",
        "GA4_MEASUREMENT_ID",
        "GA4_API_SECRET",
        "GOOGLE_ADS_CUSTOMER_ID",
        "GOOGLE_ADS_CONVERSION_ACTION_ID",
        "UTMIFY_API_TOKEN",
        "ENDERECO_FLORICULTURA",
        "LOJA_CEP",
        "MERCADO_PAGO_ACCESS_TOKEN",
        "MERCADO_PAGO_PUBLIC_KEY",
        "MERCADO_PAGO_WEBHOOK_SECRET",
    ):
        config[key] = ""
    config["UTMIFY_PLATFORM"] = "WhatsAppManual"
    return config


def runtime_config(store_ref_id: int | None = None) -> dict[str, Any]:
    """Retorna config por loja; usa o .env somente enquanto nao existe registro."""
    try:
        store = db.session.get(Store, store_ref_id) if store_ref_id else default_store()
        if not store:
            return _disabled_runtime_config()
        settings = get_settings(store.id)
    except (RuntimeError, SQLAlchemyError):
        db.session.rollback()
        return _environment_runtime_config() if store_ref_id is None else _disabled_runtime_config()
    if not settings:
        if store.slug == DEFAULT_STORE_SLUG:
            logger.warning("tenant.env_fallback store=default reason=no_settings")
            return _environment_runtime_config()
        return _disabled_runtime_config()
    return {
        "MARKETING_DISPATCH_ENABLED": settings.marketing_dispatch_enabled,
        "META_PIXEL_ID": settings.meta_pixel_id or "",
        "META_CAPI_ACCESS_TOKEN": settings.get_secret("meta_capi_access_token") or "",
        "GA4_MEASUREMENT_ID": settings.ga4_measurement_id or "",
        "GA4_API_SECRET": settings.get_secret("ga4_api_secret") or "",
        "GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY": settings.ga4_validate_only,
        "GOOGLE_DATAMANAGER_ENABLED": settings.google_datamanager_enabled,
        "GOOGLE_ADS_CUSTOMER_ID": settings.google_ads_customer_id or "",
        "GOOGLE_ADS_CONVERSION_ACTION_ID": settings.google_ads_conversion_action_id or "",
        # Credencial tecnica compartilhada da plataforma, nao do lojista.
        "GOOGLE_DATAMANAGER_CREDENTIALS_JSON": current_app.config.get(
            "GOOGLE_DATAMANAGER_CREDENTIALS_JSON"
        )
        or "",
        "UTMIFY_ENABLED": settings.utmify_enabled,
        "UTMIFY_API_TOKEN": settings.get_secret("utmify_api_token") or "",
        "UTMIFY_PLATFORM": settings.utmify_platform or "WhatsAppManual",
        "UTMIFY_IS_TEST": settings.utmify_is_test,
        "ENDERECO_FLORICULTURA": settings.endereco_floricultura or "",
        "LOJA_CEP": settings.loja_cep or "",
        "MERCADO_PAGO_ENABLED": getattr(settings, "mercado_pago_enabled", False),
        "MERCADO_PAGO_ACCESS_TOKEN": settings.get_secret("mercado_pago_access_token") or "",
        "MERCADO_PAGO_PUBLIC_KEY": settings.get_secret("mercado_pago_public_key") or "",
        "MERCADO_PAGO_WEBHOOK_SECRET": settings.get_secret("mercado_pago_webhook_secret") or "",
    }


def uses_environment_fallback(store_ref_id: int | None = None) -> bool:
    """Indica se o tenant default ainda nao possui settings persistidas."""
    if store_ref_id is not None:
        return False
    try:
        store = default_store()
        return get_settings(store.id) is None
    except (RuntimeError, SQLAlchemyError):
        db.session.rollback()
        return True
