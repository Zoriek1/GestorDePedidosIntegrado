"""Testes para o context manager secure_runtime_config (Tarefa 4.2)."""

import gc

from app.models.store import Store
from app.models.store_setting import StoreSetting
from app.services.integration_settings_service import runtime_config
from app.services.secure_config import SECRET_KEYS, secure_runtime_config


def _store(session) -> Store:
    store = Store(name="Plante uma Flor", slug="default", active=True)
    session.add(store)
    session.commit()
    return store


def _setup_settings(session, store: Store) -> None:
    settings = StoreSetting(store_ref_id=store.id)
    for field, value in [
        ("meta_capi_access_token", "super-secret-token-123"),
        ("ga4_api_secret", "ga4-secret-456"),
        ("utmify_api_token", "utmify-token-789"),
    ]:
        settings.set_secret(field, value)
    session.add(settings)
    session.commit()


def test_secure_runtime_config_clears_secrets_after_use(app, session):
    store = _store(session)
    _setup_settings(session, store)
    config_ref = [None]

    with secure_runtime_config(store.id) as cfg:
        config_ref[0] = cfg
        assert cfg["META_CAPI_ACCESS_TOKEN"] == "super-secret-token-123"
        assert cfg["GA4_API_SECRET"] == "ga4-secret-456"
        assert cfg["UTMIFY_API_TOKEN"] == "utmify-token-789"

    for key in SECRET_KEYS:
        assert config_ref[0][key] is None, f"{key} deveria ser None apos uso"


def test_secure_runtime_config_works_without_secrets(app, session):
    store = _store(session)
    settings = StoreSetting(store_ref_id=store.id, meta_pixel_id="pixel-1")
    session.add(settings)
    session.commit()

    with secure_runtime_config(store.id) as cfg:
        assert cfg["META_PIXEL_ID"] == "pixel-1"
        assert cfg["META_CAPI_ACCESS_TOKEN"] == ""

    for key in SECRET_KEYS:
        assert cfg[key] is None, f"{key} deveria ser None apos uso"


def test_secure_runtime_config_same_as_runtime_config_before_cleanup(app, session):
    store = _store(session)
    _setup_settings(session, store)

    expected = runtime_config(store.id)
    with secure_runtime_config(store.id) as cfg:
        for key in expected:
            assert cfg[key] == expected[key], f"Mismatch for {key}: {cfg[key]} != {expected[key]}"


def test_secure_runtime_config_clears_refs_and_collects(app, session):
    store = _store(session)
    _setup_settings(session, store)

    config_ref = [None]

    with secure_runtime_config(store.id) as cfg:
        config_ref[0] = cfg

    assert config_ref[0] is not None
    for key in SECRET_KEYS:
        assert config_ref[0][key] is None

    config_ref[0] = None
    gc.collect()
