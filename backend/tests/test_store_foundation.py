from sqlalchemy import inspect, text

from app import db
from app.models.bling_credential import BlingCredential
from app.models.nuvemshop_store import NuvemshopStore
from app.models.store import Store
from scripts.migrations.add_store_foundation import migrate


def _replace_with_legacy_integration_tables() -> None:
    db.session.remove()
    with db.engine.begin() as connection:
        connection.execute(text("DROP TABLE nuvemshop_stores"))
        connection.execute(text("DROP TABLE bling_credentials"))
        connection.execute(text("DROP TABLE stores"))
        connection.execute(
            text(
                "CREATE TABLE nuvemshop_stores ("
                "id INTEGER PRIMARY KEY, "
                "store_id VARCHAR(50) NOT NULL UNIQUE, "
                "access_token TEXT NOT NULL"
                ")"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE bling_credentials ("
                "id INTEGER PRIMARY KEY, "
                "store_id VARCHAR(50) NOT NULL UNIQUE"
                ")"
            )
        )


def test_fresh_database_has_store_table_and_integration_foreign_keys(app):
    inspector = inspect(db.engine)

    assert "stores" in inspector.get_table_names()
    for table in ("nuvemshop_stores", "bling_credentials"):
        foreign_keys = inspector.get_foreign_keys(table)
        assert any(
            fk["constrained_columns"] == ["store_ref_id"]
            and fk["referred_table"] == "stores"
            and fk["referred_columns"] == ["id"]
            for fk in foreign_keys
        )


def test_integration_models_keep_store_ref_nullable(session):
    nuvemshop = NuvemshopStore(store_id="tenant-ready", access_token="token")
    bling = BlingCredential(store_id="tenant-ready")
    session.add_all([nuvemshop, bling])
    session.commit()

    assert nuvemshop.store_ref_id is None
    assert bling.store_ref_id is None


def test_legacy_upgrade_backfills_and_is_idempotent(app):
    _replace_with_legacy_integration_tables()
    with db.engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO nuvemshop_stores (id, store_id, access_token) "
                "VALUES (1, 'external-1', 'token-1'), (2, 'external-2', 'token-2')"
            )
        )
        connection.execute(
            text("INSERT INTO bling_credentials (id, store_id) VALUES (1, 'default')")
        )

    migrate()
    migrate()

    inspector = inspect(db.engine)
    for table in ("nuvemshop_stores", "bling_credentials"):
        columns = {column["name"] for column in inspector.get_columns(table)}
        indexes = {index["name"] for index in inspector.get_indexes(table)}
        assert "store_ref_id" in columns
        assert f"ix_{table}_store_ref_id" in indexes

    default_store = db.session.execute(db.select(Store).where(Store.slug == "default")).scalar_one()
    assert Store.query.filter_by(slug="default").count() == 1
    assert (
        db.session.execute(
            text("SELECT COUNT(*) FROM nuvemshop_stores " "WHERE store_ref_id = :store_id"),
            {"store_id": default_store.id},
        ).scalar_one()
        == 2
    )
    assert (
        db.session.execute(
            text("SELECT COUNT(*) FROM bling_credentials " "WHERE store_ref_id = :store_id"),
            {"store_id": default_store.id},
        ).scalar_one()
        == 1
    )


def test_migration_does_not_overwrite_existing_store_reference(app):
    _replace_with_legacy_integration_tables()
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE nuvemshop_stores ADD COLUMN store_ref_id INTEGER"))
        Store.__table__.create(bind=connection, checkfirst=True)
        other_store_id = connection.execute(
            Store.__table__.insert().values(name="Outra loja", slug="outra-loja", active=True)
        ).inserted_primary_key[0]
        connection.execute(
            text(
                "INSERT INTO nuvemshop_stores "
                "(id, store_id, access_token, store_ref_id) "
                "VALUES (1, 'external', 'token', :store_ref_id)"
            ),
            {"store_ref_id": other_store_id},
        )

    migrate()

    stored_ref = db.session.execute(
        text("SELECT store_ref_id FROM nuvemshop_stores WHERE id = 1")
    ).scalar_one()
    assert stored_ref == other_store_id


def test_migration_rejects_orphan_store_reference(app):
    _replace_with_legacy_integration_tables()
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE nuvemshop_stores ADD COLUMN store_ref_id INTEGER"))
        connection.execute(
            text(
                "INSERT INTO nuvemshop_stores "
                "(id, store_id, access_token, store_ref_id) "
                "VALUES (1, 'external', 'token', 999)"
            )
        )

    try:
        migrate()
    except RuntimeError as exc:
        assert "1 referencia(s) orfa(s)" in str(exc)
    else:
        raise AssertionError("Migration deveria rejeitar store_ref_id orfao")
