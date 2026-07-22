# -*- coding: utf-8 -*-
"""Side-effect-free connectivity diagnostics for marketing destinations."""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timezone

import requests
from flask import current_app

from app.services.marketing_conversion_dispatcher import (
    DATAMANAGER_INGEST_URL,
    MarketingConversionDispatcher,
)
from app.services.meta_capi import MetaConversionsApiService


class MarketingDiagnosticsService:
    def __init__(self, http=None, store_ref_id: int | None = None):
        self.http = http or requests
        # Loja cujas credenciais serao lidas. As rotas passam o tenant da request;
        # None cai na loja default (bootstrap/single-store), como runtime_config ja faz.
        self.store_ref_id = store_ref_id

    def config_status(self) -> dict:
        from app.services.secure_config import secure_runtime_config

        with secure_runtime_config(self.store_ref_id) as tenant_config:
            result = {
                "dispatch_enabled": bool(tenant_config.get("MARKETING_DISPATCH_ENABLED")),
                "meta": {
                    "configured": bool(
                        tenant_config.get("META_PIXEL_ID")
                        and tenant_config.get("META_CAPI_ACCESS_TOKEN")
                    ),
                    "test_mode": bool(current_app.config.get("META_TEST_EVENT_CODE")),
                },
                "ga4": {
                    "configured": bool(
                        tenant_config.get("GA4_MEASUREMENT_ID")
                        and tenant_config.get("GA4_API_SECRET")
                    ),
                    "validate_only": bool(
                        tenant_config.get("GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY")
                    ),
                    "measurement_id": tenant_config.get("GA4_MEASUREMENT_ID") or None,
                },
                "google_ads": {
                    "configured": bool(
                        tenant_config.get("GOOGLE_DATAMANAGER_ENABLED")
                        and current_app.config.get("GOOGLE_CLOUD_PROJECT_ID")
                        and tenant_config.get("GOOGLE_ADS_CUSTOMER_ID")
                        and tenant_config.get("GOOGLE_ADS_CONVERSION_ACTION_ID")
                    ),
                    "enabled": bool(tenant_config.get("GOOGLE_DATAMANAGER_ENABLED")),
                    "validate_only": bool(
                        current_app.config.get("GOOGLE_DATAMANAGER_VALIDATE_ONLY", True)
                    ),
                    "customer_id": tenant_config.get("GOOGLE_ADS_CUSTOMER_ID") or None,
                    "conversion_action_id": (
                        tenant_config.get("GOOGLE_ADS_CONVERSION_ACTION_ID") or None
                    ),
                },
            }
        return result

    def run(self, destination: str, meta_test_event_code: str | None = None) -> dict:
        started = time.monotonic()
        try:
            if destination == "meta":
                result = self._meta(meta_test_event_code)
            elif destination == "ga4":
                result = self._ga4()
            elif destination == "google_ads":
                result = self._google_ads()
            else:
                result = {
                    "ok": False,
                    "status": "failed",
                    "error": "destino_nao_suportado",
                }
        except Exception as exc:
            result = {
                "ok": False,
                "status": "failed",
                "error": f"diagnostic_{exc.__class__.__name__}",
            }
        result["destination"] = destination
        result["duration_ms"] = round((time.monotonic() - started) * 1000)
        return result

    def _meta(self, test_event_code: str | None) -> dict:
        service = MetaConversionsApiService(self.store_ref_id)
        code = (test_event_code or service.test_event_code or "").strip()
        if not service.pixel_id or not service.access_token:
            return {"ok": False, "status": "failed", "error": "meta_config_incompleta"}
        if not code:
            return {
                "ok": False,
                "status": "not_tested",
                "error": "meta_test_event_code_obrigatorio",
            }
        if len(code) > 100 or not all(ch.isalnum() or ch in "_-" for ch in code):
            return {"ok": False, "status": "failed", "error": "meta_test_event_code_invalido"}
        service.test_event_code = code
        diagnostic_id = uuid.uuid4().hex
        external_id = hashlib.sha256(f"marketing-diagnostic:{diagnostic_id}".encode()).hexdigest()
        response = service.send_events(
            [
                {
                    "event_name": "MarketingIntegrationTest",
                    "event_time": int(time.time()),
                    "event_id": f"marketing_diag_{diagnostic_id}",
                    "action_source": "website",
                    "user_data": {"external_id": [external_id]},
                    "custom_data": {"diagnostic": True},
                }
            ]
        )
        http_status = int(response.get("_status_code") or 0)
        received = int(response.get("events_received") or 0)
        if 200 <= http_status < 300 and received >= 1:
            return {
                "ok": True,
                "status": "validated",
                "http_status": http_status,
                "events_received": received,
                "trace_id": response.get("fbtrace_id"),
            }
        return {
            "ok": False,
            "status": "failed",
            "http_status": http_status,
            "error": response.get("_error") or "meta_diagnostic_failed",
        }

    def _ga4(self) -> dict:
        from app.services.secure_config import secure_runtime_config

        with secure_runtime_config(self.store_ref_id) as tenant_config:
            measurement_id = tenant_config.get("GA4_MEASUREMENT_ID")
            api_secret = tenant_config.get("GA4_API_SECRET")
            if not measurement_id or not api_secret:
                return {"ok": False, "status": "failed", "error": "ga4_config_incompleta"}
        now = datetime.now(timezone.utc)
        response = self.http.post(
            "https://www.google-analytics.com/debug/mp/collect",
            params={"measurement_id": measurement_id, "api_secret": api_secret},
            json={
                "client_id": f"diagnostic.{int(now.timestamp())}",
                "timestamp_micros": int(now.timestamp() * 1_000_000),
                "validation_behavior": "ENFORCE_RECOMMENDATIONS",
                "events": [
                    {
                        "name": "marketing_integration_test",
                        "params": {"engagement_time_msec": 1, "debug_mode": 1},
                    }
                ],
            },
            timeout=15,
        )
        if response.status_code < 200 or response.status_code >= 300:
            return {
                "ok": False,
                "status": "failed",
                "http_status": response.status_code,
                "error": f"ga4_http_{response.status_code}",
            }
        messages = response.json().get("validationMessages", [])
        errors = [
            item.get("validationCode") or "validation_error"
            for item in messages
            if item.get("severity") == "ERROR"
        ]
        if errors:
            return {
                "ok": False,
                "status": "failed",
                "http_status": response.status_code,
                "error": f"ga4_validation:{','.join(errors[:5])}",
            }
        return {"ok": True, "status": "validated", "http_status": response.status_code}

    def _google_ads(self) -> dict:
        from app.services.secure_config import secure_runtime_config

        with secure_runtime_config(self.store_ref_id) as tenant_config:
            customer_id = "".join(
                ch for ch in tenant_config.get("GOOGLE_ADS_CUSTOMER_ID", "") if ch.isdigit()
            )
            action_id = tenant_config.get("GOOGLE_ADS_CONVERSION_ACTION_ID")
            if not tenant_config.get("GOOGLE_DATAMANAGER_ENABLED"):
                return {"ok": False, "status": "failed", "error": "datamanager_desabilitado"}
            if not customer_id or not action_id:
                return {"ok": False, "status": "failed", "error": "datamanager_config_incompleta"}
        dispatcher = MarketingConversionDispatcher(http=self.http)
        diagnostic_id = uuid.uuid4().hex
        response = self.http.post(
            DATAMANAGER_INGEST_URL,
            headers=dispatcher._google_headers(),
            json={
                "destinations": [
                    {
                        "operatingAccount": {
                            "accountType": "GOOGLE_ADS",
                            "accountId": customer_id,
                        },
                        "productDestinationId": str(action_id),
                    }
                ],
                "events": [
                    {
                        "transactionId": f"GESTOR-DIAG-{diagnostic_id}",
                        "eventTimestamp": datetime.now(timezone.utc).isoformat(),
                        "conversionValue": 0.01,
                        "currency": "BRL",
                        "eventSource": "WEB",
                        "adIdentifiers": {"gclid": f"diagnostic-{diagnostic_id}"},
                    }
                ],
                "encoding": "HEX",
                "validateOnly": True,
            },
            timeout=20,
        )
        if response.status_code < 200 or response.status_code >= 300:
            return {
                "ok": False,
                "status": "failed",
                "http_status": response.status_code,
                "error": f"datamanager_http_{response.status_code}",
            }
        request_id = response.json().get("requestId")
        if not request_id:
            return {
                "ok": False,
                "status": "failed",
                "http_status": response.status_code,
                "error": "datamanager_sem_request_id",
            }
        return {
            "ok": True,
            "status": "validated",
            "http_status": response.status_code,
            "request_id": str(request_id),
        }
