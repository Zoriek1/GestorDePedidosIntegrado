# -*- coding: utf-8 -*-
"""Testes UTMify: payload, match de lead, gatilho de venda e resiliência a falha HTTP."""
from datetime import date, datetime
from unittest.mock import patch

import pytest
import requests
from zoneinfo import ZoneInfo

from app.models.lead import Lead
from app.models.pedido import Pedido, TIMEZONE_BRASIL


class TestUtmifyApiHelpers:
    def test_map_payment_method(self):
        from app.services.utmify_api import map_payment_method

        assert map_payment_method("PIX") == "pix"
        assert map_payment_method("Cartão de crédito") == "credit_card"
        assert map_payment_method("boleto bancário") == "boleto"
        assert map_payment_method(None) == "free_price"
        assert map_payment_method("dinheiro") == "free_price"

    def test_tracking_parameters_from_lead_omits_empty(self):
        from app.services.utmify_api import tracking_parameters_from_lead

        lead = Lead(
            dedup_key="k1",
            utm_source="fb",
            utm_medium=None,
            sck="abc",
        )
        d = tracking_parameters_from_lead(lead)
        assert d["utm_source"] == "fb"
        assert d["sck"] == "abc"
        assert "utm_medium" not in d

    def test_build_utmify_order_payload(self):
        from app.services.utmify_api import build_utmify_order_payload

        p = Pedido(
            cliente="Maria",
            telefone_cliente="(62) 99999-0000",
            destinatario="X",
            tipo_pedido="Entrega",
            produto="Rosa",
            valor="100,00",
            dia_entrega=date.today(),
            horario="10:00",
            cidade="Goiânia",
            pagamento="PIX",
            quantidade=2,
            status_pagamento="Pago",
        )
        p.id = 42
        p.created_at = datetime(2025, 6, 1, 15, 30, 0, tzinfo=TIMEZONE_BRASIL)
        p.updated_at = datetime(2025, 6, 2, 16, 0, 0, tzinfo=TIMEZONE_BRASIL)

        lead = Lead(
            dedup_key="k2",
            utm_campaign="c1",
            ip_address="192.168.0.1",
        )

        body = build_utmify_order_payload(p, lead, platform="WhatsAppManual", is_test=True)

        assert body["orderId"] == "42"
        assert body["platform"] == "WhatsAppManual"
        assert body["paymentMethod"] == "pix"
        assert body["status"] == "paid"
        assert body["isTest"] is True
        assert body["customer"]["name"] == "Maria"
        assert body["customer"]["phone"] == "62999990000"
        assert body["customer"]["ip"] == "192.168.0.1"
        assert body["commission"]["totalPriceInCents"] == 10000
        assert body["commission"]["currency"] == "BRL"
        assert body["products"][0]["quantity"] == 2
        assert body["products"][0]["priceInCents"] == 5000
        assert "2025-06-01" in (body["createdAt"] or "")
        assert body["trackingParameters"]["utm_campaign"] == "c1"


class TestUtmifyHelper:
    def test_extract_fbclid_from_fbc(self):
        from app.utils.utmify_helper import extract_fbclid_from_fbc

        assert extract_fbclid_from_fbc("fb.1.1234567890.AbCdEf") == "AbCdEf"
        assert extract_fbclid_from_fbc("rawid") == "rawid"
        assert extract_fbclid_from_fbc(None) is None

    def test_resolve_lead_priority_sck_over_phone_only(self, app):
        from app import db
        from app.utils.utmify_helper import resolve_lead_for_pedido

        with app.app_context():
            db.create_all()
            p = Pedido(
                cliente="C",
                telefone_cliente="62911112222",
                destinatario="D",
                tipo_pedido="Entrega",
                produto="P",
                dia_entrega=date.today(),
                horario="09:00",
                cidade="Goiânia",
            )
            db.session.add(p)
            db.session.commit()

            older = Lead(
                dedup_key="o1",
                phone="62911112222",
                created_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=ZoneInfo("UTC")),
            )
            newer_plain = Lead(
                dedup_key="n1",
                phone="62911112222",
                created_at=datetime(2025, 2, 1, 10, 0, 0, tzinfo=ZoneInfo("UTC")),
            )
            with_sck = Lead(
                dedup_key="s1",
                phone="62911112222",
                sck="promo",
                created_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=ZoneInfo("UTC")),
            )
            db.session.add_all([older, newer_plain, with_sck])
            db.session.commit()

            lead, method = resolve_lead_for_pedido(p)
            assert method == "sck"
            assert lead is not None
            assert lead.sck == "promo"

    def test_resolve_lead_fbclid_when_no_sck_phone_lead(self, app):
        from app import db
        from app.utils.utmify_helper import resolve_lead_for_pedido

        with app.app_context():
            db.create_all()
            p = Pedido(
                cliente="C",
                telefone_cliente="62900001111",
                destinatario="D",
                tipo_pedido="Entrega",
                produto="P",
                dia_entrega=date.today(),
                horario="09:00",
                cidade="Goiânia",
                fbc="fb.1.123.xyclick",
            )
            db.session.add(p)
            db.session.commit()

            db.session.add(
                Lead(
                    dedup_key="f1",
                    fbclid="xyclick",
                    phone=None,
                )
            )
            db.session.commit()

            lead, method = resolve_lead_for_pedido(p)
            assert method == "fbclid"
            assert lead.fbclid == "xyclick"

    @patch("app.utils.utmify_helper.post_utmify_order")
    def test_send_on_pendente_to_pago_transition(self, mock_post, app):
        from app import db
        from app.utils.utmify_helper import send_utmify_if_purchase

        app.config["UTMIFY_ENABLED"] = True
        app.config["UTMIFY_API_TOKEN"] = "t" * 20
        app.config["UTMIFY_POSTBACK_URL"] = "https://api.utmify.com.br/api-credentials/orders"
        app.config["UTMIFY_PLATFORM"] = "WhatsAppManual"
        app.config["UTMIFY_TIMEOUT_SECONDS"] = 5
        app.config["UTMIFY_IS_TEST"] = False

        mock_post.return_value = {"ok": True, "status_code": 200, "error": None}

        with app.app_context():
            db.create_all()
            pedido = Pedido(
                cliente="C",
                telefone_cliente="62988776655",
                destinatario="D",
                tipo_pedido="Entrega",
                produto="P",
                dia_entrega=date.today(),
                horario="09:00",
                cidade="Goiânia",
                status_pagamento="Pago",
            )
            db.session.add(pedido)
            db.session.commit()

            ok = send_utmify_if_purchase(pedido, None, "Pendente")
            assert ok is True
            assert mock_post.call_count == 1

    @patch("app.utils.utmify_helper.post_utmify_order")
    def test_no_send_when_already_pago(self, mock_post, app):
        from app import db
        from app.utils.utmify_helper import send_utmify_if_purchase

        app.config["UTMIFY_ENABLED"] = True
        app.config["UTMIFY_API_TOKEN"] = "t" * 20
        app.config["UTMIFY_POSTBACK_URL"] = "https://api.utmify.com.br/api-credentials/orders"

        with app.app_context():
            db.create_all()
            pedido = Pedido(
                cliente="C",
                telefone_cliente="62988776655",
                destinatario="D",
                tipo_pedido="Entrega",
                produto="P",
                dia_entrega=date.today(),
                horario="09:00",
                cidade="Goiânia",
                status_pagamento="Pago",
            )
            db.session.add(pedido)
            db.session.commit()

            send_utmify_if_purchase(pedido, None, "Pago")
            mock_post.assert_not_called()

    @patch("app.utils.utmify_helper.post_utmify_order")
    def test_api_error_does_not_raise(self, mock_post, app):
        from app import db
        from app.utils.utmify_helper import send_utmify_if_purchase

        app.config["UTMIFY_ENABLED"] = True
        app.config["UTMIFY_API_TOKEN"] = "t" * 20
        app.config["UTMIFY_POSTBACK_URL"] = "https://api.utmify.com.br/api-credentials/orders"

        mock_post.return_value = {"ok": False, "status_code": 500, "error": "HTTP 500"}

        with app.app_context():
            db.create_all()
            pedido = Pedido(
                cliente="C",
                telefone_cliente="62988776655",
                destinatario="D",
                tipo_pedido="Entrega",
                produto="P",
                dia_entrega=date.today(),
                horario="09:00",
                cidade="Goiânia",
                status_pagamento="Parcial",
            )
            db.session.add(pedido)
            db.session.commit()

            ok = send_utmify_if_purchase(pedido, None, None)
            assert ok is False


class TestUtmifyPost:
    @patch("app.services.utmify_api.requests.post")
    def test_post_utmify_order_timeout(self, mock_post):
        from app.services.utmify_api import post_utmify_order

        mock_post.side_effect = requests.exceptions.Timeout()

        r = post_utmify_order(
            {"orderId": "1"},
            url="https://x.test/o",
            api_token="abc",
            timeout_seconds=3,
        )
        assert r["ok"] is False
        assert "timeout" in (r.get("error") or "")
