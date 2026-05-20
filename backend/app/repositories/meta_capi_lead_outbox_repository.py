# -*- coding: utf-8 -*-
"""
Outbox Meta CAPI — funil de leads (Contact / Lead).
"""
import json
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.lead import Lead
from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox
from app.models.pedido import datetime_now_brazil
from app.repositories.base_repository import BaseRepository
from app.services.meta_capi import MetaConversionsApiService


class MetaCapiLeadOutboxRepository(BaseRepository):
    """Repository para MetaCapiLeadOutbox."""

    STAGE_CONTACT = "contact"
    STAGE_LEAD = "lead"
    STAGE_DISQUALIFIED = "disqualified"

    def __init__(self):
        super().__init__(MetaCapiLeadOutbox)
        self.service = MetaConversionsApiService()

    def get_by_lead_and_stage(self, lead_id: int, stage: str) -> Optional[MetaCapiLeadOutbox]:
        return (
            self.model.query.filter_by(lead_id=lead_id, funnel_stage=stage).first()
        )

    def create_contact_from_lead(self, lead: Lead) -> Optional[MetaCapiLeadOutbox]:
        if self.get_by_lead_and_stage(lead.id, self.STAGE_CONTACT):
            return None
        event = self.service.build_contact_event_from_lead(lead)
        payload_safe = {
            "event_name": event["event_name"],
            "event_time": event["event_time"],
            "event_id": event["event_id"],
            "action_source": event["action_source"],
            "event_source_url": event.get("event_source_url"),
            "custom_data": event["custom_data"],
            "user_data": event.get("user_data", {}),
        }
        event_time = lead.created_at or datetime_now_brazil()
        row = MetaCapiLeadOutbox(
            lead_id=lead.id,
            funnel_stage=self.STAGE_CONTACT,
            event_id=event["event_id"],
            event_time=event_time,
            payload_json=json.dumps(payload_safe),
            status="pending",
            attempts=0,
        )
        try:
            db.session.add(row)
            db.session.commit()
            return row
        except IntegrityError:
            db.session.rollback()
            return None

    def create_lead_stage_from_lead(
        self, lead: Lead, *, event_time: Optional[datetime] = None
    ) -> Optional[MetaCapiLeadOutbox]:
        if self.get_by_lead_and_stage(lead.id, self.STAGE_LEAD):
            return None
        ts = event_time or lead.updated_at or lead.created_at or datetime_now_brazil()
        event_time_int = int(ts.timestamp())
        event = self.service.build_lead_event_from_lead(lead, event_time_override=event_time_int)
        payload_safe = {
            "event_name": event["event_name"],
            "event_time": event["event_time"],
            "event_id": event["event_id"],
            "action_source": event["action_source"],
            "event_source_url": event.get("event_source_url"),
            "custom_data": event["custom_data"],
            "user_data": event.get("user_data", {}),
        }
        row = MetaCapiLeadOutbox(
            lead_id=lead.id,
            funnel_stage=self.STAGE_LEAD,
            event_id=event["event_id"],
            event_time=ts,
            payload_json=json.dumps(payload_safe),
            status="pending",
            attempts=0,
        )
        try:
            db.session.add(row)
            db.session.commit()
            return row
        except IntegrityError:
            db.session.rollback()
            return None

    def create_disqualified_from_lead(
        self, lead: Lead, *, event_time: Optional[datetime] = None
    ) -> Optional[MetaCapiLeadOutbox]:
        """
        Cria outbox para evento custom LeadDisqualified (status -> descarte).
        Idempotente: se já existe row disqualified para o lead, retorna None.
        """
        if self.get_by_lead_and_stage(lead.id, self.STAGE_DISQUALIFIED):
            return None
        ts = event_time or datetime_now_brazil()
        event_time_int = int(ts.timestamp())
        event = self.service.build_disqualified_event_from_lead(
            lead, event_time_override=event_time_int
        )
        payload_safe = {
            "event_name": event["event_name"],
            "event_time": event["event_time"],
            "event_id": event["event_id"],
            "action_source": event["action_source"],
            "event_source_url": event.get("event_source_url"),
            "custom_data": event["custom_data"],
            "user_data": event.get("user_data", {}),
        }
        row = MetaCapiLeadOutbox(
            lead_id=lead.id,
            funnel_stage=self.STAGE_DISQUALIFIED,
            event_id=event["event_id"],
            event_time=ts,
            payload_json=json.dumps(payload_safe),
            status="pending",
            attempts=0,
        )
        try:
            db.session.add(row)
            db.session.commit()
            return row
        except IntegrityError:
            db.session.rollback()
            return None

    def get_pending(self, limit: int = 50) -> List[MetaCapiLeadOutbox]:
        return (
            self.model.query.filter_by(status="pending")
            .order_by(MetaCapiLeadOutbox.created_at.asc())
            .limit(limit)
            .all()
        )

    def get_failed_retryable(self, limit: int = 50) -> List[MetaCapiLeadOutbox]:
        return (
            self.model.query.filter_by(status="failed", error_type="retryable")
            .filter(MetaCapiLeadOutbox.attempts < 3)
            .order_by(MetaCapiLeadOutbox.updated_at.asc())
            .limit(limit)
            .all()
        )

    def mark_sent(
        self, entry_id: int, sent_at: datetime, response: Optional[Dict] = None
    ) -> Optional[MetaCapiLeadOutbox]:
        entry = self.get_by_id(entry_id)
        if not entry:
            return None
        entry.status = "sent"
        entry.sent_at = sent_at
        entry.updated_at = datetime_now_brazil()
        if response:
            debug_info = {
                "events_received": response.get("events_received", 0),
                "fbtrace_id": response.get("fbtrace_id", ""),
            }
            entry.last_error = json.dumps(debug_info)
        db.session.commit()
        return entry

    def mark_failed(
        self,
        entry_id: int,
        error: str,
        status_code: int,
        error_type: str,
        attempts: int,
    ) -> Optional[MetaCapiLeadOutbox]:
        entry = self.get_by_id(entry_id)
        if not entry:
            return None
        entry.status = "failed"
        entry.error_type = error_type
        entry.attempts = attempts
        entry.updated_at = datetime_now_brazil()
        error_with_code = f"[HTTP {status_code}] {error}" if status_code else error
        entry.last_error = error_with_code
        db.session.commit()
        return entry
