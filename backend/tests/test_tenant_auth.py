"""Fase A — identidade autenticada por loja: JWT, login e contexto da request."""

import os
from datetime import datetime, timedelta, timezone

import jwt

from app.models.store import Store
from app.models.user import User
from app.services.auth_service import decode_token, generate_token, hash_password


def _store(session, slug: str, name: str | None = None, active: bool = True) -> Store:
    store = Store(name=name or slug, slug=slug, active=active)
    session.add(store)
    session.commit()
    return store


def _user(session, role: str, email: str, store: Store | None, is_active: bool = True) -> User:
    user = User(
        name=email,
        email=email,
        password_hash=hash_password("secret123"),
        role=role,
        is_active=is_active,
        store_ref_id=store.id if store else None,
    )
    session.add(user)
    session.commit()
    return user


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def test_jwt_of_two_stores_has_distinct_claims(session):
    store_a = _store(session, "loja-a")
    store_b = _store(session, "loja-b")
    admin_a = _user(session, "admin", "a@a.test", store_a)
    admin_b = _user(session, "admin", "b@b.test", store_b)

    claims_a = decode_token(generate_token(admin_a))
    claims_b = decode_token(generate_token(admin_b))

    assert claims_a["store_ref_id"] == store_a.id
    assert claims_a["store_slug"] == "loja-a"
    assert claims_b["store_slug"] == "loja-b"
    assert claims_a["store_ref_id"] != claims_b["store_ref_id"]


def test_legacy_token_without_tenant_resolves_store_from_user(client, session):
    store = _store(session, "default")
    admin = _user(session, "admin", "legacy@a.test", store)

    secret = os.environ.get("JWT_SECRET_KEY") or os.environ["SECRET_KEY"]
    legacy_token = jwt.encode(
        {
            "user_id": admin.id,
            "role": "admin",
            "email": admin.email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        secret,
        algorithm="HS256",
    )

    resp = client.get("/api/config/integrations", headers=_bearer(legacy_token))
    assert resp.status_code == 200
    assert resp.get_json()["config"]["store"]["slug"] == "default"


# ---------------------------------------------------------------------------
# Login / loja ausente ou inativa
# ---------------------------------------------------------------------------
def test_user_with_missing_store_cannot_login(session, client):
    # Usuário com vínculo explícito a uma loja que não existe (órfão) -> loja ausente.
    # (FK desabilitada no ambiente de teste permite simular o dangling reference.)
    user = _user(session, "admin", "orfao@a.test", store=_store(session, "temp"))
    user.store_ref_id = 999999
    session.commit()

    resp = client.post("/api/auth/login", json={"email": "orfao@a.test", "password": "secret123"})
    assert resp.status_code == 403


def test_legacy_user_without_store_still_logs_in(session, client):
    # Compat de rollout: base legada single-tenant (sem loja default e sem vínculo)
    # continua autenticando.
    _user(session, "vendedor", "legacy-login@a.test", store=None)

    resp = client.post(
        "/api/auth/login", json={"email": "legacy-login@a.test", "password": "secret123"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "legacy-login@a.test"


def test_legacy_user_without_store_fails_closed_in_multi_store(session, client):
    _store(session, "loja-a")
    _store(session, "loja-b")
    legacy = _user(session, "admin", "legacy-multi@a.test", store=None)

    response = client.get("/api/users", headers=_bearer(generate_token(legacy)))

    assert response.status_code == 403
    assert response.get_json()["message"] == "Empresa do usuario nao identificada."


def test_inactive_store_blocks_login(client, session):
    store = _store(session, "loja-inativa", active=False)
    _user(session, "admin", "inativa@a.test", store)

    resp = client.post("/api/auth/login", json={"email": "inativa@a.test", "password": "secret123"})
    assert resp.status_code == 403


def test_inactive_store_blocks_authenticated_request(client, session):
    store = _store(session, "loja-x", active=True)
    admin = _user(session, "admin", "x@a.test", store)
    token = generate_token(admin, store)

    # Loja é desativada depois de o token ter sido emitido.
    store.active = False
    session.commit()

    resp = client.get("/api/config/integrations", headers=_bearer(token))
    assert resp.status_code == 403


def test_inactive_user_cannot_use_token(client, session):
    store = _store(session, "default")
    admin = _user(session, "admin", "off@a.test", store)
    token = generate_token(admin, store)

    admin.is_active = False
    session.commit()

    resp = client.get("/api/config/integrations", headers=_bearer(token))
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Isolamento de settings por loja
# ---------------------------------------------------------------------------
def test_admin_reads_and_writes_only_own_store_settings(client, session):
    store_a = _store(session, "loja-a")
    store_b = _store(session, "loja-b")
    admin_a = _user(session, "admin", "a@a.test", store_a)
    admin_b = _user(session, "admin", "b@b.test", store_b)

    r = client.put(
        "/api/config/integrations",
        headers=_bearer(generate_token(admin_a, store_a)),
        json={"meta_pixel_id": "pixel-A", "meta_capi_access_token": "token-A-0001"},
    )
    assert r.status_code == 200
    assert r.get_json()["config"]["store"]["slug"] == "loja-a"

    r = client.put(
        "/api/config/integrations",
        headers=_bearer(generate_token(admin_b, store_b)),
        json={"meta_pixel_id": "pixel-B"},
    )
    assert r.status_code == 200
    assert r.get_json()["config"]["store"]["slug"] == "loja-b"

    # Admin A vê só A
    r = client.get("/api/config/integrations", headers=_bearer(generate_token(admin_a, store_a)))
    cfg_a = r.get_json()["config"]
    assert cfg_a["store"]["slug"] == "loja-a"
    assert cfg_a["meta_pixel_id"] == "pixel-A"

    # Admin B vê só B (não herda pixel/segredo de A)
    r = client.get("/api/config/integrations", headers=_bearer(generate_token(admin_b, store_b)))
    cfg_b = r.get_json()["config"]
    assert cfg_b["store"]["slug"] == "loja-b"
    assert cfg_b["meta_pixel_id"] == "pixel-B"
    assert cfg_b["meta_capi_access_token"] is None
    assert cfg_b["has_meta_capi_access_token"] is False


def test_store_without_settings_returns_disabled_config_without_default_secrets(
    client, session, app
):
    # Segredo no .env não pode vazar para uma loja nova sem settings.
    app.config["META_PIXEL_ID"] = "pixel-do-env"
    app.config["META_CAPI_ACCESS_TOKEN"] = "segredo-do-env"

    _store(session, "default")
    store_b = _store(session, "loja-nova")
    admin_b = _user(session, "admin", "nova@a.test", store_b)

    r = client.get("/api/config/integrations", headers=_bearer(generate_token(admin_b, store_b)))
    assert r.status_code == 200
    cfg = r.get_json()["config"]
    assert cfg["configured"] is False
    assert cfg["meta_pixel_id"] is None
    assert cfg["meta_capi_access_token"] is None


def test_config_rejects_foreign_store_ref_id_in_payload(client, session):
    store_a = _store(session, "loja-a")
    store_b = _store(session, "loja-b")
    admin_a = _user(session, "admin", "a@a.test", store_a)

    r = client.put(
        "/api/config/integrations",
        headers=_bearer(generate_token(admin_a, store_a)),
        json={"store_ref_id": store_b.id, "meta_pixel_id": "x"},
    )
    assert r.status_code == 400


def test_non_admin_forbidden_on_integrations(client, session):
    store = _store(session, "default")
    viewer = _user(session, "viewer", "v@a.test", store)

    r = client.get("/api/config/integrations", headers=_bearer(generate_token(viewer, store)))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Escrita de usuário herda a loja do admin autenticado
# ---------------------------------------------------------------------------
def test_created_user_inherits_admin_store_and_ignores_payload(client, session):
    store_a = _store(session, "loja-a")
    store_b = _store(session, "loja-b")
    admin_a = _user(session, "admin", "a@a.test", store_a)

    r = client.post(
        "/api/users",
        headers=_bearer(generate_token(admin_a, store_a)),
        json={
            "name": "Novo Vendedor",
            "email": "novo@a.test",
            "password": "secret123",
            "role": "vendedor",
            "store_ref_id": store_b.id,  # deve ser ignorado
        },
    )
    assert r.status_code == 201
    created = User.query.filter_by(email="novo@a.test").one()
    assert created.store_ref_id == store_a.id


def test_admin_cannot_manage_legacy_null_store_user_in_multi_store(client, session):
    store_a = _store(session, "loja-a")
    _store(session, "loja-b")
    admin_a = _user(session, "admin", "admin-a@a.test", store_a)
    legacy = _user(session, "vendedor", "legacy-null@a.test", store=None)

    response = client.get("/api/users", headers=_bearer(generate_token(admin_a, store_a)))

    assert response.status_code == 200
    ids = {item["id"] for item in response.get_json()["users"]}
    assert legacy.id not in ids
