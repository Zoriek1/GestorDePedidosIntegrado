# -*- coding: utf-8 -*-
"""
Repository para EventsOutbox — tabela unificada de eventos de marketing.

Substitui MetaCapiOutbox (Purchase), MetaCapiLeadOutbox (Contact/Lead)
e MarketingConversionOutbox (GA4) com uma única tabela de outbox.
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.events_outbox import EventsOutbox
from app.models.pedido import datetime_now_brazil
from app.repositories.base_repository import BaseRepository


class EventsOutboxRepository(BaseRepository):
    """Repository para operações com a tabela unificada events_outbox."""

    def __init__(self):
        super().__init__(EventsOutbox)

    # ------------------------------------------------------------------
    # Dedup
    # ------------------------------------------------------------------
    def _build_dedup_key(
        self,
        lead_id: int | None,
        pedido_id: int | None,
        destino: str,
        evento: str,
    ) -> str:
        """SHA-256 de 'pedido_id:lead_id:destino:evento' (64 chars)."""
        raw = f"{pedido_id or 0}:{lead_id or 0}:{destino}:{evento}"
        return hashlib.sha256(raw.encode()).hexdigest()[:64]

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def create_event(
        self,
        *,
        lead_id: int | None,
        pedido_id: int | None,
        destino: str,
        evento: str,
        event_time: datetime,
        payload_json: str,
        store_ref_id: int | None = None,
    ) -> Optional[EventsOutbox]:
        """Cria uma linha no outbox com checagem de dedup via dedup_key.

        Retorna None se já existir (IntegrityError na unique constraint).
        """
        dedup_key = self._build_dedup_key(lead_id, pedido_id, destino, evento)
        row = EventsOutbox(
            lead_id=lead_id,
            pedido_id=pedido_id,
            store_ref_id=store_ref_id,
            destino=destino,
            evento=evento,
            dedup_key=dedup_key,
            event_time=event_time,
            payload_json=payload_json,
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

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------
    def get_pending(
        self, limit: int = 50, store_ref_id: int | None = None
    ) -> List[EventsOutbox]:
        """Busca linhas pendentes ordenadas por created_at ASC."""
        query = EventsOutbox.query.filter_by(status="pending")
        if store_ref_id is not None:
            query = query.filter(EventsOutbox.store_ref_id == store_ref_id)
        return query.order_by(EventsOutbox.created_at.asc()).limit(limit).all()

    def get_failed_retryable(
        self,
        limit: int = 50,
        min_updated_age_seconds: int | None = None,
        store_ref_id: int | None = None,
    ) -> List[EventsOutbox]:
        """Busca linhas failed retryáveis (attempts < 3, error_type='retryable')."""
        query = EventsOutbox.query.filter_by(
            status="failed", error_type="retryable"
        ).filter(EventsOutbox.attempts < 3)
        if store_ref_id is not None:
            query = query.filter(EventsOutbox.store_ref_id == store_ref_id)
        if min_updated_age_seconds:
            cutoff = datetime_now_brazil() - timedelta(seconds=min_updated_age_seconds)
            query = query.filter(EventsOutbox.updated_at <= cutoff)
        return query.order_by(EventsOutbox.updated_at.asc()).limit(limit).all()

    # ------------------------------------------------------------------
    # Atualização de status
    # ------------------------------------------------------------------
    def mark_sent(
        self,
        entry_id: int,
        sent_at: datetime,
        response: dict | None = None,
    ) -> Optional[EventsOutbox]:
        """Marca status='sent' e sent_at."""
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
        attempts: int,
        status_code: int | None = None,
        error_type: str = "retryable",
    ) -> Optional[EventsOutbox]:
        """Marca status='failed', last_error e attempts."""
        entry = self.get_by_id(entry_id)
        if not entry:
            return None
        entry.status = "failed"
        entry.attempts = attempts
        entry.updated_at = datetime_now_brazil()
        error_with_code = f"[HTTP {status_code}] {error}" if status_code else error
        entry.last_error = error_with_code[:1000]
        db.session.commit()
        return entry
