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
from app.repositories.meta_capi_lead_outbox_repository import MetaCapiLeadOutboxRepository
from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository
from app.repositories.pedido_repository import PedidoRepository
from app.services.meta_capi import MetaConversionsApiService
from app.utils.meta_capi_helper import should_skip_purchase_for_meta_capi

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
        self.lead_outbox_repo = MetaCapiLeadOutboxRepository()
        # Instância default (tenant None) só para helpers puros: sanitize/classify.
        # O ENVIO usa uma instância por tenant (pixel/token da própria loja), nunca
        # um único token para lotes de lojas diferentes (invariante da Fase D).
        self.service = MetaConversionsApiService()
        self._services: dict = {}

    def _service_for(self, store_ref_id):
        """Serviço Meta da loja da linha, cacheado durante o ciclo."""
        svc = self._services.get(store_ref_id)
        if svc is None:
            svc = MetaConversionsApiService(store_ref_id=store_ref_id)
            self._services[store_ref_id] = svc
        return svc

    def _partition_by_store(self, batch: list, stats: dict, *, lead: bool) -> dict:
        """Agrupa entries por ``store_ref_id`` para envio isolado por tenant.

        Linhas de empresa inativa são invalidadas aqui (falha permanente,
        `store_inactive`) e não entram em nenhum grupo de envio — aplica a
        política de descarte da Fase D às linhas já pendentes.
        """
        from app.services.tenancy import is_store_inactive

        fperm_key = "lead_failed_permanent" if lead else "failed_permanent"
        repo = self.lead_outbox_repo if lead else self.outbox_repo
        groups: dict = {}
        for entry in batch:
            store_ref_id = getattr(entry, "store_ref_id", None)
            if is_store_inactive(store_ref_id):
                repo.mark_failed(entry.id, "store_inactive", 0, "permanent", entry.attempts)
                stats[fperm_key] += 1
                continue
            groups.setdefault(store_ref_id, []).append(entry)
        return groups

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
            "failed_permanent": 0,
            "failed_retryable": 0,
            "errors": [],
            "lead_pending_processed": 0,
            "lead_failed_retryable_processed": 0,
            "lead_sent_success": 0,
            "lead_sent_failed": 0,
            "lead_failed_permanent": 0,
            "lead_failed_retryable": 0,
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

            print("[META_CAPI] Processando outbox de leads (Contact/Lead)...")
            self._process_lead_outbox_batch(stats, limit=50)

            print(
                "[META_CAPI] Ciclo completo — "
                f"Purchase: enviados_ok={stats['sent_success']} falhas={stats['sent_failed']}; "
                f"Lead (Contact/Lead): enviados_ok={stats['lead_sent_success']} "
                f"falhas={stats['lead_sent_failed']}",
                flush=True,
            )
            print(f"[META_CAPI] Stats detalhadas: {stats}", flush=True)
            return stats

        except Exception as e:
            error_msg = f"Erro fatal no command: {str(e)}"
            print(f"[ERROR] {error_msg}")
            stats["errors"].append(error_msg)
            import traceback

            traceback.print_exc()
            return stats

    def process_outbox_cycle(
        self,
        limit: int = 50,
        retry_backoff_seconds: int = 0,
        quiet: bool = False,
        store_ref_id: int | None = None,
    ) -> dict:
        """
        Ciclo leve do worker async: processa apenas pendentes + failed-retryable
        (Purchase e Lead), SEM o safety-net diário de "buscar novos purchases".

        Pensado para rodar a cada poucos segundos no `capi-worker`. O envio em si
        reusa `_process_pending_batch` (Purchase) e `_process_lead_outbox_batch`
        (Contact/Lead). `retry_backoff_seconds` evita queimar as 3 tentativas de um
        registro retryable em poucos segundos (só retenta após esse intervalo).

        Args:
            limit: Limite de registros por lote.
            retry_backoff_seconds: Idade mínima (s) de `updated_at` para reprocessar
                um failed-retryable. 0 = sem backoff (retenta na hora).
            quiet: Quando True, não imprime nada nos ciclos ociosos (sem pendências).
                Usado pelo polling do capi-worker para não poluir o log a cada 5s.

        Returns:
            dict: Estatísticas do ciclo (mesmas chaves de execute()).
        """
        stats = {
            "pending_processed": 0,
            "failed_retryable_processed": 0,
            "sent_success": 0,
            "sent_failed": 0,
            "failed_permanent": 0,
            "failed_retryable": 0,
            "errors": [],
            "lead_pending_processed": 0,
            "lead_failed_retryable_processed": 0,
            "lead_sent_success": 0,
            "lead_sent_failed": 0,
            "lead_failed_permanent": 0,
            "lead_failed_retryable": 0,
        }
        self._process_pending_batch(
            stats,
            limit=limit,
            retry_backoff_seconds=retry_backoff_seconds,
            quiet=quiet,
            store_ref_id=store_ref_id,
        )
        self._process_lead_outbox_batch(
            stats,
            limit=limit,
            retry_backoff_seconds=retry_backoff_seconds,
            quiet=quiet,
            store_ref_id=store_ref_id,
        )
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

        return [pedido for pedido in pedidos if not should_skip_purchase_for_meta_capi(pedido)]

    def _process_pending_batch(
        self,
        stats: dict,
        limit: int = 50,
        retry_backoff_seconds: int = 0,
        quiet: bool = False,
        store_ref_id: int | None = None,
    ):
        """
        Processa lote interno de pendentes e failed retryáveis

        Nota: Este é um "lote interno" para organização, não Graph Batch API.
        Pode enviar até ~1000 eventos por request Meta (usar 50 por segurança).

        Args:
            stats: Dicionário de estatísticas (atualizado in-place)
            limit: Limite de registros por lote (padrão: 50)
            retry_backoff_seconds: Idade mínima de `updated_at` para reprocessar um
                failed-retryable (0 = sem backoff).
            quiet: Suprime o log de "nenhum registro pendente" (polling do worker).
            store_ref_id: Se informado, filtra apenas por esta loja.
        """
        # Buscar pendentes
        pending = self.outbox_repo.get_pending(limit=limit, store_ref_id=store_ref_id)
        stats["pending_processed"] = len(pending)

        # Buscar failed retryáveis
        failed_retryable = self.outbox_repo.get_failed_retryable(
            limit=limit,
            min_updated_age_seconds=retry_backoff_seconds or None,
            store_ref_id=store_ref_id,
        )
        stats["failed_retryable_processed"] = len(failed_retryable)

        # Combinar todos os registros para processar
        all_to_process = pending + failed_retryable

        if not all_to_process:
            if not quiet:
                print("[META_CAPI] Nenhum registro pendente para processar")
            return

        print(f"[META_CAPI] Processando {len(all_to_process)} registros...")

        # Processar em lotes
        batch_size = 50  # Lote interno (não Graph Batch API)
        for i in range(0, len(all_to_process), batch_size):
            batch = all_to_process[i : i + batch_size]
            self._send_batch(batch, stats)

    def _send_batch(self, batch: list, stats: dict):
        """Envia um lote agrupado por tenant, uma instância/token Meta por loja."""
        for store_ref_id, entries in self._partition_by_store(batch, stats, lead=False).items():
            print(
                f"[META_CAPI] Grupo Purchase store_ref_id={store_ref_id}: "
                f"{len(entries)} linha(s)",
                flush=True,
            )
            self._send_batch_group(self._service_for(store_ref_id), entries, stats)

    def _send_batch_group(self, service, batch: list, stats: dict):
        """
        Envia um lote de eventos de UMA loja para Meta

        Args:
            service: MetaConversionsApiService já configurado com o tenant do grupo
            batch: Lista de MetaCapiOutbox (mesmo store_ref_id) para enviar
            stats: Dicionário de estatísticas (atualizado in-place)
        """
        # Reconstruir eventos a partir do payload_json
        events = []
        outbox_map = {}  # Mapear event_id -> outbox_entry

        for entry in batch:
            try:
                pedido = Pedido.query.get(entry.order_id)
                if pedido and should_skip_purchase_for_meta_capi(pedido):
                    reason = "Ignorado por origem site/nuvemshop"
                    print(f"[META_CAPI] {reason}: pedido #{pedido.id}")
                    self.outbox_repo.mark_failed(entry.id, reason, 0, "permanent", entry.attempts)
                    stats["failed_permanent"] += 1
                    continue

                # Parse payload JSON
                payload = json.loads(entry.payload_json)
                event = {
                    "event_name": payload["event_name"],
                    "event_time": payload["event_time"],
                    "event_id": payload["event_id"],
                    "action_source": payload["action_source"],
                    "event_source_url": payload.get("event_source_url"),
                    "user_data": payload.get("user_data", {}),
                    "custom_data": payload["custom_data"],
                }
                events.append(service.sanitize_event_payload(event))
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

        # Enviar para Meta (token/pixel do tenant deste grupo)
        print(f"[META_CAPI] Enviando {len(events)} eventos para Meta...")
        response = service.send_events(events)

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
            error_type, is_retryable = service.classify_error(response, status_code)

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
                    if is_retryable:
                        stats["failed_retryable"] += 1
                    else:
                        stats["failed_permanent"] += 1

            stats["errors"].append(f"Batch failed: {error_msg}")

    def _process_lead_outbox_batch(
        self,
        stats: dict,
        limit: int = 50,
        retry_backoff_seconds: int = 0,
        quiet: bool = False,
        store_ref_id: int | None = None,
    ):
        pending = self.lead_outbox_repo.get_pending(limit=limit, store_ref_id=store_ref_id)
        stats["lead_pending_processed"] = len(pending)
        failed_retryable = self.lead_outbox_repo.get_failed_retryable(
            limit=limit,
            min_updated_age_seconds=retry_backoff_seconds or None,
            store_ref_id=store_ref_id,
        )
        stats["lead_failed_retryable_processed"] = len(failed_retryable)
        all_to_process = pending + failed_retryable
        if not all_to_process:
            if not quiet:
                print("[META_CAPI] Nenhum registro pendente na outbox de leads")
            return
        print(f"[META_CAPI] Processando {len(all_to_process)} registros (leads)...")
        batch_size = 50
        for i in range(0, len(all_to_process), batch_size):
            batch = all_to_process[i : i + batch_size]
            self._send_lead_batch(batch, stats)

    def _send_lead_batch(self, batch: list, stats: dict):
        """Envia lote de leads agrupado por tenant, uma instância/token por loja."""
        for store_ref_id, entries in self._partition_by_store(batch, stats, lead=True).items():
            print(
                f"[META_CAPI] Grupo Lead store_ref_id={store_ref_id}: " f"{len(entries)} linha(s)",
                flush=True,
            )
            self._send_lead_batch_group(self._service_for(store_ref_id), entries, stats)

    def _send_lead_batch_group(self, service, batch: list, stats: dict):
        events = []
        outbox_map = {}

        for entry in batch:
            try:
                payload = json.loads(entry.payload_json)
                event = {
                    "event_name": payload["event_name"],
                    "event_time": payload["event_time"],
                    "event_id": payload["event_id"],
                    "action_source": payload["action_source"],
                    "event_source_url": payload.get("event_source_url"),
                    "user_data": payload.get("user_data", {}),
                    "custom_data": payload["custom_data"],
                }
                events.append(service.sanitize_event_payload(event))
                outbox_map[entry.event_id] = entry
            except Exception as e:
                error_msg = f"Erro ao parsear payload lead outbox #{entry.id}: {str(e)}"
                print(f"[ERROR] {error_msg}")
                stats["errors"].append(error_msg)
                self.lead_outbox_repo.mark_failed(
                    entry.id, error_msg, 0, "permanent", entry.attempts + 1
                )
                stats["lead_sent_failed"] += 1

        if not events:
            print("[META_CAPI] Nenhum evento lead válido para enviar no lote")
            return

        print(f"[META_CAPI] Enviando {len(events)} eventos (leads) para Meta...")
        response = service.send_events(events)
        status_code = response.get("_status_code", 200)
        sent_at = datetime_now_brazil()

        if status_code == 200 and "events_received" in response:
            events_received = response.get("events_received", 0)
            fbtrace_id = response.get("fbtrace_id", "")
            print(
                f"[META_CAPI] Leads: sucesso — {events_received} eventos (fbtrace_id: {fbtrace_id})"
            )
            for entry in batch:
                if entry.event_id in outbox_map:
                    self.lead_outbox_repo.mark_sent(entry.id, sent_at, response)
                    stats["lead_sent_success"] += 1
        else:
            error_type, is_retryable = service.classify_error(response, status_code)
            error_detail = response.get("details", response.get("error", {}))
            meta_error = None
            if isinstance(error_detail, dict) and "error" in error_detail:
                meta_error = error_detail.get("error")
            else:
                meta_error = error_detail
            if isinstance(meta_error, dict):
                error_msg = meta_error.get("message", response.get("_error", "Erro desconhecido"))
            else:
                error_msg = response.get("_error") or str(meta_error) or "Erro desconhecido"
            print(f"[META_CAPI] Erro leads {status_code}: {error_msg}")
            for entry in batch:
                if entry.event_id in outbox_map:
                    new_attempts = entry.attempts + 1 if is_retryable else entry.attempts
                    self.lead_outbox_repo.mark_failed(
                        entry.id, error_msg, status_code, error_type, new_attempts
                    )
                    stats["lead_sent_failed"] += 1
                    if is_retryable:
                        stats["lead_failed_retryable"] += 1
                    else:
                        stats["lead_failed_permanent"] += 1
            stats["errors"].append(f"Lead batch failed: {error_msg}")
