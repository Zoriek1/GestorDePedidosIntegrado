"""Fase B — OAuth/callbacks sem sessão com trigger data-driven (loja ativa)."""

from urllib.parse import parse_qs, urlparse

from app import db
from app.integrations.bling.token_service import BlingTokenService
from app.models.bling_credential import BlingCredential
from app.models.nuvemshop_store import NuvemshopStore
from app.models.store import Store
from app.models.user import User
from app.services import tenancy
from app.services.auth_service import generate_token, hash_password
from app.services.oauth_state import sign_state, verify_state


def _store(session, slug: str, active: bool = True) -> Store:
    store = Store(name=slug, slug=slug, active=active)
    session.add(store)
    session.commit()
    return store


def _admin(session, email: str, store: Store) -> User:
    user = User(
        name=email,
        email=email,
        password_hash=hash_password("secret123"),
        role="admin",
        is_active=True,
        store_ref_id=store.id,
    )
    session.add(user)
    session.commit()
    return user


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _bling_config(app) -> None:
    app.config.update(
        BLING_CLIENT_ID="cid",
        BLING_CLIENT_SECRET="csecret",
        BLING_REDIRECT_URI="https://app.test/api/integrations/bling/oauth/callback",
        BLING_AUTH_BASE_URL="https://bling.test/oauth",
    )


# ---------------------------------------------------------------------------
# OAuth state assinado
# ---------------------------------------------------------------------------
def test_oauth_state_roundtrip_and_rejections():
    state = sign_state(7, "bling")
    payload = verify_state(state, "bling")
    assert payload and payload["srid"] == 7

    # Provedor diferente não valida (sem replay entre Bling/Nuvemshop).
    assert verify_state(state, "nuvemshop") is None
    # State adulterado é rejeitado.
    body, _, sig = state.partition(".")
    assert verify_state(f"{body}.{sig}x", "bling") is None
    assert verify_state("lixo", "bling") is None
    assert verify_state(None, "bling") is None
    # Expirado é rejeitado.
    assert verify_state(sign_state(7, "bling", ttl_seconds=-10), "bling") is None


# ---------------------------------------------------------------------------
# Trigger data-driven
# ---------------------------------------------------------------------------
def test_is_multi_store_trigger(app, session):
    a = _store(session, "default")
    assert tenancy.is_multi_store() is False  # 1 loja ativa

    _store(session, "loja-inativa", active=False)
    assert tenancy.is_multi_store() is False  # 2ª loja inativa não conta

    _store(session, "loja-b")
    assert tenancy.is_multi_store() is True  # 2 lojas ativas

    # Override manual força o modo estrito mesmo com 1 loja ativa.
    db.session.delete(Store.query.filter_by(slug="loja-b").first())
    db.session.commit()
    assert tenancy.is_multi_store() is False
    app.config["FORCE_MULTI_TENANT"] = True
    assert tenancy.is_multi_store() is True
    app.config["FORCE_MULTI_TENANT"] = False
    assert a.slug == "default"


# ---------------------------------------------------------------------------
# Bling
# ---------------------------------------------------------------------------
def test_bling_install_state_is_bound_to_current_store(app, client, session):
    _bling_config(app)
    store = _store(session, "default")
    admin = _admin(session, "a@a.test", store)

    resp = client.get(
        "/api/integrations/bling/install", headers=_bearer(generate_token(admin, store))
    )
    assert resp.status_code == 200
    url = resp.get_json()["authorize_url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    assert verify_state(state, "bling")["srid"] == store.id


def test_bling_callback_binds_credential_to_store(app, client, session, monkeypatch):
    store = _store(session, "default")
    monkeypatch.setattr(
        BlingTokenService,
        "_post_token",
        staticmethod(
            lambda data: {
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "x",
                "_status_code": 200,
            }
        ),
    )

    state = sign_state(store.id, "bling")
    resp = client.get(f"/api/integrations/bling/oauth/callback?code=abc&state={state}")
    assert resp.status_code == 302

    cred = BlingCredential.query.filter_by(store_ref_id=store.id).one()
    assert cred.store_id == store.slug
    assert cred.refresh_token_encrypted


def test_bling_callback_fails_closed_in_multi_store(app, client, session):
    _store(session, "default")
    _store(session, "loja-b")  # 2 lojas ativas -> multi-store

    resp = client.get("/api/integrations/bling/oauth/callback?code=abc")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Nuvemshop
# ---------------------------------------------------------------------------
def test_nuvemshop_install_includes_tenant_state(app, client, session):
    app.config.update(NUVEMSHOP_APP_ID="123", NUVEMSHOP_PUBLIC_BASE_URL="https://app.test")
    from app.config import Config

    monkey_prev = (Config.NUVEMSHOP_APP_ID, Config.NUVEMSHOP_PUBLIC_BASE_URL)
    Config.NUVEMSHOP_APP_ID = "123"
    Config.NUVEMSHOP_PUBLIC_BASE_URL = "https://app.test"
    try:
        store = _store(session, "default")
        admin = _admin(session, "a@a.test", store)
        resp = client.get(
            "/api/integrations/nuvemshop/install",
            headers=_bearer(generate_token(admin, store)),
        )
        assert resp.status_code == 200
        url = resp.get_json()["authorize_url"]
        state = parse_qs(urlparse(url).query)["state"][0]
        assert verify_state(state, "nuvemshop")["srid"] == store.id
    finally:
        Config.NUVEMSHOP_APP_ID, Config.NUVEMSHOP_PUBLIC_BASE_URL = monkey_prev


def test_nuvemshop_callback_binds_store_ref(app, client, session, monkeypatch):
    from app.config import Config

    prev = (
        Config.NUVEMSHOP_APP_ID,
        Config.NUVEMSHOP_CLIENT_SECRET,
        Config.NUVEMSHOP_USER_AGENT,
        Config.NUVEMSHOP_PUBLIC_BASE_URL,
    )
    Config.NUVEMSHOP_APP_ID = "123"
    Config.NUVEMSHOP_CLIENT_SECRET = "secret"
    Config.NUVEMSHOP_USER_AGENT = "App (a@a.test)"
    Config.NUVEMSHOP_PUBLIC_BASE_URL = "https://app.test"
    monkeypatch.setattr(
        "app.routes.nuvemshop.NuvemshopTokenService.exchange_code",
        lambda **kwargs: {"access_token": "tok", "user_id": "EXT-A"},
    )
    monkeypatch.setattr("app.routes.nuvemshop.NuvemshopClient", lambda **kwargs: object())
    monkeypatch.setattr("app.routes.nuvemshop._setup_order_webhooks", lambda *a, **k: None)
    try:
        store = _store(session, "default")
        state = sign_state(store.id, "nuvemshop")
        resp = client.get(f"/api/integrations/nuvemshop/oauth/callback?code=abc&state={state}")
        assert resp.status_code == 302
        ns = NuvemshopStore.query.filter_by(store_id="EXT-A").one()
        assert ns.store_ref_id == store.id
    finally:
        (
            Config.NUVEMSHOP_APP_ID,
            Config.NUVEMSHOP_CLIENT_SECRET,
            Config.NUVEMSHOP_USER_AGENT,
            Config.NUVEMSHOP_PUBLIC_BASE_URL,
        ) = prev


def test_nuvemshop_callback_fails_closed_in_multi_store(app, client, session):
    from app.config import Config

    prev = (Config.NUVEMSHOP_APP_ID, Config.NUVEMSHOP_CLIENT_SECRET)
    Config.NUVEMSHOP_APP_ID = "123"
    Config.NUVEMSHOP_CLIENT_SECRET = "secret"
    try:
        _store(session, "default")
        _store(session, "loja-b")  # multi-store
        resp = client.get("/api/integrations/nuvemshop/oauth/callback?code=abc")
        assert resp.status_code == 400
    finally:
        Config.NUVEMSHOP_APP_ID, Config.NUVEMSHOP_CLIENT_SECRET = prev


def test_nuvemshop_config_scoped_to_current_store_in_multi_store(app, client, session):
    store_a = _store(session, "loja-a")
    store_b = _store(session, "loja-b")  # 2 ativas -> multi-store
    admin_a = _admin(session, "a@a.test", store_a)
    admin_b = _admin(session, "b@b.test", store_b)

    session.add_all(
        [
            NuvemshopStore(
                store_id="EXT-A", access_token="ta", active=True, store_ref_id=store_a.id
            ),
            NuvemshopStore(
                store_id="EXT-B", access_token="tb", active=True, store_ref_id=store_b.id
            ),
        ]
    )
    session.commit()

    r_a = client.get(
        "/api/integrations/nuvemshop/config", headers=_bearer(generate_token(admin_a, store_a))
    )
    r_b = client.get(
        "/api/integrations/nuvemshop/config", headers=_bearer(generate_token(admin_b, store_b))
    )
    assert r_a.get_json()["store_id"] == "EXT-A"
    assert r_b.get_json()["store_id"] == "EXT-B"


# ---------------------------------------------------------------------------
# Backfill migration (defensiva/idempotente)
# ---------------------------------------------------------------------------
def test_backfill_store_ref_on_integrations(app, session):
    from scripts.migrations.backfill_store_ref_on_integrations import migrate

    default = _store(session, "default")
    session.add_all(
        [
            NuvemshopStore(store_id="EXT-1", access_token="t", active=True),
            BlingCredential(store_id="default"),
        ]
    )
    session.commit()

    migrate()
    migrate()  # idempotente

    ns = NuvemshopStore.query.filter_by(store_id="EXT-1").one()
    bc = BlingCredential.query.filter_by(store_id="default").one()
    assert ns.store_ref_id == default.id
    assert bc.store_ref_id == default.id
