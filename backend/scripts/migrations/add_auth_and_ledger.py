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
    from app import create_app, db
    from sqlalchemy import inspect, text

    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        # ------------------------------------------------------------------
        # 1. Criar tabela users
        # ------------------------------------------------------------------
        if "users" not in existing_tables:
            print("[migration] Criando tabela users...")
            db.session.execute(text("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200) NOT NULL,
                    email VARCHAR(200) NOT NULL UNIQUE,
                    password_hash VARCHAR(256) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'vendedor',
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """))
            db.session.execute(text("CREATE INDEX ix_users_email ON users (email)"))
            db.session.commit()
            print("[migration] ✓ users criada")
        else:
            print("[migration] users já existe, pulando")

        # ------------------------------------------------------------------
        # 2. Criar tabela payroll_config
        # ------------------------------------------------------------------
        if "payroll_config" not in existing_tables:
            print("[migration] Criando tabela payroll_config...")
            db.session.execute(text("""
                CREATE TABLE payroll_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    category VARCHAR(50) NOT NULL,
                    label VARCHAR(100) NOT NULL,
                    amount REAL NOT NULL,
                    frequency VARCHAR(20) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL
                )
            """))
            db.session.execute(text("CREATE INDEX ix_payroll_user ON payroll_config (user_id)"))
            db.session.commit()
            print("[migration] ✓ payroll_config criada")
        else:
            print("[migration] payroll_config já existe, pulando")

        # ------------------------------------------------------------------
        # 3. Criar tabela commission_config
        # ------------------------------------------------------------------
        if "commission_config" not in existing_tables:
            print("[migration] Criando tabela commission_config...")
            db.session.execute(text("""
                CREATE TABLE commission_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    source VARCHAR(50) NOT NULL,
                    rate REAL NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL
                )
            """))
            db.session.execute(text("CREATE INDEX ix_commission_user ON commission_config (user_id)"))
            db.session.commit()
            print("[migration] ✓ commission_config criada")
        else:
            print("[migration] commission_config já existe, pulando")

        # ------------------------------------------------------------------
        # 4. Criar tabela ledger_entry
        # ------------------------------------------------------------------
        if "ledger_entry" not in existing_tables:
            print("[migration] Criando tabela ledger_entry...")
            db.session.execute(text("""
                CREATE TABLE ledger_entry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    type VARCHAR(10) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    pedido_id INTEGER UNIQUE REFERENCES pedidos(id),
                    week_ref DATE NOT NULL,
                    created_at DATETIME NOT NULL,
                    created_by INTEGER NOT NULL REFERENCES users(id)
                )
            """))
            db.session.execute(text("CREATE INDEX ix_ledger_user ON ledger_entry (user_id)"))
            db.session.execute(text("CREATE INDEX ix_ledger_user_week ON ledger_entry (user_id, week_ref)"))
            db.session.commit()
            print("[migration] ✓ ledger_entry criada")
        else:
            print("[migration] ledger_entry já existe, pulando")

        # ------------------------------------------------------------------
        # 5. Adicionar coluna vendedor_id em pedidos
        # ------------------------------------------------------------------
        pedidos_cols = [c["name"] for c in inspector.get_columns("pedidos")]
        if "vendedor_id" not in pedidos_cols:
            print("[migration] Adicionando pedidos.vendedor_id...")
            db.session.execute(text(
                "ALTER TABLE pedidos ADD COLUMN vendedor_id INTEGER REFERENCES users(id)"
            ))
            db.session.commit()
            print("[migration] ✓ pedidos.vendedor_id adicionada")
        else:
            print("[migration] pedidos.vendedor_id já existe, pulando")

        print("\n[migration] Concluído com sucesso!")


if __name__ == "__main__":
    run()
