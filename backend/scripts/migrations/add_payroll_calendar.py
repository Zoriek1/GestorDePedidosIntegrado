# -*- coding: utf-8 -*-
"""
Migration: Adiciona campos do calendário de pagamento e confirmação ao módulo Recebíveis

Altera:
  - payroll_config: adiciona coluna payment_day (Integer, nullable)
  - ledger_entry: adiciona colunas due_date (Date), status (String), confirmed_at (DateTime)
    - Rows existentes recebem status='confirmado' (retrocompatibilidade)

Funciona com SQLite (dev) e PostgreSQL (produção).

Uso:
  cd backend
  python scripts/migrations/add_payroll_calendar.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def run():
    from sqlalchemy import inspect, text

    from app import create_app, db

    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        dialect = db.engine.dialect.name  # 'sqlite' ou 'postgresql'

        # ------------------------------------------------------------------
        # 1. payroll_config: adicionar payment_day
        # ------------------------------------------------------------------
        payroll_cols = [c["name"] for c in inspector.get_columns("payroll_config")]
        if "payment_day" not in payroll_cols:
            print("[migration] Adicionando payroll_config.payment_day...")
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE payroll_config ADD COLUMN IF NOT EXISTS " "payment_day INTEGER"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE payroll_config ADD COLUMN " "payment_day INTEGER")
                )
            db.session.commit()
            print("[migration] ✓ payroll_config.payment_day adicionada")
        else:
            print("[migration] payroll_config.payment_day já existe, pulando")

        # Re-inspecionar colunas de ledger_entry após possíveis alterações anteriores
        inspector = inspect(db.engine)
        ledger_cols = [c["name"] for c in inspector.get_columns("ledger_entry")]

        # ------------------------------------------------------------------
        # 2. ledger_entry: adicionar due_date
        # ------------------------------------------------------------------
        if "due_date" not in ledger_cols:
            print("[migration] Adicionando ledger_entry.due_date...")
            if dialect == "postgresql":
                db.session.execute(
                    text("ALTER TABLE ledger_entry ADD COLUMN IF NOT EXISTS due_date DATE")
                )
            else:
                db.session.execute(text("ALTER TABLE ledger_entry ADD COLUMN due_date DATE"))
            db.session.commit()
            print("[migration] ✓ ledger_entry.due_date adicionada")
        else:
            print("[migration] ledger_entry.due_date já existe, pulando")

        # ------------------------------------------------------------------
        # 3. ledger_entry: adicionar status (default 'confirmado' para rows existentes)
        # ------------------------------------------------------------------
        inspector = inspect(db.engine)
        ledger_cols = [c["name"] for c in inspector.get_columns("ledger_entry")]

        if "status" not in ledger_cols:
            print("[migration] Adicionando ledger_entry.status...")
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE ledger_entry ADD COLUMN IF NOT EXISTS "
                        "status VARCHAR(20) NOT NULL DEFAULT 'confirmado'"
                    )
                )
            else:
                db.session.execute(
                    text(
                        "ALTER TABLE ledger_entry ADD COLUMN "
                        "status VARCHAR(20) NOT NULL DEFAULT 'confirmado'"
                    )
                )
            db.session.commit()
            print("[migration] ✓ ledger_entry.status adicionada (default='confirmado')")
        else:
            print("[migration] ledger_entry.status já existe, pulando")

        # ------------------------------------------------------------------
        # 4. ledger_entry: adicionar confirmed_at
        # ------------------------------------------------------------------
        inspector = inspect(db.engine)
        ledger_cols = [c["name"] for c in inspector.get_columns("ledger_entry")]

        if "confirmed_at" not in ledger_cols:
            print("[migration] Adicionando ledger_entry.confirmed_at...")
            if dialect == "postgresql":
                db.session.execute(
                    text("ALTER TABLE ledger_entry ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMP")
                )
            else:
                db.session.execute(
                    text("ALTER TABLE ledger_entry ADD COLUMN confirmed_at TIMESTAMP")
                )
            db.session.commit()
            print("[migration] ✓ ledger_entry.confirmed_at adicionada")
        else:
            print("[migration] ledger_entry.confirmed_at já existe, pulando")

        print("\n[migration] Concluído com sucesso!")


if __name__ == "__main__":
    run()
