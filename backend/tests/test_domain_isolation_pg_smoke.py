# -*- coding: utf-8 -*-
"""Smoke de isolamento com 2 lojas em PostgreSQL real — item 0.5 do gate de rollout.

Complementa a suíte SQLite (que já cobre isolamento exaustivamente) provando que o
mesmo comportamento vale contra um Postgres real, com o modo estrito ligado
(FORCE_MULTI_TENANT) e requisições HTTP de verdade via Flask test_client.

Como rodar (banco descartável, nunca o de produção):

    set TEST_DATABASE_URL=postgresql://user:pass@host:5432/gestor_gate
    python -m pytest tests/test_domain_isolation_pg_smoke.py -q
"""

import os
from datetime import date

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL.startswith("postgresql"),
    reason="Requer TEST_DATABASE_URL apontando para um PostgreSQL real",
)


@pytest.fixture
def pg_app():
    from app import create_app, db

    app = create_app(
        config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
            # Liga o modo estrito mesmo com só 2 lojas de teste recém-criadas.
            "FORCE_MULTI_TENANT": True,
        }
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def _store(db, slug):
    from app.models.store import Store

    store = Store(name=slug, slug=slug, active=True)
    db.session.add(store)
    db.session.commit()
    return store


def _admin(db, store, email):
    from app.models.user import User
    from app.services.auth_service import hash_password

    user = User(
        name=f"Admin {store.slug}",
        email=email,
        store_ref_id=store.id,
        password_hash=hash_password("senha-teste-123"),
        role="admin",
    )
    db.session.add(user)
    db.session.commit()
    return user


def _pedido(db, store, numero, cliente):
    from app.models.pedido import Pedido

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


def _auth_headers(user, store):
    from app.services.auth_service import generate_token

    return {"Authorization": f"Bearer {generate_token(user, store)}"}


def test_login_returns_token_scoped_to_own_store(pg_app):
    """Login via API real (não direto via generate_token) confirma o fluxo ponta a ponta."""
    from app import db

    with pg_app.app_context():
        store_a = _store(db, "smoke-a")
        _admin(db, store_a, "admin-a@smoke.test")

    client = pg_app.test_client()
    r = client.post(
        "/api/auth/login",
        json={"email": "admin-a@smoke.test", "password": "senha-teste-123"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["user"]["store_slug"] == "smoke-a"
    assert data["access_token"]


def test_pedido_get_hides_other_store_and_own_store_works(pg_app):
    """IDs conhecidos da outra loja -> 404; leitura da própria loja funciona."""
    from app import db

    with pg_app.app_context():
        store_a = _store(db, "smoke-a")
        store_b = _store(db, "smoke-b")
        user_a = _admin(db, store_a, "admin-a@smoke.test")
        pedido_a = _pedido(db, store_a, 1, "Cliente A")
        pedido_b = _pedido(db, store_b, 1, "Cliente B")
        headers_a = _auth_headers(user_a, store_a)
        pedido_a_id, pedido_b_id = pedido_a.id, pedido_b.id

    client = pg_app.test_client()

    r_own = client.get(f"/api/pedidos/{pedido_a_id}", headers=headers_a)
    assert r_own.status_code == 200
    assert r_own.get_json()["pedido"]["id"] == pedido_a_id

    r_cross = client.get(f"/api/pedidos/{pedido_b_id}", headers=headers_a)
    assert r_cross.status_code == 404


def test_pedido_list_does_not_leak_other_store(pg_app):
    """Listagem da loja A não inclui pedidos da loja B, mesmo com IDs sobrepostos."""
    from app import db

    with pg_app.app_context():
        store_a = _store(db, "smoke-a")
        store_b = _store(db, "smoke-b")
        user_a = _admin(db, store_a, "admin-a@smoke.test")
        pedido_a = _pedido(db, store_a, 1, "Cliente A")
        _pedido(db, store_b, 1, "Cliente B")  # mesmo numero_pedido=1, loja diferente
        headers_a = _auth_headers(user_a, store_a)
        pedido_a_id = pedido_a.id

    client = pg_app.test_client()
    r = client.get("/api/pedidos", headers=headers_a)
    assert r.status_code == 200
    ids = {p["id"] for p in r.get_json()["pedidos"]}
    assert ids == {pedido_a_id}


def test_numero_pedido_reinicia_por_loja(pg_app):
    """Duas lojas têm numero_pedido=1 simultaneamente, sem conflito de unique composta."""
    from app import db

    with pg_app.app_context():
        store_a = _store(db, "smoke-a")
        store_b = _store(db, "smoke-b")
        pedido_a = _pedido(db, store_a, 1, "Cliente A")
        pedido_b = _pedido(db, store_b, 1, "Cliente B")
        assert pedido_a.numero_pedido == 1
        assert pedido_b.numero_pedido == 1
        assert pedido_a.id != pedido_b.id
