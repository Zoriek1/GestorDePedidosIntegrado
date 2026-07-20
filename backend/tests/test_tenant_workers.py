"""Fase D — filas e workers por empresa.

O tenant vem da própria linha da outbox; poll/retry/reprocessamento o preservam.
Um ciclo processa duas empresas com tokens/destinos distintos, empresa inativa não
gera novos envios e a falha de uma empresa não altera a linha de outra.
"""

import json
from datetime import date

from app import db
from app.commands.send_daily_purchases_to_meta_command import (
    SendDailyPurchasesToMetaCommand,
)
from app.models.bling_outbox import BlingOutbox
from app.models.lead import Lead
from app.models.marketing_conversion_outbox import MarketingConversionOutbox
from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.models.pedido import Pedido, datetime_now_brazil
from app.models.store import Store
from app.models.store_setting import StoreSetting


def _store(slug: str, active: bool = True) -> Store:
    store = Store(name=slug, slug=slug, active=active)
    db.session.add(store)
    db.session.commit()
    return store


def _settings(store: Store, *, pixel: str | None, token: str | None) -> StoreSetting:
    settings = StoreSetting(store_ref_id=store.id, meta_pixel_id=pixel)
    if token is not None:
        settings.set_secret("meta_capi_access_token", token)
    db.session.add(settings)
    db.session.commit()
    return settings


def _pedido(store: Store, numero: int) -> Pedido:
    pedido = Pedido(
        store_ref_id=store.id,
        numero_pedido=numero,
        cliente=f"Cliente {store.slug}",
        telefone_cliente="11999999999",
        destinatario="Destino",
        produto="Flores",
        valor="R$ 50,00",
        dia_entrega=date.today(),
        horario="10:00",
    )
    db.session.add(pedido)
    db.session.commit()
    return pedido


def _meta_purchase_row(store: Store, pedido: Pedido) -> MetaCapiOutbox:
    event_id = f"order_{pedido.id}"
    payload = {
        "event_name": "Purchase",
        "event_time": int(datetime_now_brazil().timestamp()),
        "event_id": event_id,
        "action_source": "chat",
        "user_data": {"ph": ["deadbeef"]},
        "custom_data": {"value": 50.0, "currency": "BRL", "order_id": str(pedido.id)},
    }
    row = MetaCapiOutbox(
        order_id=pedido.id,
        store_ref_id=store.id,
        event_id=event_id,
        event_time=datetime_now_brazil(),
        payload_json=json.dumps(payload),
        status="pending",
        attempts=0,
    )
    db.session.add(row)
    db.session.commit()
    return row


def _patch_send_events(monkeypatch, calls):
    """Substitui o envio real: registra (pixel, token, event_ids) por chamada.

    Sucesso quando há access_token; devolve o erro de config quando ausente,
    exatamente como o serviço real, para exercitar a classificação de erro.
    """
    from app.services.meta_capi import MetaConversionsApiService

    def fake_send(self, events):
        event_ids = [e.get("event_id") for e in events]
        calls.append({"pixel": self.pixel_id, "token": self.access_token, "event_ids": event_ids})
        if not self.access_token or not self.pixel_id:
            return {
                "_status_code": 0,
                "_error": "META_PIXEL_ID e META_CAPI_ACCESS_TOKEN devem estar configurados",
                "error": {"message": "config"},
                "events_received": 0,
            }
        return {"_status_code": 200, "events_received": len(events), "fbtrace_id": "t"}

    monkeypatch.setattr(MetaConversionsApiService, "send_events", fake_send)


# --- Envio Meta por tenant --------------------------------------------------


def test_meta_worker_uses_per_tenant_token(app, monkeypatch):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        _settings(store_a, pixel="PIXEL_A", token="TOKEN_A")
        _settings(store_b, pixel="PIXEL_B", token="TOKEN_B")
        row_a = _meta_purchase_row(store_a, _pedido(store_a, 1))
        row_b = _meta_purchase_row(store_b, _pedido(store_b, 1))

        calls = []
        _patch_send_events(monkeypatch, calls)

        SendDailyPurchasesToMetaCommand().process_outbox_cycle(limit=50)

        # Um envio por tenant, cada um com o pixel/token da sua própria loja.
        by_pixel = {c["pixel"]: c for c in calls}
        assert set(by_pixel) == {"PIXEL_A", "PIXEL_B"}
        assert by_pixel["PIXEL_A"]["token"] == "TOKEN_A"
        assert by_pixel["PIXEL_A"]["event_ids"] == [row_a.event_id]
        assert by_pixel["PIXEL_B"]["token"] == "TOKEN_B"
        assert by_pixel["PIXEL_B"]["event_ids"] == [row_b.event_id]

        db.session.refresh(row_a)
        db.session.refresh(row_b)
        assert row_a.status == "sent"
        assert row_b.status == "sent"


def test_meta_worker_isolates_invalid_tenant(app, monkeypatch):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        _settings(store_a, pixel="PIXEL_A", token="TOKEN_A")
        # B sem token: credencial inválida.
        _settings(store_b, pixel="PIXEL_B", token=None)
        row_a = _meta_purchase_row(store_a, _pedido(store_a, 1))
        row_b = _meta_purchase_row(store_b, _pedido(store_b, 1))

        calls = []
        _patch_send_events(monkeypatch, calls)

        SendDailyPurchasesToMetaCommand().process_outbox_cycle(limit=50)

        db.session.refresh(row_a)
        db.session.refresh(row_b)
        # A é enviada; a falha de B não altera A.
        assert row_a.status == "sent"
        assert row_b.status == "failed"
        # O tenant gravado na linha é preservado (nunca recalculado).
        assert row_a.store_ref_id == store_a.id
        assert row_b.store_ref_id == store_b.id


# --- Empresa inativa: bloqueia enqueue e invalida pendentes -----------------


def test_inactive_store_invalidates_pending_meta_row(app, monkeypatch):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b", active=False)
        _settings(store_a, pixel="PIXEL_A", token="TOKEN_A")
        _settings(store_b, pixel="PIXEL_B", token="TOKEN_B")
        row_a = _meta_purchase_row(store_a, _pedido(store_a, 1))
        row_b = _meta_purchase_row(store_b, _pedido(store_b, 1))

        calls = []
        _patch_send_events(monkeypatch, calls)

        SendDailyPurchasesToMetaCommand().process_outbox_cycle(limit=50)

        db.session.refresh(row_a)
        db.session.refresh(row_b)
        # A empresa inativa não envia; a linha pendente é invalidada.
        assert row_a.status == "sent"
        assert row_b.status == "failed"
        assert row_b.last_error and "store_inactive" in row_b.last_error
        # send_events só foi chamado para a loja ativa.
        sent_pixels = {c["pixel"] for c in calls}
        assert sent_pixels == {"PIXEL_A"}


def test_inactive_store_blocks_bling_enqueue(app):
    from app.integrations.bling.token_service import BlingTokenService
    from app.models.bling_credential import BlingCredential
    from app.utils.bling_helper import enqueue_bling_for_new_order

    with app.app_context():
        app.config["BLING_ENABLED"] = True
        store = _store("a", active=False)
        db.session.add(
            BlingCredential(
                store_id="default",
                store_ref_id=store.id,
                access_token_encrypted=BlingTokenService.encrypt("access"),
                refresh_token_encrypted=BlingTokenService.encrypt("refresh"),
                active=True,
            )
        )
        db.session.commit()
        pedido = _pedido(store, 1)

        assert enqueue_bling_for_new_order(pedido) is False
        assert BlingOutbox.query.count() == 0


# --- Migration: backfill pelo pai e idempotência ----------------------------


def test_outbox_migration_backfills_from_parent_and_is_idempotent(app):
    from scripts.migrations.add_store_ref_to_outboxes import migrate

    with app.app_context():
        store = _store("default")
        pedido = _pedido(store, 1)
        lead = Lead(store_ref_id=store.id, dedup_key="lead-d")
        db.session.add(lead)
        db.session.commit()

        # Linhas legadas sem tenant (store_ref_id NULL).
        db.session.add_all(
            [
                MetaCapiOutbox(
                    order_id=pedido.id,
                    store_ref_id=None,
                    event_id=f"order_{pedido.id}",
                    event_time=datetime_now_brazil(),
                    payload_json="{}",
                    status="pending",
                ),
                MetaCapiLeadOutbox(
                    lead_id=lead.id,
                    store_ref_id=None,
                    funnel_stage="contact",
                    event_id=f"lead_{lead.id}",
                    event_time=datetime_now_brazil(),
                    payload_json="{}",
                    status="pending",
                ),
                MarketingConversionOutbox(
                    pedido_id=pedido.id,
                    store_ref_id=None,
                    lead_id=lead.id,
                    destino="ga4",
                    evento="whatsapp_purchase",
                    transaction_id=f"TX-{pedido.id}",
                    event_time=datetime_now_brazil(),
                    payload_json="{}",
                    status="pending",
                ),
                BlingOutbox(
                    pedido_id=pedido.id,
                    store_ref_id=None,
                    operation="send_order",
                    status="pending",
                    step="pending",
                ),
            ]
        )
        db.session.commit()

        migrate()
        migrate()  # idempotente

        opts = {"include_all_tenants": True}
        meta = MetaCapiOutbox.query.execution_options(**opts).one()
        lead_row = MetaCapiLeadOutbox.query.execution_options(**opts).one()
        mkt = MarketingConversionOutbox.query.execution_options(**opts).one()
        bling = BlingOutbox.query.execution_options(**opts).one()

        assert meta.store_ref_id == store.id
        assert lead_row.store_ref_id == store.id
        assert mkt.store_ref_id == store.id
        assert bling.store_ref_id == store.id
