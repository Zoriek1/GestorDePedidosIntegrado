# -*- coding: utf-8 -*-
"""
Migration: Criar tabela pedido_manual_overrides

Esta tabela rastreia campos de pedidos que foram editados manualmente,
permitindo que sincronizações de webhooks não sobrescrevam edições manuais.
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def create_pedido_manual_overrides_table():
    """Cria tabela para rastrear overrides manuais de campos de pedidos"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if "pedido_manual_overrides" in existing_tables:
            print("[SKIP] Tabela pedido_manual_overrides já existe")
            return

        statements = [
            """
            CREATE TABLE pedido_manual_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                field_name VARCHAR(50) NOT NULL,
                field_value TEXT,
                edited_by VARCHAR(100),
                edited_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                UNIQUE (pedido_id, field_name)
            );
            """
        ]

        index_statements = [
            "CREATE INDEX idx_pedido_manual_overrides_pedido_id ON pedido_manual_overrides(pedido_id);",
            "CREATE INDEX idx_pedido_manual_overrides_field_name ON pedido_manual_overrides(field_name);",
        ]

        try:
            for statement in statements:
                db.session.execute(db.text(statement))
            db.session.commit()

            for index_sql in index_statements:
                db.session.execute(db.text(index_sql))
            db.session.commit()

            print("[SUCCESS] Tabela pedido_manual_overrides criada com sucesso")
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Erro ao criar tabela: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    create_pedido_manual_overrides_table()
