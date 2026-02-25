# -*- coding: utf-8 -*-
"""
Migration: Adicionar campos para integração Nuvemshop

Adiciona os seguintes campos:
- pedidos: plataforma, canal, frete_cobrado_cliente, desconto_frete, frete_liquido_cliente
- pedido_external_refs: agendamento_source, needs_review
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def column_exists(table_name: str, column_name: str) -> bool:
    """Verifica se uma coluna existe em uma tabela"""
    inspector = db.inspect(db.engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def add_nuvemshop_integration_fields():
    """Adiciona campos necessários para integração Nuvemshop melhorada"""
    with app.app_context():
        # Campos a adicionar na tabela pedidos
        pedidos_columns = [
            ("plataforma", "VARCHAR(50)"),
            ("canal", "VARCHAR(50)"),
            ("frete_cobrado_cliente", "FLOAT"),
            ("desconto_frete", "FLOAT"),
            ("frete_liquido_cliente", "FLOAT"),
        ]

        # Campos a adicionar na tabela pedido_external_refs
        external_refs_columns = [
            ("agendamento_source", "VARCHAR(50)"),
            ("needs_review", "BOOLEAN DEFAULT 0"),
        ]

        added_count = 0
        skipped_count = 0

        try:
            # Adicionar colunas na tabela pedidos
            for column_name, column_type in pedidos_columns:
                if column_exists("pedidos", column_name):
                    print(f"[SKIP] Coluna pedidos.{column_name} já existe")
                    skipped_count += 1
                else:
                    sql = f"ALTER TABLE pedidos ADD COLUMN {column_name} {column_type}"
                    db.session.execute(db.text(sql))
                    print(f"[ADD] Coluna pedidos.{column_name} adicionada")
                    added_count += 1

            # Adicionar colunas na tabela pedido_external_refs
            for column_name, column_type in external_refs_columns:
                if column_exists("pedido_external_refs", column_name):
                    print(f"[SKIP] Coluna pedido_external_refs.{column_name} já existe")
                    skipped_count += 1
                else:
                    sql = f"ALTER TABLE pedido_external_refs ADD COLUMN {column_name} {column_type}"
                    db.session.execute(db.text(sql))
                    print(f"[ADD] Coluna pedido_external_refs.{column_name} adicionada")
                    added_count += 1

            db.session.commit()

            print(
                f"\n[SUCCESS] Migration concluída: {added_count} colunas adicionadas, {skipped_count} já existiam"
            )

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Erro na migration: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    add_nuvemshop_integration_fields()
