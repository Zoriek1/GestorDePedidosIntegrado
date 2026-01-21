# -*- coding: utf-8 -*-
"""
Repository para MetaCapiOutbox
Gerencia operações de outbox para eventos Meta Conversions API
"""
import json
from datetime import datetime
from typing import Dict, List, Optional

from app import db
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.models.pedido import Pedido, datetime_now_brazil
from app.repositories.base_repository import BaseRepository
from app.services.meta_capi import MetaConversionsApiService


class MetaCapiOutboxRepository(BaseRepository):
    """Repository para operações com MetaCapiOutbox"""

    def __init__(self):
        super().__init__(MetaCapiOutbox)
        self.service = MetaConversionsApiService()

    def get_by_order_id(self, order_id: int) -> Optional[MetaCapiOutbox]:
        """
        Verifica se já existe registro na outbox para um pedido

        Args:
            order_id: ID do pedido

        Returns:
            MetaCapiOutbox ou None se não existir
        """
        return self.model.query.filter_by(order_id=order_id).first()

    def create_from_pedido(self, pedido: Pedido) -> Optional[MetaCapiOutbox]:
        """
        Cria registro na outbox a partir de um pedido

        Verifica se já existe para evitar duplicação.
        Monta payload SEM PII em claro (apenas hashes).

        Args:
            pedido: Objeto Pedido

        Returns:
            MetaCapiOutbox criado, ou None se já existir
        """
        # Verificar se já existe
        existing = self.get_by_order_id(pedido.id)
        if existing:
            return None

        # Montar evento
        event = self.service.build_purchase_event(pedido)

        # Criar payload JSON (sem PII em claro)
        # O payload já contém apenas hashes, mas vamos garantir
        payload_safe = {
            "event_name": event["event_name"],
            "event_time": event["event_time"],
            "event_id": event["event_id"],
            "action_source": event["action_source"],
            "custom_data": event["custom_data"],
            # user_data já contém apenas hashes
            "user_data": event.get("user_data", {}),
        }

        # Timestamp do evento (usar updated_at quando status mudou, ou created_at)
        event_time = pedido.updated_at if pedido.updated_at else pedido.created_at

        # Criar registro
        outbox_entry = MetaCapiOutbox(
            order_id=pedido.id,
            event_id=f"order_{pedido.id}",
            event_time=event_time,
            payload_json=json.dumps(payload_safe),
            status="pending",
            attempts=0,
        )

        db.session.add(outbox_entry)
        db.session.commit()

        return outbox_entry

    def get_pending(self, limit: int = 50) -> List[MetaCapiOutbox]:
        """
        Busca registros pendentes para envio (lote interno)

        Args:
            limit: Limite de registros (padrão: 50)

        Returns:
            Lista de MetaCapiOutbox com status='pending'
        """
        return (
            self.model.query.filter_by(status="pending")
            .order_by(MetaCapiOutbox.created_at.asc())
            .limit(limit)
            .all()
        )

    def get_failed_retryable(self, limit: int = 50) -> List[MetaCapiOutbox]:
        """
        Busca registros failed com error_type='retryable' e attempts < 3

        Args:
            limit: Limite de registros (padrão: 50)

        Returns:
            Lista de MetaCapiOutbox com status='failed' e error_type='retryable'
        """
        return (
            self.model.query.filter_by(status="failed", error_type="retryable")
            .filter(MetaCapiOutbox.attempts < 3)
            .order_by(MetaCapiOutbox.updated_at.asc())
            .limit(limit)
            .all()
        )

    def mark_sent(
        self, id: int, sent_at: datetime, response: Optional[Dict] = None
    ) -> Optional[MetaCapiOutbox]:
        """
        Marca registro como enviado

        Guarda events_received e fbtrace_id para debug.

        Args:
            id: ID do registro na outbox
            sent_at: Data/hora de envio
            response: Resposta da API Meta (opcional)

        Returns:
            MetaCapiOutbox atualizado ou None se não encontrado
        """
        entry = self.get_by_id(id)
        if not entry:
            return None

        entry.status = "sent"
        entry.sent_at = sent_at
        entry.updated_at = datetime_now_brazil()

        # Guardar informações de debug na last_error (formato JSON)
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
        id: int,
        error: str,
        status_code: int,
        error_type: str,
        attempts: int,
    ) -> Optional[MetaCapiOutbox]:
        """
        Marca registro como falhou

        Guarda last_error com código HTTP e error_type.

        Args:
            id: ID do registro na outbox
            error: Mensagem de erro
            status_code: Código HTTP (se disponível)
            error_type: 'retryable' ou 'permanent'
            attempts: Número de tentativas (já incrementado)

        Returns:
            MetaCapiOutbox atualizado ou None se não encontrado
        """
        entry = self.get_by_id(id)
        if not entry:
            return None

        entry.status = "failed"
        entry.error_type = error_type
        entry.attempts = attempts
        entry.updated_at = datetime_now_brazil()

        # Guardar erro com código HTTP
        error_with_code = f"[HTTP {status_code}] {error}" if status_code else error
        entry.last_error = error_with_code

        db.session.commit()
        return entry
