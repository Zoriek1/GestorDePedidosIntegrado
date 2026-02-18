# -*- coding: utf-8 -*-
"""
Migration: Criar tabela meta_capi_outbox
Cria tabela para outbox de eventos Meta Conversions API
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def create_meta_capi_outbox_table():
    """Cria tabela meta_capi_outbox"""
    with app.app_context():
        # Verificar se tabela já existe
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if "meta_capi_outbox" in existing_tables:
            print("[SKIP] Tabela meta_capi_outbox já existe")
            return

        print("[CREATE] Criando tabela meta_capi_outbox...")

        # SQL para criar tabela
        sql = """
        CREATE TABLE meta_capi_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            event_id VARCHAR(100) UNIQUE NOT NULL,
            event_time DATETIME NOT NULL,
            payload_json TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            error_type VARCHAR(20),
            sent_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            FOREIGN KEY (order_id) REFERENCES pedidos(id)
        );
        """

        # Criar índices
        indexes_sql = [
            "CREATE INDEX idx_meta_capi_outbox_status ON meta_capi_outbox(status);",
            "CREATE INDEX idx_meta_capi_outbox_order_id ON meta_capi_outbox(order_id);",
            "CREATE INDEX idx_meta_capi_outbox_event_id ON meta_capi_outbox(event_id);",
            "CREATE INDEX idx_meta_capi_outbox_error_type ON meta_capi_outbox(error_type);",
        ]

        try:
            # Executar SQL
            db.session.execute(db.text(sql))
            db.session.commit()

            # Criar índices
            for index_sql in indexes_sql:
                db.session.execute(db.text(index_sql))
            db.session.commit()

            print("[SUCCESS] Tabela meta_capi_outbox criada com sucesso")
            print("[SUCCESS] Índices criados com sucesso")

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Erro ao criar tabela: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    create_meta_capi_outbox_table()
