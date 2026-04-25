# -*- coding: utf-8 -*-
"""
Migration: Criar tabelas Nuvemshop (stores, webhook deliveries, external refs)
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def create_nuvemshop_tables():
    """Cria tabelas para integração Nuvemshop"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        statements = []
        index_statements = []

        if "nuvemshop_stores" not in existing_tables:
            statements.append(
                """
                CREATE TABLE nuvemshop_stores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_id VARCHAR(50) NOT NULL UNIQUE,
                    access_token TEXT NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT 1,
                    default_vendedor_id INTEGER,
                    installed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    uninstalled_at DATETIME,
                    FOREIGN KEY (default_vendedor_id) REFERENCES users(id)
                );
                """
            )
            index_statements.append(
                "CREATE INDEX idx_nuvemshop_stores_store_id ON nuvemshop_stores(store_id);"
            )
            index_statements.append(
                "CREATE INDEX idx_nuvemshop_stores_default_vendedor_id ON nuvemshop_stores(default_vendedor_id);"
            )
        else:
            print("[SKIP] Tabela nuvemshop_stores já existe")

        if "nuvemshop_webhook_deliveries" not in existing_tables:
            statements.append(
                """
                CREATE TABLE nuvemshop_webhook_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_id VARCHAR(50) NOT NULL,
                    event VARCHAR(100) NOT NULL,
                    resource_id VARCHAR(80),
                    raw_body TEXT NOT NULL,
                    headers_json TEXT,
                    order_json TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    last_error TEXT,
                    received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME
                );
                """
            )
            index_statements.extend(
                [
                    "CREATE INDEX idx_nuvemshop_deliveries_store_id ON nuvemshop_webhook_deliveries(store_id);",
                    "CREATE INDEX idx_nuvemshop_deliveries_event ON nuvemshop_webhook_deliveries(event);",
                    "CREATE INDEX idx_nuvemshop_deliveries_resource_id ON nuvemshop_webhook_deliveries(resource_id);",
                    "CREATE INDEX idx_nuvemshop_deliveries_status ON nuvemshop_webhook_deliveries(status);",
                ]
            )
        else:
            print("[SKIP] Tabela nuvemshop_webhook_deliveries já existe")

        if "pedido_external_refs" not in existing_tables:
            statements.append(
                """
                CREATE TABLE pedido_external_refs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider VARCHAR(50) NOT NULL,
                    store_id VARCHAR(50) NOT NULL,
                    external_order_id VARCHAR(80) NOT NULL,
                    external_order_number VARCHAR(50),
                    order_token VARCHAR(100),
                    pedido_id INTEGER NOT NULL,
                    schedule_pending BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                    UNIQUE (provider, store_id, external_order_id)
                );
                """
            )
            index_statements.extend(
                [
                    "CREATE INDEX idx_pedido_external_provider ON pedido_external_refs(provider);",
                    "CREATE INDEX idx_pedido_external_store_id ON pedido_external_refs(store_id);",
                    "CREATE INDEX idx_pedido_external_order_id ON pedido_external_refs(external_order_id);",
                    "CREATE INDEX idx_pedido_external_pedido_id ON pedido_external_refs(pedido_id);",
                    "CREATE INDEX idx_pedido_external_pending ON pedido_external_refs(schedule_pending);",
                ]
            )
        else:
            print("[SKIP] Tabela pedido_external_refs já existe")

        if not statements:
            print("[OK] Nenhuma tabela nova para criar")
            return

        try:
            for statement in statements:
                db.session.execute(db.text(statement))
            db.session.commit()

            for index_sql in index_statements:
                db.session.execute(db.text(index_sql))
            db.session.commit()

            print("[SUCCESS] Tabelas Nuvemshop criadas com sucesso")
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Erro ao criar tabelas: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    create_nuvemshop_tables()
