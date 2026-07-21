# -*- coding: utf-8 -*-
"""Servicos de orquestracao da integracao Bling."""

import json
import time
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from flask import current_app

from app import db
from app.integrations.bling.client import BlingClient
from app.integrations.bling.errors import (
    BlingApiError,
    BlingConfigError,
    BlingIntegrationError,
    BlingRetryableError,
    BlingValidationError,
)
from app.integrations.bling.mapper import BlingOrderMapper, money_float, parse_decimal_money
from app.integrations.bling.token_service import BlingTokenService
from app.models.bling_category import BlingCategory
from app.models.bling_financial_account import BlingFinancialAccount
from app.models.bling_integration_log import BlingIntegrationLog
from app.models.bling_outbox import BlingOutbox
from app.models.bling_payment_mapping import BlingPaymentMapping
from app.models.bling_payment_method import BlingPaymentMethod
from app.models.pedido import Pedido, datetime_now_brazil
from app.models.pedido_external_ref import PedidoExternalRef
from app.services.tenancy import is_store_inactive
from app.utils.fiscal import is_valid_cpf_cnpj, normalize_cpf_cnpj, normalize_uf

GESTOR_PAYMENT_LABELS = [
    "Pix",
    "Cartao de Credito",
    "Cartao de Debito",
    "Dinheiro",
    "Transferencia",
    "Boleto",
    "Outro",
    "Cartão de Crédito",
    "Cartão de Débito",
    "Transferência",
]


class BlingIntegrationService:
    provider = "bling"

    def __init__(self, store_ref_id: Optional[int] = None) -> None:
        self.mapper = BlingOrderMapper()
        self.store_ref_id = store_ref_id

    def client(self, store_ref_id: Optional[int] = None) -> BlingClient:
        resolved_store_ref_id = store_ref_id if store_ref_id is not None else self.store_ref_id
        access_token = BlingTokenService.get_valid_access_token(store_ref_id=resolved_store_ref_id)
        return BlingClient(
            access_token=access_token,
            base_url=current_app.config["BLING_API_BASE_URL"],
            timeout_seconds=int(current_app.config.get("BLING_TIMEOUT_SECONDS") or 20),
            on_unauthorized=lambda: BlingTokenService.decrypt(
                BlingTokenService.refresh_access_token(
                    store_ref_id=resolved_store_ref_id
                ).access_token_encrypted
            ),
        )

    def _ensure_enabled(self) -> None:
        """Bloqueia operacoes que chamam a API de venda/baixa quando a
        integracao esta desligada. OAuth, preview e sync_config nao passam por
        aqui de proposito: precisam funcionar para configurar antes de habilitar."""
        if not current_app.config.get("BLING_ENABLED"):
            raise BlingConfigError("Integracao Bling desabilitada (BLING_ENABLED=false)")

    def status(self) -> Dict[str, Any]:
        credential = None
        try:
            credential = BlingTokenService.get_credential(store_ref_id=self.store_ref_id)
        except BlingIntegrationError:
            pass
        return {
            "enabled": bool(current_app.config.get("BLING_ENABLED")),
            "connected": bool(credential and credential.refresh_token_encrypted),
            "credential": credential.to_dict() if credential else None,
            "counts": {
                "payment_methods": BlingPaymentMethod.query.count(),
                "financial_accounts": BlingFinancialAccount.query.count(),
                "categories": BlingCategory.query.count(),
                "mappings": BlingPaymentMapping.query.count(),
                "outbox_pending": BlingOutbox.query.filter(
                    BlingOutbox.status.in_(["pending", "failed_retryable"])
                ).count(),
            },
        }

    def sync_config(self) -> Dict[str, Any]:
        client = self.client()
        warnings: List[str] = []
        counts = {"payment_methods": 0, "financial_accounts": 0, "categories": 0}

        payment_methods = self._extract_list(client.list_payment_methods())
        counts["payment_methods"] = self._sync_payment_methods(payment_methods)

        try:
            accounts = self._extract_list(client.list_financial_accounts())
            counts["financial_accounts"] = self._sync_financial_accounts(accounts)
        except Exception as exc:
            warnings.append(f"Falha ao sincronizar contas/portadores: {type(exc).__name__}")

        try:
            categories = self._extract_list(client.list_categories())
            counts["categories"] = self._sync_categories(categories)
        except Exception as exc:
            warnings.append(f"Falha ao sincronizar categorias: {type(exc).__name__}")

        product = None
        try:
            product = self.ensure_default_product(client)
        except Exception as exc:
            warnings.append(f"Falha ao garantir produto generico no Bling: {type(exc).__name__}")

        created_mappings = self.ensure_default_mapping_rows()
        db.session.commit()
        return {
            "counts": counts,
            "created_mappings": created_mappings,
            "product": product,
            "warnings": warnings,
        }

    def ensure_default_product(self, client: Optional[BlingClient] = None) -> Dict[str, Any]:
        """Garante que o produto generico (BLING_DEFAULT_PRODUCT_CODE) exista no
        Bling. Idempotente: procura pelo codigo e cria so se faltar. O mapper
        referencia o item do pedido por esse codigo, entao ele precisa existir."""
        client = client or self.client()
        code = current_app.config.get("BLING_DEFAULT_PRODUCT_CODE") or "PEDIDO-FLORICULTURA"

        if self._product_exists(client, code):
            return {"code": code, "created": False}

        payload = {
            "nome": current_app.config.get("BLING_DEFAULT_PRODUCT_NAME") or "Pedido Floricultura",
            "codigo": code,
            "tipo": "P",
            "formato": "S",
            "unidade": "UN",
            "situacao": "Ativo",
            "preco": 0,
        }
        try:
            response = client.create_product(payload)
        except BlingApiError:
            # Bling exige codigo unico. Se a criacao falhou, pode ser porque o
            # produto ja existe mas a busca por codigo nao o trouxe; reconfirma.
            if self._product_exists(client, code):
                return {"code": code, "created": False}
            raise
        data = response.get("data") if isinstance(response, dict) else None
        new_id = str(data.get("id")) if isinstance(data, dict) and data.get("id") else None
        return {"code": code, "created": True, "id": new_id}

    def _product_exists(self, client: BlingClient, code: str) -> bool:
        items = self._extract_list(client.search_products({"codigo": code, "limite": 100}))
        return any(
            str(item.get("codigo") or "") == str(code) for item in items if isinstance(item, dict)
        )

    def ensure_contact_for_pedido(
        self, pedido: Pedido, client: Optional[BlingClient] = None
    ) -> str:
        """Resolve o contato.id obrigatorio da venda usando o CLIENTE do pedido:
        procura no Bling pelo nome exato e reaproveita; senao cria um contato com
        o nome (e telefone) do cliente. Assim o Bling fica com os clientes reais.
        BLING_DEFAULT_CONTACT_ID, se definido, sobrepoe (usa um contato fixo)."""
        configured = str(current_app.config.get("BLING_DEFAULT_CONTACT_ID") or "").strip()
        if configured:
            return configured

        client = client or self.client()
        nome = (getattr(pedido, "cliente", None) or "").strip() or "Cliente Gestor"
        telefone = (getattr(pedido, "telefone_cliente", None) or "").strip()
        cliente_rel = getattr(pedido, "cliente_rel", None)
        documento = normalize_cpf_cnpj(
            getattr(pedido, "cpf_cnpj", None) or getattr(cliente_rel, "cpf_cnpj", None)
        )
        if documento and not is_valid_cpf_cnpj(documento):
            documento = None
        phone = self._contact_phone(telefone)

        if documento:
            items = self._extract_list(
                client.search_contacts({"numeroDocumento": documento, "limite": 100})
            )
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_document = normalize_cpf_cnpj(item.get("numeroDocumento"))
                if item_document == documento and item.get("id"):
                    return str(item["id"])

        if phone:
            items = self._extract_list(client.search_contacts({"telefone": phone, "limite": 100}))
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_phone = self._contact_phone(item.get("telefone") or item.get("celular"))
                if item_phone == phone and item.get("id"):
                    return str(item["id"])

        items = self._extract_list(client.search_contacts({"pesquisa": nome, "limite": 100}))
        for item in items:
            if (
                isinstance(item, dict)
                and str(item.get("nome") or "").strip().lower() == nome.lower()
                and item.get("id")
            ):
                return str(item["id"])

        # situacao "A" (ativo) e obrigatorio no Bling. Telefone so vai se for um
        # numero BR plausivel -- um telefone invalido faz o Bling recusar o
        # contato inteiro (o telefone real tambem fica nas observacoes da venda).
        payload: Dict[str, Any] = {
            "nome": nome,
            "tipo": "J" if documento and len(documento) == 14 else "F",
            "situacao": "A",
        }
        if documento:
            payload["numeroDocumento"] = documento
        if phone:
            payload["telefone"] = phone
        address = self._contact_address_from_pedido(pedido)
        if address:
            payload["endereco"] = {"geral": address}
            payload["pais"] = {"nome": "BRASIL"}
        # Marca o contato como "Cliente" (papel) para nao dar BO em NF/relatorios.
        type_id = self._cliente_contact_type_id(client)
        if type_id:
            payload["tiposContato"] = [{"id": self._as_bling_id(type_id)}]
        response = client.create_contact(payload)
        data = response.get("data") if isinstance(response, dict) else None
        new_id = str(data.get("id")) if isinstance(data, dict) and data.get("id") else None
        if not new_id:
            raise BlingRetryableError(
                "Nao foi possivel criar/obter o contato do cliente no Bling",
                details={"response": response, "cliente": nome},
            )
        return new_id

    @staticmethod
    def _contact_address_from_pedido(pedido: Pedido) -> Optional[Dict[str, str]]:
        """Monta o endereco geral do contato usando o endereco de entrega."""
        if str(getattr(pedido, "tipo_pedido", "Entrega") or "").strip().lower() != "entrega":
            return None

        values = {
            "endereco": str(getattr(pedido, "rua", None) or "").strip(),
            "cep": str(getattr(pedido, "cep", None) or "").strip(),
            "bairro": str(getattr(pedido, "bairro", None) or "").strip(),
            "municipio": str(getattr(pedido, "cidade", None) or "").strip(),
            "uf": normalize_uf(getattr(pedido, "uf", None)) or "",
            "numero": str(getattr(pedido, "numero", None) or "").strip() or "S/N",
            "complemento": str(
                getattr(pedido, "complemento", None) or getattr(pedido, "apto", None) or ""
            ).strip(),
        }
        required = ("endereco", "cep", "bairro", "municipio")
        if any(not values[field] for field in required):
            return None
        return {key: value for key, value in values.items() if value}

    def _cliente_contact_type_id(self, client: BlingClient) -> Optional[str]:
        """Resolve o id do tipo de contato "Cliente". Usa BLING_CONTACT_TYPE_ID
        se definido; senao consulta /contatos/tipos. Best-effort: retorna None se
        nao conseguir, para nao impedir a criacao do contato."""
        configured = str(current_app.config.get("BLING_CONTACT_TYPE_ID") or "").strip()
        if configured:
            return configured
        try:
            items = self._extract_list(client.list_contact_types())
        except Exception:
            return None
        for item in items:
            if not isinstance(item, dict):
                continue
            desc = str(item.get("descricao") or item.get("nome") or "").strip().lower()
            if desc == "cliente" or desc.startswith("cliente"):
                return str(item.get("id"))
        return None

    @staticmethod
    def _contact_phone(raw: Any) -> Optional[str]:
        """Retorna o telefone so se parecer um numero BR valido: 10 digitos
        (fixo, DDD+8) ou 11 digitos (celular, DDD + 9XXXXXXXX). Senao None."""
        digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
        if len(digits) == 11 and digits[2] == "9":
            return digits
        if len(digits) == 10:
            return digits
        return None

    def ensure_default_mapping_rows(self) -> int:
        created = 0
        for label in GESTOR_PAYMENT_LABELS:
            exists = BlingPaymentMapping.query.filter_by(gestor_payment_label=label).first()
            if exists:
                continue
            db.session.add(BlingPaymentMapping(gestor_payment_label=label, active=True))
            created += 1
        return created

    def list_config(self) -> Dict[str, Any]:
        self.ensure_default_mapping_rows()
        db.session.commit()
        return {
            "payment_methods": [
                m.to_dict()
                for m in BlingPaymentMethod.query.order_by(BlingPaymentMethod.nome).all()
            ],
            "financial_accounts": [
                a.to_dict()
                for a in BlingFinancialAccount.query.order_by(BlingFinancialAccount.nome).all()
            ],
            "categories": [
                c.to_dict() for c in BlingCategory.query.order_by(BlingCategory.nome).all()
            ],
            "mappings": [
                m.to_dict()
                for m in BlingPaymentMapping.query.order_by(
                    BlingPaymentMapping.gestor_payment_label
                ).all()
            ],
        }

    def save_mapping(self, mapping_id: int, data: Dict[str, Any]) -> BlingPaymentMapping:
        mapping = BlingPaymentMapping.query.get(mapping_id)
        if not mapping:
            raise BlingValidationError("Mapeamento Bling nao encontrado")
        for field in [
            "bling_payment_method_id",
            "bling_financial_account_id",
            "bling_category_id",
        ]:
            if field in data:
                value = data.get(field)
                setattr(mapping, field, int(value) if value not in (None, "", 0) else None)
        if "active" in data:
            mapping.active = bool(data.get("active"))
        mapping.updated_at = datetime_now_brazil()
        db.session.commit()
        return mapping

    def preview_order(self, pedido_id: int) -> Dict[str, Any]:
        pedido = self._get_pedido(pedido_id)
        warnings = []
        try:
            context = self.mapper.build(pedido)
        except BlingValidationError as exc:
            return {
                "pedido_id": pedido_id,
                "valid": False,
                "warnings": warnings,
                "errors": [{"message": str(exc), "details": exc.details}],
                "payload": None,
            }
        ref = self._get_order_ref(pedido_id)
        outbox = self._latest_outbox(pedido_id)
        if ref:
            warnings.append(
                "Pedido ja possui referencia Bling; reenvio continuara do estado salvo."
            )
        return {
            "pedido_id": pedido_id,
            "valid": True,
            "warnings": warnings,
            "errors": [],
            "payload": context["payload"],
            "financial_plan": self._serialize_plan(context["financial_plan"]),
            "external_ref": ref.to_dict() if hasattr(ref, "to_dict") else self._serialize_ref(ref),
            "outbox": outbox.to_dict() if outbox else None,
        }

    def send_order(self, pedido_id: int) -> Dict[str, Any]:
        self._ensure_enabled()
        pedido = self._get_pedido(pedido_id)
        outbox = self._latest_outbox(pedido_id)
        if outbox and outbox.status == "completed":
            return {"outbox": outbox.to_dict(), "already_completed": True}

        context = self.mapper.build(pedido)
        if not outbox:
            outbox = BlingOutbox(
                pedido_id=pedido_id,
                operation="send_order",
                status="pending",
                step="pending",
                payload_json=self._json_dumps(context["payload"]),
            )
            db.session.add(outbox)
            db.session.commit()
        else:
            outbox.payload_json = self._json_dumps(context["payload"])
            outbox.updated_at = datetime_now_brazil()
            db.session.commit()

        self.process_outbox(outbox.id)
        refreshed = BlingOutbox.query.get(outbox.id)
        return {"outbox": refreshed.to_dict()}

    def retry_outbox(self, outbox_id: int) -> Dict[str, Any]:
        self._ensure_enabled()
        outbox = BlingOutbox.query.get(outbox_id)
        if not outbox:
            raise BlingValidationError("Outbox Bling nao encontrada")
        if outbox.status == "completed":
            return {"outbox": outbox.to_dict(), "already_completed": True}
        outbox.status = "pending"
        outbox.error_code = None
        outbox.error_message = None
        outbox.next_retry_at = None
        db.session.commit()
        self._dispatch(outbox.id, outbox.operation)
        return {"outbox": BlingOutbox.query.get(outbox.id).to_dict()}

    def cancel_order(self, pedido_id: int) -> Dict[str, Any]:
        """Enfileira e processa o cancelamento da venda no Bling. So faz algo se o
        pedido foi enviado (tem venda no Bling)."""
        self._ensure_enabled()
        outbox = (
            BlingOutbox.query.filter_by(pedido_id=pedido_id, operation="cancel_order")
            .order_by(BlingOutbox.id.desc())
            .first()
        )
        if outbox and outbox.status == "completed":
            return {"outbox": outbox.to_dict(), "already_completed": True}
        if not outbox:
            outbox = BlingOutbox(
                pedido_id=pedido_id,
                operation="cancel_order",
                status="pending",
                step="pending",
            )
            db.session.add(outbox)
            db.session.commit()
        else:
            outbox.status = "pending"
            outbox.error_code = None
            outbox.error_message = None
            outbox.next_retry_at = None
            outbox.updated_at = datetime_now_brazil()
            db.session.commit()
        self.process_cancel(outbox.id)
        return {"outbox": BlingOutbox.query.get(outbox.id).to_dict()}

    def process_pending(self, limit: int = 20, store_ref_id: int | None = None) -> Dict[str, int]:
        self._ensure_enabled()
        now = datetime_now_brazil()
        query = BlingOutbox.query.filter(
            BlingOutbox.status.in_(["pending", "failed_retryable"]),
            (BlingOutbox.next_retry_at.is_(None)) | (BlingOutbox.next_retry_at <= now),
        )
        if store_ref_id is not None:
            query = query.filter(BlingOutbox.store_ref_id == store_ref_id)
        outboxes = query.order_by(BlingOutbox.created_at.asc()).limit(limit).all()
        processed = 0
        failed = 0
        results: List[Dict[str, Any]] = []
        for outbox in outboxes:
            # Empresa inativa: invalida a linha pendente e não envia (política Fase D).
            if is_store_inactive(getattr(outbox, "store_ref_id", None)):
                self._mark_failed(
                    outbox,
                    "store_inactive",
                    "Empresa inativa: envio Bling invalidado",
                    retryable=False,
                )
                refreshed = BlingOutbox.query.get(outbox.id)
                processed += 1
                failed += 1
                results.append(
                    {
                        "outbox_id": refreshed.id,
                        "pedido_id": refreshed.pedido_id,
                        "operation": refreshed.operation,
                        "status": refreshed.status,
                        "step": refreshed.step,
                        "error_code": refreshed.error_code,
                        "error_message": refreshed.error_message,
                    }
                )
                continue
            self._dispatch(outbox.id, outbox.operation)
            refreshed = BlingOutbox.query.get(outbox.id)
            processed += 1
            if refreshed.status.startswith("failed"):
                failed += 1
            results.append(
                {
                    "outbox_id": refreshed.id,
                    "pedido_id": refreshed.pedido_id,
                    "store_ref_id": refreshed.store_ref_id,
                    "operation": refreshed.operation,
                    "status": refreshed.status,
                    "step": refreshed.step,
                    "error_code": refreshed.error_code,
                    "error_message": refreshed.error_message,
                }
            )
        return {"processed": processed, "failed": failed, "results": results}

    def _dispatch(self, outbox_id: int, operation: str) -> None:
        if operation == "cancel_order":
            self.process_cancel(outbox_id)
        else:
            self.process_outbox(outbox_id)

    def _claim_outbox(self, outbox_id: int) -> Optional[BlingOutbox]:
        """Claim atomico: assume o outbox apenas se ele ainda estiver disponivel.
        Um unico UPDATE condicional e atomico em Postgres e SQLite, impedindo que
        envio manual (container web) e bling-worker processem o mesmo outbox em
        paralelo. Retorna o outbox atualizado, ou None se outro ja assumiu."""
        outbox = BlingOutbox.query.get(outbox_id)
        if not outbox:
            raise BlingValidationError("Outbox Bling nao encontrada")
        claimed = (
            db.session.query(BlingOutbox)
            .filter(
                BlingOutbox.id == outbox_id,
                BlingOutbox.status.in_(["pending", "failed_retryable"]),
            )
            .update(
                {
                    "status": "processing",
                    "attempts": BlingOutbox.attempts + 1,
                    "updated_at": datetime_now_brazil(),
                },
                synchronize_session=False,
            )
        )
        db.session.commit()
        if not claimed:
            return None
        db.session.refresh(outbox)
        return outbox

    def process_outbox(self, outbox_id: int) -> None:
        self._ensure_enabled()
        outbox = self._claim_outbox(outbox_id)
        if outbox is None:
            # Outro processo ja assumiu (processing/completed/failed_final).
            return

        try:
            # Dentro do try para que falhas aqui (pedido removido, token ausente)
            # marquem o outbox como failed_* em vez de deixa-lo preso em processing.
            pedido = self._get_pedido(outbox.pedido_id)
            client = self.client(store_ref_id=pedido.store_ref_id)
            self._log(outbox, "info", "validating_mapping", "Validando pedido e mapeamentos")
            context = self.mapper.build(pedido)
            payload = context["payload"]
            plan = context["financial_plan"]
            outbox.payload_json = self._json_dumps(payload)

            self._log(outbox, "info", "checking_duplicate", "Checando duplicidade no Bling")
            order_id = outbox.bling_order_id or self._resolve_existing_order_id(client, pedido)

            if not order_id:
                # Bling v3 exige contato.id na venda: resolve/cria o contato do
                # cliente do pedido e injeta no payload antes de criar.
                contact_id = self.ensure_contact_for_pedido(pedido, client)
                payload.setdefault("contato", {})["id"] = self._as_bling_id(contact_id)
                outbox.payload_json = self._json_dumps(payload)
                outbox.step = "creating_order"
                db.session.commit()
                self._log(
                    outbox,
                    "info",
                    "creating_order",
                    "Criando pedido de venda no Bling",
                    request=payload,
                )
                response = client.create_order(payload)
                order_id = self._extract_order_id(response)
                outbox.response_json = self._json_dumps(response)
                outbox.bling_order_id = str(order_id)
                outbox.bling_order_number = self._extract_order_number(response)
                self._upsert_external_ref(pedido.id, str(order_id), outbox.bling_order_number)
                db.session.commit()
            else:
                outbox.bling_order_id = str(order_id)
                self._upsert_external_ref(pedido.id, str(order_id), outbox.bling_order_number)
                db.session.commit()

            receivable_ids = self._stored_receivable_ids(outbox)
            launch_response = None
            if not receivable_ids and outbox.step not in ("finding_receivables", "settling_entry"):
                outbox.step = "launching_order_accounts"
                db.session.commit()
                self._log(outbox, "info", "launching_order_accounts", "Lancando contas do pedido")
                try:
                    launch_response = client.launch_order_accounts(str(outbox.bling_order_id))
                    # Loga a resposta crua: e a fonte mais confiavel das contas
                    # geradas para este pedido.
                    self._log(
                        outbox,
                        "info",
                        "launching_order_accounts",
                        "Contas lancadas",
                        response=launch_response,
                    )
                    outbox.response_json = self._json_dumps(launch_response)
                except BlingApiError as exc:
                    # lancar-contas nao e idempotente: se as contas ja foram
                    # lancadas (retry), o Bling recusa -- tratamos como sucesso e
                    # seguimos para localizar/baixar.
                    if self._accounts_already_launched(exc):
                        self._log(
                            outbox,
                            "info",
                            "launching_order_accounts",
                            "Contas ja estavam lancadas; seguindo",
                        )
                        launch_response = None
                    else:
                        raise
                outbox.step = "finding_receivables"
                db.session.commit()

            if not receivable_ids:
                self._log(outbox, "info", "finding_receivables", "Localizando contas geradas")
                receivables_by_marker = self._find_receivables(
                    client,
                    plan,
                    str(outbox.bling_order_id),
                    store_number=f"GESTOR-{outbox.pedido_id}",
                    launch_response=launch_response,
                    contact_id=(payload.get("contato") or {}).get("id"),
                )
                receivable_ids = [
                    {
                        "marker": marker,
                        "id": str(item.get("id")),
                        "raw": item,
                    }
                    for marker, item in receivables_by_marker.items()
                ]
                outbox.bling_receivable_ids_json = self._json_dumps(receivable_ids)
                outbox.step = "settling_entry"
                db.session.commit()

            self._settle_receivables_if_needed(
                client, pedido, outbox, plan, receivable_ids, context
            )

            outbox.status = "completed"
            outbox.step = "completed"
            outbox.error_code = None
            outbox.error_message = None
            outbox.finished_at = datetime_now_brazil()
            outbox.updated_at = datetime_now_brazil()
            self._log(outbox, "info", "completed", "Integracao Bling concluida")
            db.session.commit()
        except BlingIntegrationError as exc:
            db.session.rollback()
            outbox = BlingOutbox.query.get(outbox_id)
            details = dict(exc.details or {})
            # Para erros da API, anexa a resposta crua do Bling (com error.fields)
            # ao log -- e ai que aparece o campo exato que o Bling recusou.
            if isinstance(exc, BlingApiError):
                details["status_code"] = exc.status_code
                if exc.payload is not None:
                    details["bling_response"] = exc.payload
            self._mark_failed(outbox, exc.code, str(exc), retryable=exc.retryable, details=details)
        except Exception as exc:
            db.session.rollback()
            outbox = BlingOutbox.query.get(outbox_id)
            self._mark_failed(
                outbox,
                "unexpected_error",
                f"{type(exc).__name__}: {exc}",
                retryable=True,
            )

    def process_cancel(self, outbox_id: int) -> None:
        """Cancela a venda no Bling, na ordem: apagar contas a receber -> estornar
        lancamento da venda -> apagar a venda. Cada passo e idempotente (404/ja
        feito = ok), para o cancelamento poder ser retentado com seguranca."""
        self._ensure_enabled()
        outbox = self._claim_outbox(outbox_id)
        if outbox is None:
            return

        try:
            # Resolve o order_id so pelo banco (sem chamar o Bling); se nao houver
            # venda, conclui sem nem abrir client.
            order_id, send_outbox = self._resolve_order_id_for_cancel(outbox.pedido_id)
            if not order_id:
                self._finish_outbox(outbox, "Pedido sem venda no Bling; nada a cancelar")
                return

            pedido = self._get_pedido(outbox.pedido_id)
            client = self.client(store_ref_id=pedido.store_ref_id)
            outbox.bling_order_id = str(order_id)

            # 1) Apagar os recebimentos (lancamentos de caixa) do pedido -- e o
            #    que desfaz a baixa. Conta paga so pode ser excluida depois disso;
            #    o estornar-contas da venda nao serve aqui (recusa conta paga).
            outbox.step = "reversing_receipts"
            db.session.commit()
            self._log(
                outbox, "info", "reversing_receipts", "Apagando recebimentos (baixas) do pedido"
            )
            self._delete_order_cash_entries(client, outbox)

            # 2) Apagar as contas a receber (agora sem baixa, pendentes).
            outbox.step = "deleting_receivables"
            db.session.commit()
            for rid in self._resolve_receivables_for_cancel(client, outbox.pedido_id, send_outbox):
                self._log(outbox, "info", "deleting_receivables", f"Apagando conta a receber {rid}")
                self._delete_receivable_idempotent(client, rid)

            # 3) Apagar a venda (sem contas, agora pode ser apagada).
            outbox.step = "deleting_order"
            db.session.commit()
            self._log(outbox, "info", "deleting_order", "Apagando venda no Bling")
            self._delete_order_idempotent(client, str(order_id))

            self._finish_outbox(outbox, "Venda cancelada no Bling")
        except BlingIntegrationError as exc:
            db.session.rollback()
            outbox = BlingOutbox.query.get(outbox_id)
            details = dict(exc.details or {})
            if isinstance(exc, BlingApiError):
                details["status_code"] = exc.status_code
                if exc.payload is not None:
                    details["bling_response"] = exc.payload
            self._mark_failed(outbox, exc.code, str(exc), retryable=exc.retryable, details=details)
        except Exception as exc:
            db.session.rollback()
            outbox = BlingOutbox.query.get(outbox_id)
            self._mark_failed(
                outbox, "unexpected_error", f"{type(exc).__name__}: {exc}", retryable=True
            )

    def _finish_outbox(self, outbox: BlingOutbox, message: str) -> None:
        outbox.status = "completed"
        outbox.step = "completed"
        outbox.error_code = None
        outbox.error_message = None
        outbox.finished_at = datetime_now_brazil()
        outbox.updated_at = datetime_now_brazil()
        self._log(outbox, "info", "completed", message)
        db.session.commit()

    def _resolve_order_id_for_cancel(self, pedido_id: int):
        send = (
            BlingOutbox.query.filter_by(pedido_id=pedido_id, operation="send_order")
            .order_by(BlingOutbox.id.desc())
            .first()
        )
        if send and send.bling_order_id:
            return str(send.bling_order_id), send
        ref = self._get_order_ref(pedido_id)
        if ref:
            return str(ref.external_order_id), send
        return None, send

    def _resolve_receivables_for_cancel(
        self, client: BlingClient, pedido_id: int, send_outbox: Optional[BlingOutbox]
    ) -> List[str]:
        ids: List[str] = []
        for item in self._stored_receivable_ids(send_outbox) if send_outbox else []:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
        if ids:
            return ids
        # best-effort: busca por marcador do pedido (o historico contem GESTOR-{id}-)
        prefix = f"GESTOR-{pedido_id}-"
        try:
            hits = self._extract_list(
                client.list_receivables({"pesquisa": f"GESTOR-{pedido_id}", "limite": 100})
            )
        except Exception:
            hits = []
        for item in hits:
            if (
                isinstance(item, dict)
                and item.get("id")
                and prefix in json.dumps(item, ensure_ascii=False, default=str)
            ):
                ids.append(str(item["id"]))
        return ids

    def _delete_order_cash_entries(self, client: BlingClient, outbox: BlingOutbox) -> None:
        """Apaga os lancamentos de caixa (recebimentos/baixas) do pedido -- e o
        que desfaz a baixa. Localiza por historico (contem GESTOR-{pedido_id})."""
        prefix = f"GESTOR-{outbox.pedido_id}"
        try:
            items = self._extract_list(
                client.list_cash_entries({"pesquisa": prefix, "limite": 100})
            )
        except Exception:
            items = []
        for item in items:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            if prefix not in json.dumps(item, ensure_ascii=False, default=str):
                continue
            self._log(
                outbox, "info", "reversing_receipts", f"Apagando recebimento (caixa) {item['id']}"
            )
            self._delete_cash_entry_idempotent(client, str(item["id"]))

    def _delete_cash_entry_idempotent(self, client: BlingClient, cash_id: str) -> None:
        try:
            client.delete_cash_entry(cash_id)
        except BlingApiError as exc:
            if not self._is_not_found(exc):
                raise

    def _delete_receivable_idempotent(self, client: BlingClient, receivable_id: str) -> None:
        try:
            client.delete_receivable(receivable_id)
        except BlingApiError as exc:
            if not self._is_not_found(exc):
                raise

    def _reverse_accounts_idempotent(self, client: BlingClient, order_id: str) -> None:
        try:
            client.reverse_order_accounts(order_id)
        except BlingApiError as exc:
            if not self._is_not_found(exc):
                raise

    def _delete_order_idempotent(self, client: BlingClient, order_id: str) -> None:
        try:
            client.delete_order(order_id)
        except BlingApiError as exc:
            if not self._is_not_found(exc):
                raise

    @staticmethod
    def _is_not_found(exc: BlingApiError) -> bool:
        return getattr(exc, "status_code", None) == 404

    def _settle_receivables_if_needed(
        self,
        client: BlingClient,
        pedido: Pedido,
        outbox: BlingOutbox,
        plan: List[Dict[str, Any]],
        receivable_ids: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> None:
        by_marker = {item["marker"]: item for item in receivable_ids}
        mappings = context["mappings"]
        total = parse_decimal_money(getattr(pedido, "valor", None))

        for row in plan:
            if not row.get("should_settle"):
                continue
            item = by_marker.get(row["marker"])
            if not item or not item.get("id"):
                raise BlingRetryableError(
                    "Conta a receber para baixa nao localizada",
                    details={"marker": row["marker"]},
                )

            # Idempotencia entre retries: se ja baixamos esta conta numa tentativa
            # anterior, nao baixar de novo (evita baixa dupla quando uma parcela
            # baixou e outra falhou no mesmo ciclo).
            if item.get("settled"):
                self._log(
                    outbox, "info", "settling_entry", f"Conta {item['id']} ja baixada (idempotente)"
                )
                continue

            raw = item.get("raw") or {}
            if self._receivable_is_paid(raw):
                self._log(outbox, "info", "settling_entry", f"Conta {item['id']} ja baixada")
                continue

            mapping = mappings[row["payment_label"]]
            payload = {
                "data": row["due_date"],
                "usarDataVencimento": False,
                "portador": {"id": self._as_bling_id(mapping.financial_account.bling_id)},
                "categoria": {"id": self._as_bling_id(mapping.category.bling_id)},
                "historico": f"{row['marker']} - baixa Gestor",
                "valorRecebido": money_float(row["amount"]),
            }
            tarifa = self._settlement_fee(pedido, row, total)
            if tarifa > Decimal("0.00"):
                payload["tarifa"] = money_float(tarifa)

            self._log(
                outbox,
                "info",
                "settling_entry",
                f"Baixando conta {item['id']}",
                request=payload,
            )
            response = client.settle_receivable(str(item["id"]), payload)
            outbox.response_json = self._json_dumps(response)
            # Marca a conta como baixada e persiste no proprio outbox, para que
            # um retry posterior pule esta parcela.
            item["settled"] = True
            outbox.bling_receivable_ids_json = self._json_dumps(receivable_ids)
            db.session.commit()

    def _settlement_fee(self, pedido: Pedido, row: Dict[str, Any], total: Decimal) -> Decimal:
        taxa = parse_decimal_money(getattr(pedido, "taxa_cartao_valor", None))
        if taxa <= Decimal("0.00") or total <= Decimal("0.00"):
            return Decimal("0.00")
        label = (row.get("payment_label") or "").lower()
        if "cart" not in label:
            return Decimal("0.00")
        if row["amount"] >= total:
            return taxa
        return (taxa * row["amount"] / total).quantize(Decimal("0.01"))

    def _resolve_existing_order_id(self, client: BlingClient, pedido: Pedido) -> Optional[str]:
        ref = self._get_order_ref(pedido.id)
        if ref:
            return str(ref.external_order_id)
        try:
            response = client.list_orders_by_store_number(f"GESTOR-{pedido.id}")
        except BlingIntegrationError:
            # Erros ja classificados (4xx final / 5xx retryable) sobem como estao.
            raise
        except Exception as exc:
            # Falhar fechado: sem conseguir verificar duplicidade, NAO criar outro
            # pedido. Retentar depois e mais seguro que duplicar no Bling.
            raise BlingRetryableError(
                "Nao foi possivel verificar duplicidade no Bling",
                details={"error": f"{type(exc).__name__}: {exc}"},
            ) from exc
        items = self._extract_list(response)
        if items:
            order_id = str(items[0].get("id"))
            order_number = str(items[0].get("numero") or items[0].get("numeroLoja") or "")
            self._upsert_external_ref(pedido.id, order_id, order_number or None)
            return order_id
        return None

    def _find_receivables(
        self,
        client: BlingClient,
        plan: List[Dict[str, Any]],
        order_id: str,
        store_number: str,
        launch_response: Any = None,
        contact_id: Any = None,
    ) -> Dict[str, Dict[str, Any]]:
        # As contas a receber demoram a aparecer depois do lancar-contas (o Bling
        # responde 204 e gera de forma assincrona). Tentamos algumas vezes com uma
        # pausa curta antes de desistir, em vez de falhar e esperar o backoff.
        markers = [row["marker"] for row in plan]
        attempts = int(current_app.config.get("BLING_RECEIVABLE_FIND_ATTEMPTS") or 4)
        delay = float(current_app.config.get("BLING_RECEIVABLE_FIND_DELAY_SECONDS") or 2.0)

        found: Dict[str, Dict[str, Any]] = {}
        sample: List[Dict[str, Any]] = []
        for attempt in range(1, attempts + 1):
            found, sample = self._collect_receivables(
                client,
                plan,
                markers,
                order_id,
                store_number,
                contact_id,
                launch_response if attempt == 1 else None,
            )
            if len(found) == len(markers):
                return found
            if attempt < attempts:
                time.sleep(delay)

        missing = [marker for marker in markers if marker not in found]
        raise BlingRetryableError(
            "Contas a receber ainda nao localizadas no Bling",
            details={"missing_markers": missing, "order_id": order_id, "scanned_sample": sample},
        )

    def _collect_receivables(
        self,
        client: BlingClient,
        plan: List[Dict[str, Any]],
        markers: List[str],
        order_id: str,
        store_number: str,
        contact_id: Any,
        launch_response: Any,
    ) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """Uma passada de localizacao: junta candidatos e casa cada parcela por
        marcador (GESTOR-{id}-{kind}, presente no historico da conta), por vinculo
        com a venda (origem.id) e por valor+vencimento."""
        found: Dict[str, Dict[str, Any]] = {}
        order_items: List[Dict[str, Any]] = []

        def consider(items: Any) -> None:
            for item in self._extract_list(items):
                if not isinstance(item, dict):
                    continue
                self._match_markers(item, markers, found)
                if self._receivable_links_order(item, order_id):
                    order_items.append(item)

        # a) Resposta do lancar-contas (contas DESTE pedido, quando vier corpo).
        consider(launch_response)

        # b) Busca por numeroLoja (GESTOR-{id}): aparece no historico de TODAS as
        #    parcelas do pedido, entao uma busca traz todas de uma vez.
        if len(found) < len(markers):
            try:
                consider(client.list_receivables({"pesquisa": store_number, "limite": 100}))
            except Exception:
                pass

        # c) Contas do contato do pedido (conjunto pequeno) -> casa por origem.id.
        if contact_id and len(found) < len(markers):
            try:
                consider(client.list_receivables({"idContato": contact_id, "limite": 100}))
            except Exception:
                pass

        # d) Casa as contas vinculadas a venda por valor+vencimento.
        if len(found) < len(markers) and order_items:
            self._match_by_amount_due(order_items, plan, found)

        return found, order_items[:3]

    def _match_markers(
        self,
        item: Any,
        markers: List[str],
        found: Dict[str, Dict[str, Any]],
    ) -> None:
        """Casa uma conta a receber a um marcador GESTOR-{id}-{kind}. O marcador
        e unico por pedido/parcela, entao substring no JSON da conta basta."""
        if not isinstance(item, dict):
            return
        item_text = json.dumps(item, ensure_ascii=False, default=str)
        for marker in markers:
            if marker not in found and marker in item_text:
                found[marker] = item

    def _match_by_amount_due(
        self,
        items: List[Dict[str, Any]],
        plan: List[Dict[str, Any]],
        found: Dict[str, Dict[str, Any]],
    ) -> None:
        """Casa parcela do plano -> conta a receber por valor (e vencimento).
        Usado quando as contas sao sabidamente do pedido (resposta do lancar-contas
        ou contas vinculadas ao pedido), mas nao carregam o marcador."""
        used = {id(v) for v in found.values()}
        for row in plan:
            if row["marker"] in found:
                continue
            target_value = money_float(row["amount"])
            target_due = row.get("due_date")
            for item in items:
                if id(item) in used:
                    continue
                value = self._receivable_value(item)
                if value is None or abs(value - target_value) >= 0.005:
                    continue
                due = self._receivable_due(item)
                if target_due and due and due != target_due:
                    continue
                found[row["marker"]] = item
                used.add(id(item))
                break

    @staticmethod
    def _receivable_value(item: Dict[str, Any]) -> Optional[float]:
        for key in ("valor", "valorDocumento", "valorTotal", "saldo"):
            value = item.get(key)
            if value is not None:
                try:
                    return round(float(value), 2)
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _receivable_due(item: Dict[str, Any]) -> Optional[str]:
        for key in ("vencimento", "dataVencimento", "dataVencimentoOriginal", "data"):
            value = item.get(key)
            if value:
                return str(value)[:10]
        return None

    def _receivable_links_order(self, item: Dict[str, Any], order_id: str) -> bool:
        """Detecta se a conta a receber esta vinculada ao pedido de venda."""
        if not isinstance(item, dict):
            return False
        oid = str(order_id)
        for key in ("origem", "vinculo", "venda", "pedidoVenda", "pedido"):
            sub = item.get(key)
            if isinstance(sub, dict) and str(sub.get("id")) == oid:
                return True
        for key in ("idVendaOrigem", "idOrigem", "idPedidoVenda", "idPedido"):
            if str(item.get(key)) == oid:
                return True
        return False

    @staticmethod
    def _accounts_already_launched(exc: BlingApiError) -> bool:
        """Detecta o erro do Bling "contas ja lancadas / NF gerada" (code 62) ao
        tentar lancar contas de novo num retry -- e benigno: as contas existem."""
        payload = getattr(exc, "payload", None)
        if isinstance(payload, dict):
            error = payload.get("error") or {}
            for field in error.get("fields") or []:
                if isinstance(field, dict) and str(field.get("code")) == "62":
                    return True
        text = str(exc).lower()
        return "lançadas" in text or "lancadas" in text or "foi gerada a nota" in text

    def _is_bling_active(self, raw: Dict[str, Any]) -> bool:
        situacao = raw.get("situacao", raw.get("ativo", True))
        if isinstance(situacao, dict):
            labels = [
                situacao.get("valor"),
                situacao.get("nome"),
                situacao.get("descricao"),
            ]
            if any(
                str(label).strip().lower()
                in {"0", "false", "falso", "inativo", "inactive", "desativado", "disabled"}
                for label in labels
                if label is not None
            ):
                return False
            situacao = situacao.get("id") if situacao.get("id") is not None else True
        if isinstance(situacao, bool):
            return situacao
        text = str(situacao).strip().lower()
        if text in {"0", "false", "falso", "inativo", "inactive", "desativado", "disabled"}:
            return False
        return True

    def _sync_payment_methods(self, items: Iterable[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            bling_id = str(raw.get("id") or "")
            name = raw.get("descricao") or raw.get("nome") or raw.get("description")
            if not bling_id or not name:
                continue
            item = BlingPaymentMethod.query.filter_by(bling_id=bling_id).first()
            if not item:
                item = BlingPaymentMethod(bling_id=bling_id, nome=str(name))
                db.session.add(item)
            item.nome = str(name)
            item.tipo = str(raw.get("tipoPagamento") or raw.get("tipo") or "") or None
            item.finalidade = str(raw.get("finalidade") or "") or None
            item.destino = str(raw.get("destino") or "") or None
            item.ativo = self._is_bling_active(raw)
            item.raw_json = self._json_dumps(raw)
            item.synced_at = datetime_now_brazil()
            count += 1
        return count

    def _sync_financial_accounts(self, items: Iterable[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            bling_id = str(raw.get("id") or "")
            name = raw.get("descricao") or raw.get("nome") or raw.get("description")
            if not bling_id or not name:
                continue
            item = BlingFinancialAccount.query.filter_by(bling_id=bling_id).first()
            if not item:
                item = BlingFinancialAccount(bling_id=bling_id, nome=str(name))
                db.session.add(item)
            item.nome = str(name)
            item.tipo = str(raw.get("tipo") or raw.get("aliasIntegracao") or "") or None
            item.ativo = self._is_bling_active(raw)
            item.raw_json = self._json_dumps(raw)
            item.synced_at = datetime_now_brazil()
            count += 1
        return count

    def _sync_categories(self, items: Iterable[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            bling_id = str(raw.get("id") or "")
            name = raw.get("descricao") or raw.get("nome") or raw.get("description")
            if not bling_id or not name:
                continue
            item = BlingCategory.query.filter_by(bling_id=bling_id).first()
            if not item:
                item = BlingCategory(bling_id=bling_id, nome=str(name))
                db.session.add(item)
            item.nome = str(name)
            item.tipo = str(raw.get("tipo") or "") or None
            item.ativo = self._is_bling_active(raw)
            item.raw_json = self._json_dumps(raw)
            item.synced_at = datetime_now_brazil()
            count += 1
        return count

    def _get_pedido(self, pedido_id: int) -> Pedido:
        pedido = Pedido.query.filter(Pedido.id == pedido_id).first()
        if not pedido or pedido.deleted_at is not None:
            raise BlingValidationError("Pedido nao encontrado")
        return pedido

    def _latest_outbox(self, pedido_id: int) -> Optional[BlingOutbox]:
        return (
            BlingOutbox.query.filter_by(pedido_id=pedido_id, operation="send_order")
            .order_by(BlingOutbox.id.desc())
            .first()
        )

    def _get_order_ref(self, pedido_id: int) -> Optional[PedidoExternalRef]:
        pedido = Pedido.query.filter(Pedido.id == pedido_id).first()
        if not pedido:
            return None
        return PedidoExternalRef.query.filter_by(
            store_ref_id=pedido.store_ref_id,
            provider=self.provider,
            store_id=current_app.config.get("BLING_STORE_ID") or "default",
            pedido_id=pedido_id,
        ).first()

    def _upsert_external_ref(
        self,
        pedido_id: int,
        external_order_id: str,
        external_order_number: Optional[str] = None,
    ) -> PedidoExternalRef:
        pedido = self._get_pedido(pedido_id)
        store_id = current_app.config.get("BLING_STORE_ID") or "default"
        ref = PedidoExternalRef.query.filter_by(
            store_ref_id=pedido.store_ref_id,
            provider=self.provider,
            store_id=store_id,
            external_order_id=str(external_order_id),
        ).first()
        if not ref:
            ref = PedidoExternalRef(
                store_ref_id=pedido.store_ref_id,
                provider=self.provider,
                store_id=store_id,
                external_order_id=str(external_order_id),
                pedido_id=pedido_id,
            )
            db.session.add(ref)
        ref.external_order_number = external_order_number
        ref.pedido_id = pedido_id
        ref.updated_at = datetime_now_brazil()
        db.session.commit()
        return ref

    def _mark_failed(
        self,
        outbox: BlingOutbox,
        code: str,
        message: str,
        *,
        retryable: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not outbox:
            return
        outbox.error_code = code
        outbox.error_message = message
        outbox.updated_at = datetime_now_brazil()
        if retryable and outbox.attempts < outbox.max_attempts:
            outbox.status = "failed_retryable"
            outbox.next_retry_at = datetime_now_brazil() + timedelta(minutes=5)
        else:
            outbox.status = "failed_final"
            outbox.finished_at = datetime_now_brazil()
        db.session.add(outbox)
        self._log(outbox, "error", outbox.step, message, response=details, error_code=code)
        db.session.commit()

    def _log(
        self,
        outbox: BlingOutbox,
        level: str,
        step: str,
        message: str,
        *,
        request: Any = None,
        response: Any = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ) -> None:
        log = BlingIntegrationLog(
            outbox_id=outbox.id if outbox else None,
            pedido_id=outbox.pedido_id if outbox else None,
            level=level,
            step=step,
            message=message,
            request_json=self._json_dumps(request) if request is not None else None,
            response_json=self._json_dumps(response) if response is not None else None,
            status_code=status_code,
            error_code=error_code,
        )
        db.session.add(log)
        if outbox:
            outbox.step = step or outbox.step
            outbox.updated_at = datetime_now_brazil()
        db.session.commit()
        self._console(
            outbox,
            level,
            step,
            message,
            response=response,
            status_code=status_code,
            error_code=error_code,
        )

    @staticmethod
    def _console(
        outbox: Optional[BlingOutbox],
        level: str,
        step: str,
        message: str,
        *,
        response: Any = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """Espelha o evento no stdout para acompanhar a integracao pelo log do
        container (worker e web), em linguagem clara."""
        pid = f"#{outbox.pedido_id}" if outbox else "-"
        op = outbox.operation if outbox else "-"
        tag = {"error": "ERRO", "warning": "AVISO", "critical": "CRITICO"}.get(level, "info")
        line = f"[BLING] {pid} {op} [{tag}] {step}: {message}"
        if error_code:
            line += f" (code={error_code})"
        print(line, flush=True)
        # Em erro, imprime a resposta crua do Bling (status + corpo) para
        # diagnostico direto no console, sem precisar consultar o banco.
        if level in ("error", "critical") and response is not None:
            try:
                snippet = json.dumps(response, ensure_ascii=False, default=str)
            except Exception:
                snippet = str(response)
            print(f"        resposta Bling: {snippet[:2000]}", flush=True)

    def _extract_order_id(self, response: Any) -> str:
        data = response.get("data") if isinstance(response, dict) else None
        if isinstance(data, dict) and data.get("id"):
            return str(data["id"])
        if isinstance(response, dict) and response.get("id"):
            return str(response["id"])
        raise BlingRetryableError("Resposta de criacao do pedido Bling sem ID", details=response)

    def _extract_order_number(self, response: Any) -> Optional[str]:
        data = response.get("data") if isinstance(response, dict) else None
        source = data if isinstance(data, dict) else response if isinstance(response, dict) else {}
        value = source.get("numero") or source.get("numeroLoja")
        return str(value) if value else None

    def _extract_list(self, response: Any) -> List[Dict[str, Any]]:
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            data = response.get("data")
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("items", "result", "registros"):
                    if isinstance(data.get(key), list):
                        return data[key]
            for key in ("items", "result", "registros"):
                if isinstance(response.get(key), list):
                    return response[key]
        return []

    def _stored_receivable_ids(self, outbox: BlingOutbox) -> List[Dict[str, Any]]:
        if not outbox.bling_receivable_ids_json:
            return []
        try:
            value = json.loads(outbox.bling_receivable_ids_json)
            return value if isinstance(value, list) else []
        except Exception:
            return []

    def _receivable_is_paid(self, raw: Dict[str, Any]) -> bool:
        situacao = raw.get("situacao") if isinstance(raw, dict) else None
        if isinstance(situacao, dict):
            situacao = situacao.get("id") or situacao.get("valor")
        if str(situacao) in {"2", "Pago", "Recebido"}:
            return True
        if isinstance(raw, dict) and "saldo" in raw:
            return parse_decimal_money(raw.get("saldo")) == Decimal("0.00")
        return False

    def _serialize_plan(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                **{k: v for k, v in row.items() if k != "amount"},
                "amount": money_float(row["amount"]),
            }
            for row in plan
        ]

    def _serialize_ref(self, ref: Optional[PedidoExternalRef]) -> Optional[Dict[str, Any]]:
        if not ref:
            return None
        return {
            "id": ref.id,
            "provider": ref.provider,
            "store_id": ref.store_id,
            "external_order_id": ref.external_order_id,
            "external_order_number": ref.external_order_number,
            "pedido_id": ref.pedido_id,
        }

    def _as_bling_id(self, value: Any) -> int | str:
        text = str(value)
        return int(text) if text.isdigit() else text

    def _json_dumps(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)
