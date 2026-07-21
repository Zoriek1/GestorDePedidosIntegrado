# -*- coding: utf-8 -*-
"""
Migration: Correções do sistema de comissão/salário (auditoria 2026-04).

Aplica:
  - ledger_entry: novas colunas commission_rate, commission_source, void_reason
  - commission_config: índices parciais únicos por (user_id, fonte_pedido_id) e
    (user_id, source) quando is_active=1, prevenindo configs duplicadas
  - payroll_config: backfill payment_day=4 (Sexta) onde NULL e frequency='semanal'
  - ledger_entry: backfill best-effort de commission_rate/source para CREDITs de
    comissão existentes a partir da commission_config ativa correspondente

Os CHECK constraints (payment_day BETWEEN 0 AND 6, rate >= 0) são definidos no
modelo SQLAlchemy. SQLite não aceita ADD CONSTRAINT em ALTER TABLE existente
sem recriar a tabela; em PostgreSQL adicionamos via ALTER TABLE quando possível.

Uso:
  cd backend
  python scripts/migrations/fix_commission_system.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def _column_exists(inspector, table: str, column: str) -> bool:
    return column in [c["name"] for c in inspector.get_columns(table)]


def _index_exists(inspector, table: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def run():
    from sqlalchemy import inspect, text

    from app import create_app, db

    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        dialect = db.engine.dialect.name

        # ------------------------------------------------------------------
        # 1. ledger_entry: novas colunas (commission_rate, commission_source,
        #    void_reason)
        # ------------------------------------------------------------------
        if not _column_exists(inspector, "ledger_entry", "commission_rate"):
            print("[migration] ledger_entry.commission_rate...")
            db.session.execute(
                text("ALTER TABLE ledger_entry ADD COLUMN commission_rate NUMERIC(5,4)")
            )
            db.session.commit()
            print("[migration] ok")
        inspector = inspect(db.engine)

        if not _column_exists(inspector, "ledger_entry", "commission_source"):
            print("[migration] ledger_entry.commission_source...")
            db.session.execute(
                text("ALTER TABLE ledger_entry ADD COLUMN commission_source VARCHAR(50)")
            )
            db.session.commit()
            print("[migration] ok")
        inspector = inspect(db.engine)

        if not _column_exists(inspector, "ledger_entry", "void_reason"):
            print("[migration] ledger_entry.void_reason...")
            db.session.execute(text("ALTER TABLE ledger_entry ADD COLUMN void_reason VARCHAR(50)"))
            db.session.commit()
            print("[migration] ok")

        # ------------------------------------------------------------------
        # 2. commission_config: índices parciais únicos
        # ------------------------------------------------------------------
        inspector = inspect(db.engine)
        if not _index_exists(inspector, "commission_config", "ux_comm_user_fonte_active"):
            print("[migration] index ux_comm_user_fonte_active...")
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ux_comm_user_fonte_active "
                        "ON commission_config (user_id, fonte_pedido_id) "
                        "WHERE is_active = TRUE AND fonte_pedido_id IS NOT NULL"
                    )
                )
            else:
                db.session.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ux_comm_user_fonte_active "
                        "ON commission_config (user_id, fonte_pedido_id) "
                        "WHERE is_active = 1 AND fonte_pedido_id IS NOT NULL"
                    )
                )
            db.session.commit()
            print("[migration] ok")

        if not _index_exists(inspector, "commission_config", "ux_comm_user_source_active"):
            print("[migration] index ux_comm_user_source_active...")
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ux_comm_user_source_active "
                        "ON commission_config (user_id, source) "
                        "WHERE is_active = TRUE AND fonte_pedido_id IS NULL AND source <> ''"
                    )
                )
            else:
                db.session.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ux_comm_user_source_active "
                        "ON commission_config (user_id, source) "
                        "WHERE is_active = 1 AND fonte_pedido_id IS NULL AND source <> ''"
                    )
                )
            db.session.commit()
            print("[migration] ok")

        # ------------------------------------------------------------------
        # 3. payroll_config: backfill payment_day NULL → 4 (Sexta) para
        #    frequency='semanal'
        # ------------------------------------------------------------------
        result = db.session.execute(
            text(
                "UPDATE payroll_config SET payment_day = 4 "
                "WHERE payment_day IS NULL AND frequency = 'semanal'"
            )
        )
        db.session.commit()
        affected = getattr(result, "rowcount", 0) or 0
        if affected:
            print(f"[migration] payroll_config: backfill payment_day=4 em {affected} linha(s)")

        # ------------------------------------------------------------------
        # 4. ledger_entry: backfill best-effort de commission_rate/source
        #    para CREDITs de comissão sem snapshot.
        # ------------------------------------------------------------------
        # Estratégia: associa cada CREDIT ao CommissionConfig ativo do mesmo
        # user_id e source (extraído de category 'comissao_*').
        backfill_sql = text(
            """
            UPDATE ledger_entry
            SET
                commission_rate = (
                    SELECT cc.rate FROM commission_config cc
                    WHERE cc.user_id = ledger_entry.user_id
                      AND cc.is_active = 1
                      AND cc.source = SUBSTR(ledger_entry.category, 10)
                    LIMIT 1
                ),
                commission_source = SUBSTR(ledger_entry.category, 10)
            WHERE ledger_entry.type = 'CREDIT'
              AND ledger_entry.category LIKE 'comissao_%'
              AND ledger_entry.commission_rate IS NULL
            """
        )
        # PostgreSQL usa SUBSTRING e bool TRUE
        if dialect == "postgresql":
            backfill_sql = text(
                """
                UPDATE ledger_entry le
                SET commission_rate = (
                        SELECT cc.rate FROM commission_config cc
                        WHERE cc.user_id = le.user_id
                          AND cc.is_active = TRUE
                          AND cc.source = SUBSTRING(le.category FROM 10)
                        LIMIT 1
                    ),
                    commission_source = SUBSTRING(le.category FROM 10)
                WHERE le.type = 'CREDIT'
                  AND le.category LIKE 'comissao_%'
                  AND le.commission_rate IS NULL
                """
            )
        result = db.session.execute(backfill_sql)
        db.session.commit()
        affected = getattr(result, "rowcount", 0) or 0
        print(f"[migration] ledger_entry: backfill snapshot em {affected} CREDIT(s)")

        print("\n[migration] Concluído.")


if __name__ == "__main__":
    run()
