# -*- coding: utf-8 -*-
"""Migration idempotente da integracao Bling."""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402

app = create_app()


def column_exists(table_name: str, column_name: str) -> bool:
    inspector = db.inspect(db.engine)
    if table_name not in inspector.get_table_names():
        return False
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def ensure_outbox_unique() -> None:
    """Garante a unique (pedido_id, operation) em bling_outbox para bases que
    foram criadas antes da constraint. Tabela nova ja nasce com ela via
    create_all(); aqui tratamos o caso de tabela pre-existente."""
    table = "bling_outbox"
    constraint = "uq_bling_outbox_pedido_operation"
    inspector = db.inspect(db.engine)
    if table not in inspector.get_table_names():
        return  # create_all() acabou de criar com a constraint
    existing = {uc.get("name") for uc in inspector.get_unique_constraints(table)}
    if constraint in existing:
        print(f"[SKIP] {constraint} ja existe")
        return

    dups = db.session.execute(
        db.text(
            "SELECT pedido_id, operation, COUNT(*) c FROM bling_outbox "
            "GROUP BY pedido_id, operation HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if dups:
        # Nao apagamos historico automaticamente (logs referenciam outbox_id).
        print(
            f"[WARN] {len(dups)} grupo(s) duplicado(s) em bling_outbox; resolva "
            "manualmente antes de aplicar a unique. "
            f"Exemplos: {[tuple(d) for d in dups[:5]]}"
        )
        return

    if db.engine.dialect.name == "sqlite":
        print(
            "[SKIP] SQLite nao suporta ADD CONSTRAINT; tabela nova ja nasce com a "
            "unique via create_all()"
        )
        return

    db.session.execute(
        db.text(f"ALTER TABLE {table} ADD CONSTRAINT {constraint} " "UNIQUE (pedido_id, operation)")
    )
    db.session.commit()
    print(f"[ADD] {constraint}")


def create_bling_integration():
    with app.app_context():
        try:
            db.create_all()
            db.session.commit()
            pedido_columns = [
                ("regra_pagamento", "VARCHAR(30)"),
                ("percentual_entrada", "FLOAT"),
                ("valor_entrada", "NUMERIC(12, 2)"),
                ("valor_restante", "NUMERIC(12, 2)"),
                ("forma_pagamento_entrada", "VARCHAR(50)"),
                ("forma_pagamento_restante", "VARCHAR(50)"),
                # TIMESTAMP e portavel entre Postgres (producao) e SQLite (dev);
                # Postgres nao reconhece o tipo DATETIME do MySQL/SQLite.
                ("entrada_recebida_at", "TIMESTAMP"),
                ("saldo_recebido_at", "TIMESTAMP"),
            ]
            added = 0
            skipped = 0
            for column, definition in pedido_columns:
                if column_exists("pedidos", column):
                    skipped += 1
                    print(f"[SKIP] pedidos.{column}")
                    continue
                db.session.execute(db.text(f"ALTER TABLE pedidos ADD COLUMN {column} {definition}"))
                db.session.commit()
                added += 1
                print(f"[ADD] pedidos.{column}")
            ensure_outbox_unique()
            print(f"[SUCCESS] Bling migration concluida: {added} colunas, {skipped} skips")
        except Exception as exc:
            db.session.rollback()
            print(f"[ERROR] Migration Bling falhou: {exc}")
            raise


if __name__ == "__main__":
    create_bling_integration()
