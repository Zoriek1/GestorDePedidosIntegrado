# -*- coding: utf-8 -*-
"""
Migration: Ledger → Double-Entry

O que faz:
1. Detecta o banco (SQLite ou PostgreSQL) e aplica a estratégia correta.
2. SQLite: recria a tabela ledger_entry (única forma de alterar schema).
3. PostgreSQL: ADD COLUMN progressivo + UPDATE de status.
4. Ambos: migra status pendente→active / confirmado→settled,
          adiciona paid_at em pedidos,
          cria índice parcial UNIQUE em pedido_id WHERE voided=FALSE.
5. Idempotente: sai cedo se 'voided' já existir.

Uso (VPS com Docker Compose):
    docker compose exec web python scripts/migrations/migrate_ledger_to_double_entry.py

Uso (local):
    cd backend
    python scripts/migrations/migrate_ledger_to_double_entry.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db


def column_exists(table: str, col: str) -> bool:
    from sqlalchemy import inspect as sa_inspect
    insp = sa_inspect(db.engine)
    return col in [c["name"] for c in insp.get_columns(table)]


def table_exists(table: str) -> bool:
    from sqlalchemy import inspect as sa_inspect
    insp = sa_inspect(db.engine)
    return table in insp.get_table_names()


def is_sqlite() -> bool:
    return db.engine.dialect.name == "sqlite"


def _add_paid_at():
    if not column_exists("pedidos", "paid_at"):
        print("[MIGRATION] Adicionando paid_at à tabela pedidos...")
        db.session.execute(db.text("ALTER TABLE pedidos ADD COLUMN paid_at DATETIME"))
        db.session.commit()
        print("[MIGRATION]   paid_at adicionado.")
    else:
        print("[MIGRATION]   paid_at já existe em pedidos — pulando.")


def migrate_sqlite():
    """Estratégia SQLite: recria a tabela inteira (SQLite não suporta DROP/RENAME COLUMN)."""
    print("[MIGRATION] SQLite detectado — usando estratégia de recriação de tabela.")

    db.session.execute(db.text("PRAGMA foreign_keys=OFF"))
    db.session.commit()

    # Criar nova tabela com schema correto
    print("[MIGRATION] Criando ledger_entry_v2...")
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
            FOREIGN KEY (user_id)        REFERENCES users(id),
            FOREIGN KEY (created_by)     REFERENCES users(id),
            FOREIGN KEY (settled_by_id)  REFERENCES ledger_entry_v2(id),
            CHECK (type IN ('CREDIT', 'DEBIT')),
            CHECK (status IN ('active', 'settled')),
            CHECK (amount > 0)
        )
    """))
    db.session.commit()

    # Detectar se o schema antigo tem confirmed_at
    has_confirmed_at = column_exists("ledger_entry", "confirmed_at")
    settled_at_src = "confirmed_at" if has_confirmed_at else "NULL"

    print(f"[MIGRATION] Copiando dados (confirmed_at={'sim' if has_confirmed_at else 'não'})...")
    db.session.execute(db.text(f"""
        INSERT INTO ledger_entry_v2
            (id, user_id, type, category, amount, description, pedido_id,
             week_ref, due_date, status, settled_at, settled_by_id, voided,
             created_at, created_by)
        SELECT
            id, user_id, type, category, amount, description, pedido_id,
            week_ref, due_date,
            CASE status
                WHEN 'confirmado' THEN 'settled'
                WHEN 'pendente'   THEN 'active'
                ELSE status
            END,
            {settled_at_src},
            NULL,
            0,
            created_at, created_by
        FROM ledger_entry
    """))
    db.session.commit()

    _create_retroactive_debits()

    print("[MIGRATION] Substituindo ledger_entry por ledger_entry_v2...")
    db.session.execute(db.text("DROP TABLE ledger_entry"))
    db.session.execute(db.text("ALTER TABLE ledger_entry_v2 RENAME TO ledger_entry"))
    db.session.commit()

    _create_indexes_sqlite()

    db.session.execute(db.text("PRAGMA foreign_keys=ON"))
    db.session.commit()


def migrate_postgresql():
    """Estratégia PostgreSQL: ADD COLUMN progressivo + UPDATE."""
    print("[MIGRATION] PostgreSQL detectado — usando ADD COLUMN progressivo.")

    # Adicionar colunas novas se não existem
    new_cols = [
        ("voided", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("settled_at", "TIMESTAMP"),
        ("settled_by_id", "INTEGER"),
    ]
    for col, definition in new_cols:
        if not column_exists("ledger_entry", col):
            print(f"[MIGRATION]   ADD COLUMN {col}...")
            db.session.execute(db.text(
                f"ALTER TABLE ledger_entry ADD COLUMN {col} {definition}"
            ))
    db.session.commit()

    # Converter status antigo → novo
    print("[MIGRATION] Convertendo status pendente→active, confirmado→settled...")
    db.session.execute(db.text(
        "UPDATE ledger_entry SET status='active' WHERE status='pendente'"
    ))
    db.session.execute(db.text(
        "UPDATE ledger_entry SET status='settled' WHERE status='confirmado'"
    ))

    # Preencher settled_at a partir de confirmed_at se existir
    if column_exists("ledger_entry", "confirmed_at"):
        print("[MIGRATION]   Preenchendo settled_at a partir de confirmed_at...")
        db.session.execute(db.text(
            "UPDATE ledger_entry SET settled_at=confirmed_at WHERE confirmed_at IS NOT NULL"
        ))
    db.session.commit()

    _create_retroactive_debits()

    _create_indexes_postgresql()


def _create_retroactive_debits():
    """Cria DEBIT retroativo para CREDITs já settled (funciona em ambos os bancos)."""
    print("[MIGRATION] Criando DEBITs retroativos para CREDITs já quitados...")
    # Trabalha na tabela que ainda pode ser ledger_entry_v2 (SQLite) ou ledger_entry (PG)
    tbl = "ledger_entry_v2" if (is_sqlite() and table_exists("ledger_entry_v2")) else "ledger_entry"

    settled_rows = db.session.execute(db.text(f"""
        SELECT user_id, SUM(amount) as total, MIN(created_at) as ref_date,
               MIN(week_ref) as week_ref
        FROM {tbl}
        WHERE type='CREDIT' AND status='settled' AND settled_by_id IS NULL
        GROUP BY user_id
        HAVING SUM(amount) > 0
    """)).fetchall()

    for row in settled_rows:
        uid, total, ref_date, week_ref = row
        if is_sqlite():
            result = db.session.execute(db.text(f"""
                INSERT INTO {tbl}
                    (user_id, type, category, amount, description,
                     week_ref, status, settled_at, voided, created_at, created_by)
                VALUES
                    (:uid, 'DEBIT', 'pagamento', :amount,
                     'Quitação retroativa (migração double-entry)',
                     :week_ref, 'settled', :now, 0, :now, :uid)
            """), {"uid": uid, "amount": float(total), "week_ref": week_ref, "now": ref_date})
            debit_id = result.lastrowid
        else:
            result = db.session.execute(db.text(f"""
                INSERT INTO {tbl}
                    (user_id, type, category, amount, description,
                     week_ref, status, settled_at, voided, created_at, created_by)
                VALUES
                    (:uid, 'DEBIT', 'pagamento', :amount,
                     'Quitação retroativa (migração double-entry)',
                     :week_ref, 'settled', :now, FALSE, :now, :uid)
                RETURNING id
            """), {"uid": uid, "amount": float(total), "week_ref": week_ref, "now": ref_date})
            debit_id = result.scalar()

        db.session.execute(db.text(f"""
            UPDATE {tbl}
            SET settled_by_id = :debit_id
            WHERE user_id = :uid AND type='CREDIT' AND status='settled'
        """), {"debit_id": debit_id, "uid": uid})

    db.session.commit()
    print(f"[MIGRATION]   {len(settled_rows)} vendedor(es) com quitação retroativa.")


def _create_indexes_sqlite():
    print("[MIGRATION] Recriando índices SQLite...")
    for ddl in [
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_user_id ON ledger_entry(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_week_ref ON ledger_entry(week_ref)",
        "CREATE INDEX IF NOT EXISTS ix_ledger_user_week ON ledger_entry(user_id, week_ref)",
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_pedido_active
           ON ledger_entry(pedido_id)
           WHERE voided=0 AND pedido_id IS NOT NULL""",
    ]:
        db.session.execute(db.text(ddl))
    db.session.commit()


def _create_indexes_postgresql():
    print("[MIGRATION] Recriando índices PostgreSQL...")
    # Remover índice UNIQUE simples antigo (se existia)
    db.session.execute(db.text(
        "DROP INDEX IF EXISTS uq_ledger_entry_pedido_id"
    ))
    for ddl in [
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_user_id ON ledger_entry(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_week_ref ON ledger_entry(week_ref)",
        "CREATE INDEX IF NOT EXISTS ix_ledger_user_week ON ledger_entry(user_id, week_ref)",
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_pedido_active
           ON ledger_entry(pedido_id)
           WHERE voided=FALSE AND pedido_id IS NOT NULL""",
    ]:
        db.session.execute(db.text(ddl))
    db.session.commit()


def migrate():
    print("[MIGRATION] Iniciando migrate_ledger_to_double_entry...")
    print(f"[MIGRATION] Banco: {db.engine.dialect.name}")

    # ── 0. Banco novo: apenas criar tabelas ─────────────────────────────────
    if not table_exists("ledger_entry"):
        print("[MIGRATION] Tabela ledger_entry não existe — db.create_all()...")
        db.create_all()
        _add_paid_at()
        print("[MIGRATION] Banco novo criado. Nada a migrar.")
        return

    # ── 1. Já migrado: apenas garantir paid_at ──────────────────────────────
    if column_exists("ledger_entry", "voided"):
        print("[MIGRATION] Schema já na versão double-entry. Verificando paid_at...")
        _add_paid_at()
        print("[MIGRATION] Nada a fazer.")
        return

    # ── 2. Migração necessária ───────────────────────────────────────────────
    if is_sqlite():
        migrate_sqlite()
    else:
        migrate_postgresql()

    _add_paid_at()
    print("[MIGRATION] migrate_ledger_to_double_entry concluída com sucesso.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
