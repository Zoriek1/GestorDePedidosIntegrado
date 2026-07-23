from app import db
from app.models.store import Store
from app.models.store_setting import StoreSetting
from app.models.user import User
from app.services.auth_service import generate_token, hash_password
from app.services.integration_settings_service import runtime_config
from app.utils.crypto import decrypt_secret, encrypt_secret
from scripts.migrations.create_store_settings import migrate

import sqlalchemy as sa


def _store(session) -> Store:
    store = Store(name="Plante uma Flor", slug="default", active=True)
    session.add(store)
    session.commit()
    return store


def _user(session, role: str) -> User:
    user = User(
        name=f"Usuario {role}",
        email=f"{role}@integration.test",
        password_hash=hash_password("secret"),
        role=role,
    )
    session.add(user)
    session.commit()
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {generate_token(user)}"}


def test_generic_crypto_is_versioned_and_accepts_legacy_plaintext(app):
    purpose = b":test-purpose"
    encrypted = encrypt_secret("segredo", purpose)

    assert encrypted.startswith("v1:")
    assert "segredo" not in encrypted
    assert decrypt_secret(encrypted, purpose) == "segredo"
    assert decrypt_secret("legacy-plaintext", purpose) == "legacy-plaintext"


def test_admin_can_save_mask_and_clear_secrets(client, session):
    store = _store(session)
    admin = _user(session, "admin")

    response = client.put(
        "/api/config/integrations",
        headers=_headers(admin),
        json={
            "marketing_dispatch_enabled": True,
            "meta_pixel_id": "pixel-123",
            "meta_capi_access_token": "meta-secret-1234",
            "ga4_measurement_id": "G-ABC123",
            "ga4_api_secret": "ga-secret-5678",
            "ga4_validate_only": False,
            "google_datamanager_enabled": True,
            "google_ads_customer_id": "123-456-7890",
            "google_ads_conversion_action_id": "987654",
            "utmify_enabled": True,
            "utmify_api_token": "utmify-secret-9012",
            "utmify_platform": "WhatsAppManual",
            "utmify_is_test": True,
            "endereco_floricultura": "Rua das Flores, 10, Sao Paulo",
            "loja_cep": "01001000",
        },
    )

    assert response.status_code == 200
    config = response.get_json()["config"]
    assert config["meta_capi_access_token"] == "********1234"
    assert config["ga4_api_secret"] == "********5678"
    assert config["utmify_api_token"] == "********9012"
    assert config["loja_cep"] == "01001-000"
    assert "meta-secret" not in response.get_data(as_text=True)

    settings = StoreSetting.query.filter_by(store_ref_id=store.id).one()
    assert settings.meta_capi_access_token_encrypted.startswith("v1:")
    assert settings.get_secret("meta_capi_access_token") == "meta-secret-1234"

    response = client.put(
        "/api/config/integrations",
        headers=_headers(admin),
        json={
            "meta_pixel_id": "pixel-updated",
            "meta_capi_access_token": "********1234",
        },
    )
    assert response.status_code == 200
    session.refresh(settings)
    assert settings.meta_pixel_id == "pixel-updated"
    assert settings.get_secret("meta_capi_access_token") == "meta-secret-1234"

    response = client.put(
        "/api/config/integrations",
        headers=_headers(admin),
        json={"meta_capi_access_token": ""},
    )
    assert response.status_code == 200
    session.refresh(settings)
    assert settings.get_secret("meta_capi_access_token") is None


def test_patch_field_accepts_body_without_content_type(client, session):
    """O fetch() do browser nao seta Content-Type ao mandar uma string JSON.

    Sem o fallback de _parse_json_body o Flask nao parseia o body e o PATCH
    responde 400 "Campo 'value' obrigatorio". Este teste fixa o contrato: body
    JSON valido sem Content-Type ainda grava o campo.

    Cuidado ao reproduzir com a lib `requests`: ela seta Content-Type sozinha
    quando se usa `json=`, o que mascara a regressao.
    """
    store = _store(session)
    admin = _user(session, "admin")

    response = client.patch(
        "/api/config/integrations/meta_capi/meta_pixel_id",
        headers=_headers(admin),
        data='{"value": "pixel-sem-content-type"}',
        content_type=None,
    )

    assert response.status_code == 200
    settings = StoreSetting.query.filter_by(store_ref_id=store.id).one()
    assert settings.meta_pixel_id == "pixel-sem-content-type"


def test_patch_field_rejects_control_chars(client, session):
    """Bytes de controle abrem espaco para log injection e smuggling."""
    _store(session)
    admin = _user(session, "admin")

    response = client.patch(
        "/api/config/integrations/meta_capi/meta_pixel_id",
        headers=_headers(admin),
        json={"value": "pixel\r\ninjetado"},
    )

    assert response.status_code == 400
    assert "inválidos" in response.get_json()["error"]


def test_integration_settings_reject_non_admin(client, session):
    _store(session)
    viewer = _user(session, "viewer")

    response = client.get("/api/config/integrations", headers=_headers(viewer))

    assert response.status_code == 403


def test_store_settings_migration_imports_environment_once(app, session):
    store = _store(session)
    app.config.update(
        META_PIXEL_ID="pixel-from-env",
        META_CAPI_ACCESS_TOKEN="secret-from-env",
        UTMIFY_ENABLED=True,
        UTMIFY_API_TOKEN="utmify-from-env",
    )

    migrate()
    migrate()

    settings = StoreSetting.query.filter_by(store_ref_id=store.id).one()
    assert settings.meta_pixel_id == "pixel-from-env"
    assert settings.get_secret("meta_capi_access_token") == "secret-from-env"
    assert settings.get_secret("utmify_api_token") == "utmify-from-env"
    assert StoreSetting.query.filter_by(store_ref_id=store.id).count() == 1


def test_runtime_config_prefers_database_and_falls_back_to_environment(app, session):
    app.config["META_PIXEL_ID"] = "pixel-env"
    assert runtime_config()["META_PIXEL_ID"] == "pixel-env"

    store = _store(session)
    settings = StoreSetting(store_ref_id=store.id, meta_pixel_id="pixel-db")
    settings.set_secret("meta_capi_access_token", "token-db")
    session.add(settings)
    session.commit()

    config = runtime_config(store.id)
    assert config["META_PIXEL_ID"] == "pixel-db"
    assert config["META_CAPI_ACCESS_TOKEN"] == "token-db"

    settings.set_secret("meta_capi_access_token", None)
    app.config["META_CAPI_ACCESS_TOKEN"] = "token-env-nao-deve-voltar"
    other_store = Store(name="Outra loja", slug="outra-loja", active=True)
    session.add(other_store)
    session.commit()

    assert runtime_config(store.id)["META_CAPI_ACCESS_TOKEN"] == ""
    assert runtime_config(other_store.id)["META_PIXEL_ID"] == ""
    assert runtime_config(other_store.id)["META_CAPI_ACCESS_TOKEN"] == ""


def test_migration_adds_missing_columns_to_existing_table(app, session):
    """Simula deploy antigo: tabela store_settings existe mas sem colunas novas.

    Cenario de producao: a tabela foi criada por uma versao anterior do ORM
    que nao tinha mercado_pago_*, taxa_cartao_*, endereco_floricultura, loja_cep.
    O migration deve detectar e adicionar as colunas faltantes.
    """
    store = Store(name="Plante uma Flor", slug="default", active=True)
    session.add(store)
    session.commit()

    # 1) Dropa a tabela completa que db.create_all() criou
    StoreSetting.__table__.drop(bind=db.engine, checkfirst=True)

    # 2) Recria SO com as colunas originais (simula deploy antigo)
    session.execute(sa.text(
        "CREATE TABLE store_settings ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  store_ref_id INTEGER NOT NULL,"
        "  marketing_dispatch_enabled BOOLEAN NOT NULL DEFAULT 0,"
        "  meta_pixel_id VARCHAR(50),"
        "  meta_capi_access_token_encrypted TEXT,"
        "  ga4_measurement_id VARCHAR(30),"
        "  ga4_api_secret_encrypted TEXT,"
        "  ga4_validate_only BOOLEAN NOT NULL DEFAULT 0,"
        "  google_datamanager_enabled BOOLEAN NOT NULL DEFAULT 0,"
        "  google_ads_customer_id VARCHAR(30),"
        "  google_ads_conversion_action_id VARCHAR(80),"
        "  utmify_enabled BOOLEAN NOT NULL DEFAULT 0,"
        "  utmify_api_token_encrypted TEXT,"
        "  utmify_platform VARCHAR(80),"
        "  utmify_is_test BOOLEAN NOT NULL DEFAULT 0,"
        "  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
        "  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ")"
    ))
    session.commit()

    # Confirma que as colunas novas NAO existem
    inspector = sa.inspect(db.engine)
    cols_before = {c["name"] for c in inspector.get_columns("store_settings")}
    assert "mercado_pago_access_token_encrypted" not in cols_before
    assert "taxa_cartao_debito_pct" not in cols_before
    assert "endereco_floricultura" not in cols_before
    assert "loja_cep" not in cols_before

    # 3) Roda o migration — deve adicionar as colunas faltantes
    migrate()

    # 4) Confirma que as colunas agora existem (usa PRAGMA para bypass do cache do inspector)
    rows = session.execute(sa.text("PRAGMA table_info(store_settings)")).fetchall()
    cols_after = {row[1] for row in rows}
    assert "mercado_pago_access_token_encrypted" in cols_after
    assert "mercado_pago_public_key_encrypted" in cols_after
    assert "mercado_pago_webhook_secret_encrypted" in cols_after
    assert "mercado_pago_enabled" in cols_after
    assert "taxa_cartao_debito_pct" in cols_after
    assert "taxa_cartao_credito_json" in cols_after
    assert "endereco_floricultura" in cols_after
    assert "loja_cep" in cols_after

    # 5) ORM consegue consultar a tabela sem erro
    loaded = StoreSetting.query.filter_by(store_ref_id=store.id).one()
    assert loaded.mercado_pago_enabled is False
    assert loaded.taxa_cartao_debito_pct == 0
    assert loaded.endereco_floricultura is None
    assert loaded.loja_cep is None


def test_migration_is_idempotent_on_already_complete_table(app, session):
    """Se a tabela ja tem todas as colunas, o migration nao quebra nem duplica."""
    store = Store(name="Plante uma Flor", slug="default", active=True)
    session.add(store)
    session.commit()

    # Cria tabela COMPLETA (colunas todas presentes)
    StoreSetting.__table__.create(bind=db.engine, checkfirst=True)
    settings = StoreSetting(store_ref_id=store.id, meta_pixel_id="pixel-full")
    session.add(settings)
    session.commit()

    # Roda o migration — deve ser idempotente
    migrate()

    # Dados preservados, sem duplicacao
    loaded = StoreSetting.query.filter_by(store_ref_id=store.id).one()
    assert loaded.meta_pixel_id == "pixel-full"
    assert StoreSetting.query.filter_by(store_ref_id=store.id).count() == 1
