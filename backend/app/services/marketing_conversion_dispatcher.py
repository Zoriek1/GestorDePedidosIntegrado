# -*- coding: utf-8 -*-
"""Entrega e acompanha os destinos do marketing_conversion_outbox."""

from __future__ import annotations

import json
from datetime import timedelta

import requests
from flask import current_app

from app import db
from app.models.marketing_conversion_outbox import MarketingConversionOutbox
from app.models.pedido import datetime_now_brazil
from app.services.tenancy import is_store_inactive

DATAMANAGER_SCOPE = "https://www.googleapis.com/auth/datamanager"
DATAMANAGER_INGEST_URL = "https://datamanager.googleapis.com/v1/events:ingest"
DATAMANAGER_STATUS_URL = "https://datamanager.googleapis.com/v1/requestStatus:retrieve"
DATAMANAGER_INITIAL_STATUS_DELAY = timedelta(minutes=30)
DATAMANAGER_MAX_STATUS_DELAY = timedelta(minutes=60)
DATAMANAGER_STATUS_TIMEOUT = timedelta(hours=24)
DATAMANAGER_BACKOFF_MULTIPLIER = 1.3


class MarketingConversionDispatcher:
    def __init__(self, http=None):
        self.http = http or requests

    def process_cycle(self, limit: int = 50) -> dict:
        from app.services.secure_config import secure_runtime_config

        stats = {"processed": 0, "sent": 0, "submitted": 0, "failed": 0}
        with secure_runtime_config() as tenant_config:
            if not tenant_config.get("MARKETING_DISPATCH_ENABLED"):
                return stats

        rows = (
            MarketingConversionOutbox.query.filter_by(status="pending")
            .order_by(MarketingConversionOutbox.created_at.asc())
            .limit(limit)
            .all()
        )
        for row in rows:
            stats["processed"] += 1
            # Empresa inativa: invalida a linha pendente e não envia (política Fase D).
            if is_store_inactive(getattr(row, "store_ref_id", None)):
                self._fail(row, "store_inactive")
                stats["failed"] += 1
                continue
            try:
                result = self._send(row)
                stats[result] += 1
            except Exception as exc:
                self._fail(row, f"dispatcher:{exc.__class__.__name__}")
                stats["failed"] += 1

        submitted = (
            MarketingConversionOutbox.query.filter_by(destino="google_ads", status="submitted")
            .order_by(MarketingConversionOutbox.submitted_at.asc())
            .limit(limit)
            .all()
        )
        now = datetime_now_brazil()
        for row in submitted:
            next_check = self._aware(row.next_status_check_at, now)
            if next_check and next_check > now:
                continue
            stats["processed"] += 1
            self._poll_google_ads(row, stats)
        return stats

    def _send(self, row: MarketingConversionOutbox) -> str:
        if row.destino == "ga4":
            return self._send_ga4(row)
        if row.destino == "google_ads":
            return self._send_google_ads(row)
        self._fail(row, "destino_nao_suportado")
        return "failed"

    def _send_ga4(self, row: MarketingConversionOutbox) -> str:
        from app.services.secure_config import secure_runtime_config

        with secure_runtime_config(getattr(row, "store_ref_id", None)) as tenant_config:
            measurement_id = tenant_config.get("GA4_MEASUREMENT_ID")
            api_secret = tenant_config.get("GA4_API_SECRET")
            if not measurement_id or not api_secret:
                self._fail(row, "ga4_config_incompleta")
                return "failed"
            validate_only = tenant_config.get("GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY", False)
        base = (
            "https://www.google-analytics.com/debug/mp/collect"
            if validate_only
            else "https://www.google-analytics.com/mp/collect"
        )
        response = self.http.post(
            base,
            params={"measurement_id": measurement_id, "api_secret": api_secret},
            json=json.loads(row.payload_json),
            timeout=10,
        )
        row.attempts += 1
        row.last_http_status = response.status_code
        if response.status_code < 200 or response.status_code >= 300:
            self._fail(row, f"ga4_http_{response.status_code}", commit=False)
            db.session.commit()
            return "failed"
        if validate_only:
            messages = response.json().get("validationMessages", [])
            errors = [
                message.get("validationCode", "validation_error")
                for message in messages
                if message.get("severity") == "ERROR"
            ]
            if errors:
                self._fail(row, f"ga4_validation:{','.join(errors[:5])}", commit=False)
                db.session.commit()
                return "failed"
        row.status = "sent"
        row.sent_at = datetime_now_brazil()
        row.last_error = "validated_only" if validate_only else None
        db.session.commit()
        return "sent"

    def _credentials(self, row: MarketingConversionOutbox | None = None):
        import google.auth
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        from app.services.secure_config import secure_runtime_config

        with secure_runtime_config(getattr(row, "store_ref_id", None)) as tenant_config:
            raw = tenant_config.get("GOOGLE_DATAMANAGER_CREDENTIALS_JSON")
        if raw:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(raw), scopes=[DATAMANAGER_SCOPE]
            )
        else:
            credentials, _ = google.auth.default(scopes=[DATAMANAGER_SCOPE])
        credentials.refresh(Request())
        return credentials

    def _google_headers(self, row: MarketingConversionOutbox | None = None) -> dict:
        credentials = self._credentials(row)
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }
        project_id = current_app.config.get("GOOGLE_CLOUD_PROJECT_ID")
        if project_id:
            headers["x-goog-user-project"] = project_id
        return headers

    def _headers_for_row(self, row: MarketingConversionOutbox) -> dict:
        if getattr(row, "store_ref_id", None) is None:
            return self._google_headers()
        return self._google_headers(row)

    def _send_google_ads(self, row: MarketingConversionOutbox) -> str:
        from app.services.secure_config import secure_runtime_config

        with secure_runtime_config(getattr(row, "store_ref_id", None)) as tenant_config:
            customer_id = "".join(
                ch for ch in tenant_config.get("GOOGLE_ADS_CUSTOMER_ID", "") if ch.isdigit()
            )
            action_id = tenant_config.get("GOOGLE_ADS_CONVERSION_ACTION_ID")
            if not customer_id or not action_id:
                self._fail(row, "datamanager_config_incompleta")
                return "failed"
        validate_only = bool(current_app.config.get("GOOGLE_DATAMANAGER_VALIDATE_ONLY", True))
        body = {
            "destinations": [
                {
                    "operatingAccount": {
                        "accountType": "GOOGLE_ADS",
                        "accountId": customer_id,
                    },
                    "productDestinationId": str(action_id),
                }
            ],
            "events": [json.loads(row.payload_json)],
            "encoding": "HEX",
            "validateOnly": validate_only,
        }
        response = self.http.post(
            DATAMANAGER_INGEST_URL, headers=self._headers_for_row(row), json=body, timeout=20
        )
        row.attempts += 1
        row.last_http_status = response.status_code
        if response.status_code < 200 or response.status_code >= 300:
            self._fail(row, f"datamanager_http_{response.status_code}", commit=False)
            db.session.commit()
            return "failed"
        request_id = response.json().get("requestId")
        if not request_id:
            self._fail(row, "datamanager_sem_request_id", commit=False)
            db.session.commit()
            return "failed"
        row.request_id = str(request_id)
        row.validation_only = validate_only
        row.status_check_attempts = 0
        row.last_status_check_at = None
        row.next_status_check_at = None
        row.submitted_at = datetime_now_brazil()
        if validate_only:
            # Diagnostics by request_id are unavailable for validateOnly calls.
            # A successful HTTP response completes this validation request.
            row.status = "sent"
            row.sent_at = datetime_now_brazil()
            row.next_status_check_at = None
            row.last_error = "validated_only"
            db.session.commit()
            return "sent"
        row.status = "submitted"
        row.next_status_check_at = row.submitted_at + DATAMANAGER_INITIAL_STATUS_DELAY
        row.last_error = None
        db.session.commit()
        return "submitted"

    def _poll_google_ads(self, row: MarketingConversionOutbox, stats: dict) -> None:
        if row.validation_only:
            # Compatibility for validation rows created before validateOnly was
            # finalized synchronously. They cannot be queried for diagnostics.
            row.status = "sent"
            row.sent_at = datetime_now_brazil()
            row.next_status_check_at = None
            row.last_error = "validated_only"
            db.session.commit()
            stats["sent"] += 1
            return
        if not row.request_id:
            self._fail(row, "datamanager_sem_request_id")
            stats["failed"] += 1
            return
        now = datetime_now_brazil()
        submitted_at = self._aware(row.submitted_at, now)
        if submitted_at and now - submitted_at >= DATAMANAGER_STATUS_TIMEOUT:
            self._fail(row, "datamanager_status_timeout_24h")
            stats["failed"] += 1
            return
        try:
            response = self.http.get(
                DATAMANAGER_STATUS_URL,
                headers=self._headers_for_row(row),
                params={"requestId": row.request_id},
                timeout=15,
            )
            row.status_check_attempts = (row.status_check_attempts or 0) + 1
            row.last_status_check_at = now
            row.last_http_status = response.status_code
            if response.status_code < 200 or response.status_code >= 300:
                row.last_error = f"datamanager_status_http_{response.status_code}"
                self._schedule_next_status_check(row, now)
                db.session.commit()
                return
            statuses = response.json().get("requestStatusPerDestination", [])
            values = {item.get("requestStatus") for item in statuses}
            if values and values <= {"SUCCESS"}:
                row.status = "sent"
                row.sent_at = datetime_now_brazil()
                row.next_status_check_at = None
                row.last_error = None
                db.session.commit()
                stats["sent"] += 1
            elif values & {"FAILED", "PARTIAL_SUCCESS"}:
                reasons = []
                for item in statuses:
                    for error in item.get("errorInfo", {}).get("errorCounts", []):
                        if error.get("reason"):
                            reasons.append(error["reason"])
                self._fail(row, f"datamanager_processing:{','.join(reasons[:5]) or 'failed'}")
                stats["failed"] += 1
            else:
                row.last_error = (
                    "datamanager_processing"
                    if "PROCESSING" in values
                    else "datamanager_status_sem_destinos"
                )
                self._schedule_next_status_check(row, now)
                db.session.commit()
        except Exception as exc:
            # Status assíncrono será consultado novamente no próximo ciclo.
            db.session.rollback()
            row.status_check_attempts = (row.status_check_attempts or 0) + 1
            row.last_status_check_at = now
            row.last_error = f"datamanager_status:{exc.__class__.__name__}"
            self._schedule_next_status_check(row, now)
            db.session.commit()

    @staticmethod
    def _aware(value, reference):
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=reference.tzinfo)

    @staticmethod
    def _schedule_next_status_check(row: MarketingConversionOutbox, now) -> None:
        attempts = max(1, int(row.status_check_attempts or 1))
        base_seconds = DATAMANAGER_INITIAL_STATUS_DELAY.total_seconds() * (
            DATAMANAGER_BACKOFF_MULTIPLIER**attempts
        )
        jitter = sum((row.request_id or "").encode("utf-8")) % 31
        delay_seconds = min(DATAMANAGER_MAX_STATUS_DELAY.total_seconds(), base_seconds + jitter)
        row.next_status_check_at = now + timedelta(seconds=delay_seconds)

    @staticmethod
    def _fail(row: MarketingConversionOutbox, reason: str, commit: bool = True) -> None:
        row.status = "failed"
        row.last_error = reason[:1000]
        if commit:
            db.session.commit()
