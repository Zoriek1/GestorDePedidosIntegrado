# -*- coding: utf-8 -*-
"""Testes do F6/E0 — Grid de Integracoes (PATCH/validate/validation_log)."""

from unittest.mock import patch

import pytest

from app.models.integration_validation_log import IntegrationValidationLog
from app.models.store import Store
from app.models.store_setting import StoreSetting
from app.models.user import User
from app.services.auth_service import generate_token, hash_password
from app.services.integration_validation.lock import store_lock

# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture
def store(session) -> Store:
    store = Store(name="Plante uma Flor", slug="default", active=True)
    session.add(store)
    session.commit()
    return store


@pytest.fixture
def other_store(session) -> Store:
    other = Store(name="Outra Loja", slug="outra", active=True)
    session.add(other)
    session.commit()
    return other


@pytest.fixture
def admin(session) -> User:
    user = User(
        name="Admin",
        email="admin@test.local",
        password_hash=hash_password("secret"),
        role="admin",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def viewer(session) -> User:
    user = User(
        name="Viewer",
        email="viewer@test.local",
        password_hash=hash_password("secret"),
        role="viewer",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def auth_headers(admin) -> dict:
    return {"Authorization": f"Bearer {generate_token(admin)}"}


# ----------------------------------------------------------------------------
# Helpers de validacao (formato)
# ----------------------------------------------------------------------------


def test_validate_meta_pixel_id_format():
    from app.services.integration_validation.meta_capi import validate_meta_pixel_id

    ok, err = validate_meta_pixel_id("1234567890")
    assert ok and err is None
    ok, err = validate_meta_pixel_id("abc")
    assert not ok and "digitos" in (err or "")
    ok, err = validate_meta_pixel_id("")
    assert not ok


def test_validate_google_ads_format_only():
    from app.services.integration_validation.google_ads import (
        validate_google_ads_conversion_action_id,
        validate_google_ads_customer_id,
    )

    ok, err = validate_google_ads_customer_id("123-456-7890")
    assert ok and err is None
    ok, err = validate_google_ads_customer_id("1234567890")
    assert not ok
    ok, err = validate_google_ads_conversion_action_id("987654")
    assert ok and err is None
    ok, err = validate_google_ads_conversion_action_id("abc")
    assert not ok


def test_validate_utmify_token_and_platform():
    from app.services.integration_validation.utmify import (
        validate_utmify_api_token,
        validate_utmify_platform,
    )

    ok, _ = validate_utmify_api_token("a" * 20)
    assert ok
    ok, err = validate_utmify_api_token("short")
    assert not ok and "16" in (err or "")
    ok, _ = validate_utmify_platform("Loja")
    assert ok
    ok, err = validate_utmify_platform("Invalida")
    assert not ok


def test_validate_cep_calls_viacep_and_handles_not_found():
    from app.services.integration_validation.dados_operacionais import (
        validate_loja_cep,
    )

    fake = lambda url, timeout: (200, {"erro": True})  # noqa: E731
    ok, err = validate_loja_cep("01001-000", http_get=fake)
    assert not ok and "nao encontrado" in (err or "")

    fake_ok = lambda url, timeout: (200, {"erro": False, "logradouro": "Praça"})  # noqa: E731
    ok, err = validate_loja_cep("01001000", http_get=fake_ok)
    assert ok and err is None

    ok, err = validate_loja_cep("invalid", http_get=fake_ok)
    assert not ok

    fake_500 = lambda url, timeout: (500, {"erro": False})  # noqa: E731
    ok, err = validate_loja_cep("01001-000", http_get=fake_500)
    assert not ok and "500" in (err or "")


def test_validate_meta_token_format_and_meta_call():
    from app.services.integration_validation.meta_capi import (
        validate_meta_capi_access_token,
    )

    ok, err = validate_meta_capi_access_token("x" * 20)
    assert not ok and "vazio" in (err or "").lower() or not ok  # sem rede -> falha

    fake_200 = lambda url, timeout: (200, {"id": "123"})  # noqa: E731
    ok, err = validate_meta_capi_access_token("a" * 32, http_get=fake_200)
    assert ok and err is None

    fake_401 = lambda url, timeout: (401, {"error": {"message": "x"}})  # noqa: E731
    ok, err = validate_meta_capi_access_token("a" * 32, http_get=fake_401)
    assert not ok and "invalido" in (err or "").lower()


# ----------------------------------------------------------------------------
# Lock
# ----------------------------------------------------------------------------


def test_store_lock_serializes_per_store():
    import threading
    import time

    order = []

    def slow(store_id):
        with store_lock(store_id):
            order.append(f"start-{store_id}")
            time.sleep(0.05)
            order.append(f"end-{store_id}")

    threads = [
        threading.Thread(target=slow, args=(1,)),
        threading.Thread(target=slow, args=(1,)),
        threading.Thread(target=slow, args=(2,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Locks por loja sao independentes: store 2 pode rodar entre stores 1.
    assert order.count("start-1") == 2
    assert order.count("end-1") == 2


# ----------------------------------------------------------------------------
# PATCH endpoint
# ----------------------------------------------------------------------------


def test_patch_field_updates_and_resets_validation_log(client, session, store, admin, auth_headers):
    # Setup: log de validacao antigo para o canal.
    session.add(
        IntegrationValidationLog(
            store_ref_id=store.id, channel="meta_capi", field="meta_pixel_id", ok=True
        )
    )
    session.commit()

    response = client.patch(
        "/api/config/integrations/meta_capi/meta_pixel_id",
        headers=auth_headers,
        json={"value": "1234567890"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    settings = StoreSetting.query.filter_by(store_ref_id=store.id).one()
    assert settings.meta_pixel_id == "1234567890"
    assert (
        IntegrationValidationLog.query.filter_by(store_ref_id=store.id, channel="meta_capi").count()
        == 0
    )


def test_patch_field_none_removes_secret_and_logs(client, session, store, admin, auth_headers):
    settings = StoreSetting(store_ref_id=store.id)
    settings.set_secret("meta_capi_access_token", "anterior-1234")
    session.add(settings)
    session.add(
        IntegrationValidationLog(store_ref_id=store.id, channel="meta_capi", field=None, ok=True)
    )
    session.commit()

    response = client.patch(
        "/api/config/integrations/meta_capi/meta_capi_access_token",
        headers=auth_headers,
        json={"value": None},
    )
    assert response.status_code == 200
    session.refresh(settings)
    assert settings.get_secret("meta_capi_access_token") is None
    assert (
        IntegrationValidationLog.query.filter_by(store_ref_id=store.id, channel="meta_capi").count()
        == 0
    )


def test_patch_masked_value_is_noop(client, session, store, admin, auth_headers):
    settings = StoreSetting(store_ref_id=store.id)
    settings.set_secret("meta_capi_access_token", "orig-9999")
    session.add(settings)
    session.commit()

    response = client.patch(
        "/api/config/integrations/meta_capi/meta_capi_access_token",
        headers=auth_headers,
        json={"value": "********9999"},
    )
    assert response.status_code == 200
    session.refresh(settings)
    assert settings.get_secret("meta_capi_access_token") == "orig-9999"


def test_patch_rejects_unknown_channel(client, session, admin, auth_headers):
    response = client.patch(
        "/api/config/integrations/nuvemshop/foo",
        headers=auth_headers,
        json={"value": "x"},
    )
    assert response.status_code == 400


def test_patch_rejects_field_not_in_channel(client, session, admin, auth_headers):
    response = client.patch(
        "/api/config/integrations/meta_capi/loja_cep",
        headers=auth_headers,
        json={"value": "01001-000"},
    )
    assert response.status_code == 400


def test_patch_rejects_non_admin(client, session, store, viewer):
    headers = {"Authorization": f"Bearer {generate_token(viewer)}"}
    response = client.patch(
        "/api/config/integrations/meta_capi/meta_pixel_id",
        headers=headers,
        json={"value": "1234567890"},
    )
    assert response.status_code == 403


# ----------------------------------------------------------------------------
# Validate endpoint
# ----------------------------------------------------------------------------


def test_validate_field_writes_log(client, session, store, admin, auth_headers):
    fake = lambda url, timeout: (200, {"id": "123"})  # noqa: E731
    with patch("app.services.integration_validation.meta_capi._default_http_get", fake):
        response = client.post(
            "/api/config/integrations/meta_capi/meta_capi_access_token/validate",
            headers=auth_headers,
            json={"value": "a" * 32},
        )
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["ok"] is True
    log = IntegrationValidationLog.query.filter_by(store_ref_id=store.id, channel="meta_capi").one()
    assert log.ok is True
    assert log.field == "meta_capi_access_token"


def test_validate_field_uses_saved_secret_when_no_value(
    client, session, store, admin, auth_headers
):
    settings = StoreSetting(store_ref_id=store.id)
    settings.set_secret("meta_capi_access_token", "salvo-token-1234567890")
    session.add(settings)
    session.commit()

    fake = lambda url, timeout: (200, {"id": "123"})  # noqa: E731
    with patch("app.services.integration_validation.meta_capi._default_http_get", fake):
        response = client.post(
            "/api/config/integrations/meta_capi/meta_capi_access_token/validate",
            headers=auth_headers,
            json={},
        )
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_validate_cep_format_only_no_network(client, session, store, admin, auth_headers):
    # CEP fora de formato -> erro de formato sem chamar rede.
    response = client.post(
        "/api/config/integrations/dados_operacionais/loja_cep/validate",
        headers=auth_headers,
        json={"value": "abc"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is False
    assert "00000-000" in (body["error"] or "")


def test_validate_rejects_unknown_channel(client, session, admin, auth_headers):
    response = client.post(
        "/api/config/integrations/nuvemshop/foo/validate",
        headers=auth_headers,
        json={"value": "x"},
    )
    assert response.status_code == 400


# ----------------------------------------------------------------------------
# GET validation status
# ----------------------------------------------------------------------------


def test_list_validation_returns_latest(client, session, store, admin, auth_headers):
    session.add_all(
        [
            IntegrationValidationLog(
                store_ref_id=store.id, channel="meta_capi", field=None, ok=True
            ),
            IntegrationValidationLog(
                store_ref_id=store.id,
                channel="meta_capi",
                field="meta_capi_access_token",
                ok=False,
                error="invalido",
            ),
        ]
    )
    session.commit()

    response = client.get(
        "/api/config/integrations/validation?channel=meta_capi",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert len(body["entries"]) == 2


def test_channel_status_returns_latest(client, session, store, admin, auth_headers):
    session.add(
        IntegrationValidationLog(
            store_ref_id=store.id,
            channel="meta_capi",
            field="meta_pixel_id",
            ok=True,
        )
    )
    session.commit()

    response = client.get(
        "/api/config/integrations/meta_capi/status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["channel"] == "meta_capi"
    assert body["ok"] is True


# ----------------------------------------------------------------------------
# Multi-tenant
# ----------------------------------------------------------------------------


def test_patch_isolated_per_store(client, session, store, other_store, admin, auth_headers):
    response_a = client.patch(
        "/api/config/integrations/meta_capi/meta_pixel_id",
        headers=auth_headers,
        json={"value": "1111111111"},
    )
    assert response_a.status_code == 200
    a_settings = StoreSetting.query.filter_by(store_ref_id=store.id).one()
    assert a_settings.meta_pixel_id == "1111111111"
    # Outra loja nao foi afetada
    assert StoreSetting.query.filter_by(store_ref_id=other_store.id).count() == 0


def test_validation_log_isolated_per_store(
    client, session, store, other_store, admin, auth_headers
):
    session.add(
        IntegrationValidationLog(
            store_ref_id=other_store.id,
            channel="meta_capi",
            field=None,
            ok=True,
        )
    )
    session.commit()

    response = client.get(
        "/api/config/integrations/meta_capi/status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    # O admin da loja A nao enxerga log da loja other_store.
    assert response.get_json()["ok"] is None


# ----------------------------------------------------------------------------
# E6 — Disconnect OAuth
# ----------------------------------------------------------------------------


@pytest.fixture
def bling_credential(session, store):
    from app.models.bling_credential import BlingCredential

    cred = BlingCredential(
        store_id=store.slug,
        store_ref_id=store.id,
        access_token_encrypted="fake_encrypted_at",
        refresh_token_encrypted="fake_encrypted_rt",
        token_type="Bearer",
        active=True,
    )
    session.add(cred)
    session.commit()
    return cred


@pytest.fixture
def nuvemshop_store(session, store):
    from app.models.nuvemshop_store import NuvemshopStore

    ns = NuvemshopStore(
        store_id="12345",
        store_ref_id=store.id,
        access_token="plaintext_token",
        active=True,
    )
    session.add(ns)
    session.commit()
    return ns


def test_bling_disconnect_sets_inactive_and_clears_tokens(
    client, admin, store, bling_credential
):
    token = generate_token(admin)
    resp = client.delete(
        "/api/integrations/bling/disconnect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json["success"] is True

    from app.models.bling_credential import BlingCredential

    cred = BlingCredential.query.filter_by(store_ref_id=store.id).first()
    assert cred.active is False
    assert cred.access_token_encrypted is None
    assert cred.refresh_token_encrypted is None


def test_bling_disconnect_rejects_non_admin(client, viewer, store, bling_credential):
    token = generate_token(viewer)
    resp = client.delete(
        "/api/integrations/bling/disconnect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_nuvemshop_disconnect_sets_inactive(client, admin, store, nuvemshop_store):
    token = generate_token(admin)
    resp = client.delete(
        "/api/integrations/nuvemshop/disconnect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json["success"] is True

    from app.models.nuvemshop_store import NuvemshopStore

    ns = NuvemshopStore.query.filter_by(store_ref_id=store.id).first()
    assert ns.active is False
    assert ns.uninstalled_at is not None


def test_bling_disconnect_idempotent_when_no_credential(client, admin, store):
    token = generate_token(admin)
    resp = client.delete(
        "/api/integrations/bling/disconnect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json["success"] is True


def test_nuvemshop_disconnect_idempotent_when_no_store(client, admin, store):
    token = generate_token(admin)
    resp = client.delete(
        "/api/integrations/nuvemshop/disconnect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json["success"] is True


def test_nuvemshop_disconnect_rejects_non_admin(client, viewer, store, nuvemshop_store):
    token = generate_token(viewer)
    resp = client.delete(
        "/api/integrations/nuvemshop/disconnect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
