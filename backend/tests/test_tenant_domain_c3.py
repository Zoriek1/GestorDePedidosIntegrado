"""Fase C.3 — isolamento de referências externas de pedidos."""

from datetime import date

from flask import g

from app import db
from app.integrations.bling.service import BlingIntegrationService
from app.models.pedido import Pedido
from app.models.pedido_external_ref import PedidoExternalRef
from app.models.store import Store
from scripts.migrations.add_store_ref_to_order_external_refs import migrate


def _store(slug: str) -> Store:
    store = Store(name=slug, slug=slug, active=True)
    db.session.add(store)
    db.session.commit()
    return store


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


def test_external_reference_unique_is_local_to_store(app):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        pedido_a = _pedido(store_a, 1)
        pedido_b = _pedido(store_b, 1)
        db.session.add_all(
            [
                PedidoExternalRef(
                    store_ref_id=store_a.id,
                    provider="nuvemshop",
                    store_id="provider-store",
                    external_order_id="42",
                    pedido_id=pedido_a.id,
                ),
                PedidoExternalRef(
                    store_ref_id=store_b.id,
                    provider="nuvemshop",
                    store_id="provider-store",
                    external_order_id="42",
                    pedido_id=pedido_b.id,
                ),
            ]
        )
        db.session.commit()

        assert PedidoExternalRef.query.execution_options(include_all_tenants=True).count() == 2


def test_external_reference_filter_hides_other_store(app):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        pedido_a = _pedido(store_a, 1)
        pedido_b = _pedido(store_b, 1)
        db.session.add_all(
            [
                PedidoExternalRef(
                    store_ref_id=store_a.id,
                    provider="nuvemshop",
                    store_id="a",
                    external_order_id="1",
                    pedido_id=pedido_a.id,
                ),
                PedidoExternalRef(
                    store_ref_id=store_b.id,
                    provider="nuvemshop",
                    store_id="b",
                    external_order_id="2",
                    pedido_id=pedido_b.id,
                ),
            ]
        )
        db.session.commit()

        with app.test_request_context("/"):
            g.tenant_store_id = store_a.id
            g.tenant_multi = True
            refs = PedidoExternalRef.query.order_by(PedidoExternalRef.id).all()
            assert [ref.store_ref_id for ref in refs] == [store_a.id]


def test_bling_reference_derives_store_from_pedido(app):
    with app.app_context():
        store = _store("default")
        pedido = _pedido(store, 1)

        ref = BlingIntegrationService()._upsert_external_ref(
            pedido.id,
            external_order_id="bling-10",
            external_order_number="10",
        )
        db.session.commit()

        assert ref.store_ref_id == store.id
        assert ref.pedido_id == pedido.id


def test_c3_migration_is_idempotent_on_fresh_schema(app):
    with app.app_context():
        store = _store("default")
        pedido = _pedido(store, 1)
        db.session.add(
            PedidoExternalRef(
                store_ref_id=store.id,
                provider="nuvemshop",
                store_id="provider-store",
                external_order_id="42",
                pedido_id=pedido.id,
            )
        )
        db.session.commit()

        migrate()
        migrate()

        assert PedidoExternalRef.query.count() == 1
