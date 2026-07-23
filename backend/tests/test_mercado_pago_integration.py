# -*- coding: utf-8 -*-
"""Testes da integracao Mercado Pago Point."""

from decimal import Decimal

import pytest

from app.integrations.mercado_pago.errors import (
    MercadoPagoApiError,
    MercadoPagoValidationError,
)
from app.integrations.mercado_pago.mapper import (
    CATEGORY_NAME,
    CONTACT_NAME,
    FINANCIAL_ACCOUNT_NAME,
    MercadoPagoReceivableMapper,
    parse_decimal,
)
from app.integrations.mercado_pago.webhook import verify_mp_signature


# =============================================================================
# parse_decimal
# =============================================================================
class TestParseDecimal:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (None, Decimal("0.00")),
            (10.5, Decimal("10.50")),
            ("10,50", Decimal("10.50")),
            (Decimal("10.50"), Decimal("10.50")),
            (100, Decimal("100.00")),
        ],
    )
    def test_parse_decimal(self, raw, expected):
        assert parse_decimal(raw) == expected


# =============================================================================
# Mapper - extract_payment_info
# =============================================================================
class TestMapperExtractPaymentInfo:
    def setup_method(self):
        self.mapper = MercadoPagoReceivableMapper()

    def test_extracts_basic_fields(self):
        payment = {
            "id": 12345678,
            "transaction_amount": 150.0,
            "transaction_details": {"net_received_amount": 142.50},
            "payment_method_id": "visa",
            "payment_type_id": "point_of_sale",
            "status": "approved",
            "date_approved": "2026-07-23T10:30:00.000-03:00",
        }
        info = self.mapper.extract_payment_info(payment)

        assert info["mp_payment_id"] == "12345678"
        assert info["amount"] == Decimal("150.00")
        assert info["net_amount"] == Decimal("142.50")
        assert info["description"] == "Venda Point #12345678"

    def test_fallback_to_amount_when_net_zero(self):
        payment = {
            "id": 999,
            "transaction_amount": 100.0,
            "transaction_details": {"net_received_amount": 0},
            "payment_method_id": "pix",
            "payment_type_id": "point_of_sale",
            "status": "approved",
            "date_approved": "2026-07-23T10:30:00.000-03:00",
        }
        info = self.mapper.extract_payment_info(payment)
        assert info["net_amount"] == Decimal("100.00")


# =============================================================================
# Mapper - should_process
# =============================================================================
class TestMapperShouldProcess:
    def setup_method(self):
        self.mapper = MercadoPagoReceivableMapper()

    def test_approve_point_of_sale(self):
        payment = {"status": "approved", "payment_type_id": "point_of_sale"}
        should, reason = self.mapper.should_process(payment)
        assert should is True
        assert reason == ""

    def test_reject_pending(self):
        payment = {"status": "pending", "payment_type_id": "point_of_sale"}
        should, reason = self.mapper.should_process(payment)
        assert should is False
        assert "pending" in reason.lower()

    def test_reject_non_point_of_sale(self):
        payment = {"status": "approved", "payment_type_id": "online"}
        should, reason = self.mapper.should_process(payment)
        assert should is False
        assert "online" in reason.lower()


# =============================================================================
# Mapper - build_bling_receivable_payload
# =============================================================================
class TestMapperBuildBlingPayload:
    def setup_method(self):
        self.mapper = MercadoPagoReceivableMapper()

    def test_builds_correct_payload(self):
        info = {
            "mp_payment_id": "12345678",
            "net_amount": Decimal("142.50"),
            "date_approved": "2026-07-23T10:30:00.000-03:00",
            "description": "Venda Point #12345678",
        }
        payload = self.mapper.build_bling_receivable_payload(
            info, "contact_123", "cat_456", "fa_789"
        )

        assert payload["contato"] == {"id": "contact_123"}
        assert payload["valor"] == 142.5
        assert payload["vencimento"] == "2026-07-23"
        assert payload["categoria"] == {"id": "cat_456"}
        assert payload["contaFinanceira"] == {"id": "fa_789"}
        assert "12345678" in payload["observacao"]


# =============================================================================
# Mapper - build_bling_settle_payload
# =============================================================================
class TestMapperBuildSettlePayload:
    def setup_method(self):
        self.mapper = MercadoPagoReceivableMapper()

    def test_builds_settle_payload(self):
        info = {
            "mp_payment_id": "12345678",
            "net_amount": Decimal("142.50"),
            "date_approved": "2026-07-23T10:30:00.000-03:00",
            "description": "Venda Point #12345678",
        }
        payload = self.mapper.build_bling_settle_payload(info, "fa_789", "cat_456")

        assert payload["portador"] == {"id": "fa_789"}
        assert payload["categoria"] == {"id": "cat_456"}
        assert payload["valorRecebido"] == 142.5
        assert payload["usarDataVencimento"] is False


# =============================================================================
# Webhook HMAC validation
# =============================================================================
class TestWebhookHMAC:
    def test_valid_signature(self):
        import hashlib
        import hmac

        secret = "test-secret"
        body = b'{"type":"payment","data":{"id":123}}'
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        x_signature = f"ts=1234567890,v1={sig}"

        assert verify_mp_signature(body, x_signature, secret) is True

    def test_invalid_signature(self):
        body = b'{"type":"payment","data":{"id":123}}'
        x_signature = "ts=1234567890,v1=invalidhash"

        assert verify_mp_signature(body, x_signature, "test-secret") is False

    def test_missing_signature(self):
        assert verify_mp_signature(b"body", "", "secret") is False

    def test_missing_secret(self):
        assert verify_mp_signature(b"body", "ts=1,v1=abc", "") is False

    def test_malformed_signature(self):
        assert verify_mp_signature(b"body", "bad-format", "secret") is False


# =============================================================================
# Client errors
# =============================================================================
class TestMercadoPagoClient:
    def test_api_error_retryable(self):
        err = MercadoPagoApiError("error", status_code=500)
        assert err.is_retryable is True

    def test_api_error_not_retryable_401(self):
        err = MercadoPagoApiError("unauthorized", status_code=401)
        assert err.is_retryable is False

    def test_api_error_not_retryable_404(self):
        err = MercadoPagoApiError("not found", status_code=404)
        assert err.is_retryable is False


# =============================================================================
# Service - handle_webhook validation
# =============================================================================
class TestServiceHandleWebhook:
    def test_rejects_invalid_json(self):
        from app import create_app

        app = create_app({"TESTING": True, "SECRET_KEY": "test"})
        with app.app_context():
            from app.integrations.mercado_pago.service import MercadoPagoService

            svc = MercadoPagoService()
            with pytest.raises(MercadoPagoValidationError, match="Body JSON invalido"):
                svc.handle_webhook(b"not-json", {})

    def test_rejects_missing_payment_id(self):
        from app import create_app

        app = create_app({"TESTING": True, "SECRET_KEY": "test"})
        with app.app_context():
            from app.integrations.mercado_pago.service import MercadoPagoService

            svc = MercadoPagoService()
            body = b'{"type":"payment","data":{}}'
            with pytest.raises(MercadoPagoValidationError, match="payment_id ausente"):
                svc.handle_webhook(body, {})

    def test_rejects_wrong_event_type(self):
        from app import create_app

        app = create_app({"TESTING": True, "SECRET_KEY": "test"})
        with app.app_context():
            from app.integrations.mercado_pago.service import MercadoPagoService

            svc = MercadoPagoService()
            body = b'{"type":"merchant_order","data":{"id":123}}'
            with pytest.raises(MercadoPagoValidationError, match="Evento tipo"):
                svc.handle_webhook(body, {})


# =============================================================================
# Service - should_process filtering
# =============================================================================
class TestServiceProcessFiltering:
    def test_skips_non_approved(self):
        from app import create_app

        app = create_app({"TESTING": True, "SECRET_KEY": "test"})
        with app.app_context():
            from app.integrations.mercado_pago.service import MercadoPagoService

            svc = MercadoPagoService()
            payment = {"status": "cancelled", "payment_type_id": "point_of_sale"}
            should, _ = svc.mapper.should_process(payment)
            assert should is False


# =============================================================================
# Constants
# =============================================================================
class TestConstants:
    def test_contact_name(self):
        assert CONTACT_NAME == "Mercado Pago [Maquininha]"

    def test_category_name(self):
        assert CATEGORY_NAME == "Vendas"

    def test_financial_account_name(self):
        assert FINANCIAL_ACCOUNT_NAME == "Mercado Pago Point"
