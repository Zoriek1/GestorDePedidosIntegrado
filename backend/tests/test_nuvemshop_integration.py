# -*- coding: utf-8 -*-
"""
Testes da integração Nuvemshop.

Inclui testes para:
- Verificação HMAC
- Mapeamento de pedidos
- Extração de agendamento (Huapps)
- Extração de storefront/canal
- Extração de frete
- Proteção de overrides manuais
"""
import hashlib
import hmac
from datetime import date

from app.integrations.nuvemshop.mapper import map_nuvemshop_order_to_pedido_data
from app.integrations.nuvemshop.service import NuvemshopOrderImporter
from app.integrations.nuvemshop.verifier import verify_nuvemshop_hmac
from app.models.nuvemshop_store import NuvemshopStore
from app.models.nuvemshop_webhook_delivery import NuvemshopWebhookDelivery
from app.models.pedido import Pedido
from app.models.pedido_external_ref import PedidoExternalRef
from app.models.pedido_manual_override import PedidoManualOverride


def test_verify_nuvemshop_hmac():
    """Testa verificação de assinatura HMAC"""
    secret = "test-secret"
    body = b'{"hello":"world"}'
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    assert verify_nuvemshop_hmac(body, signature, secret) is True
    assert verify_nuvemshop_hmac(body, "invalid", secret) is False


def test_map_order_huapps_schedule_pending():
    """Testa mapeamento de pedido Huapps com data pendente"""
    order = {
        "id": 123,
        "number": 456,
        "token": "abc",
        "contact_name": "Maria",
        "contact_phone": "+55 (62) 99999-9999",
        "created_at": "2025-01-01T10:00:00+0000",
        "currency": "BRL",
        "total": "100.00",
        "shipping_option": "Entrega Agendada (Huapps) - Dia Inteiro (08:00 - 18:00)",
        "shipping_address": {
            "name": "Joao",
            "address": "Rua A",
            "number": "10",
            "locality": "Centro",
            "city": "Goiania",
            "zipcode": "74000-000",
        },
        "products": [{"name": "Buque", "quantity": 1}],
    }

    pedido_data, schedule_pending, _, agendamento_source = map_nuvemshop_order_to_pedido_data(order)

    assert pedido_data["horario"] == "08:00 - 18:00"
    assert pedido_data["dia_entrega"] == date(2025, 1, 1)
    assert schedule_pending is True
    assert agendamento_source == "fallback"


def test_map_order_date_from_custom_field():
    """Testa extração de data de custom fields"""
    order = {
        "id": 123,
        "number": 456,
        "token": "abc",
        "contact_name": "Maria",
        "contact_phone": "+55 (62) 99999-9999",
        "created_at": "2025-01-01T10:00:00+0000",
        "currency": "BRL",
        "total": "100.00",
        # sem horário no frete, para validar extração via custom field
        "shipping_option": "Entrega Agendada (Huapps)",
        "custom_fields": [{"name": "Agendamento", "value": "02/01/2025 14:00 - 16:00 (tarde)"}],
        "shipping_address": {
            "name": "Joao",
            "address": "Rua A",
            "number": "10",
            "locality": "Centro",
            "city": "Goiania",
            "zipcode": "74000-000",
        },
        "products": [{"name": "Buque", "quantity": 1}],
    }

    pedido_data, schedule_pending, _, agendamento_source = map_nuvemshop_order_to_pedido_data(order)

    assert pedido_data["dia_entrega"] == date(2025, 1, 2)
    assert pedido_data["horario"] == "14:00 - 16:00"
    assert schedule_pending is False
    assert "custom_field" in agendamento_source


def test_map_order_storefront_to_canal():
    """Testa mapeamento de storefront para canal"""
    # Teste com storefront = "store" (Site)
    order_store = {
        "id": 123,
        "number": 456,
        "token": "abc",
        "contact_name": "Maria",
        "contact_phone": "+55 (62) 99999-9999",
        "created_at": "2025-01-01T10:00:00+0000",
        "currency": "BRL",
        "total": "100.00",
        "storefront": "store",
        "shipping_option": "Entrega Agendada",
        "custom_fields": [{"name": "Data", "value": "02/01/2025"}],
        "shipping_address": {
            "name": "Joao",
            "address": "Rua A",
            "number": "10",
            "locality": "Centro",
            "city": "Goiania",
            "zipcode": "74000-000",
        },
        "products": [{"name": "Buque", "quantity": 1}],
    }

    pedido_data, _, _, _ = map_nuvemshop_order_to_pedido_data(order_store)
    assert pedido_data["plataforma"] == "Nuvemshop"
    assert pedido_data["canal"] == "Site"

    # Teste com storefront = "meli" (Mercado Livre)
    order_meli = order_store.copy()
    order_meli["storefront"] = "meli"
    pedido_data, _, _, _ = map_nuvemshop_order_to_pedido_data(order_meli)
    assert pedido_data["canal"] == "Mercado Livre"

    # Teste com storefront = "pos" (PDV)
    order_pos = order_store.copy()
    order_pos["storefront"] = "pos"
    pedido_data, _, _, _ = map_nuvemshop_order_to_pedido_data(order_pos)
    assert pedido_data["canal"] == "PDV"


def test_map_order_frete_extraction():
    """Testa extração de custos de frete"""
    order = {
        "id": 123,
        "number": 456,
        "token": "abc",
        "contact_name": "Maria",
        "contact_phone": "+55 (62) 99999-9999",
        "created_at": "2025-01-01T10:00:00+0000",
        "currency": "BRL",
        "total": "219.90",
        "shipping_cost_customer": "8.90",
        "discount_shipping": "8.90",  # Frete grátis
        "storefront": "store",
        "shipping_option": "Entrega Agendada",
        "custom_fields": [{"name": "Data", "value": "02/01/2025"}],
        "shipping_address": {
            "name": "Joao",
            "address": "Rua A",
            "number": "10",
            "locality": "Centro",
            "city": "Goiania",
            "zipcode": "74000-000",
        },
        "products": [{"name": "Buque 12 rosas", "quantity": 1}],
    }

    pedido_data, _, _, _ = map_nuvemshop_order_to_pedido_data(order)

    assert pedido_data["frete_cobrado_cliente"] == 8.90
    assert pedido_data["desconto_frete"] == 8.90
    # Cliente pagou R$ 0 de frete (frete grátis)
    assert pedido_data["frete_liquido_cliente"] is None or pedido_data["frete_liquido_cliente"] == 0


def test_case_146_sentinela():
    """
    Caso sentinela #146 (order_id=1891180096) - Pedido Nuvemshop/Huapps.

    Dados reais:
    - Data/hora do pedido: 31/01/2026 19:03
    - Produto: 1x Buquê 12 rosas (tradicional) – R$ 219,90
    - Frete: R$ 8,90 com desconto total (frete grátis)
    - Modalidade: "Entrega Agendada (Huapps) – Tarde (13:00–18:00)"
    - Pagamento: Nuvem Pago, status recebido

    Validações:
    - plataforma = "Nuvemshop"
    - canal = "Site"
    - Horário extraído do shipping_option
    - Frete corretamente separado
    """
    order = {
        "id": 1891180096,
        "number": 146,
        "token": "abc123token",
        "contact_name": "Cliente Teste",
        "contact_phone": "+55 (62) 99999-9999",
        "created_at": "2026-01-31T19:03:00-0300",
        "currency": "BRL",
        "total": "219.90",
        "total_paid_by_customer": "219.90",
        "shipping_cost_customer": "8.90",
        "discount_shipping": "8.90",
        "storefront": "store",
        "payment_status": "paid",
        "gateway_name": "Nuvem Pago",
        "shipping_option": "Entrega Agendada (Huapps) - Tarde (13:00 - 18:00)",
        "note": "Mensagem longa do cliente aqui...",
        "shipping_address": {
            "name": "Destinatario Teste",
            "address": "Rua das Flores",
            "number": "123",
            "locality": "Jardim Goias",
            "city": "Goiania",
            "zipcode": "74810-000",
            "phone": "+55 (62) 88888-8888",
        },
        "products": [{"name": "Buquê 12 rosas (tradicional)", "quantity": 1}],
        "customer": {
            "name": "Cliente Teste",
            "phone": "+55 (62) 99999-9999",
        },
    }

    (
        pedido_data,
        schedule_pending,
        shipping_option_text,
        agendamento_source,
    ) = map_nuvemshop_order_to_pedido_data(order)

    # Validar plataforma e canal
    assert pedido_data["plataforma"] == "Nuvemshop"
    assert pedido_data["canal"] == "Site"

    # Validar horário extraído do shipping_option
    assert pedido_data["horario"] == "13:00 - 18:00"
    assert "Tarde" in shipping_option_text or "13:00" in shipping_option_text

    # Validar que schedule_pending é True (data não vem do Huapps)
    assert schedule_pending is True
    assert agendamento_source == "fallback"

    # Validar data fallback = data do pedido (31/01/2026)
    assert pedido_data["dia_entrega"] == date(2026, 1, 31)

    # Validar frete
    assert pedido_data["frete_cobrado_cliente"] == 8.90
    assert pedido_data["desconto_frete"] == 8.90

    # Validar produto
    assert "Buquê 12 rosas" in pedido_data["produto"]

    # Validar valor
    assert "219" in pedido_data["valor"]

    # Validar status pagamento (case-sensitive: "Pago", "Pendente", "Parcial")
    assert pedido_data["status_pagamento"] == "Pago"

    # Validar dados do cliente
    assert pedido_data["cliente"] == "Cliente Teste"
    assert pedido_data["destinatario"] == "Destinatario Teste"


def test_importer_idempotent(session):
    """Testa idempotência do importer (não duplicar pedidos)"""
    store = NuvemshopStore(store_id="999", access_token="token", active=True)
    session.add(store)
    session.commit()

    delivery = NuvemshopWebhookDelivery(
        store_id="999",
        event="order/created",
        resource_id="123",
        raw_body="{}",
        headers_json="{}",
    )
    session.add(delivery)
    session.commit()

    order = {
        "id": 123,
        "number": 456,
        "token": "abc",
        "contact_name": "Maria",
        "contact_phone": "+55 (62) 99999-9999",
        "created_at": "2025-01-01T10:00:00+0000",
        "currency": "BRL",
        "total": "100.00",
        "storefront": "store",
        "shipping_option": "Entrega Agendada (Huapps) - Dia Inteiro (08:00 - 18:00)",
        "shipping_address": {
            "name": "Joao",
            "address": "Rua A",
            "number": "10",
            "locality": "Centro",
            "city": "Goiania",
            "zipcode": "74000-000",
        },
        "products": [{"name": "Buque", "quantity": 1}],
    }

    importer = NuvemshopOrderImporter(store, user_agent="TestApp")
    importer.client.get_order = lambda _: order

    assert importer.process_delivery(delivery) is True

    delivery_2 = NuvemshopWebhookDelivery(
        store_id="999",
        event="order/created",
        resource_id="123",
        raw_body="{}",
        headers_json="{}",
    )
    session.add(delivery_2)
    session.commit()

    assert importer.process_delivery(delivery_2) is True

    assert Pedido.query.count() == 1
    assert PedidoExternalRef.query.count() == 1


def test_manual_override_protection(session):
    """Testa que overrides manuais protegem campos de serem sobrescritos"""
    # Criar store e pedido
    store = NuvemshopStore(store_id="888", access_token="token", active=True)
    session.add(store)
    session.commit()

    delivery = NuvemshopWebhookDelivery(
        store_id="888",
        event="order/created",
        resource_id="999",
        raw_body="{}",
        headers_json="{}",
    )
    session.add(delivery)
    session.commit()

    order = {
        "id": 999,
        "number": 100,
        "token": "xyz",
        "contact_name": "Cliente Original",
        "contact_phone": "+55 (62) 99999-9999",
        "created_at": "2025-01-01T10:00:00+0000",
        "currency": "BRL",
        "total": "100.00",
        "storefront": "store",
        "payment_status": "pending",
        "shipping_option": "Entrega Normal",
        "custom_fields": [{"name": "Data", "value": "15/01/2025"}],
        "shipping_address": {
            "name": "Destinatario",
            "address": "Rua A",
            "number": "10",
            "locality": "Centro",
            "city": "Goiania",
            "zipcode": "74000-000",
        },
        "products": [{"name": "Produto", "quantity": 1}],
    }

    importer = NuvemshopOrderImporter(store, user_agent="TestApp")
    importer.client.get_order = lambda _: order

    # Importar pedido inicial
    assert importer.process_delivery(delivery) is True

    # Verificar pedido criado
    pedido = Pedido.query.first()
    assert pedido is not None
    assert pedido.status_pagamento == "Pendente"
    original_dia_entrega = pedido.dia_entrega

    # Simular edição manual: criar override
    PedidoManualOverride.set_override(
        pedido_id=pedido.id, field_name="status_pagamento", field_value="Pago", edited_by="admin"
    )
    pedido.status_pagamento = "Pago"
    session.commit()

    # Verificar que override existe
    assert PedidoManualOverride.has_override(pedido.id, "status_pagamento") is True

    # Simular webhook de atualização
    delivery_2 = NuvemshopWebhookDelivery(
        store_id="888",
        event="order/updated",
        resource_id="999",
        raw_body="{}",
        headers_json="{}",
    )
    session.add(delivery_2)
    session.commit()

    # Order atualizado com status diferente
    order_updated = order.copy()
    order_updated["payment_status"] = "paid"

    importer.client.get_order = lambda _: order_updated
    assert importer.process_delivery(delivery_2) is True

    # Verificar que status_pagamento NÃO foi sobrescrito (override protege)
    session.refresh(pedido)
    assert pedido.status_pagamento == "Pago"  # Manteve o override manual


def test_external_ref_tracks_agendamento_source(session):
    """Testa que external_ref rastreia a fonte do agendamento"""
    store = NuvemshopStore(store_id="777", access_token="token", active=True)
    session.add(store)
    session.commit()

    delivery = NuvemshopWebhookDelivery(
        store_id="777",
        event="order/created",
        resource_id="555",
        raw_body="{}",
        headers_json="{}",
    )
    session.add(delivery)
    session.commit()

    order = {
        "id": 555,
        "number": 50,
        "token": "abc",
        "contact_name": "Maria",
        "contact_phone": "+55 (62) 99999-9999",
        "created_at": "2025-01-01T10:00:00+0000",
        "currency": "BRL",
        "total": "100.00",
        "storefront": "store",
        "shipping_option": "Entrega Agendada (Huapps) - 08:00 - 12:00",
        "shipping_address": {
            "name": "Joao",
            "address": "Rua A",
            "number": "10",
            "locality": "Centro",
            "city": "Goiania",
            "zipcode": "74000-000",
        },
        "products": [{"name": "Buque", "quantity": 1}],
    }

    importer = NuvemshopOrderImporter(store, user_agent="TestApp")
    importer.client.get_order = lambda _: order

    assert importer.process_delivery(delivery) is True

    # Verificar external_ref
    ref = PedidoExternalRef.query.first()
    assert ref is not None
    assert ref.agendamento_source == "fallback"  # Data não veio explícita
    assert ref.needs_review is True  # Precisa revisão
    assert ref.schedule_pending is True
