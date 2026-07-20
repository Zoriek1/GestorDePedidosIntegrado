"""
Servicos de integracao Nuvemshop (OAuth e importacao de pedidos).
"""

import json
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

import requests
from sqlalchemy.exc import IntegrityError

from app import db
from app.integrations.nuvemshop.client import NuvemshopClient
from app.integrations.nuvemshop.mapper import map_nuvemshop_order_to_pedido_data
from app.models import FontePedido, Pedido
from app.models.cliente import Cliente
from app.models.nuvemshop_store import NuvemshopStore
from app.models.nuvemshop_webhook_delivery import NuvemshopWebhookDelivery
from app.models.pedido import datetime_now_brazil
from app.models.pedido_external_ref import PedidoExternalRef
from app.models.pedido_manual_override import PedidoManualOverride

logger = logging.getLogger(__name__)

# Serialização por pedido externo. Cada webhook é processado em sua própria thread
# (Ack-First, Process-Later em routes/nuvemshop.py). Sem isso, order/created e
# order/paid do MESMO pedido rodam em paralelo, ambos veem "ref inexistente" e
# ambos criam um Pedido → duplicata (um pendente, um pago). O lock serializa as
# threads do mesmo processo; a UniqueConstraint do PedidoExternalRef + o fallback
# de IntegrityError cobrem corridas entre processos (múltiplos workers).
_order_locks_guard = threading.Lock()
_order_locks: Dict[str, threading.Lock] = {}


def _get_order_lock(key: str) -> threading.Lock:
    with _order_locks_guard:
        lock = _order_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _order_locks[key] = lock
        return lock


class NuvemshopTokenService:
    TOKEN_URL = "https://www.tiendanube.com/apps/authorize/token"

    @staticmethod
    def exchange_code(
        code: str,
        app_id: str,
        client_secret: str,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Troca o `code` por `access_token` via endpoint da Nuvemshop/Tiendanube.

        Nota: apesar de alguns exemplos omitirem, o endpoint pode exigir `grant_type`.
        """
        data: Dict[str, Any] = {
            "client_id": app_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }
        if redirect_uri:
            data["redirect_uri"] = redirect_uri

        response = requests.post(
            NuvemshopTokenService.TOKEN_URL,
            data=data,
            headers={"Accept": "application/json"},
            timeout=20,
        )

        # Alguns ambientes retornam JSON com content-type text/html; não confiar no header.
        try:
            payload = response.json()
        except Exception:
            payload = {"raw_text": (response.text or "")[:1000]}

        payload["_status_code"] = response.status_code
        return payload


class NuvemshopOrderImporter:
    def __init__(self, store: NuvemshopStore, user_agent: str) -> None:
        self.store = store
        self.user_agent = user_agent
        self.client = NuvemshopClient(
            store_id=store.store_id,
            access_token=store.access_token,
            user_agent=user_agent,
        )

    def process_pending(self, limit: int = 50) -> Tuple[int, int]:
        deliveries = (
            NuvemshopWebhookDelivery.query.filter_by(status="pending")
            .order_by(NuvemshopWebhookDelivery.received_at.asc())
            .limit(limit)
            .all()
        )

        processed = 0
        failed = 0

        for delivery in deliveries:
            ok = self.process_delivery(delivery)
            if ok:
                processed += 1
            else:
                failed += 1

        return processed, failed

    def _fetch_order_with_cartinha_retry(
        self,
        order_id: str,
        attempts: int = 3,
        gap_seconds: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Busca o pedido na Nuvemshop, retentando se a "cartinha" (note/owner_note)
        ainda não chegou. A Nuvemshop às vezes propaga o `note` com atraso após
        o webhook order/created, então um único GET pode pegar o pedido sem a
        mensagem do cartão.

        Faz até `attempts` tentativas espaçadas por `gap_seconds`. Sai cedo se
        encontrar a cartinha. Se nenhum lookup tiver cartinha, retorna a última
        resposta (pode realmente ser um pedido sem cartinha — esperado).

        Janela total ≈ attempts × ~1s API + (attempts-1) × gap = ~13s com defaults.
        Seguro chamar daqui porque o webhook é processado em background thread
        (ack-first em routes/nuvemshop.py), sem afetar o ACK ao Nuvemshop.
        """
        last: Dict[str, Any] = {}
        for i in range(attempts):
            last = self.client.get_order(order_id)
            if last and (last.get("note") or last.get("owner_note")):
                if i > 0:
                    logger.info(
                        f"[NUVEMSHOP] cartinha encontrada na tentativa {i + 1} para order {order_id}"
                    )
                return last
            if i < attempts - 1:
                time.sleep(gap_seconds)
        logger.info(
            f"[NUVEMSHOP] cartinha vazia após {attempts} tentativas para order {order_id} "
            f"(pode ser pedido sem cartinha)"
        )
        return last

    def process_delivery(self, delivery: NuvemshopWebhookDelivery) -> bool:
        try:
            if not self.store.active:
                return self._mark_failed(delivery, "store_inactive")

            if not delivery.event.startswith("order/"):
                return self._mark_processed(delivery)

            order_id = delivery.resource_id
            if not order_id:
                return self._mark_failed(delivery, "missing_order_id")

            order = self._fetch_order_with_cartinha_retry(order_id)
            # Custom fields vêm de endpoint separado na API Nuvemshop
            try:
                custom_fields = self.client.get_order_custom_fields(order_id)
                if custom_fields:
                    order["custom_fields"] = custom_fields
            except Exception as exc:
                logger.debug(f"Custom fields não disponíveis para order {order_id}: {exc}")

            delivery.order_json = json.dumps(order, ensure_ascii=False)

            (
                pedido_data,
                schedule_pending,
                shipping_option_text,
                agendamento_source,
            ) = map_nuvemshop_order_to_pedido_data(order)

            self._apply_delivery_slot(pedido_data, order)

            pedido_data["endereco"] = self._compose_endereco(pedido_data)

            # Fonte sempre "Site" para pedidos importados da Nuvemshop
            # (o campo "canal" já indica a origem real: Site, Mercado Livre, PDV, etc)
            fonte = self._get_or_create_fonte("Site")
            pedido_data["fonte_pedido_id"] = fonte.id
            pedido_data["fonte_pedido"] = "Site"

            # Vincular ou criar cliente automaticamente
            cliente_id = self._get_or_create_cliente(pedido_data)
            if cliente_id:
                pedido_data["cliente_id"] = cliente_id

            # Loja pode ter um vendedor padrao persistido para atribuir
            # automaticamente pedidos novos no momento da importacao.
            self._apply_default_vendor(pedido_data)

            # UPSERT idempotente por (provider, store_id, external_order_id),
            # serializado por pedido para fechar a corrida created↔paid.
            order_key = f"{self.store.store_id}:{order.get('id')}"
            with _get_order_lock(order_key):
                external_ref = self._get_external_ref(order)
                if external_ref:
                    logger.info(
                        "[NUVEMSHOP] order=%s já existe (pedido_id=%s) — "
                        "atualizando via event=%s.",
                        order.get("id"),
                        external_ref.pedido_id,
                        delivery.event,
                    )
                    self._update_existing_pedido(
                        external_ref, pedido_data, schedule_pending, agendamento_source
                    )
                else:
                    try:
                        pedido = self._create_pedido_with_ref(
                            order, pedido_data, fonte.id, schedule_pending, agendamento_source
                        )
                    except IntegrityError:
                        # Outro processo/worker criou o ref entre o SELECT e o
                        # INSERT (corrida entre processos). pedido+ref reverteram
                        # juntos (sem órfão); reabrimos e tratamos como update.
                        db.session.rollback()
                        external_ref = self._get_external_ref(order)
                        if not external_ref:
                            raise
                        logger.warning(
                            "[NUVEMSHOP] Corrida detectada para order=%s — ref criado "
                            "por outro evento; atualizando pedido_id=%s (event=%s).",
                            order.get("id"),
                            external_ref.pedido_id,
                            delivery.event,
                        )
                        self._update_existing_pedido(
                            external_ref, pedido_data, schedule_pending, agendamento_source
                        )
                    else:
                        logger.info(
                            "[NUVEMSHOP] order=%s criado como pedido_id=%s (event=%s).",
                            order.get("id"),
                            pedido.id,
                            delivery.event,
                        )
                        # Calcular distância automaticamente após criar pedido
                        self._calculate_distance_if_needed(pedido.id)

                        # Enviar push notification para novo pedido Nuvemshop
                        self._send_push_new_order(pedido)

                        # Se schedule_pending (sem custom fields ainda), agendar retry
                        if schedule_pending:
                            try:
                                from flask import current_app

                                app = current_app._get_current_object()
                                self._schedule_custom_fields_retry(order_id, pedido.id, app)
                            except Exception as exc:
                                logger.debug(f"Erro ao agendar retry para custom fields: {exc}")

            return self._mark_processed(delivery)
        except Exception as exc:
            db.session.rollback()
            return self._mark_failed(delivery, f"import_error: {type(exc).__name__}")

    def _compose_endereco(self, pedido_data: Dict[str, Any]) -> Optional[str]:
        parts = [
            pedido_data.get("rua"),
            pedido_data.get("numero"),
            pedido_data.get("complemento"),
            pedido_data.get("bairro"),
            pedido_data.get("cidade"),
            pedido_data.get("cep"),
        ]
        clean = [p for p in parts if p]
        return " - ".join(clean) if clean else None

    def _apply_delivery_slot(self, pedido_data: Dict[str, Any], order: Dict[str, Any]) -> None:
        """
        Calcula slot_inicio e slot_deadline para pedidos importados do site.
        Idempotente: ignora silenciosamente se faltar dia_entrega.
        """
        from app.integrations.nuvemshop.mapper import _parse_datetime
        from app.services.delivery_slot_allocator import (
            allocate_slot,
            parse_customer_window,
        )

        dia_entrega = pedido_data.get("dia_entrega")
        if not dia_entrega:
            return

        paid_at = _parse_datetime(order.get("created_at")) or datetime_now_brazil()
        customer_window = parse_customer_window(pedido_data.get("horario"))

        try:
            slot_inicio, slot_deadline = allocate_slot(
                dia_entrega=dia_entrega,
                paid_at_local=paid_at,
                is_expressa=bool(pedido_data.get("is_expressa")),
                customer_window=customer_window,
            )
        except Exception:
            logger.warning(
                "[NUVEMSHOP] Falha ao alocar slot — pedido segue sem slot.",
                exc_info=True,
            )
            return

        pedido_data["slot_inicio"] = slot_inicio
        pedido_data["slot_deadline"] = slot_deadline

    def _get_or_create_cliente(self, pedido_data: Dict[str, Any]) -> Optional[int]:
        """
        Busca ou cria cliente baseado no telefone.

        Args:
            pedido_data: Dados do pedido mapeado

        Returns:
            int: ID do cliente ou None se não foi possível criar
        """
        telefone = pedido_data.get("telefone_cliente")
        if not telefone or telefone == "0000000000":
            return None

        # Buscar cliente existente por telefone dentro da empresa da instalação.
        store_ref_id = getattr(self.store, "store_ref_id", None)
        cliente = Cliente.query.execution_options(include_all_tenants=True).filter(
            Cliente.store_ref_id == store_ref_id,
            Cliente.telefone == telefone,
        ).first()

        if not cliente:
            # Criar novo cliente
            nome = pedido_data.get("cliente") or "Cliente Nuvemshop"
            try:
                cliente = Cliente(
                    store_ref_id=store_ref_id,
                    nome=nome,
                    telefone=telefone,
                    email=None,  # Email será adicionado nas observações
                    observacoes="Criado automaticamente via importação Nuvemshop",
                )
                db.session.add(cliente)
                db.session.flush()  # Garantir que tem ID
                logger.info(f"Novo cliente criado via Nuvemshop: {nome} ({telefone})")
            except Exception as e:
                logger.warning(f"Falha ao criar cliente: {e}")
                return None

        return cliente.id

    def _get_or_create_fonte(self, nome: str) -> FontePedido:
        store_ref_id = getattr(self.store, "store_ref_id", None)
        fonte = FontePedido.query.execution_options(include_all_tenants=True).filter_by(
            nome=nome,
            store_ref_id=store_ref_id,
        ).first()
        if fonte:
            return fonte
        fonte = FontePedido(nome=nome, ativo=True, store_ref_id=store_ref_id)
        db.session.add(fonte)
        db.session.commit()
        return fonte

    def _apply_default_vendor(self, pedido_data: Dict[str, Any]) -> None:
        """Aplica o vendedor padrao da loja quando o pedido ainda nao tem vendedor."""
        if pedido_data.get("vendedor_id") is not None:
            return

        default_vendedor_id = getattr(self.store, "default_vendedor_id", None)
        if default_vendedor_id:
            from app.models.user import User

            valid = User.query.filter(
                User.id == default_vendedor_id,
                User.store_ref_id == getattr(self.store, "store_ref_id", None),
                User.role == "vendedor",
                User.is_active.is_(True),
            ).first()
            if valid:
                pedido_data["vendedor_id"] = default_vendedor_id
            else:
                logger.warning(
                    "[NUVEMSHOP] Vendedor padrão %s não pertence à empresa da instalação",
                    default_vendedor_id,
                )

    def _get_external_ref(self, order: Dict[str, Any]) -> Optional[PedidoExternalRef]:
        """
        Busca external_ref por external_order_id.
        Se não encontrar, tenta encontrar pedido duplicado por telefone + data próxima.
        """
        # Primeiro, tentar buscar por external_order_id (método padrão)
        external_ref = (
            PedidoExternalRef.query.execution_options(include_all_tenants=True).filter_by(
                store_ref_id=getattr(self.store, "store_ref_id", None),
                provider="nuvemshop",
                store_id=str(self.store.store_id),
                external_order_id=str(order.get("id")),
            )
            .order_by(PedidoExternalRef.id.desc())
            .first()
        )

        if external_ref:
            return external_ref

        # Se não encontrou, tentar detectar pedido duplicado por telefone + data próxima
        # Isso ajuda quando um pedido foi criado manualmente no painel antes de ser importado
        telefone = self._extract_phone_from_order(order)
        if not telefone or telefone == "0000000000":
            return None

        # Buscar pedidos criados nos últimos 10 minutos com mesmo telefone
        from datetime import timedelta

        created_at = self._parse_order_created_at(order)
        if not created_at:
            return None

        time_window_start = created_at - timedelta(minutes=10)
        time_window_end = created_at + timedelta(minutes=10)

        # Buscar pedidos sem external_ref que foram criados no mesmo período
        pedidos_duplicados = (
            Pedido.query.execution_options(include_all_tenants=True).filter(
                Pedido.store_ref_id == getattr(self.store, "store_ref_id", None),
                Pedido.telefone_cliente == telefone,
                Pedido.created_at >= time_window_start,
                Pedido.created_at <= time_window_end,
                ~Pedido.id.in_(
                    db.session.query(PedidoExternalRef.pedido_id).filter(
                        PedidoExternalRef.provider == "nuvemshop",
                        PedidoExternalRef.store_ref_id
                        == getattr(self.store, "store_ref_id", None),
                    )
                ),
            )
            .order_by(Pedido.created_at.desc())
            .limit(1)
            .all()
        )

        if pedidos_duplicados:
            pedido_duplicado = pedidos_duplicados[0]
            logger.info(
                f"[Duplicate Detection] Encontrado pedido duplicado #{pedido_duplicado.id} "
                f"para telefone {telefone} criado em {pedido_duplicado.created_at}"
            )
            # Criar external_ref para vincular o pedido existente
            external_ref = PedidoExternalRef(
                store_ref_id=getattr(self.store, "store_ref_id", None),
                provider="nuvemshop",
                store_id=str(self.store.store_id),
                external_order_id=str(order.get("id")),
                external_order_number=str(order.get("number")) if order.get("number") else None,
                order_token=str(order.get("token")) if order.get("token") else None,
                pedido_id=pedido_duplicado.id,
                schedule_pending=True,  # Será atualizado quando custom fields chegarem
                agendamento_source="duplicate_detection",
                needs_review=True,
            )
            db.session.add(external_ref)
            db.session.commit()
            return external_ref

        return None

    def _extract_phone_from_order(self, order: Dict[str, Any]) -> Optional[str]:
        """Extrai telefone normalizado do pedido da Nuvemshop."""
        from app.integrations.nuvemshop.mapper import _normalize_phone, _safe_str

        customer = order.get("customer") or {}
        shipping_address = order.get("shipping_address") or {}

        telefone = (
            _safe_str(order.get("contact_phone"))
            or _safe_str(customer.get("phone"))
            or _safe_str(order.get("billing_phone"))
            or _safe_str(shipping_address.get("phone"))
        )

        if telefone:
            return _normalize_phone(telefone)
        return None

    def _parse_order_created_at(self, order: Dict[str, Any]):
        """Parse da data de criação do pedido."""
        from app.integrations.nuvemshop.mapper import _parse_datetime

        created_at_str = order.get("created_at")
        if not created_at_str:
            return None

        return _parse_datetime(created_at_str)

    def _create_pedido_with_ref(
        self,
        order: Dict[str, Any],
        pedido_data: Dict[str, Any],
        fonte_id: int,
        schedule_pending: bool,
        agendamento_source: str = None,
    ) -> Pedido:
        """Cria Pedido + PedidoExternalRef na MESMA transação (atômico).

        Por que atômico: a UniqueConstraint
        (provider, store_id, external_order_id) do PedidoExternalRef é a fonte
        única de verdade contra duplicação. Commitando pedido e ref juntos, se
        outro evento/worker já gravou o ref (corrida), o commit levanta
        IntegrityError e AMBOS revertem — nunca sobra um Pedido órfão duplicado
        (era a causa do "um pendente + um pago"). O caller trata o IntegrityError
        como update.
        """
        from app.services.order_commission_lifecycle import apply_commission_lifecycle
        from app.services.order_number_allocator import allocate_order_number

        store_ref_id = getattr(self.store, "store_ref_id", None)
        pedido_data["store_ref_id"] = store_ref_id
        pedido_data["numero_pedido"] = allocate_order_number(store_ref_id)

        pedido = Pedido(**pedido_data)
        db.session.add(pedido)
        db.session.flush()  # garante pedido.id antes do lifecycle e do ref

        # Se o pedido já chega pago + com vendedor (caso raro mas possível em
        # webhook order/paid com atribuição prévia), gera a comissão.
        try:
            apply_commission_lifecycle(
                pedido,
                previous=None,
                actor_id=getattr(pedido, "vendedor_id", None),
            )
        except Exception:
            logger.warning(
                "[NUVEMSHOP] Falha em apply_commission_lifecycle no _create_pedido %s",
                pedido.id,
                exc_info=True,
            )

        ref = PedidoExternalRef(
            store_ref_id=store_ref_id,
            provider="nuvemshop",
            store_id=str(self.store.store_id),
            external_order_id=str(order.get("id")),
            external_order_number=str(order.get("number")) if order.get("number") else None,
            order_token=str(order.get("token")) if order.get("token") else None,
            pedido_id=pedido.id,
            schedule_pending=schedule_pending,
            agendamento_source=agendamento_source,
            needs_review=(agendamento_source == "fallback"),
        )
        db.session.add(ref)
        db.session.commit()  # pedido + ref num único commit (atômico)

        return pedido

    def _update_existing_pedido(
        self,
        external_ref: PedidoExternalRef,
        pedido_data: Dict[str, Any],
        schedule_pending: bool,
        agendamento_source: str = None,
    ) -> None:
        from app.services.order_commission_lifecycle import (
            apply_commission_lifecycle,
            snapshot_commission_fields,
        )

        pedido = Pedido.query.execution_options(include_all_tenants=True).filter(
            Pedido.id == external_ref.pedido_id,
            Pedido.store_ref_id == getattr(self.store, "store_ref_id", None),
        ).first()
        if not pedido:
            return

        # Snapshot ANTES de qualquer mutação — necessário para detectar
        # transições de status_pagamento (Pendente → Pago) e mudanças sensíveis
        # que exigem estorno.
        prev_snapshot = snapshot_commission_fields(pedido)

        # Buscar campos com override manual (não devem ser sobrescritos)
        overridden_fields = PedidoManualOverride.get_overridden_fields(pedido.id)

        # Atualizar campos relevantes sem sobrescrever dados manuais
        # SYNC DESCONECTADO (decisão do usuário): após criação, o status_pedido local
        # nunca é alterado pelo webhook Nuvemshop. Evita reverter pedidos que avançaram
        # localmente (Embalado, Em Rota, Entregue) para "agendado" quando o lojista
        # mexe no painel. Cancelamento explícito do Nuvemshop ainda vence — entra como
        # "cancelado" porque é uma operação destrutiva que precisa propagar.
        incoming_status = pedido_data.get("status")
        if incoming_status == "cancelado":
            status_update = "cancelado"
        else:
            status_update = pedido.status  # mantém o status local atual

        updates = {
            "status_pagamento": pedido_data.get("status_pagamento") or pedido.status_pagamento,
            "pagamento": pedido_data.get("pagamento") or pedido.pagamento,
            "status": status_update,
            "obs_entrega": pedido_data.get("obs_entrega") or pedido.obs_entrega,
            "observacoes": self._merge_observacoes(
                pedido.observacoes, pedido_data.get("observacoes")
            ),
            "updated_at": datetime_now_brazil(),
        }

        if getattr(pedido, "vendedor_id", None) is None and getattr(
            self.store, "default_vendedor_id", None
        ):
            updates["vendedor_id"] = self.store.default_vendedor_id

        # --- Campos críticos: preencher quando vazios/placeholder ---
        # Esses campos podem chegar vazios no order/created (pedido pendente)
        # e só ficarem disponíveis no order/paid ou order/updated.
        new_dest = pedido_data.get("destinatario") or ""
        if new_dest and new_dest != "Nao informado":
            cur_dest = pedido.destinatario or ""
            if not cur_dest or cur_dest == "Nao informado" or cur_dest == pedido.cliente:
                updates["destinatario"] = new_dest

        new_cliente = pedido_data.get("cliente") or ""
        if new_cliente and new_cliente != "Nao informado":
            if not pedido.cliente or pedido.cliente == "Nao informado":
                updates["cliente"] = new_cliente

        new_valor = pedido_data.get("valor") or ""
        if new_valor:
            cur_valor = pedido.valor or ""
            if not cur_valor or cur_valor in ("", "R$ 0,00", "R$ 0.00", "0.00"):
                updates["valor"] = new_valor

        new_produto = pedido_data.get("produto") or ""
        if new_produto and new_produto != "Produto Nuvemshop":
            if not pedido.produto or pedido.produto == "Produto Nuvemshop":
                updates["produto"] = new_produto

        new_tel = pedido_data.get("telefone_cliente") or ""
        if new_tel and new_tel != "0000000000":
            if not pedido.telefone_cliente or pedido.telefone_cliente == "0000000000":
                updates["telefone_cliente"] = new_tel

        # Se o pedido estava "schedule_pending" (data/hora ainda não confirmada),
        # permitir atualizar o agendamento quando a info chegar depois (ex.: custom fields).
        if external_ref.schedule_pending and not schedule_pending:
            if pedido_data.get("dia_entrega"):
                updates["dia_entrega"] = pedido_data.get("dia_entrega")
            if pedido_data.get("horario"):
                updates["horario"] = pedido_data.get("horario")
            # Quando a info do agendamento chega depois, o slot original foi
            # alocado com base em dados parciais — realocar agora que temos a info real.
            if pedido_data.get("slot_inicio") is not None:
                updates["slot_inicio"] = pedido_data.get("slot_inicio")
            if pedido_data.get("slot_deadline") is not None:
                updates["slot_deadline"] = pedido_data.get("slot_deadline")

        # is_expressa é determinístico pelos campos do pedido — atualiza sempre
        # (idempotente; o mesmo webhook sempre produz o mesmo valor).
        if "is_expressa" in pedido_data:
            updates["is_expressa"] = bool(pedido_data.get("is_expressa"))

        if pedido_data.get("endereco") and not pedido.endereco:
            updates["endereco"] = pedido_data.get("endereco")
            updates["rua"] = pedido_data.get("rua")
            updates["numero"] = pedido_data.get("numero")
            updates["bairro"] = pedido_data.get("bairro")
            updates["cidade"] = pedido_data.get("cidade")
            updates["cep"] = pedido_data.get("cep")

        for field in [
            "tipo_local",
            "nome_local",
            "apto",
            "bloco",
            "torre",
            "andar",
            "quadra",
            "lote",
            "complemento",
        ]:
            if pedido_data.get(field) and not getattr(pedido, field, None):
                updates[field] = pedido_data.get(field)

        # Adicionar campos de frete/canal se vieram no mapeamento
        for field in [
            "frete_cobrado_cliente",
            "desconto_frete",
            "frete_liquido_cliente",
            "plataforma",
            "canal",
        ]:
            if pedido_data.get(field) is not None:
                updates[field] = pedido_data.get(field)

        # Aplicar apenas campos que NÃO têm override manual
        for key, value in updates.items():
            if key in overridden_fields:
                # Campo tem override manual - NÃO sobrescrever
                continue
            if hasattr(pedido, key):
                setattr(pedido, key, value)

        # Nunca voltar para pending se já foi confirmado manualmente.
        if external_ref.schedule_pending and not schedule_pending:
            external_ref.schedule_pending = False
            external_ref.needs_review = False
        elif not external_ref.schedule_pending and schedule_pending:
            # manter False (confirmação manual vence)
            pass

        # Atualizar fonte do agendamento se disponível
        if agendamento_source:
            external_ref.agendamento_source = agendamento_source
            external_ref.needs_review = agendamento_source == "fallback"

        external_ref.updated_at = datetime_now_brazil()

        # Após todas as mutações: dispara o ciclo de vida de comissão.
        # Garante que pedidos do site/Nuvemshop transitando Pendente→Pago, com
        # mudança de vendedor, ou com edição de campos sensíveis, gerem ou
        # estornem comissão como qualquer outro pedido.
        try:
            apply_commission_lifecycle(
                pedido,
                previous=prev_snapshot,
                actor_id=getattr(pedido, "vendedor_id", None),
            )
        except Exception:
            logger.warning(
                "[NUVEMSHOP] Falha em apply_commission_lifecycle no _update_existing_pedido %s",
                pedido.id,
                exc_info=True,
            )

        db.session.commit()

    def _merge_observacoes(self, current: Optional[str], incoming: Optional[str]) -> Optional[str]:
        if not incoming:
            return current
        if not current:
            return incoming
        if incoming in current:
            return current
        return f"{current} | {incoming}"

    def _mark_processed(self, delivery: NuvemshopWebhookDelivery) -> bool:
        delivery.status = "processed"
        delivery.last_error = None
        delivery.processed_at = datetime_now_brazil()
        db.session.commit()
        return True

    def _mark_failed(self, delivery: NuvemshopWebhookDelivery, error: str) -> bool:
        delivery.status = "failed"
        delivery.last_error = error
        delivery.processed_at = datetime_now_brazil()
        db.session.commit()
        return False

    def _calculate_distance_if_needed(self, pedido_id: int) -> None:
        """
        Calcula distância do pedido automaticamente se tiver endereço válido.

        Args:
            pedido_id: ID do pedido para calcular distância
        """
        pedido = Pedido.query.execution_options(include_all_tenants=True).filter(
            Pedido.id == pedido_id,
            Pedido.store_ref_id == getattr(self.store, "store_ref_id", None),
        ).first()
        if not pedido:
            return

        # Só calcular se for entrega e tiver CEP ou endereço
        if pedido.tipo_pedido != "Entrega":
            logger.debug(f"Pedido #{pedido_id} é Retirada, não calculando distância")
            return

        # Precisa de rua e bairro no mínimo
        if not pedido.rua or not pedido.bairro:
            logger.debug(f"Pedido #{pedido_id} sem rua/bairro, não calculando distância")
            return

        try:
            from app.services.distancia import distancia_service

            resultado = distancia_service.calcular_distancia_pedido(
                pedido_id=pedido_id,
                rua=pedido.rua,
                numero=pedido.numero,
                bairro=pedido.bairro,
                cidade=pedido.cidade,
                cep=pedido.cep,
                cliente_id=pedido.cliente_id,
            )

            if resultado and "error" not in resultado:
                pedido.distancia_km = resultado.get("distancia_km")

                # Salvar coordenadas se disponíveis
                if resultado.get("coords_destino_lat"):
                    pedido.coords_lat = resultado.get("coords_destino_lat")
                if resultado.get("coords_destino_lon"):
                    pedido.coords_lon = resultado.get("coords_destino_lon")

                db.session.commit()
                logger.info(
                    f"Distância calculada para pedido #{pedido_id}: " f"{pedido.distancia_km} km"
                )
                # Enfileirar cálculo de frete (não altera lógica de distância)
                try:
                    from app.services.fila_taxa_entrega import enfileirar_calculo_taxa

                    enfileirar_calculo_taxa(pedido_id, pedido.store_ref_id)
                except Exception:
                    pass
            else:
                error_msg = (
                    resultado.get("error", "Erro desconhecido") if resultado else "Resultado vazio"
                )
                logger.warning(f"Falha ao calcular distância para pedido #{pedido_id}: {error_msg}")
        except ImportError:
            logger.debug("Serviço de distância não disponível")
        except Exception as e:
            logger.warning(f"Erro ao calcular distância para pedido #{pedido_id}: {e}")

    def _schedule_custom_fields_retry(
        self, order_id: str, pedido_id: int, app, delay_seconds: int = 5
    ) -> None:
        """
        Agenda uma tarefa para buscar novamente o pedido da API após delay,
        para capturar custom fields que podem chegar com alguns segundos de atraso.

        Args:
            order_id: ID do pedido na Nuvemshop
            pedido_id: ID do pedido interno
            app: Instância do Flask app (para contexto)
            delay_seconds: Delay em segundos antes de tentar novamente (padrão: 5s)
        """

        def _retry_worker():
            try:
                with app.app_context():
                    # Buscar pedido novamente da API
                    order = self.client.get_order(order_id)
                    if not order:
                        logger.debug(f"[Retry] Pedido {order_id} não encontrado na API")
                        return

                    # Custom fields vêm de endpoint separado
                    custom_fields = self.client.get_order_custom_fields(order_id)
                    if custom_fields:
                        order["custom_fields"] = custom_fields
                    has_custom_fields = bool(custom_fields)

                    if not has_custom_fields:
                        logger.debug(
                            f"[Retry] Pedido {order_id} ainda sem custom fields após {delay_seconds}s"
                        )
                        return

                    # Buscar external_ref e pedido
                    external_ref = PedidoExternalRef.query.execution_options(
                        include_all_tenants=True
                    ).filter_by(
                        store_ref_id=getattr(self.store, "store_ref_id", None),
                        provider="nuvemshop",
                        store_id=str(self.store.store_id),
                        external_order_id=str(order_id),
                        pedido_id=pedido_id,
                    ).first()

                    if not external_ref:
                        logger.debug(f"[Retry] ExternalRef não encontrado para pedido {pedido_id}")
                        return

                    # Mapear novamente e atualizar
                    (
                        pedido_data,
                        schedule_pending,
                        shipping_option_text,
                        agendamento_source,
                    ) = map_nuvemshop_order_to_pedido_data(order)

                    pedido_data["endereco"] = self._compose_endereco(pedido_data)

                    # Atualizar pedido com custom fields
                    self._update_existing_pedido(
                        external_ref, pedido_data, schedule_pending, agendamento_source
                    )

                    logger.info(
                        f"[Retry] Pedido {pedido_id} atualizado com custom fields após {delay_seconds}s"
                    )

            except Exception as exc:
                logger.warning(
                    f"[Retry] Erro ao buscar custom fields para pedido {pedido_id}: {exc}"
                )

        # Agendar tarefa em thread separada após delay
        timer = threading.Timer(delay_seconds, _retry_worker)
        timer.daemon = True
        timer.start()
        logger.debug(f"[Retry] Agendado retry para pedido {pedido_id} após {delay_seconds}s")

    def _send_push_new_order(self, pedido: Pedido) -> None:
        """Envia push notification para novo pedido importado da Nuvemshop."""
        try:
            from flask import current_app

            from app.services.notification_service import (
                format_delivery_datetime,
                send_push_to_all_async,
            )

            dest = pedido.destinatario or pedido.cliente or "Novo pedido"
            produto = pedido.produto or "Produto Nuvemshop"

            # Formatar data/hora de entrega
            entrega_info = format_delivery_datetime(pedido.dia_entrega, pedido.horario)
            if entrega_info:
                body = f"#{pedido.display_number} - {dest} | {produto} | Entrega: {entrega_info}"
            else:
                body = f"#{pedido.display_number} - {dest} | {produto}"

            send_push_to_all_async(
                app=current_app._get_current_object(),
                title="Novo Pedido Nuvemshop!",
                body=body,
                url="/",
                store_ref_id=pedido.store_ref_id,
            )
        except Exception as exc:
            logger.debug("Push notification não enviada: %s", exc)
