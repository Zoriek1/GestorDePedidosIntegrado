# -*- coding: utf-8 -*-
"""Enforce NOT NULL on store_ref_id across 19 tables + unique constraint on users."""

import re
import sys
from pathlib import Path

from sqlalchemy import inspect, text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402

TABLES = [
    "pedidos",
    "leads",
    "lead_touchpoints",
    "clientes",
    "fontes_pedido",
    "enderecos_clientes",
    "pedido_external_refs",
    "pedido_manual_overrides",
    "pedido_sugestoes_endereco",
    "push_subscriptions",
    "audit_log",
    "rotas_otimizadas",
    "meta_capi_outbox",
    "meta_capi_lead_outbox",
    "marketing_conversion_outbox",
    "bling_outbox",
    "users",
    "bling_credentials",
    "nuvemshop_stores",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _column_exists(inspector, table: str) -> bool:
    return "store_ref_id" in {col["name"] for col in inspector.get_columns(table)}


def _is_already_not_null(inspector, table: str) -> bool:
    for col in inspector.get_columns(table):
        if col["name"] == "store_ref_id":
            return not col.get("nullable", True)
    return False


def _count_nulls(connection, table: str) -> int:
    return connection.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE store_ref_id IS NULL")
    ).scalar_one()


# ---------------------------------------------------------------------------
# Postgres
# ---------------------------------------------------------------------------

def _pg_set_not_null(connection, table: str) -> None:
    connection.execute(
        text(f"ALTER TABLE {table} ALTER COLUMN store_ref_id SET NOT NULL")
    )


# ---------------------------------------------------------------------------
# SQLite rebuild (ALTER COLUMN not supported)
# ---------------------------------------------------------------------------

def _sqlite_create_sql(connection, table: str):
    row = connection.execute(
        text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table},
    ).fetchone()
    return row[0] if row else None


def _split_column_defs(sql: str) -> list:
    match = re.match(
        r"(?i)CREATE\s+TABLE\s+[\"']?\w+[\"']?\s*\((.*)\)\s*;?\s*$",
        sql,
        re.DOTALL,
    )
    if not match:
        return []
    body = match.group(1)
    parts, depth, buf = [], 0, []
    for ch in body:
        if ch == "(" :
            depth += 1; buf.append(ch)
        elif ch == ")":
            depth -= 1; buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip()); buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def _sqlite_rebuild_not_null(connection, table: str) -> bool:
    original = _sqlite_create_sql(connection, table)
    if not original:
        raise RuntimeError(f"Table {table} not found in sqlite_master")
    if re.search(r"(?i)store_ref_id\s+[^,\)]*\bNOT\s+NULL\b", original):
        return False

    indexes = []
    for idx in connection.execute(text(f"PRAGMA index_list({table})")).fetchall():
        idx_name = idx[1]
        if idx_name.startswith("sqlite_"):
            continue
        cols = [
            r[2]
            for r in connection.execute(text(f"PRAGMA index_info({idx_name})")).fetchall()
        ]
        indexes.append((idx_name, bool(idx[2]), cols))

    parts = _split_column_defs(original)
    modified = False
    for i, part in enumerate(parts):
        if re.match(r"""(?i)["']?store_ref_id["']?\s+\w+""", part):
            if "NOT NULL" not in part.upper():
                parts[i] = part.rstrip() + " NOT NULL"
                modified = True
            break
    if not modified:
        return False

    temp = f"{table}__nn_migrate"
    new_sql = f'CREATE TABLE "{temp}" (\n' + ",\n".join(parts) + "\n)"

    col_names = [
        c[1] for c in connection.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
    ]
    joined = ", ".join(col_names)

    connection.execute(text(f'DROP TABLE IF EXISTS "{temp}"'))
    connection.execute(text(new_sql))
    connection.execute(
        text(f'INSERT INTO "{temp}" ({joined}) SELECT {joined} FROM "{table}"')
    )
    connection.execute(text(f'DROP TABLE "{table}"'))
    connection.execute(text(f'ALTER TABLE "{temp}" RENAME TO "{table}"'))

    for idx_name, unique, cols in indexes:
        unique_kw = "UNIQUE " if unique else ""
        cols_str = ", ".join(cols)
        connection.execute(
            text(f"CREATE {unique_kw}INDEX IF NOT EXISTS {idx_name} ON {table} ({cols_str})")
        )
    return True


# ---------------------------------------------------------------------------
# Unique constraint
# ---------------------------------------------------------------------------

def _ensure_unique_constraint(connection, inspector, table, name, columns):
    if connection.dialect.name == "sqlite":
        for idx in connection.execute(text(f"PRAGMA index_list({table})")).fetchall():
            if idx[1] == name:
                print(f"[SKIP] {name} already exists")
                return
        connection.execute(
            text(f"CREATE UNIQUE INDEX {name} ON {table} ({columns})")
        )
    else:
        for uc in inspector.get_unique_constraints(table):
            if uc.get("name") == name:
                print(f"[SKIP] {name} already exists")
                return
        connection.execute(
            text(f"ALTER TABLE {table} ADD CONSTRAINT {name} UNIQUE ({columns})")
        )
    print(f"[MIGRATE] {name} constraint added")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _migrate_connection(connection) -> None:
    engine = connection.engine
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    is_sqlite = engine.dialect.name == "sqlite"

    for table in TABLES:
        if table not in existing:
            print(f"[SKIP] {table} does not exist")
            continue
        if not _column_exists(inspector, table):
            print(f"[SKIP] {table}.store_ref_id column missing")
            continue
        if _is_already_not_null(inspector, table):
            print(f"[SKIP] {table}.store_ref_id already NOT NULL")
            continue

        nulls = _count_nulls(connection, table)
        if nulls:
            raise RuntimeError(
                f"{table}: {nulls} row(s) with NULL store_ref_id — backfill first"
            )

        if is_sqlite:
            _sqlite_rebuild_not_null(connection, table)
        else:
            _pg_set_not_null(connection, table)
        print(f"[MIGRATE] {table}.store_ref_id → NOT NULL")

    # --- unique constraint ------------------------------------------------
    inspector = inspect(engine)
    if "users" in existing:
        _ensure_unique_constraint(
            connection, inspector, "users", "uq_users_store_email", "store_ref_id, email"
        )


def migrate() -> None:
    if db.engine.dialect.name == "sqlite":
        with db.engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
            conn.exec_driver_sql("PRAGMA legacy_alter_table=ON")
            conn.commit()
            with conn.begin():
                _migrate_connection(conn)
            conn.exec_driver_sql("PRAGMA legacy_alter_table=OFF")
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
            conn.commit()
    else:
        with db.engine.begin() as conn:
            _migrate_connection(conn)
    print("[SUCCESS] enforce store_ref_id NOT NULL complete")


def run() -> None:
    app = create_app()
    with app.app_context():
        migrate()


if __name__ == "__main__":
    run()