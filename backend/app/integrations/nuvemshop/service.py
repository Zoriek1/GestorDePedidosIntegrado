"""
Servicos de integracao Nuvemshop (OAuth e importacao de pedidos).
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

import requests

from app import db
from app.integrations.nuvemshop.client import NuvemshopClient
from app.integrations.nuvemshop.mapper import map_nuvemshop_order_to_pedido_data
from app.models import FontePedido, Pedido
from app.models.cliente import Cliente
from app.models.nuvemshop_store import NuvemshopStore
from app.models.nuvemshop_webhook_delivery import NuvemshopWebhookDelivery
from app.models.pedido import datetime_now_brazil
from app.models.pedido_external_ref import PedidoExternalRef
from app.models.pedido_fonte import PedidoFonte
from app.models.pedido_manual_override import PedidoManualOverride

logger = logging.getLogger(__name__)


class NuvemshopTokenService:
    TOKEN_URL = "https://www.tiendanube.com/apps/authorize/token"

    @staticmethod
    def exchange_code(
        code: str,
        app_id: str,
        client_secret: str,
        redirect_uri: str | None = None,
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

    def process_delivery(self, delivery: NuvemshopWebhookDelivery) -> bool:
        try:
            if not self.store.active:
                return self._mark_failed(delivery, "store_inactive")

            if not delivery.event.startswith("order/"):
                return self._mark_processed(delivery)

            order_id = delivery.resource_id
            if not order_id:
                return self._mark_failed(delivery, "missing_order_id")

            order = self.client.get_order(order_id)
            delivery.order_json = json.dumps(order, ensure_ascii=False)

            (
                pedido_data,
                schedule_pending,
                shipping_option_text,
                agendamento_source,
            ) = map_nuvemshop_order_to_pedido_data(order)

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

            external_ref = self._get_external_ref(order)
            if external_ref:
                self._update_existing_pedido(
                    external_ref, pedido_data, schedule_pending, agendamento_source
                )
            else:
                pedido = self._create_pedido(pedido_data, fonte.id)
                self._create_external_ref(order, pedido.id, schedule_pending, agendamento_source)

                # Calcular distância automaticamente após criar pedido
                self._calculate_distance_if_needed(pedido.id)

            return self._mark_processed(delivery)
        except Exception as exc:
            db.session.rollback()
            return self._mark_failed(delivery, f"import_error: {type(exc).__name__}")

    def _compose_endereco(self, pedido_data: Dict[str, Any]) -> Optional[str]:
        parts = [
            pedido_data.get("rua"),
            pedido_data.get("numero"),
            pedido_data.get("bairro"),
            pedido_data.get("cidade"),
            pedido_data.get("cep"),
        ]
        clean = [p for p in parts if p]
        return " - ".join(clean) if clean else None

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

        # Buscar cliente existente por telefone
        cliente = Cliente.buscar_por_telefone(telefone)

        if not cliente:
            # Criar novo cliente
            nome = pedido_data.get("cliente") or "Cliente Nuvemshop"
            try:
                cliente = Cliente(
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
        fonte = FontePedido.query.filter_by(nome=nome).first()
        if fonte:
            return fonte
        fonte = FontePedido(nome=nome, ativo=True)
        db.session.add(fonte)
        db.session.commit()
        return fonte

    def _get_external_ref(self, order: Dict[str, Any]) -> Optional[PedidoExternalRef]:
        return (
            PedidoExternalRef.query.filter_by(
                provider="nuvemshop",
                store_id=str(self.store.store_id),
                external_order_id=str(order.get("id")),
            )
            .order_by(PedidoExternalRef.id.desc())
            .first()
        )

    def _create_pedido(self, pedido_data: Dict[str, Any], fonte_id: int) -> Pedido:
        pedido = Pedido(**pedido_data)
        db.session.add(pedido)
        db.session.commit()

        try:
            PedidoFonte.adicionar_pedido(pedido.id, fonte_id, pedido_data.get("valor"))
        except Exception:
            # Nao falhar se a tabela da fonte nao puder ser atualizada
            pass

        return pedido

    def _update_existing_pedido(
        self,
        external_ref: PedidoExternalRef,
        pedido_data: Dict[str, Any],
        schedule_pending: bool,
        agendamento_source: str = None,
    ) -> None:
        pedido = Pedido.query.get(external_ref.pedido_id)
        if not pedido:
            return

        # Buscar campos com override manual (não devem ser sobrescritos)
        overridden_fields = PedidoManualOverride.get_overridden_fields(pedido.id)

        # Atualizar campos relevantes sem sobrescrever dados manuais
        updates = {
            "status_pagamento": pedido_data.get("status_pagamento") or pedido.status_pagamento,
            "pagamento": pedido_data.get("pagamento") or pedido.pagamento,
            "status": pedido_data.get("status") or pedido.status,
            "obs_entrega": pedido_data.get("obs_entrega") or pedido.obs_entrega,
            "observacoes": self._merge_observacoes(
                pedido.observacoes, pedido_data.get("observacoes")
            ),
            "updated_at": datetime_now_brazil(),
        }

        # Se o pedido estava "schedule_pending" (data/hora ainda não confirmada),
        # permitir atualizar o agendamento quando a info chegar depois (ex.: custom fields).
        if external_ref.schedule_pending and not schedule_pending:
            if pedido_data.get("dia_entrega"):
                updates["dia_entrega"] = pedido_data.get("dia_entrega")
            if pedido_data.get("horario"):
                updates["horario"] = pedido_data.get("horario")

        if pedido_data.get("endereco") and not pedido.endereco:
            updates["endereco"] = pedido_data.get("endereco")
            updates["rua"] = pedido_data.get("rua")
            updates["numero"] = pedido_data.get("numero")
            updates["bairro"] = pedido_data.get("bairro")
            updates["cidade"] = pedido_data.get("cidade")
            updates["cep"] = pedido_data.get("cep")

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

        db.session.commit()

    def _merge_observacoes(self, current: Optional[str], incoming: Optional[str]) -> Optional[str]:
        if not incoming:
            return current
        if not current:
            return incoming
        if incoming in current:
            return current
        return f"{current} | {incoming}"

    def _create_external_ref(
        self,
        order: Dict[str, Any],
        pedido_id: int,
        schedule_pending: bool,
        agendamento_source: str = None,
    ) -> None:
        ref = PedidoExternalRef(
            provider="nuvemshop",
            store_id=str(self.store.store_id),
            external_order_id=str(order.get("id")),
            external_order_number=str(order.get("number")) if order.get("number") else None,
            order_token=str(order.get("token")) if order.get("token") else None,
            pedido_id=pedido_id,
            schedule_pending=schedule_pending,
            agendamento_source=agendamento_source,
            needs_review=(agendamento_source == "fallback"),
        )
        db.session.add(ref)
        db.session.commit()

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
        pedido = Pedido.query.get(pedido_id)
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
            else:
                error_msg = (
                    resultado.get("error", "Erro desconhecido") if resultado else "Resultado vazio"
                )
                logger.warning(f"Falha ao calcular distância para pedido #{pedido_id}: {error_msg}")
        except ImportError:
            logger.debug("Serviço de distância não disponível")
        except Exception as e:
            logger.warning(f"Erro ao calcular distância para pedido #{pedido_id}: {e}")
