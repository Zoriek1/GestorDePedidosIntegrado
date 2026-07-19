# -*- coding: utf-8 -*-
import json
from datetime import date

from app.models.lead import Lead
from app.models.marketing_conversion_outbox import MarketingConversionOutbox
from app.models.pedido import Pedido, datetime_now_brazil
from app.services.marketing_conversion_dispatcher import MarketingConversionDispatcher
from app.services.marketing_conversion_service import enqueue_whatsapp_purchase
from app.utils.tracking_token import extract_tracking_token_from_text

VALID_TOKEN = "A3F9B7K20K"


def _pedido() -> Pedido:
    return Pedido(
        cliente="Cliente WhatsApp",
        telefone_cliente="(62) 99999-0000",
        destinatario="Destinatário",
        tipo_pedido="Entrega",
        produto="Buquê",
        valor="299,90",
        dia_entrega=date.today(),
        horario="10:00",
        codigo_whatsapp=VALID_TOKEN,
    )


def test_codigo_de_atendimento_parenteses_e_reconhecido():
    text = "Olá! (código de atendimento: A3F9B7K20K)"
    assert extract_tracking_token_from_text(text) == VALID_TOKEN


def test_enfileira_ga4_e_google_ads_uma_vez_por_pedido(app, session):
    app.config.update(
        MARKETING_DISPATCH_ENABLED=True,
        GA4_MEASUREMENT_ID="G-TEST",
        GA4_API_SECRET="secret-test",
        GOOGLE_DATAMANAGER_ENABLED=True,
    )
    pedido = _pedido()
    session.add(pedido)
    session.flush()
    lead = Lead(
        dedup_key="marketing-linked-lead",
        event="whatsapp_click",
        token_rastreio=VALID_TOKEN,
        token_valido=True,
        status="compra_realizada",
        pedido_id=pedido.id,
        phone="62999990000",
        gclid="google-click",
        ga_client_id="123.456",
        ga_session_id="1700000000",
        ga_session_started_at=datetime_now_brazil(),
    )
    session.add(lead)
    session.commit()

    assert len(enqueue_whatsapp_purchase(pedido)) == 2
    assert len(enqueue_whatsapp_purchase(pedido)) == 0
    rows = session.query(MarketingConversionOutbox).order_by(MarketingConversionOutbox.destino).all()
    assert len(rows) == 2
    assert {row.transaction_id for row in rows} == {f"GESTOR-WA-{pedido.id}"}

    ga4 = next(row for row in rows if row.destino == "ga4")
    ga4_payload = json.loads(ga4.payload_json)
    params = ga4_payload["events"][0]["params"]
    assert ga4_payload["events"][0]["name"] == "whatsapp_purchase"
    assert params["value"] == 299.9
    assert params["currency"] == "BRL"
    assert params["session_id"] == 1700000000
    assert "phone" not in ga4.payload_json.lower()

    ads = next(row for row in rows if row.destino == "google_ads")
    ads_payload = json.loads(ads.payload_json)
    assert ads_payload["adIdentifiers"]["gclid"] == "google-click"
    phone_hash = ads_payload["userData"]["userIdentifiers"][0]["phoneNumber"]
    assert len(phone_hash) == 64
    assert "62999990000" not in ads.payload_json


def test_nao_enfileira_sem_token_ligado_ou_sem_valor(app, session):
    app.config.update(
        MARKETING_DISPATCH_ENABLED=True,
        GA4_MEASUREMENT_ID="G-TEST",
        GA4_API_SECRET="secret-test",
        GOOGLE_DATAMANAGER_ENABLED=True,
    )
    pedido = _pedido()
    pedido.codigo_whatsapp = None
    session.add(pedido)
    session.commit()
    assert enqueue_whatsapp_purchase(pedido) == []
    pedido.codigo_whatsapp = VALID_TOKEN
    pedido.valor = ""
    session.commit()
    assert enqueue_whatsapp_purchase(pedido) == []


class _Response:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


class _Http:
    def __init__(self):
        self.get_calls = 0

    def post(self, url, **kwargs):
        if "datamanager" in url:
            return _Response(200, {"requestId": "request-123"})
        return _Response(204)

    def get(self, url, **kwargs):
        self.get_calls += 1
        return _Response(200, {"requestStatusPerDestination": [{"requestStatus": "SUCCESS"}]})


def test_worker_processa_destinos_independentemente(app, session):
    app.config.update(
        MARKETING_DISPATCH_ENABLED=True,
        GA4_MEASUREMENT_ID="G-TEST",
        GA4_API_SECRET="secret-test",
        GOOGLE_DATAMANAGER_ENABLED=True,
        GOOGLE_DATAMANAGER_VALIDATE_ONLY=True,
        GOOGLE_ADS_CUSTOMER_ID="123-456-7890",
        GOOGLE_ADS_CONVERSION_ACTION_ID="987654",
    )
    pedido = _pedido()
    session.add(pedido)
    session.flush()
    lead = Lead(
        dedup_key="dispatcher-linked-lead",
        event="whatsapp_click",
        token_rastreio=VALID_TOKEN,
        token_valido=True,
        status="compra_realizada",
        pedido_id=pedido.id,
        phone="62999990000",
        gclid="google-click",
        ga_client_id="123.456",
    )
    session.add(lead)
    session.commit()
    enqueue_whatsapp_purchase(pedido)

    http = _Http()
    dispatcher = MarketingConversionDispatcher(http=http)
    dispatcher._google_headers = lambda: {"Authorization": "Bearer test"}
    stats = dispatcher.process_cycle()
    assert stats["failed"] == 0
    assert session.query(MarketingConversionOutbox).filter_by(status="sent").count() == 2
    ads = session.query(MarketingConversionOutbox).filter_by(destino="google_ads").one()
    assert ads.last_error == "validated_only"
    assert ads.request_id == "request-123"
    assert http.get_calls == 0


def test_google_ads_real_usa_diagnostico_assincrono(app, session):
    app.config.update(
        MARKETING_DISPATCH_ENABLED=True,
        GOOGLE_DATAMANAGER_ENABLED=True,
        GOOGLE_DATAMANAGER_VALIDATE_ONLY=False,
        GOOGLE_ADS_CUSTOMER_ID="123-456-7890",
        GOOGLE_ADS_CONVERSION_ACTION_ID="987654",
    )
    pedido = _pedido()
    session.add(pedido)
    session.flush()
    lead = Lead(
        dedup_key="dispatcher-real-google-ads",
        event="whatsapp_click",
        token_rastreio=VALID_TOKEN,
        token_valido=True,
        status="compra_realizada",
        pedido_id=pedido.id,
        phone="62999990000",
        gclid="google-click",
        ga_client_id="123.456",
    )
    session.add(lead)
    session.commit()
    enqueue_whatsapp_purchase(pedido)
    session.query(MarketingConversionOutbox).filter_by(destino="ga4").delete()
    session.commit()

    http = _Http()
    dispatcher = MarketingConversionDispatcher(http=http)
    dispatcher._google_headers = lambda: {"Authorization": "Bearer test"}
    stats = dispatcher.process_cycle()

    assert stats["submitted"] == 1
    assert stats["sent"] == 1
    ads = session.query(MarketingConversionOutbox).filter_by(destino="google_ads").one()
    assert ads.status == "sent"
    assert ads.last_error is None
    assert http.get_calls == 1


def test_google_ads_validate_only_finaliza_registro_submitted_legado(app, session):
    app.config.update(
        MARKETING_DISPATCH_ENABLED=True,
        GOOGLE_DATAMANAGER_VALIDATE_ONLY=True,
    )
    pedido = _pedido()
    session.add(pedido)
    session.flush()
    lead = Lead(
        dedup_key="dispatcher-legacy-validation",
        event="whatsapp_click",
        token_rastreio=VALID_TOKEN,
        token_valido=True,
        status="compra_realizada",
        pedido_id=pedido.id,
        phone="62999990000",
        gclid="google-click",
    )
    session.add(lead)
    session.flush()
    row = MarketingConversionOutbox(
        pedido_id=pedido.id,
        lead_id=lead.id,
        destino="google_ads",
        evento="purchase",
        transaction_id=f"GESTOR-WA-{pedido.id}",
        event_time=datetime_now_brazil(),
        payload_json="{}",
        status="submitted",
        request_id="legacy-request",
        submitted_at=datetime_now_brazil(),
    )
    session.add(row)
    session.commit()

    http = _Http()
    stats = MarketingConversionDispatcher(http=http).process_cycle()

    assert row.status == "sent"
    assert row.last_error == "validated_only"
    assert stats["sent"] == 1
    assert http.get_calls == 0
