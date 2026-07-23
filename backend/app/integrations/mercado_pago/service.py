# -*- coding: utf-8 -*-
"""Servico de orquestracao da integracao Mercado Pago Point -> Bling."""

import logging
import time
from datetime import timedelta
from typing import Any, Dict, Optional

from flask import current_app

from app import db
from app.integrations.bling.client import BlingClient
from app.integrations.bling.token_service import BlingTokenService
from app.integrations.mercado_pago.client import MercadoPagoClient
from app.integrations.mercado_pago.errors import (
    MercadoPagoConfigError,
    MercadoPagoError,
    MercadoPagoRetryableError,
    MercadoPagoValidationError,
)
from app.integrations.mercado_pago.mapper import (
    CATEGORY_NAME,
    CONTACT_NAME,
    FINANCIAL_ACCOUNT_NAME,
    MercadoPagoReceivableMapper,
)
from app.integrations.mercado_pago.webhook import verify_mp_signature
from app.models.mercado_pago_integration_log import MercadoPagoIntegrationLog
from app.models.mercado_pago_outbox import MercadoPagoOutbox
from app.models.pedido import datetime_now_brazil
from app.services.tenancy import is_store_inactive

logger = logging.getLogger(__name__)

RETRY_BACKOFF_MINUTES = 5


class MercadoPagoService:
    provider = "mercado_pago"

    def __init__(self, store_ref_id: Optional[int] = None) -> None:
        self.mapper = MercadoPagoReceivableMapper()
        self.store_ref_id = store_ref_id

    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------

    def mp_client(self, store_ref_id: Optional[int] = None) -> MercadoPagoClient:
        resolved = store_ref_id if store_ref_id is not None else self.store_ref_id
        token = self._resolve_access_token(resolved)
        if not token:
            raise MercadoPagoConfigError("Access token do Mercado Pago nao configurado")
        base_url = current_app.config.get(
            "MERCADO_PAGO_API_BASE_URL", "https://api.mercadopago.com"
        )
        return MercadoPagoClient(access_token=token, base_url=base_url)

    def bling_client(
        self, store_ref_id: Optional[int] = None
    ) -> BlingClient:
        resolved = store_ref_id if store_ref_id is not None else self.store_ref_id
        access_token = BlingTokenService.get_valid_access_token(
            store_ref_id=resolved
        )
        return BlingClient(
            access_token=access_token,
            base_url=current_app.config["BLING_API_BASE_URL"],
            timeout_seconds=int(
                current_app.config.get("BLING_TIMEOUT_SECONDS") or 20
            ),
            on_unauthorized=lambda: BlingTokenService.decrypt(
                BlingTokenService.refresh_access_token(
                    store_ref_id=resolved
                ).access_token_encrypted
            ),
        )

    def _resolve_access_token(
        self, store_ref_id: Optional[int]
    ) -> Optional[str]:
        """Busca access token via integration_settings_service (DB-first, env-fallback)."""
        try:
            from app.services.integration_settings_service import runtime_config

            cfg = runtime_config(store_ref_id)
            token = cfg.get("MERCADO_PAGO_ACCESS_TOKEN")
            if token:
                return token
        except Exception:
            pass
        return current_app.config.get("MERCADO_PAGO_ACCESS_TOKEN") or None

    def _resolve_webhook_secret(
        self, store_ref_id: Optional[int]
    ) -> Optional[str]:
        try:
            from app.services.integration_settings_service import runtime_config

            cfg = runtime_config(store_ref_id)
            secret = cfg.get("MERCADO_PAGO_WEBHOOK_SECRET")
            if secret:
                return secret
        except Exception:
            pass
        return current_app.config.get("MERCADO_PAGO_WEBHOOK_SECRET") or None

    def _ensure_enabled(self) -> None:
        if not current_app.config.get("MERCADO_PAGO_ENABLED"):
            raise MercadoPagoConfigError(
                "Integracao Mercado Pago Point desabilitada (MERCADO_PAGO_ENABLED=false)"
            )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        token = self._resolve_access_token(self.store_ref_id)
        return {
            "enabled": bool(current_app.config.get("MERCADO_PAGO_ENABLED")),
            "connected": bool(token),
            "counts": {
                "pending": MercadoPagoOutbox.query.filter_by(
                    status="pending"
                ).count(),
                "failed": MercadoPagoOutbox.query.filter(
                    MercadoPagoOutbox.status.in_(["failed_retryable", "failed_final"])
                ).count(),
                "completed": MercadoPagoOutbox.query.filter_by(
                    status="completed"
                ).count(),
            },
        }

    # ------------------------------------------------------------------
    # Setup (criar webhook no MP + contato no Bling)
    # ------------------------------------------------------------------

    def setup_integration(self, store_ref_id: Optional[int] = None) -> Dict[str, Any]:
        self._ensure_enabled()
        resolved = store_ref_id if store_ref_id is not None else self.store_ref_id
        mp_client = self.mp_client(resolved)
        secret = self._resolve_webhook_secret(resolved)
        if not secret:
            raise MercadoPagoConfigError("MERCADO_PAGO_WEBHOOK_SECRET nao configurado")

        webhook_url = self._build_webhook_url()
        result = {"webhook": None, "contact_id": None}

        # Criar webhook no MP
        existing = mp_client.list_webhooks()
        items = existing.get("items", []) if isinstance(existing, dict) else []
        already_exists = False
        for wh in items:
            if wh.get("url") == webhook_url:
                result["webhook"] = {"id": wh.get("id"), "status": "already_exists"}
                already_exists = True
                break
        if not already_exists:
            wh_resp = mp_client.create_webhook(webhook_url, secret)
            result["webhook"] = {
                "id": wh_resp.get("id"),
                "status": "created",
            }

        # Garante contato no Bling
        try:
            bc = self.bling_client(resolved)
            contact_id = self._ensure_bling_contact(bc)
            result["contact_id"] = contact_id
        except Exception as exc:
            result["contact_error"] = str(exc)

        return result

    def _build_webhook_url(self) -> str:
        base = (
            current_app.config.get("PUBLIC_BASE_URL", "")
            or current_app.config.get("NUVEMSHOP_PUBLIC_BASE_URL", "")
            or ""
        ).rstrip("/")
        return f"{base}/api/integrations/mercadopago/webhook"

    # ------------------------------------------------------------------
    # Webhook handling
    # ------------------------------------------------------------------

    def handle_webhook(
        self, raw_body: bytes, headers: Dict[str, str]
    ) -> Dict[str, Any]:
        import json

        from flask import g

        secret = self._resolve_webhook_secret(self.store_ref_id)
        x_signature = headers.get("x-signature", "")
        if secret and not verify_mp_signature(raw_body, x_signature, secret):
            raise MercadoPagoValidationError("Assinatura HMAC invalida")

        try:
            body = json.loads(raw_body)
        except Exception:
            raise MercadoPagoValidationError("Body JSON invalido")

        event_type = body.get("type", "")
        data = body.get("data", {})
        payment_id = str(data.get("id", "")).strip()

        if event_type != "payment" or not payment_id:
            raise MercadoPagoValidationError(
                f"Evento tipo '{event_type}' ou payment_id ausente, ignorando"
            )

        # Upsert na outbox (idempotente)
        existing = MercadoPagoOutbox.query.filter_by(mp_payment_id=payment_id).first()
        if existing:
            return {
                "payment_id": payment_id,
                "status": "already_enqueued",
                "outbox_id": existing.id,
            }

        tenant_id = getattr(g, "tenant_store_id", None)
        outbox = MercadoPagoOutbox(
            mp_payment_id=payment_id,
            mp_notification_id=str(data.get("id", "")),
            raw_webhook_json=raw_body.decode("utf-8", errors="replace"),
            status="pending",
            step="pending",
            store_ref_id=tenant_id,
        )
        db.session.add(outbox)
        db.session.commit()

        return {"payment_id": payment_id, "status": "enqueued", "outbox_id": outbox.id}

    # ------------------------------------------------------------------
    # Processamento da outbox
    # ------------------------------------------------------------------

    def process_pending(
        self, limit: int = 20, store_ref_id: Optional[int] = None
    ) -> Dict[str, Any]:
        from datetime import datetime

        now = datetime_now_brazil()
        query = MercadoPagoOutbox.query.filter(
            MercadoPagoOutbox.status.in_(["pending", "failed_retryable"]),
            db.or_(
                MercadoPagoOutbox.next_retry_at.is_(None),
                MercadoPagoOutbox.next_retry_at <= now,
            ),
        ).order_by(MercadoPagoOutbox.created_at.asc()).limit(limit)

        outboxes = query.all()
        processed = 0
        errors = 0

        for outbox in outboxes:
            if is_store_inactive(outbox.store_ref_id):
                continue
            try:
                self.process_outbox(outbox, store_ref_id=outbox.store_ref_id)
                processed += 1
            except Exception:
                errors += 1
                logger.exception(
                    "Erro processando outbox MP %s", outbox.mp_payment_id
                )

        return {"processed": processed, "errors": errors, "total": len(outboxes)}

    def process_outbox(
        self,
        outbox: MercadoPagoOutbox,
        store_ref_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        self._ensure_enabled()
        resolved = store_ref_id if store_ref_id is not None else outbox.store_ref_id
        self._claim_outbox(outbox)
        self._log(outbox, "info", outbox.step, "Iniciando processamento")

        try:
            # Step 1: Buscar pagamento no MP
            outbox.step = "fetching_payment"
            db.session.commit()
            mp_client = self.mp_client(resolved)
            payment = mp_client.get_payment(outbox.mp_payment_id)
            import json as _json

            payment = mp_client.get_payment(outbox.mp_payment_id)
            outbox.payment_json = _json.dumps(payment)
            db.session.commit()
            self._log(
                outbox,
                "info",
                "fetching_payment",
                f"Pagamento {outbox.mp_payment_id} obtido",
            )

            # Step 2: Validar
            should, reason = self.mapper.should_process(payment)
            if not should:
                outbox.status = "completed"
                outbox.step = "skipped"
                outbox.finished_at = datetime_now_brazil()
                db.session.commit()
                self._log(outbox, "info", "skipped", reason)
                return {"status": "skipped", "reason": reason}

            info = self.mapper.extract_payment_info(payment)

            # Step 3: Garantir contato no Bling
            outbox.step = "ensuring_contact"
            db.session.commit()
            bc = self.bling_client(resolved)
            contact_id = self._ensure_bling_contact(bc)
            outbox.bling_contact_id = contact_id
            db.session.commit()
            self._log(
                outbox,
                "info",
                "ensuring_contact",
                f"Contato Bling: {contact_id}",
            )

            # Step 4: Criar conta a receber
            outbox.step = "creating_receivable"
            db.session.commit()
            category_id = self._ensure_bling_category(bc)
            fa_id = self._ensure_bling_financial_account(bc)
            payload = self.mapper.build_bling_receivable_payload(
                info, contact_id, category_id, fa_id
            )
            resp = bc.post("/contas/receber", payload)
            receivable_id = str(
                (resp.get("data") if isinstance(resp, dict) else resp) or {}
            )
            # O Bling retorna o id no campo data.id
            if isinstance(resp, dict):
                data = resp.get("data") or resp
                if isinstance(data, dict):
                    receivable_id = str(data.get("id", ""))
            outbox.bling_receivable_id = receivable_id
            db.session.commit()
            self._log(
                outbox,
                "info",
                "creating_receivable",
                f"Conta a receber criada: {receivable_id}",
            )

            # Step 5: Baixar (quitar)
            outbox.step = "settling_receivable"
            db.session.commit()
            settle_payload = self.mapper.build_bling_settle_payload(
                info, fa_id, category_id
            )
            bc.settle_receivable(receivable_id, settle_payload)
            self._log(
                outbox,
                "info",
                "settling_receivable",
                f"Conta {receivable_id} baixada com sucesso",
            )

            # Completo
            outbox.status = "completed"
            outbox.step = "completed"
            outbox.finished_at = datetime_now_brazil()
            db.session.commit()
            self._log(outbox, "info", "completed", "Processamento concluido")
            return {"status": "completed", "receivable_id": receivable_id}

        except MercadoPagoError as exc:
            db.session.rollback()
            retryable = isinstance(exc, MercadoPagoRetryableError)
            self._mark_failed(outbox, retryable, str(exc))
            raise
        except Exception as exc:
            db.session.rollback()
            self._mark_failed(outbox, True, str(exc))
            raise

    # ------------------------------------------------------------------
    # Bling helpers
    # ------------------------------------------------------------------

    def _ensure_bling_contact(self, client: BlingClient) -> str:
        """Busca ou cria contato 'Mercado Pago [Maquininha]' no Bling."""
        items = client.search_contacts({"pesquisa": CONTACT_NAME, "limite": 100})
        data = items.get("data", []) if isinstance(items, dict) else []
        for item in data:
            if (
                isinstance(item, dict)
                and str(item.get("nome") or "").strip().lower()
                == CONTACT_NAME.lower()
                and item.get("id")
            ):
                return str(item["id"])

        # Criar
        resp = client.create_contact(
            {
                "nome": CONTACT_NAME,
                "tipo": "J",
                "situacao": "A",
            }
        )
        data_resp = resp.get("data") if isinstance(resp, dict) else resp
        if isinstance(data_resp, dict) and data_resp.get("id"):
            return str(data_resp["id"])
        raise MercadoPagoRetryableError(
            "Nao foi possivel criar contato no Bling",
            details={"response": resp},
        )

    def _ensure_bling_category(self, client: BlingClient) -> str:
        """Busca categoria 'Vendas' no Bling."""
        cats = client.list_categories()
        data = cats.get("data", []) if isinstance(cats, dict) else []
        for cat in data:
            if (
                isinstance(cat, dict)
                and str(cat.get("descricao") or "").strip().lower()
                == CATEGORY_NAME.lower()
                and cat.get("id")
            ):
                return str(cat["id"])
        raise MercadoPagoConfigError(
            f"Categoria '{CATEGORY_NAME}' nao encontrada no Bling"
        )

    def _ensure_bling_financial_account(self, client: BlingClient) -> str:
        """Busca ou cria conta financeira 'Mercado Pago Point' no Bling."""
        accounts = client.list_financial_accounts()
        data = accounts.get("data", []) if isinstance(accounts, dict) else []
        for acc in data:
            if (
                isinstance(acc, dict)
                and str(acc.get("descricao") or "").strip().lower()
                == FINANCIAL_ACCOUNT_NAME.lower()
                and acc.get("id")
            ):
                return str(acc["id"])
        # Criar conta financeira se nao existe
        resp = client.post(
            "/contas-bancarias",
            {"descricao": FINANCIAL_ACCOUNT_NAME, "tipo": "outros"},
        )
        data_resp = resp.get("data") if isinstance(resp, dict) else resp
        if isinstance(data_resp, dict) and data_resp.get("id"):
            return str(data_resp["id"])
        raise MercadoPagoConfigError(
            f"Conta financeira '{FINANCIAL_ACCOUNT_NAME}' nao encontrada no Bling"
        )

    # ------------------------------------------------------------------
    # Outbox helpers
    # ------------------------------------------------------------------

    def _claim_outbox(self, outbox: MercadoPagoOutbox) -> None:
        result = db.session.execute(
            db.text(
                "UPDATE mercado_pago_outbox SET status = 'processing', "
                "attempts = attempts + 1, updated_at = :now "
                "WHERE id = :id AND status IN ('pending', 'failed_retryable')"
            ),
            {"now": datetime_now_brazil(), "id": outbox.id},
        )
        db.session.commit()
        if result.rowcount == 0:
            raise MercadoPagoValidationError(
                f"Outbox {outbox.id} nao esta pendente (status={outbox.status})"
            )
        db.session.refresh(outbox)

    def _mark_failed(
        self, outbox: MercadoPagoOutbox, retryable: bool, error_message: str
    ) -> None:
        if (
            retryable
            and outbox.attempts < outbox.max_attempts
        ):
            outbox.status = "failed_retryable"
            outbox.next_retry_at = datetime_now_brazil() + timedelta(
                minutes=RETRY_BACKOFF_MINUTES
            )
        else:
            outbox.status = "failed_final"
            outbox.finished_at = datetime_now_brazil()
        outbox.error_message = error_message
        outbox.updated_at = datetime_now_brazil()
        db.session.commit()

    def _log(
        self,
        outbox: MercadoPagoOutbox,
        level: str,
        step: str,
        message: str,
        request: Any = None,
        response: Any = None,
        status_code: int = None,
    ) -> None:
        import json

        log = MercadoPagoIntegrationLog(
            outbox_id=outbox.id,
            level=level,
            step=step,
            message=message,
            request_json=json.dumps(request) if request else None,
            response_json=json.dumps(response) if response else None,
            status_code=status_code,
        )
        db.session.add(log)
        db.session.commit()
        prefix = f"[MP:{outbox.mp_payment_id}]" if outbox.mp_payment_id else "[MP]"
        logger.info("%s %s/%s - %s", prefix, level.upper(), step, message)
