# -*- coding: utf-8 -*-
"""
Migration: remove a constraint UNIQUE de coluna ledger_entry_pedido_id_key e
garante que o índice parcial uq_ledger_pedido_active esteja correto.

Por que
-------
O modelo LedgerEntry foi criado originalmente com pedido_id UNIQUE em
column-level. Quando a tabela foi criada em produção (PostgreSQL), isso virou
a constraint ledger_entry_pedido_id_key. Depois trocamos para um índice
parcial WHERE voided=FALSE — mas a constraint antiga não foi removida.

Resultado: ao estornar+recriar comissão de um pedido (ex.: troca de
tipo_pedido entrega→retirada), o INSERT da nova comissão falha com:

    duplicate key value violates unique constraint
    "ledger_entry_pedido_id_key"

mesmo com a antiga já marcada voided=True.

Esta migration:
  1. Aborta se houver mais de uma comissão ativa por pedido (não deveria,
     mas se houver é melhor o usuário corrigir antes).
  2. DROP CONSTRAINT ledger_entry_pedido_id_key (PostgreSQL apenas).
  3. DROP INDEX uq_ledger_pedido_active se existir e não tiver predicate WHERE.
  4. CREATE UNIQUE INDEX uq_ledger_pedido_active
     ON ledger_entry(pedido_id) WHERE voided=FALSE AND pedido_id IS NOT NULL.

Uso
---
    cd backend && python scripts/migrations/drop_ledger_pedido_id_unique.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db


def is_postgres() -> bool:
    return db.engine.dialect.name == "postgresql"


def find_active_duplicates() -> list:
    """Retorna [(pedido_id, qtd, ids)] de pedidos com mais de uma comissão ativa."""
    rows = db.session.execute(
        db.text(
            """
            SELECT pedido_id, COUNT(*) AS qtd
            FROM ledger_entry
            WHERE voided = :voided_false AND pedido_id IS NOT NULL
            GROUP BY pedido_id
            HAVING COUNT(*) > 1
            """
        ),
        {"voided_false": False},
    ).fetchall()

    detalhado = []
    for pid, qtd in rows:
        ids = [
            r[0]
            for r in db.session.execute(
                db.text(
                    """
                    SELECT id FROM ledger_entry
                    WHERE pedido_id = :pid AND voided = :voided_false
                    ORDER BY id
                    """
                ),
                {"pid": pid, "voided_false": False},
            ).fetchall()
        ]
        detalhado.append((pid, qtd, ids))
    return detalhado


def constraint_exists(name: str) -> bool:
    if not is_postgres():
        return False
    row = db.session.execute(
        db.text(
            """
            SELECT 1 FROM pg_constraint
            WHERE conname = :name
              AND conrelid = 'ledger_entry'::regclass
            """
        ),
        {"name": name},
    ).first()
    return row is not None


def index_exists(name: str) -> bool:
    from sqlalchemy import inspect as sa_inspect

    insp = sa_inspect(db.engine)
    return any(ix.get("name") == name for ix in insp.get_indexes("ledger_entry"))


def index_has_where_predicate(name: str) -> bool:
    """True se o índice (PostgreSQL) tem cláusula WHERE no DDL."""
    if not is_postgres():
        return True
    row = db.session.execute(
        db.text(
            """
            SELECT pg_get_indexdef(c.oid)
            FROM pg_class c
            WHERE c.relname = :name AND c.relkind = 'i'
            """
        ),
        {"name": name},
    ).first()
    if not row:
        return False
    ddl = (row[0] or "").lower()
    return " where " in ddl


def migrate():
    print(f"[MIGRATION] drop_ledger_pedido_id_unique (banco: {db.engine.dialect.name})")

    duplicates = find_active_duplicates()
    if duplicates:
        print(
            "[MIGRATION] ABORTADO: há mais de uma comissão ativa para o mesmo "
            "pedido_id. Voide as duplicatas antigas e rode novamente."
        )
        for pid, qtd, ids in duplicates:
            print(f"   - pedido_id={pid} qtd={qtd} ids={ids}")
        sys.exit(1)

    if is_postgres():
        if constraint_exists("ledger_entry_pedido_id_key"):
            print("[MIGRATION]   DROP CONSTRAINT ledger_entry_pedido_id_key...")
            db.session.execute(db.text(
                "ALTER TABLE ledger_entry "
                "DROP CONSTRAINT IF EXISTS ledger_entry_pedido_id_key"
            ))
            db.session.commit()
            print("[MIGRATION]   ok")
        else:
            print("[MIGRATION]   constraint ledger_entry_pedido_id_key já removida.")

        if index_exists("uq_ledger_pedido_active") and not index_has_where_predicate(
            "uq_ledger_pedido_active"
        ):
            print(
                "[MIGRATION]   índice uq_ledger_pedido_active sem predicate — DROP e recria..."
            )
            db.session.execute(db.text("DROP INDEX IF EXISTS uq_ledger_pedido_active"))
            db.session.commit()

        if not index_exists("uq_ledger_pedido_active"):
            print("[MIGRATION]   CREATE UNIQUE INDEX uq_ledger_pedido_active...")
            db.session.execute(db.text(
                "CREATE UNIQUE INDEX uq_ledger_pedido_active "
                "ON ledger_entry(pedido_id) "
                "WHERE voided = FALSE AND pedido_id IS NOT NULL"
            ))
            db.session.commit()
            print("[MIGRATION]   ok")
        else:
            print("[MIGRATION]   uq_ledger_pedido_active já existe com predicate.")
    else:
        # SQLite — não há constraint nomeada para remover; create_all já cria
        # o índice com sqlite_where. Reforço idempotente abaixo.
        if not index_exists("uq_ledger_pedido_active"):
            print("[MIGRATION]   CREATE UNIQUE INDEX uq_ledger_pedido_active (SQLite)...")
            db.session.execute(db.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_pedido_active "
                "ON ledger_entry(pedido_id) "
                "WHERE voided=0 AND pedido_id IS NOT NULL"
            ))
            db.session.commit()
            print("[MIGRATION]   ok")
        else:
            print("[MIGRATION]   uq_ledger_pedido_active já existe.")

    print("[MIGRATION] Concluído.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
