"""Fase C.1 — isolamento automático de pedidos, leads e dependências."""

from datetime import date

from flask import g
from sqlalchemy.orm import aliased

from app import db
from app.models.lead import Lead
from app.models.pedido import Pedido
from app.models.store import Store
from app.models.user import User
from app.services.auth_service import generate_token, hash_password
from app.services.order_number_allocator import allocate_order_number
from app.services.track_token import make_track_token
from scripts.migrations.add_store_ref_and_numero_to_orders import migrate


def _store(slug: str) -> Store:
    store = Store(name=slug, slug=slug, active=True)
    db.session.add(store)
    db.session.commit()
    return store


def _user(store: Store, email: str) -> User:
    user = User(
        name=email,
        email=email,
        password_hash=hash_password("secret123"),
        role="admin",
        store_ref_id=store.id,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _pedido(store: Store, numero: int, cliente: str) -> Pedido:
    pedido = Pedido(
        store_ref_id=store.id,
        numero_pedido=numero,
        cliente=cliente,
        telefone_cliente="11999999999",
        destinatario="Destino",
        produto="Flores",
        dia_entrega=date.today(),
        horario="10:00",
    )
    db.session.add(pedido)
    db.session.commit()
    return pedido


def test_scope_filters_query_get_alias_and_escape_hatch(app):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        pedido_a = _pedido(store_a, 1, "A")
        pedido_b = _pedido(store_b, 1, "B")
        pedido_a_id = pedido_a.id
        pedido_b_id = pedido_b.id

        with app.test_request_context("/"):
            g.tenant_initialized = True
            g.tenant_multi = True
            g.tenant_store_id = store_a.id
            g.current_store = store_a

            assert [p.id for p in Pedido.query.all()] == [pedido_a_id]
            db.session.expunge_all()
            assert db.session.get(Pedido, pedido_b_id) is None
            other = aliased(Pedido)
            assert db.session.query(other).all()[0].id == pedido_a_id
            all_rows = (
                Pedido.query.execution_options(include_all_tenants=True).order_by(Pedido.id).all()
            )
            assert [p.id for p in all_rows] == [pedido_a_id, pedido_b_id]


def test_multi_store_without_identity_is_fail_closed(app):
    with app.app_context():
        store_a = _store("a")
        _store("b")
        _pedido(store_a, 1, "A")
        with app.test_request_context("/"):
            g.tenant_initialized = True
            g.tenant_multi = True
            g.tenant_store_id = None
            assert Pedido.query.count() == 0


def test_order_number_is_local_to_store(app):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        _pedido(store_a, 7, "A")
        _pedido(store_b, 2, "B")
        assert allocate_order_number(store_a.id) == 8
        assert allocate_order_number(store_b.id) == 3


def test_jwt_cannot_read_other_order_but_signed_tracking_can(client, session):
    store_a = _store("a")
    store_b = _store("b")
    user_a = _user(store_a, "a@example.test")
    pedido_b = _pedido(store_b, 1, "B")

    response = client.get(
        f"/api/pedidos/{pedido_b.id}",
        headers={"Authorization": f"Bearer {generate_token(user_a, store_a)}"},
    )
    assert response.status_code == 404

    public = client.get(f"/api/pedidos/track/{make_track_token(pedido_b.id)}")
    assert public.status_code == 200


def test_lead_dedup_key_can_repeat_between_stores(app):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        db.session.add_all(
            [
                Lead(store_ref_id=store_a.id, dedup_key="same"),
                Lead(store_ref_id=store_b.id, dedup_key="same"),
            ]
        )
        db.session.commit()
        assert Lead.query.execution_options(include_all_tenants=True).count() == 2


def test_basic_auth_is_rejected_with_two_active_stores(client, session):
    _store("a")
    _store("b")
    response = client.get(
        "/api/pedidos",
        headers={"Authorization": "Basic YWRtaW46dGVzdHBhc3M="},
    )
    assert response.status_code == 401
    assert "multiempresa" in response.get_json()["message"]


def test_c1_migration_is_idempotent_on_fresh_schema(app):
    with app.app_context():
        store = _store("default")
        pedido = _pedido(store, 1, "A")
        db.session.add(Lead(store_ref_id=store.id, dedup_key="migration"))
        db.session.commit()

        migrate()
        migrate()

        row = Pedido.query.filter(Pedido.id == pedido.id).one()
        assert row.store_ref_id == store.id
        assert row.numero_pedido == 1
