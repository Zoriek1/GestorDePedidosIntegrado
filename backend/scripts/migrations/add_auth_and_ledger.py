# -*- coding: utf-8 -*-
"""
Migration: Adiciona tabelas do módulo Recebíveis (Auth + Comissões + Ledger)

Cria:
  - users
  - payroll_config
  - commission_config
  - ledger_entry

Altera:
  - pedidos: adiciona coluna vendedor_id

Funciona com SQLite (dev) e PostgreSQL (produção).

Uso:
  cd backend
  python scripts/migrations/add_auth_and_ledger.py
"""
import sys
from pathlib import Path

# Garantir que o backend está no sys.path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def run():
    from sqlalchemy import inspect, text

    from app import create_app, db

    app = create_app()

    with app.app_context():
        # Importar models para que o SQLAlchemy conheça as tabelas
        from app.models.ledger_entry import LedgerEntry
        from app.models.user import CommissionConfig, PayrollConfig, User

        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        dialect = db.engine.dialect.name  # 'sqlite' ou 'postgresql'

        # ------------------------------------------------------------------
        # 1–4. Criar novas tabelas via SQLAlchemy ORM (database-agnostic)
        #      checkfirst=True → não recria se já existe
        # ------------------------------------------------------------------
        for model, label in [
            (User, "users"),
            (PayrollConfig, "payroll_config"),
            (CommissionConfig, "commission_config"),
            (LedgerEntry, "ledger_entry"),
        ]:
            if label not in existing_tables:
                print(f"[migration] Criando tabela {label}...")
                model.__table__.create(bind=db.engine, checkfirst=True)
                print(f"[migration] ✓ {label} criada")
            else:
                print(f"[migration] {label} já existe, pulando")

        # ------------------------------------------------------------------
        # 5. Adicionar coluna vendedor_id em pedidos
        # ------------------------------------------------------------------
        pedidos_cols = [c["name"] for c in inspector.get_columns("pedidos")]
        if "vendedor_id" not in pedidos_cols:
            print("[migration] Adicionando pedidos.vendedor_id...")
            if dialect == "postgresql":
                # PostgreSQL: suporta ADD COLUMN IF NOT EXISTS
                db.session.execute(
                    text(
                        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS "
                        "vendedor_id INTEGER REFERENCES users(id)"
                    )
                )
            else:
                # SQLite: sem IF NOT EXISTS no ALTER TABLE
                db.session.execute(
                    text(
                        "ALTER TABLE pedidos ADD COLUMN " "vendedor_id INTEGER REFERENCES users(id)"
                    )
                )
            db.session.commit()
            print("[migration] ✓ pedidos.vendedor_id adicionada")
        else:
            print("[migration] pedidos.vendedor_id já existe, pulando")

        print("\n[migration] Concluído com sucesso!")


if __name__ == "__main__":
    run()
