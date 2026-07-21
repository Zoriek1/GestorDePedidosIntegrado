# -*- coding: utf-8 -*-
"""Tests for per-store tenant health endpoint (Tarefa 3.2) and middleware store_ref_id logging (Tarefa 3.1)."""

import base64
import logging

from datetime import datetime, timedelta

from app import db
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.models.pedido import Pedido, datetime_now_brazil
from app.models.store import Store
from app.models.user import User
from app.services.auth_service import generate_token, hash_password


def _jwt_header(user):
    return {"Authorization": f"Bearer {generate_token(user)}"}


# ── Helpers ────────────────────────────────────────────────────────────────


def _create_store(session, slug: str, name: str, active: bool = True) -> Store:
    store = Store(slug=slug, name=name, active=active)
    session.add(store)
    session.flush()
    return store


def _create_admin(session, store: Store = None) -> User:
    u = User(
        name="Admin",
        email="admin_th@t.com",
        password_hash=hash_password("x"),
        role="admin",
        store_ref_id=store.id if store else None,
    )
    session.add(u)
    session.flush()
    return u


def _create_pedido(session, store: Store, created_at: datetime) -> Pedido:
    p = Pedido(
        store_ref_id=store.id,
        cliente="Cliente",
        telefone_cliente="11999999999",
        destinatario="Dest",
        produto="Flores",
        dia_entrega=created_at.date(),
        horario="10:00",
        created_at=created_at,
    )
    session.add(p)
    session.flush()
    return p


_outbox_counter = 0


def _create_outbox(session, store: Store, status: str) -> MetaCapiOutbox:
    global _outbox_counter
    _outbox_counter += 1
    o = MetaCapiOutbox(
        store_ref_id=store.id,
        order_id=_outbox_counter,
        event_id=f"test_th_event_{_outbox_counter}",
        event_time=datetime_now_brazil(),
        payload_json="{}",
        status=status,
    )
    session.add(o)
    session.flush()
    return o


# ── Test db.session.query ├╘model queries ────────────────────────────────


def _count_pedidos_hoje(store: Store, today_start: datetime) -> int:
    return (
        db.session.query(Pedido)
        .execution_options(include_all_tenants=True)
        .filter(Pedido.store_ref_id == store.id, Pedido.created_at >= today_start)
        .count()
    )


def _count_outbox_pendente(store: Store) -> int:
    return (
        db.session.query(MetaCapiOutbox)
        .execution_options(include_all_tenants=True)
        .filter(
            MetaCapiOutbox.store_ref_id == store.id,
            MetaCapiOutbox.status == "PENDING",
        )
        .count()
    )


# ── Tarefa 3.1: Middleware store_ref_id logging ─────────────────────────────


def test_middleware_logs_store_ref_id_in_production(client, app, session):
    """Middleware includes store_ref_id in the production request_timing log."""
    store = _create_store(session, slug="log-test", name="Log Test")
    admin = _create_admin(session, store)
    session.commit()

    log_capture = []

    class CapturingHandler(logging.Handler):
        def emit(self, record):
            log_capture.append(record)

    handler = CapturingHandler()
    logger = logging.getLogger("request_timing")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    prev_env, prev_dev = None, None
    import os

    prev_env = os.environ.get("FLASK_ENV")
    os.environ["FLASK_ENV"] = "production"

    try:
        resp = client.get("/api/health", headers=_jwt_header(admin))
        assert resp.status_code == 200

        matching = [r for r in log_capture if r.getMessage().startswith("GET /api/health")]
        assert len(matching) >= 1, "no request_timing log captured"
        record = matching[0]
        msg = record.getMessage()
        assert "[store=" in msg
        assert str(store.id) in msg
        assert getattr(record, "store_ref_id", None) == store.id
    finally:
        logger.removeHandler(handler)
        if prev_env is None:
            os.environ.pop("FLASK_ENV", None)
        else:
            os.environ["FLASK_ENV"] = prev_env


def test_middleware_logs_store_ref_id_none_when_unset(client, app, session):
    """Middleware logs store=None when tenant_store_id is not set."""
    log_capture = []

    class CapturingHandler(logging.Handler):
        def emit(self, record):
            log_capture.append(record)

    handler = CapturingHandler()
    logger = logging.getLogger("request_timing")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    import os

    prev_env = os.environ.get("FLASK_ENV")
    os.environ["FLASK_ENV"] = "production"

    try:
        resp = client.get("/api/health")
        assert resp.status_code == 200

        matching = [r for r in log_capture if r.getMessage().startswith("GET /api/health")]
        if matching:
            record = matching[0]
            msg = record.getMessage()
            assert "[store=None]" in msg
            assert getattr(record, "store_ref_id", None) is None
    finally:
        logger.removeHandler(handler)
        if prev_env is None:
            os.environ.pop("FLASK_ENV", None)
        else:
            os.environ["FLASK_ENV"] = prev_env


# ── Tarefa 3.2: Tenant health endpoint ──────────────────────────────────────


def test_tenant_health_requires_jwt(client, app, session):
    """Endpoint returns 401 without JWT."""
    resp = client.get("/api/admin/tenant-health")
    assert resp.status_code == 401


def test_tenant_health_requires_admin_role(client, app, session):
    """Endpoint returns 403 for non-admin users."""
    store = _create_store(session, slug="r1", name="R1")
    user = User(
        name="Vendedor",
        email="vendedor_th@t.com",
        password_hash=hash_password("x"),
        role="vendedor",
        store_ref_id=store.id,
    )
    session.add(user)
    session.commit()

    resp = client.get("/api/admin/tenant-health", headers=_jwt_header(user))
    assert resp.status_code == 403


def test_tenant_health_returns_only_active_stores(client, app, session):
    """Endpoint excludes inactive stores from results."""
    _create_store(session, slug="inactive", name="Inactive", active=False)
    active_store = _create_store(session, slug="active-admin", name="Active", active=True)
    admin = _create_admin(session, active_store)
    session.commit()

    resp = client.get("/api/admin/tenant-health", headers=_jwt_header(admin))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    slugs = [s["slug"] for s in data["stores"]]
    assert "active-admin" in slugs
    assert "inactive" not in slugs


def test_tenant_health_returns_metrics(client, app, session):
    """Endpoint returns correct per-store pedidos_hoje and outbox_pendente counts."""
    store_a = _create_store(session, slug="store-a", name="Store A")
    store_b = _create_store(session, slug="store-b", name="Store B")
    admin = _create_admin(session, store_a)
    session.commit()

    now = datetime_now_brazil()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today_start - timedelta(days=1)

    _create_pedido(session, store_a, now)  # hoje
    _create_pedido(session, store_a, now)  # hoje
    _create_pedido(session, store_a, yesterday)  # ontem (nao conta)
    _create_pedido(session, store_b, now)  # hoje, store B
    session.flush()

    _create_outbox(session, store_a, "PENDING")
    _create_outbox(session, store_a, "PENDING")
    _create_outbox(session, store_a, "SENT")
    _create_outbox(session, store_b, "PENDING")
    session.commit()

    resp = client.get("/api/admin/tenant-health", headers=_jwt_header(admin))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True

    stores_map = {s["slug"]: s for s in data["stores"]}

    assert stores_map["store-a"]["store_id"] == store_a.id
    assert stores_map["store-a"]["name"] == "Store A"
    assert stores_map["store-a"]["pedidos_hoje"] == 2
    assert stores_map["store-a"]["outbox_pendente"] == 2

    assert stores_map["store-b"]["store_id"] == store_b.id
    assert stores_map["store-b"]["name"] == "Store B"
    assert stores_map["store-b"]["pedidos_hoje"] == 1
    assert stores_map["store-b"]["outbox_pendente"] == 1


def test_tenant_health_bypasses_tenant_scope(client, app, session):
    """Endpoint returns all stores regardless of the caller's tenant scope."""
    store_a = _create_store(session, slug="scope-a", name="Scope A")
    store_b = _create_store(session, slug="scope-b", name="Scope B")
    _create_pedido(session, store_b, datetime_now_brazil())
    _create_outbox(session, store_b, "PENDING")
    session.commit()

    admin_a = User(
        name="Admin A",
        email="admin_a_th@t.com",
        password_hash=hash_password("x"),
        role="admin",
        store_ref_id=store_a.id,
    )
    session.add(admin_a)
    session.commit()

    resp = client.get("/api/admin/tenant-health", headers=_jwt_header(admin_a))
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {s["slug"] for s in data["stores"]}
    assert "scope-a" in slugs
    assert "scope-b" in slugs
