# -*- coding: utf-8 -*-
"""
Command para enviar compras diárias para Meta Conversions API
Safety net + processamento de pendentes/failed retryáveis
"""
import json
from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from app.config import Config
from app.models.pedido import Pedido, datetime_now_brazil
from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository
from app.repositories.pedido_repository import PedidoRepository
from app.services.meta_capi import MetaConversionsApiService

# Timezone do Brasil
TIMEZONE_BRASIL = ZoneInfo("America/Sao_Paulo")


class SendDailyPurchasesToMetaCommand:
    """
    Command para enviar compras diárias para Meta Conversions API

    Responsabilidades:
    - Safety Net: Buscar pedidos do dia que mudaram para status_pagamento = Pago ou Parcial
      e criar outbox faltante (caso hook tenha falhado)
    - Processar lote interno de pendentes/failed retryáveis
    - Retry com classificação de erros
    - Logging detalhado (incluindo fbtrace_id)
    """

    def __init__(self):
        self.pedido_repo = PedidoRepository()
        self.outbox_repo = MetaCapiOutboxRepository()
        self.service = MetaConversionsApiService()

    def execute(self) -> dict:
        """
        Execução principal do command

        Returns:
            dict: Resultado da execução com estatísticas
        """
        print("[META_CAPI] Iniciando envio de compras diárias para Meta...")

        # Data de hoje em America/Sao_Paulo
        hoje = datetime.now(TIMEZONE_BRASIL).date()

        # Estatísticas
        stats = {
            "date": hoje.isoformat(),
            "new_purchases_found": 0,
            "outbox_created": 0,
            "pending_processed": 0,
            "failed_retryable_processed": 0,
            "sent_success": 0,
            "sent_failed": 0,
            "errors": [],
        }

        try:
            # Fase 1: Safety Net - Buscar novos purchases do dia
            print(f"[META_CAPI] Buscando novos purchases do dia {hoje}...")
            new_purchases = self._find_new_purchases(hoje)
            stats["new_purchases_found"] = len(new_purchases)

            # Criar outbox para novos purchases que ainda não estão na outbox
            for pedido in new_purchases:
                existing = self.outbox_repo.get_by_order_id(pedido.id)
                if not existing:
                    try:
                        self.outbox_repo.create_from_pedido(pedido)
                        stats["outbox_created"] += 1
                        print(f"[META_CAPI] Outbox criada para pedido #{pedido.id}")
                    except Exception as e:
                        error_msg = f"Erro ao criar outbox para pedido #{pedido.id}: {str(e)}"
                        print(f"[ERROR] {error_msg}")
                        stats["errors"].append(error_msg)

            # Fase 2: Processar pendentes e failed retryáveis
            print("[META_CAPI] Processando pendentes e failed retryáveis...")
            self._process_pending_batch(stats, limit=50)

            print(f"[META_CAPI] Concluído. Stats: {stats}")
            return stats

        except Exception as e:
            error_msg = f"Erro fatal no command: {str(e)}"
            print(f"[ERROR] {error_msg}")
            stats["errors"].append(error_msg)
            import traceback

            traceback.print_exc()
            return stats

    def _find_new_purchases(self, target_date: date) -> list:
        """
        Busca novos purchases do dia

        Usar paid_at se existir, senão updated_at quando status mudou.
        Janela: [00:00:00, 23:59:59] em America/Sao_Paulo.

        Args:
            target_date: Data alvo

        Returns:
            Lista de Pedidos com status_pagamento='Pago' OU 'Parcial'
        """
        # Início do dia (00:00:00) em America/Sao_Paulo
        inicio_datetime = datetime.combine(target_date, datetime.min.time(), tzinfo=TIMEZONE_BRASIL)

        # Fim do dia (23:59:59) em America/Sao_Paulo
        fim_datetime = datetime.combine(
            target_date, datetime.max.time().replace(microsecond=0), tzinfo=TIMEZONE_BRASIL
        )

        # Buscar pedidos do dia que são purchases
        # Filtrar por status_pagamento='Pago' OU 'Parcial' (case-insensitive)
        # Não verificar status='concluido' porque pode agendar para ano que vem
        # Usar updated_at (quando status_pagamento mudou) como referência
        # SQLite é case-insensitive por padrão, mas vamos usar func.upper() para garantir
        from sqlalchemy import func

        pedidos = (
            Pedido.query.filter(
                func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
                Pedido.updated_at >= inicio_datetime,
                Pedido.updated_at <= fim_datetime,
                Pedido.deleted_at.is_(None),  # Excluir soft-deleted
            )
            .order_by(Pedido.updated_at.desc())
            .all()
        )

        return pedidos

    def _process_pending_batch(self, stats: dict, limit: int = 50):
        """
        Processa lote interno de pendentes e failed retryáveis

        Nota: Este é um "lote interno" para organização, não Graph Batch API.
        Pode enviar até ~1000 eventos por request Meta (usar 50 por segurança).

        Args:
            stats: Dicionário de estatísticas (atualizado in-place)
            limit: Limite de registros por lote (padrão: 50)
        """
        # Buscar pendentes
        pending = self.outbox_repo.get_pending(limit=limit)
        stats["pending_processed"] = len(pending)

        # Buscar failed retryáveis
        failed_retryable = self.outbox_repo.get_failed_retryable(limit=limit)
        stats["failed_retryable_processed"] = len(failed_retryable)

        # Combinar todos os registros para processar
        all_to_process = pending + failed_retryable

        if not all_to_process:
            print("[META_CAPI] Nenhum registro pendente para processar")
            return

        print(f"[META_CAPI] Processando {len(all_to_process)} registros...")

        # Processar em lotes
        batch_size = 50  # Lote interno (não Graph Batch API)
        for i in range(0, len(all_to_process), batch_size):
            batch = all_to_process[i : i + batch_size]
            self._send_batch(batch, stats)

    def _send_batch(self, batch: list, stats: dict):
        """
        Envia um lote de eventos para Meta

        Args:
            batch: Lista de MetaCapiOutbox para enviar
            stats: Dicionário de estatísticas (atualizado in-place)
        """
        # Reconstruir eventos a partir do payload_json
        events = []
        outbox_map = {}  # Mapear event_id -> outbox_entry

        for entry in batch:
            try:
                # Parse payload JSON
                payload = json.loads(entry.payload_json)
                event = {
                    "event_name": payload["event_name"],
                    "event_time": payload["event_time"],
                    "event_id": payload["event_id"],
                    "action_source": payload["action_source"],
                    "user_data": payload.get("user_data", {}),
                    "custom_data": payload["custom_data"],
                }
                events.append(self.service.sanitize_event_payload(event))
                outbox_map[entry.event_id] = entry
            except Exception as e:
                error_msg = f"Erro ao parsear payload de outbox #{entry.id}: {str(e)}"
                print(f"[ERROR] {error_msg}")
                stats["errors"].append(error_msg)
                # Marcar como failed permanente
                self.outbox_repo.mark_failed(
                    entry.id, error_msg, 0, "permanent", entry.attempts + 1
                )
                stats["sent_failed"] += 1

        if not events:
            print("[META_CAPI] Nenhum evento válido para enviar no lote")
            return

        # Diagnóstico rápido de event_time (evitar timestamps futuros)
        try:
            import time

            now_ts = int(time.time())
            max_future = now_ts + (7 * 24 * 60 * 60)
            min_past = now_ts - (7 * 24 * 60 * 60)
            event_times = [e.get("event_time") for e in events if e.get("event_time")]
            if event_times:
                max_event_time = max(event_times)
                min_event_time = min(event_times)
                out_of_range = [t for t in event_times if t > max_future or t < min_past]
                if out_of_range:
                    print(
                        "[META_CAPI] AVISO: event_time fora da janela de 7 dias",
                        {
                            "min_event_time": min_event_time,
                            "max_event_time": max_event_time,
                            "out_of_range_count": len(out_of_range),
                        },
                    )
        except Exception:
            pass

        # Enviar para Meta
        print(f"[META_CAPI] Enviando {len(events)} eventos para Meta...")
        response = self.service.send_events(events)

        # Processar resposta
        status_code = response.get("_status_code", 200)
        sent_at = datetime_now_brazil()

        if status_code == 200 and "events_received" in response:
            # Sucesso
            events_received = response.get("events_received", 0)
            fbtrace_id = response.get("fbtrace_id", "")

            print(
                f"[META_CAPI] Sucesso: {events_received} eventos recebidos (fbtrace_id: {fbtrace_id})"
            )

            # Marcar todos como sent
            for entry in batch:
                if entry.event_id in outbox_map:
                    self.outbox_repo.mark_sent(entry.id, sent_at, response)
                    stats["sent_success"] += 1

        else:
            # Erro
            error_type, is_retryable = self.service.classify_error(response, status_code)

            # Capturar mensagem detalhada da Meta
            error_detail = response.get("details", response.get("error", {}))
            meta_error = None
            if isinstance(error_detail, dict) and "error" in error_detail:
                meta_error = error_detail.get("error")
            else:
                meta_error = error_detail

            if isinstance(meta_error, dict):
                error_msg = meta_error.get("message", response.get("_error", "Erro desconhecido"))
                error_code = meta_error.get("code", "")
                error_subcode = meta_error.get("error_subcode", "")
                error_type_meta = meta_error.get("type", "")

                if error_code:
                    error_msg = f"[{error_code}] {error_msg}"
                if error_subcode:
                    error_msg += f" (subcode: {error_subcode})"
                if error_type_meta:
                    error_msg += f" (type: {error_type_meta})"
            else:
                error_msg = response.get("_error") or str(meta_error) or "Erro desconhecido"

            print(f"[META_CAPI] Erro {status_code}: {error_msg}")
            print(f"[META_CAPI] Tipo: {error_type}, Retryable: {is_retryable}")

            # Se for 400, mostrar mais detalhes (sem expor dados sensíveis)
            if status_code == 400:
                # Mostrar apenas estrutura do erro, não dados completos
                details = response.get("details", {})
                meta_error_detail = None
                if isinstance(details, dict):
                    meta_error_detail = details.get("error")

                error_summary = {
                    "status_code": status_code,
                    "error_code": meta_error_detail.get("code")
                    if isinstance(meta_error_detail, dict)
                    else None,
                    "error_subcode": meta_error_detail.get("error_subcode")
                    if isinstance(meta_error_detail, dict)
                    else None,
                    "error_type": meta_error_detail.get("type")
                    if isinstance(meta_error_detail, dict)
                    else None,
                    "error_user_title": meta_error_detail.get("error_user_title")
                    if isinstance(meta_error_detail, dict)
                    else None,
                    "error_user_msg": meta_error_detail.get("error_user_msg")
                    if isinstance(meta_error_detail, dict)
                    else None,
                    "message": error_msg,
                }
                print(
                    f"[META_CAPI] Detalhes do erro 400: {json.dumps(error_summary, indent=2, ensure_ascii=False)}"
                )

                # Log adicional para debug (apenas estrutura, sem dados sensíveis)
                if Config.DEBUG:
                    # Mostrar apenas estrutura dos eventos (sem dados sensíveis)
                    events_summary = []
                    for event in events[:3]:  # Apenas primeiros 3 para não poluir
                        event_summary = {
                            "event_name": event.get("event_name"),
                            "event_id": event.get("event_id"),
                            "action_source": event.get("action_source"),
                            "has_user_data": bool(event.get("user_data")),
                            "has_custom_data": bool(event.get("custom_data")),
                        }
                        events_summary.append(event_summary)
                    print(
                        f"[META_CAPI] Estrutura dos eventos enviados: {json.dumps(events_summary, indent=2, ensure_ascii=False)}"
                    )

            # Marcar todos como failed
            for entry in batch:
                if entry.event_id in outbox_map:
                    new_attempts = entry.attempts + 1 if is_retryable else entry.attempts
                    self.outbox_repo.mark_failed(
                        entry.id, error_msg, status_code, error_type, new_attempts
                    )
                    stats["sent_failed"] += 1

            stats["errors"].append(f"Batch failed: {error_msg}")
