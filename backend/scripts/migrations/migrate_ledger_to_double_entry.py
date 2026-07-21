# -*- coding: utf-8 -*-
"""
Migration: Ledger → Double-Entry  (online, sem downtime)

Estratégia PostgreSQL:
  - Encerra sessões idle-in-transaction antes de cada DDL (o app reconecta sozinho).
  - Cada ALTER TABLE roda com lock_timeout de 5 s; falha rápido em vez de travar.
  - ADD COLUMN IF NOT EXISTS — seguro rodar múltiplas vezes.
  - Em PostgreSQL 11+, ADD COLUMN com DEFAULT constante é operação de metadados
    (sem rewrite de tabela), então o lock é brevíssimo.

Estratégia SQLite: recria a tabela (única forma de alterar schema).

Uso (VPS Docker):
    docker compose exec backend python scripts/migrations/migrate_ledger_to_double_entry.py

Uso local:
    cd backend && python scripts/migrations/migrate_ledger_to_double_entry.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def column_exists(table: str, col: str) -> bool:
    from sqlalchemy import inspect as sa_inspect
    return col in [c["name"] for c in sa_inspect(db.engine).get_columns(table)]


def table_exists(table: str) -> bool:
    from sqlalchemy import inspect as sa_inspect
    return table in sa_inspect(db.engine).get_table_names()


def is_sqlite() -> bool:
    return db.engine.dialect.name == "sqlite"


def _kill_idle_connections():
    """Encerra sessões idle-in-transaction que bloqueiam DDLs. O app reconecta sozinho."""
    killed = db.session.execute(db.text("""
        SELECT COUNT(pg_terminate_backend(pid))
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND state IN ('idle in transaction', 'idle in transaction (aborted)')
          AND pid != pg_backend_pid()
    """)).scalar()
    if killed:
        print(f"[MIGRATION]   Encerradas {killed} sessão(ões) ociosas — app reconectará automaticamente.")


def _ddl(sql: str, params: dict | None = None):
    """Executa DDL com lock_timeout de 5 s em transação própria."""
    with db.engine.connect() as conn:
        conn.execute(db.text("SET lock_timeout = '5s'"))
        conn.execute(db.text(sql) if not params else db.text(sql).bindparams(**params))
        conn.commit()


def _add_column_pg(table: str, col: str, definition: str):
    if column_exists(table, col):
        print(f"[MIGRATION]   {col} já existe — pulando.")
        return
    print(f"[MIGRATION]   ADD COLUMN {col}...")
    _kill_idle_connections()
    _ddl(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {definition}")
    print(f"[MIGRATION]   {col} adicionado.")


def _add_paid_at():
    if is_sqlite():
        if not column_exists("pedidos", "paid_at"):
            print("[MIGRATION] Adicionando paid_at em pedidos...")
            db.session.execute(db.text("ALTER TABLE pedidos ADD COLUMN paid_at DATETIME"))
            db.session.commit()
            print("[MIGRATION]   paid_at adicionado.")
        else:
            print("[MIGRATION]   paid_at já existe — pulando.")
    else:
        _add_column_pg("pedidos", "paid_at", "TIMESTAMP")


# ---------------------------------------------------------------------------
# PostgreSQL — ADD COLUMN progressivo
# ---------------------------------------------------------------------------

def migrate_postgresql():
    print("[MIGRATION] PostgreSQL — ADD COLUMN progressivo (sem downtime).")

    # 1. Novas colunas
    _add_column_pg("ledger_entry", "voided",        "BOOLEAN NOT NULL DEFAULT FALSE")
    _add_column_pg("ledger_entry", "settled_at",    "TIMESTAMP")
    _add_column_pg("ledger_entry", "settled_by_id", "INTEGER")

    # 2. Converter status antigo → novo (UPDATE em lote, sem DDL)
    with db.engine.connect() as conn:
        r1 = conn.execute(db.text(
            "UPDATE ledger_entry SET status='active'   WHERE status='pendente'"
        ))
        r2 = conn.execute(db.text(
            "UPDATE ledger_entry SET status='settled'  WHERE status='confirmado'"
        ))
        conn.commit()
        if r1.rowcount or r2.rowcount:
            print(f"[MIGRATION]   {r1.rowcount} pendente→active, {r2.rowcount} confirmado→settled.")

    # 3. settled_at ← confirmed_at (se coluna antiga ainda existir)
    if column_exists("ledger_entry", "confirmed_at"):
        with db.engine.connect() as conn:
            conn.execute(db.text(
                "UPDATE ledger_entry SET settled_at=confirmed_at "
                "WHERE confirmed_at IS NOT NULL AND settled_at IS NULL"
            ))
            conn.commit()
            print("[MIGRATION]   settled_at preenchido a partir de confirmed_at.")

    # 4. DEBITs retroativos para CREDITs já settled
    _create_retroactive_debits_pg()

    # 5. Índices
    _create_indexes_pg()


def _create_retroactive_debits_pg():
    print("[MIGRATION] DEBITs retroativos (CREDITs settled sem settled_by_id)...")
    with db.engine.connect() as conn:
        rows = conn.execute(db.text("""
            SELECT user_id,
                   SUM(amount)    AS total,
                   MIN(created_at) AS ref_date,
                   MIN(week_ref)   AS week_ref
            FROM ledger_entry
            WHERE type='CREDIT' AND status='settled' AND settled_by_id IS NULL
            GROUP BY user_id
            HAVING SUM(amount) > 0
        """)).fetchall()

        for row in rows:
            uid, total, ref_date, week_ref = row
            debit_id = conn.execute(db.text("""
                INSERT INTO ledger_entry
                    (user_id, type, category, amount, description,
                     week_ref, status, settled_at, voided, created_at, created_by)
                VALUES
                    (:uid, 'DEBIT', 'pagamento', :amount,
                     'Quitação retroativa (migração double-entry)',
                     :week_ref, 'settled', :now, FALSE, :now, :uid)
                RETURNING id
            """), {"uid": uid, "amount": float(total), "week_ref": week_ref, "now": ref_date}).scalar()

            conn.execute(db.text("""
                UPDATE ledger_entry SET settled_by_id = :debit_id
                WHERE user_id = :uid AND type='CREDIT' AND status='settled'
                  AND settled_by_id IS NULL
            """), {"debit_id": debit_id, "uid": uid})

        conn.commit()
    print(f"[MIGRATION]   {len(rows)} vendedor(es) com quitação retroativa.")


def _create_indexes_pg():
    print("[MIGRATION] Criando índices PostgreSQL...")
    _kill_idle_connections()

    stmts = [
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_user_id ON ledger_entry(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_week_ref ON ledger_entry(week_ref)",
        "CREATE INDEX IF NOT EXISTS ix_ledger_user_week ON ledger_entry(user_id, week_ref)",
        # Remove índice UNIQUE simples antigo (se existia) antes de criar o parcial
        "DROP INDEX IF EXISTS uq_ledger_entry_pedido_id",
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_pedido_active
           ON ledger_entry(pedido_id)
           WHERE voided=FALSE AND pedido_id IS NOT NULL""",
    ]
    for ddl in stmts:
        try:
            _ddl(ddl)
        except Exception as e:
            print(f"[MIGRATION]   Aviso índice (pode já existir): {e}")
    print("[MIGRATION]   Índices OK.")


# ---------------------------------------------------------------------------
# SQLite — recriação completa da tabela
# ---------------------------------------------------------------------------

def migrate_sqlite():
    print("[MIGRATION] SQLite — recriação de tabela.")

    db.session.execute(db.text("PRAGMA foreign_keys=OFF"))
    db.session.commit()

    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS ledger_entry_v2 (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            type          VARCHAR(10) NOT NULL,
            category      VARCHAR(50) NOT NULL,
            amount        NUMERIC(12,2) NOT NULL,
            description   TEXT,
            pedido_id     INTEGER,
            week_ref      DATE NOT NULL,
            due_date      DATE,
            status        VARCHAR(20) NOT NULL DEFAULT 'active',
            settled_at    DATETIME,
            settled_by_id INTEGER,
            voided        BOOLEAN NOT NULL DEFAULT 0,
            created_at    DATETIME NOT NULL,
            created_by    INTEGER NOT NULL,
            FOREIGN KEY (user_id)       REFERENCES users(id),
            FOREIGN KEY (created_by)    REFERENCES users(id),
            FOREIGN KEY (settled_by_id) REFERENCES ledger_entry_v2(id),
            CHECK (type IN ('CREDIT', 'DEBIT')),
            CHECK (status IN ('active', 'settled')),
            CHECK (amount > 0)
        )
    """))
    db.session.commit()

    has_confirmed_at = column_exists("ledger_entry", "confirmed_at")
    settled_src = "confirmed_at" if has_confirmed_at else "NULL"

    db.session.execute(db.text(f"""
        INSERT INTO ledger_entry_v2
            (id, user_id, type, category, amount, description, pedido_id,
             week_ref, due_date, status, settled_at, settled_by_id, voided,
             created_at, created_by)
        SELECT id, user_id, type, category, amount, description, pedido_id,
               week_ref, due_date,
               CASE status
                   WHEN 'confirmado' THEN 'settled'
                   WHEN 'pendente'   THEN 'active'
                   ELSE status
               END,
               {settled_src}, NULL, 0, created_at, created_by
        FROM ledger_entry
    """))
    db.session.commit()

    # DEBITs retroativos
    rows = db.session.execute(db.text("""
        SELECT user_id, SUM(amount), MIN(created_at), MIN(week_ref)
        FROM ledger_entry_v2
        WHERE type='CREDIT' AND status='settled' AND settled_by_id IS NULL
        GROUP BY user_id HAVING SUM(amount) > 0
    """)).fetchall()

    for uid, total, ref_date, week_ref in rows:
        r = db.session.execute(db.text("""
            INSERT INTO ledger_entry_v2
                (user_id, type, category, amount, description,
                 week_ref, status, settled_at, voided, created_at, created_by)
            VALUES (:uid,'DEBIT','pagamento',:amount,
                   'Quitação retroativa',:week_ref,'settled',:now,0,:now,:uid)
        """), {"uid": uid, "amount": float(total), "week_ref": week_ref, "now": ref_date})
        db.session.execute(db.text("""
            UPDATE ledger_entry_v2 SET settled_by_id=:did
            WHERE user_id=:uid AND type='CREDIT' AND status='settled' AND settled_by_id IS NULL
        """), {"did": r.lastrowid, "uid": uid})
    db.session.commit()

    db.session.execute(db.text("DROP TABLE ledger_entry"))
    db.session.execute(db.text("ALTER TABLE ledger_entry_v2 RENAME TO ledger_entry"))
    db.session.commit()

    for ddl in [
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_user_id ON ledger_entry(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_week_ref ON ledger_entry(week_ref)",
        "CREATE INDEX IF NOT EXISTS ix_ledger_user_week ON ledger_entry(user_id, week_ref)",
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_pedido_active
           ON ledger_entry(pedido_id) WHERE voided=0 AND pedido_id IS NOT NULL""",
    ]:
        db.session.execute(db.text(ddl))
    db.session.commit()

    db.session.execute(db.text("PRAGMA foreign_keys=ON"))
    db.session.commit()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def migrate():
    print(f"[MIGRATION] Iniciando migrate_ledger_to_double_entry... (banco: {db.engine.dialect.name})")

    if not table_exists("ledger_entry"):
        print("[MIGRATION] Banco novo — db.create_all()...")
        db.create_all()
        _add_paid_at()
        print("[MIGRATION] Pronto.")
        return

    if column_exists("ledger_entry", "voided"):
        print("[MIGRATION] Schema já atualizado (voided existe). Verificando paid_at...")
        _add_paid_at()
        print("[MIGRATION] Nada a fazer.")
        return

    if is_sqlite():
        migrate_sqlite()
    else:
        migrate_postgresql()

    _add_paid_at()
    print("[MIGRATION] Concluída com sucesso.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
