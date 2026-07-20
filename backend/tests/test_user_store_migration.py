"""Migration add_store_ref_to_users: banco novo (FK), banco legado (backfill idempotente)."""

import pytest
from sqlalchemy import inspect, text

from app import db
from scripts.migrations.add_store_ref_to_users import migrate


def _replace_with_legacy_users_table() -> None:
    """Recria `users` sem store_ref_id (schema legado single-tenant)."""
    db.session.remove()
    with db.engine.begin() as connection:
        connection.execute(text("DROP TABLE users"))
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(200) NOT NULL, "
                "email VARCHAR(200) NOT NULL UNIQUE, "
                "password_hash VARCHAR(256) NOT NULL, "
                "role VARCHAR(20) NOT NULL DEFAULT 'vendedor', "
                "is_active BOOLEAN NOT NULL DEFAULT 1, "
                "created_at DATETIME NOT NULL, "
                "updated_at DATETIME NOT NULL"
                ")"
            )
        )


def _seed_default_store(connection, slug: str = "default") -> int:
    connection.execute(
        text(
            "INSERT INTO stores (name, slug, active, created_at, updated_at) "
            "VALUES (:name, :slug, 1, '2020-01-01 00:00:00', '2020-01-01 00:00:00')"
        ),
        {"name": slug, "slug": slug},
    )
    return connection.execute(
        text("SELECT id FROM stores WHERE slug = :slug"), {"slug": slug}
    ).scalar_one()


def _insert_legacy_user(connection, uid: int, email: str, store_ref_id=None) -> None:
    if store_ref_id is None:
        connection.execute(
            text(
                "INSERT INTO users (id, name, email, password_hash, role, is_active, "
                "created_at, updated_at) VALUES (:id, :name, :email, 'x', 'vendedor', 1, "
                "'2020-01-01 00:00:00', '2020-01-01 00:00:00')"
            ),
            {"id": uid, "name": f"User {uid}", "email": email},
        )
    else:
        connection.execute(
            text(
                "INSERT INTO users (id, name, email, password_hash, role, is_active, "
                "store_ref_id, created_at, updated_at) VALUES (:id, :name, :email, 'x', "
                "'vendedor', 1, :store, '2020-01-01 00:00:00', '2020-01-01 00:00:00')"
            ),
            {"id": uid, "name": f"User {uid}", "email": email, "store": store_ref_id},
        )


def test_fresh_database_has_users_store_foreign_key(app):
    """O model define a FK nomeada -> create_all a materializa em banco novo."""
    foreign_keys = inspect(db.engine).get_foreign_keys("users")
    assert any(
        fk["constrained_columns"] == ["store_ref_id"]
        and fk["referred_table"] == "stores"
        and fk["referred_columns"] == ["id"]
        for fk in foreign_keys
    )


def test_legacy_upgrade_backfills_and_is_idempotent(app):
    _replace_with_legacy_users_table()
    with db.engine.begin() as connection:
        default_id = _seed_default_store(connection)
        _insert_legacy_user(connection, 1, "a@legacy.test")
        _insert_legacy_user(connection, 2, "b@legacy.test")

    migrate()
    migrate()  # segunda execução é segura

    inspector = inspect(db.engine)
    columns = {c["name"] for c in inspector.get_columns("users")}
    indexes = {i["name"] for i in inspector.get_indexes("users")}
    assert "store_ref_id" in columns
    assert "ix_users_store_ref_id" in indexes

    rows = db.session.execute(text("SELECT store_ref_id FROM users ORDER BY id")).scalars().all()
    assert rows == [default_id, default_id]


def test_migration_preserves_existing_store_reference(app):
    _replace_with_legacy_users_table()
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN store_ref_id INTEGER"))
        default_id = _seed_default_store(connection)
        other_id = _seed_default_store(connection, slug="outra-loja")
        _insert_legacy_user(connection, 1, "keep@legacy.test", store_ref_id=other_id)
        _insert_legacy_user(connection, 2, "fill@legacy.test", store_ref_id=None)

    migrate()

    kept = db.session.execute(text("SELECT store_ref_id FROM users WHERE id = 1")).scalar_one()
    filled = db.session.execute(text("SELECT store_ref_id FROM users WHERE id = 2")).scalar_one()
    assert kept == other_id  # associação não-nula preservada
    assert filled == default_id  # nulo recebeu a default


def test_migration_rejects_orphan_store_reference(app):
    _replace_with_legacy_users_table()
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN store_ref_id INTEGER"))
        _seed_default_store(connection)
        _insert_legacy_user(connection, 1, "orphan@legacy.test", store_ref_id=999)

    with pytest.raises(RuntimeError, match="orfa"):
        migrate()


def test_migration_requires_default_store(app):
    _replace_with_legacy_users_table()  # stores existe porém vazia (sem default)
    with db.engine.begin() as connection:
        _insert_legacy_user(connection, 1, "x@legacy.test")

    with pytest.raises(RuntimeError, match="[Dd]efault"):
        migrate()
