# -*- coding: utf-8 -*-
"""
Migration: Ledger → Double-Entry

O que faz:
1. Recria a tabela ledger_entry com o novo schema (double-entry):
   - amount: NUMERIC(12,2) em vez de REAL
   - status: 'active' | 'settled' em vez de 'pendente' | 'confirmado'
   - settled_at (era confirmed_at)
   - settled_by_id FK → ledger_entry.id
   - voided BOOLEAN DEFAULT 0
   - CHECK constraints em type, status, amount
2. Migra dados existentes:
   - 'pendente'  → 'active'
   - 'confirmado' → 'settled'
   - confirmed_at → settled_at
3. Para cada vendedor com CREDITs 'settled' (antigo confirmado), cria um DEBIT
   de pagamento agrupado (retroativo) e vincula os CREDITs a ele via settled_by_id.
4. Adiciona coluna paid_at na tabela pedidos (se não existir).
5. Cria índice parcial UNIQUE em pedido_id WHERE voided=0 AND pedido_id IS NOT NULL.

Pode ser executado múltiplas vezes com segurança (idempotente via IF NOT EXISTS).

Uso:
    cd backend
    python scripts/migrations/migrate_ledger_to_double_entry.py
"""
import sys
from pathlib import Path

# Adicionar backend ao path
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


def migrate():
    print("[MIGRATION] Iniciando migrate_ledger_to_double_entry...")

    # ── 1. Garantir que tabela existe (pode ser banco novo) ─────────────────
    if not table_exists("ledger_entry"):
        print("[MIGRATION] Tabela ledger_entry não existe — criando via db.create_all()")
        db.create_all()
        print("[MIGRATION] Banco novo detectado — nada a migrar.")
        return

    # ── 2. Desligar FK para manipulação segura ───────────────────────────────
    db.session.execute(db.text("PRAGMA foreign_keys=OFF"))
    db.session.commit()

    # ── 3. Criar nova tabela com schema correto ──────────────────────────────
    print("[MIGRATION] Criando ledger_entry_v2...")
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS ledger_entry_v2 (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            type        VARCHAR(10) NOT NULL,
            category    VARCHAR(50) NOT NULL,
            amount      NUMERIC(12,2) NOT NULL,
            description TEXT,
            pedido_id   INTEGER,
            week_ref    DATE NOT NULL,
            due_date    DATE,
            status      VARCHAR(20) NOT NULL DEFAULT 'active',
            settled_at  DATETIME,
            settled_by_id INTEGER,
            voided      BOOLEAN NOT NULL DEFAULT 0,
            created_at  DATETIME NOT NULL,
            created_by  INTEGER NOT NULL,
            FOREIGN KEY (user_id)        REFERENCES users(id),
            FOREIGN KEY (created_by)     REFERENCES users(id),
            FOREIGN KEY (settled_by_id)  REFERENCES ledger_entry_v2(id),
            CHECK (type IN ('CREDIT', 'DEBIT')),
            CHECK (status IN ('active', 'settled')),
            CHECK (amount > 0)
        )
    """))
    db.session.commit()

    # ── 4. Copiar dados com conversão de status ──────────────────────────────
    print("[MIGRATION] Copiando dados com conversão pendente→active, confirmado→settled...")
    db.session.execute(db.text("""
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
            confirmed_at,   -- settled_at ← confirmed_at
            NULL,           -- settled_by_id (será preenchido abaixo)
            0,              -- voided = FALSE
            created_at, created_by
        FROM ledger_entry
    """))
    db.session.commit()

    # ── 5. Criar DEBIT retroativo por vendedor (CREDITs já settled) ──────────
    print("[MIGRATION] Criando DEBITs retroativos para CREDITs já quitados...")
    from datetime import date

    settled_rows = db.session.execute(db.text("""
        SELECT user_id, SUM(amount) as total, MIN(created_at) as ref_date,
               MIN(week_ref) as week_ref
        FROM ledger_entry_v2
        WHERE type='CREDIT' AND status='settled'
        GROUP BY user_id
        HAVING SUM(amount) > 0
    """)).fetchall()

    for row in settled_rows:
        uid, total, ref_date, week_ref = row
        # Criar DEBIT de quitação retroativo
        result = db.session.execute(db.text("""
            INSERT INTO ledger_entry_v2
                (user_id, type, category, amount, description,
                 week_ref, status, settled_at, voided, created_at, created_by)
            VALUES
                (:user_id, 'DEBIT', 'pagamento', :amount,
                 'Quitação retroativa (migração double-entry)',
                 :week_ref, 'settled', :now, 0, :now, :user_id)
        """), {
            "user_id": uid,
            "amount": float(total),
            "week_ref": week_ref,
            "now": ref_date,
        })
        debit_id = result.lastrowid

        # Vincular CREDITs settled a este DEBIT
        db.session.execute(db.text("""
            UPDATE ledger_entry_v2
            SET settled_by_id = :debit_id
            WHERE user_id = :user_id AND type='CREDIT' AND status='settled'
        """), {"debit_id": debit_id, "user_id": uid})

    db.session.commit()
    print(f"[MIGRATION]   {len(settled_rows)} vendedor(es) com quitação retroativa criada.")

    # ── 6. Substituir tabela ─────────────────────────────────────────────────
    print("[MIGRATION] Substituindo ledger_entry por ledger_entry_v2...")
    db.session.execute(db.text("DROP TABLE ledger_entry"))
    db.session.execute(db.text("ALTER TABLE ledger_entry_v2 RENAME TO ledger_entry"))
    db.session.commit()

    # ── 7. Recriar índices ───────────────────────────────────────────────────
    print("[MIGRATION] Recriando índices...")
    db.session.execute(db.text(
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_user_id ON ledger_entry(user_id)"
    ))
    db.session.execute(db.text(
        "CREATE INDEX IF NOT EXISTS ix_ledger_entry_week_ref ON ledger_entry(week_ref)"
    ))
    db.session.execute(db.text(
        "CREATE INDEX IF NOT EXISTS ix_ledger_user_week ON ledger_entry(user_id, week_ref)"
    ))
    # Índice parcial UNIQUE: um pedido = uma comissão ativa (voided=0)
    db.session.execute(db.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_pedido_active
        ON ledger_entry(pedido_id)
        WHERE voided=0 AND pedido_id IS NOT NULL
    """))
    db.session.commit()

    # ── 8. paid_at em pedidos ────────────────────────────────────────────────
    if not column_exists("pedidos", "paid_at"):
        print("[MIGRATION] Adicionando paid_at à tabela pedidos...")
        db.session.execute(db.text(
            "ALTER TABLE pedidos ADD COLUMN paid_at DATETIME"
        ))
        db.session.commit()
        print("[MIGRATION]   paid_at adicionado.")
    else:
        print("[MIGRATION]   paid_at já existe em pedidos — pulando.")

    # ── 9. Reativar FK ───────────────────────────────────────────────────────
    db.session.execute(db.text("PRAGMA foreign_keys=ON"))
    db.session.commit()

    print("[MIGRATION] migrate_ledger_to_double_entry concluída com sucesso.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
