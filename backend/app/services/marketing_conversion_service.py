# -*- coding: utf-8 -*-
"""Cria conversoes de compras WhatsApp de forma idempotente."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.lead import Lead
from app.models.marketing_conversion_outbox import MarketingConversionOutbox
from app.models.pedido import TIMEZONE_BRASIL, Pedido, datetime_now_brazil
from app.services.tenancy import is_store_inactive
from app.utils.tracking_token import normalize_tracking_token


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=TIMEZONE_BRASIL) if value.tzinfo is None else value


def _google_phone_hash(value: str | None) -> str | None:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(digits) in (10, 11):
        digits = f"55{digits}"
    if not digits.startswith("55") or len(digits) not in (12, 13):
        return None
    return hashlib.sha256(f"+{digits}".encode("utf-8")).hexdigest().upper()


def _linked_store_lead(pedido: Pedido) -> Lead | None:
    token = normalize_tracking_token(getattr(pedido, "codigo_whatsapp", None))
    if not token:
        return None
    return (
        Lead.query.filter(
            Lead.pedido_id == pedido.id,
            Lead.token_rastreio == token,
            Lead.token_valido.is_(True),
            Lead.event == "whatsapp_click",
        )
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .first()
    )


def _ga4_payload(
    pedido: Pedido,
    lead: Lead,
    transaction_id: str,
    value: float,
    conversion_time: datetime,
) -> dict | None:
    if not lead.ga_client_id:
        return None
    params: dict = {
        "transaction_id": transaction_id,
        "value": value,
        "currency": "BRL",
        "sales_channel": "whatsapp",
        "lead_id": lead.id,
        "items": [],
        "engagement_time_msec": 1,
    }
    session_start = _aware(lead.ga_session_started_at)
    now = _aware(datetime_now_brazil())
    session_is_recent = (
        lead.ga_session_id
        and session_start
        and now
        and timedelta(0) <= now - session_start <= timedelta(hours=24)
    )
    if session_is_recent:
        try:
            params["session_id"] = int(lead.ga_session_id)
        except (TypeError, ValueError):
            params["session_id"] = lead.ga_session_id
    return {
        "client_id": lead.ga_client_id,
        "timestamp_micros": int(_aware(conversion_time).timestamp() * 1_000_000),
        "events": [{"name": "whatsapp_purchase", "params": params}],
    }


def _google_ads_payload(
    pedido: Pedido,
    lead: Lead,
    transaction_id: str,
    value: float,
    conversion_time: datetime,
) -> dict | None:
    ad_identifiers = {
        key: value
        for key, value in {
            "gclid": lead.gclid,
            "gbraid": lead.gbraid,
            "wbraid": lead.wbraid,
        }.items()
        if value
    }
    if not ad_identifiers:
        return None
    event = {
        "transactionId": transaction_id,
        "eventTimestamp": _aware(conversion_time).isoformat(),
        "conversionValue": value,
        "currency": "BRL",
        "eventSource": "WEB",
        "adIdentifiers": ad_identifiers,
    }
    phone_hash = _google_phone_hash(pedido.telefone_cliente or lead.phone)
    if phone_hash:
        event["userData"] = {"userIdentifiers": [{"phoneNumber": phone_hash}]}
    return event


def enqueue_whatsapp_purchase(pedido: Pedido) -> list[MarketingConversionOutbox]:
    """Enfileira GA4/Ads apenas para pedido ligado a token valido da loja."""
    from app.services.secure_config import secure_runtime_config

    with secure_runtime_config(getattr(pedido, "store_ref_id", None)) as tenant_config:
        if not tenant_config.get("MARKETING_DISPATCH_ENABLED"):
            return []
        if is_store_inactive(pedido.store_ref_id):
            return []
        value = round(float(pedido.total_pago() or 0), 2)
        if value <= 0:
            return []
        lead = _linked_store_lead(pedido)
        if not lead:
            return []

        transaction_id = f"GESTOR-WA-{pedido.id}"
        event_time = datetime_now_brazil()
        candidates: list[tuple[str, str, dict | None]] = []
        if tenant_config.get("GA4_MEASUREMENT_ID") and tenant_config.get("GA4_API_SECRET"):
            candidates.append(
                (
                    "ga4",
                    "whatsapp_purchase",
                    _ga4_payload(pedido, lead, transaction_id, value, event_time),
                )
            )
        if tenant_config.get("GOOGLE_DATAMANAGER_ENABLED"):
            candidates.append(
                (
                    "google_ads",
                    "purchase",
                    _google_ads_payload(pedido, lead, transaction_id, value, event_time),
                )
            )

    created: list[MarketingConversionOutbox] = []
    for destino, evento, payload in candidates:
        if not payload:
            continue
        exists = MarketingConversionOutbox.query.filter_by(
            pedido_id=pedido.id, destino=destino, evento=evento
        ).first()
        if exists:
            continue
        row = MarketingConversionOutbox(
            pedido_id=pedido.id,
            store_ref_id=pedido.store_ref_id,
            lead_id=lead.id,
            destino=destino,
            evento=evento,
            transaction_id=transaction_id,
            event_time=event_time,
            payload_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        )
        try:
            db.session.add(row)
            db.session.commit()
            created.append(row)
        except IntegrityError:
            db.session.rollback()
    # Dual-write: unified events outbox (GA4 only, Meta CAPI goes via events_service)
    from app.services.events_service import EventsService
    try:
        events_svc = EventsService()
        events_svc.enqueue_purchase(pedido)
    except Exception as e:
        pass  # Non-critical: old outbox still works
    return created
