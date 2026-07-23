# -*- coding: utf-8 -*-
"""
EventsDispatcher — processa o outbox unificado de eventos de marketing (Meta CAPI + GA4).

Substitui MarketingConversionDispatcher (GA4) e integra o envio Meta CAPI
que antes ficava no SendDailyPurchasesToMetaCommand.
"""
from __future__ import annotations

import json

import requests

from app import db
from app.models.events_outbox import EventsOutbox
from app.models.pedido import datetime_now_brazil
from app.repositories.events_outbox_repository import EventsOutboxRepository
from app.services.tenancy import is_store_inactive


class EventsDispatcher:
    """Processa o outbox unificado events_outbox, enviando para Meta CAPI e GA4."""

    def __init__(self, http=None):
        self.http = http or requests
        self.repo = EventsOutboxRepository()

    # ------------------------------------------------------------------
    # Ciclo principal
    # ------------------------------------------------------------------
    def process_cycle(self, limit: int = 50) -> dict:
        """Processa linhas pendentes do events_outbox. Retorna dict de estatísticas."""
        stats: dict = {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "skipped_inactive": 0,
            "skipped_disabled": 0,
        }

        rows = self.repo.get_pending(limit=limit)
        for row in rows:
            stats["processed"] += 1
            store_ref_id = getattr(row, "store_ref_id", None)

            if is_store_inactive(store_ref_id):
                self.repo.mark_failed(
                    row.id, "store_inactive", row.attempts + 1, error_type="permanent"
                )
                stats["failed"] += 1
                stats["skipped_inactive"] += 1
                continue

            try:
                result = self._send(row)
                if result == "sent":
                    stats["sent"] += 1
                else:
                    stats["failed"] += 1
            except Exception as exc:
                self.repo.mark_failed(
                    row.id, f"dispatcher:{exc.__class__.__name__}", row.attempts + 1
                )
                stats["failed"] += 1

        return stats

    # ------------------------------------------------------------------
    # Roteamento por destino
    # ------------------------------------------------------------------
    def _send(self, row: EventsOutbox) -> str:
        """Roteamento por ``destino`` da linha."""
        if row.destino == "meta_capi":
            return self._send_meta_capi(row)
        if row.destino == "ga4":
            return self._send_ga4(row)
        self.repo.mark_failed(
            row.id, f"destino_nao_suportado:{row.destino}", row.attempts + 1
        )
        return "failed"

    # ------------------------------------------------------------------
    # Meta CAPI
    # ------------------------------------------------------------------
    def _send_meta_capi(self, row: EventsOutbox) -> str:
        """Envia para Meta CAPI Graph API com access_token como query param."""
        import os

        from app.services.secure_config import secure_runtime_config

        store_ref_id = getattr(row, "store_ref_id", None)
        with secure_runtime_config(store_ref_id) as tenant_config:
            access_token = tenant_config.get("META_CAPI_ACCESS_TOKEN", "")
            pixel_id = tenant_config.get("META_PIXEL_ID", "")

        if not access_token or not pixel_id:
            self.repo.mark_failed(
                row.id, "meta_capi_config_incompleta", row.attempts + 1
            )
            return "failed"

        payload = json.loads(row.payload_json)
        event = {
            "event_name": payload["event_name"],
            "event_time": payload["event_time"],
            "event_id": payload["event_id"],
            "action_source": payload["action_source"],
            "event_source_url": payload.get("event_source_url"),
            "custom_data": payload.get("custom_data", {}),
            "user_data": payload.get("user_data", {}),
        }

        use_gateway = os.environ.get("META_CAPI_USE_GATEWAY", "false").lower() == "true"
        if use_gateway:
            gateway_endpoint = os.environ.get("META_CAPI_GATEWAY_ENDPOINT") or ""
            if gateway_endpoint:
                url = gateway_endpoint
            else:
                gateway_domain = os.environ.get("META_CAPI_GATEWAY_DOMAIN") or "gestaopedidos.planteumaflor.online"
                url = f"https://{gateway_domain}/meta-gateway/{pixel_id}/events"
        else:
            api_version = os.environ.get("META_CAPI_API_VERSION", "v21.0")
            url = f"https://graph.facebook.com/{api_version}/{pixel_id}/events"

        body = {"data": [event]}

        try:
            response = self.http.post(
                url,
                json=body,
                params={"access_token": access_token},
                timeout=30,
            )
            row.attempts += 1
            if response.status_code < 200 or response.status_code >= 300:
                error_msg = f"meta_http_{response.status_code}"
                try:
                    error_body = response.json()
                    meta_err = error_body.get("error", {})
                    if isinstance(meta_err, dict):
                        error_msg = meta_err.get("message", error_msg)
                except Exception:
                    pass
                self.repo.mark_failed(
                    row.id, error_msg, row.attempts, status_code=response.status_code
                )
                return "failed"

            result = response.json()
            sent_at = datetime_now_brazil()
            self.repo.mark_sent(row.id, sent_at, response=result)
            return "sent"

        except Exception as exc:
            row.attempts += 1
            self.repo.mark_failed(
                row.id, f"meta_request:{exc.__class__.__name__}", row.attempts
            )
            return "failed"

    # ------------------------------------------------------------------
    # GA4
    # ------------------------------------------------------------------
    def _send_ga4(self, row: EventsOutbox) -> str:
        """Envia para GA4 Measurement Protocol. Lógica reutilizada do MarketingConversionDispatcher."""
        from app.services.secure_config import secure_runtime_config

        store_ref_id = getattr(row, "store_ref_id", None)
        with secure_runtime_config(store_ref_id) as tenant_config:
            measurement_id = tenant_config.get("GA4_MEASUREMENT_ID")
            api_secret = tenant_config.get("GA4_API_SECRET")
            if not measurement_id or not api_secret:
                self.repo.mark_failed(
                    row.id, "ga4_config_incompleta", row.attempts + 1
                )
                return "failed"
            validate_only = tenant_config.get(
                "GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY", False
            )

        base = (
            "https://www.google-analytics.com/debug/mp/collect"
            if validate_only
            else "https://www.google-analytics.com/mp/collect"
        )

        try:
            response = self.http.post(
                base,
                params={"measurement_id": measurement_id, "api_secret": api_secret},
                json=json.loads(row.payload_json),
                timeout=10,
            )
            row.attempts += 1
            if response.status_code < 200 or response.status_code >= 300:
                self.repo.mark_failed(
                    row.id,
                    f"ga4_http_{response.status_code}",
                    row.attempts,
                    status_code=response.status_code,
                )
                return "failed"

            if validate_only:
                messages = response.json().get("validationMessages", [])
                errors = [
                    message.get("validationCode", "validation_error")
                    for message in messages
                    if message.get("severity") == "ERROR"
                ]
                if errors:
                    self.repo.mark_failed(
                        row.id,
                        f"ga4_validation:{','.join(errors[:5])}",
                        row.attempts,
                    )
                    return "failed"

            sent_at = datetime_now_brazil()
            row.status = "sent"
            row.sent_at = sent_at
            row.last_error = "validated_only" if validate_only else None
            db.session.commit()
            return "sent"

        except Exception as exc:
            row.attempts += 1
            self.repo.mark_failed(
                row.id, f"ga4_request:{exc.__class__.__name__}", row.attempts
            )
            return "failed"
