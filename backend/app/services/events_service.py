# -*- coding: utf-8 -*-
"""
EventsService — constrói payloads Meta CAPI + GA4 e enfileira no outbox unificado.

Cada método ``enqueue_*`` cria até 2 linhas (Meta CAPI + GA4) de forma idempotente.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from app.models.events_outbox import EventsOutbox
from app.models.pedido import Pedido, datetime_now_brazil
from app.repositories.events_outbox_repository import EventsOutboxRepository
from app.services.meta_capi import MetaConversionsApiService
from app.services.tenancy import is_store_inactive

logger = logging.getLogger(__name__)


class EventsService:
    """Serviço de enqueue de eventos de marketing (Meta CAPI + GA4) no outbox unificado."""

    def __init__(self):
        self.repo = EventsOutboxRepository()
        self.meta_service = MetaConversionsApiService()

    # ------------------------------------------------------------------
    # GA4 — helpers
    # ------------------------------------------------------------------
    def _ga4_event_payload(self, lead, event_name: str, params: dict) -> dict | None:
        """Monta payload GA4 Measurement Protocol. Retorna None se não houver client_id."""
        client_id = getattr(lead, "ga_client_id", None) or str(lead.id)
        if not client_id:
            return None
        return {
            "client_id": client_id,
            "timestamp_micros": int(
                datetime.now().timestamp() * 1_000_000
            ),
            "events": [{"name": event_name, "params": params}],
        }

    # ------------------------------------------------------------------
    # Meta CAPI — helpers
    # ------------------------------------------------------------------
    def _meta_payload_safe(self, event: dict) -> dict:
        """Extrai dict seguro do evento Meta CAPI (sem campos internos)."""
        return {
            "event_name": event["event_name"],
            "event_time": event["event_time"],
            "event_id": event["event_id"],
            "action_source": event["action_source"],
            "event_source_url": event.get("event_source_url"),
            "custom_data": event["custom_data"],
            "user_data": event.get("user_data", {}),
        }

    def _enqueue_meta(
        self,
        *,
        lead,
        pedido=None,
        destino: str,
        evento: str,
        meta_event: dict,
        event_time: datetime,
    ) -> EventsOutbox | None:
        """Enfileira um evento Meta CAPI no outbox unificado."""
        payload_safe = self._meta_payload_safe(meta_event)
        return self.repo.create_event(
            lead_id=getattr(lead, "id", None),
            pedido_id=getattr(pedido, "id", None) if pedido else None,
            destino=destino,
            evento=evento,
            event_time=event_time,
            payload_json=json.dumps(payload_safe, ensure_ascii=False, separators=(",", ":")),
            store_ref_id=getattr(lead, "store_ref_id", None),
        )

    def _enqueue_ga4(
        self,
        *,
        lead,
        pedido=None,
        evento: str,
        ga4_event_name: str,
        params: dict,
        event_time: datetime,
    ) -> EventsOutbox | None:
        """Enfileira um evento GA4 no outbox unificado."""
        payload = self._ga4_event_payload(lead, ga4_event_name, params)
        if not payload:
            return None
        return self.repo.create_event(
            lead_id=getattr(lead, "id", None),
            pedido_id=getattr(pedido, "id", None) if pedido else None,
            destino="ga4",
            evento=evento,
            event_time=event_time,
            payload_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            store_ref_id=getattr(lead, "store_ref_id", None),
        )

    # ------------------------------------------------------------------
    # Lead
    # ------------------------------------------------------------------
    def enqueue_lead(self, lead, event_time: datetime | None = None) -> list[EventsOutbox]:
        """Enfileira Lead (Meta CAPI) + generate_lead (GA4). Idempotente."""
        created: list[EventsOutbox] = []

        if is_store_inactive(getattr(lead, "store_ref_id", None)):
            return created

        ts = event_time or lead.updated_at or lead.created_at or datetime_now_brazil()
        event_time_int = int(ts.timestamp())

        # Meta CAPI — Lead
        try:
            meta_event = self.meta_service.build_lead_event_from_lead(
                lead, event_time_override=event_time_int
            )
            row = self._enqueue_meta(
                lead=lead,
                destino="meta_capi",
                evento="Lead",
                meta_event=meta_event,
                event_time=ts,
            )
            if row:
                created.append(row)
        except (ValueError, TypeError) as exc:
            logger.info("events_service.skip_lead_meta lead_id=%s error=%s", lead.id, exc)

        # GA4 — generate_lead
        row = self._enqueue_ga4(
            lead=lead,
            evento="generate_lead",
            ga4_event_name="generate_lead",
            params={
                "event_category": "lead",
                "lead_id": lead.id,
                "engagement_time_msec": 1,
            },
            event_time=ts,
        )
        if row:
            created.append(row)

        return created

    # ------------------------------------------------------------------
    # LeadDisqualified
    # ------------------------------------------------------------------
    def enqueue_disqualified(self, lead, event_time: datetime | None = None) -> list[EventsOutbox]:
        """Enfileira LeadDisqualified (Meta CAPI) + lead_disqualified (GA4). Idempotente."""
        created: list[EventsOutbox] = []

        if is_store_inactive(getattr(lead, "store_ref_id", None)):
            return created

        ts = event_time or datetime_now_brazil()
        event_time_int = int(ts.timestamp())

        # Meta CAPI — LeadDisqualified
        try:
            meta_event = self.meta_service.build_disqualified_event_from_lead(
                lead, event_time_override=event_time_int
            )
            row = self._enqueue_meta(
                lead=lead,
                destino="meta_capi",
                evento="LeadDisqualified",
                meta_event=meta_event,
                event_time=ts,
            )
            if row:
                created.append(row)
        except (ValueError, TypeError) as exc:
            logger.info(
                "events_service.skip_disqualified_meta lead_id=%s error=%s", lead.id, exc
            )

        # GA4 — lead_disqualified
        row = self._enqueue_ga4(
            lead=lead,
            evento="lead_disqualified",
            ga4_event_name="lead_disqualified",
            params={
                "event_category": "disqualified",
                "lead_id": lead.id,
                "engagement_time_msec": 1,
            },
            event_time=ts,
        )
        if row:
            created.append(row)

        return created

    # ------------------------------------------------------------------
    # Purchase
    # ------------------------------------------------------------------
    def enqueue_purchase(self, pedido: Pedido) -> list[EventsOutbox]:
        """Enfileira Purchase (Meta CAPI) + whatsapp_purchase (GA4). Idempotente."""
        from app.services.secure_config import secure_runtime_config

        created: list[EventsOutbox] = []

        if is_store_inactive(pedido.store_ref_id):
            return created

        with secure_runtime_config(pedido.store_ref_id) as tenant_config:
            if not tenant_config.get("MARKETING_DISPATCH_ENABLED"):
                return created

        # Resolver lead vinculado ao pedido (token rastreio válido)
        lead = self._linked_store_lead(pedido)
        event_time = pedido.updated_at or pedido.created_at or datetime_now_brazil()

        # Meta CAPI — Purchase
        try:
            svc = MetaConversionsApiService(store_ref_id=pedido.store_ref_id)
            meta_event = svc.build_purchase_event(pedido)
            if meta_event is not None:
                payload_safe = self._meta_payload_safe(meta_event)
                row = self.repo.create_event(
                    lead_id=getattr(lead, "id", None) if lead else None,
                    pedido_id=pedido.id,
                    destino="meta_capi",
                    evento="Purchase",
                    event_time=event_time,
                    payload_json=json.dumps(
                        payload_safe, ensure_ascii=False, separators=(",", ":")
                    ),
                    store_ref_id=pedido.store_ref_id,
                )
                if row:
                    created.append(row)
        except (ValueError, TypeError) as exc:
            logger.info(
                "events_service.skip_purchase_meta pedido_id=%s error=%s", pedido.id, exc
            )

        # GA4 — whatsapp_purchase
        if lead:

            transaction_id = f"GESTOR-WA-{pedido.id}"
            value = round(float(pedido.total_pago() or 0), 2)
            params: dict = {
                "transaction_id": transaction_id,
                "value": value,
                "currency": "BRL",
                "sales_channel": "whatsapp",
                "lead_id": lead.id,
                "items": [],
                "engagement_time_msec": 1,
            }
            row = self._enqueue_ga4(
                lead=lead,
                pedido=pedido,
                evento="whatsapp_purchase",
                ga4_event_name="whatsapp_purchase",
                params=params,
                event_time=event_time,
            )
            if row:
                created.append(row)

        return created

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    @staticmethod
    def _linked_store_lead(pedido: Pedido):
        """Busca o lead vinculado ao pedido via token de rastreio."""
        from app.models.lead import Lead
        from app.utils.tracking_token import normalize_tracking_token

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
