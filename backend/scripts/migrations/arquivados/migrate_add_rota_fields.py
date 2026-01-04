# -*- coding: utf-8 -*-
"""
Migração: Adiciona campos de rota e taxa ao modelo Pedido
e cria tabela de rotas otimizadas
"""
import os
import sys

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db  # noqa: E402


def migrate():
    """Adiciona novos campos ao banco de dados"""
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("Migração: Adicionando campos de rota e taxa")
        print("=" * 60)

        try:
            # Verificar se os campos já existem
            from sqlalchemy import inspect, text

            inspector = inspect(db.engine)
            columns = [col["name"] for col in inspector.get_columns("pedidos")]

            # Adicionar campos ao modelo Pedido se não existirem
            campos_novos = {
                "taxa_entrega": "FLOAT",
                "coords_lat": "FLOAT",
                "coords_lon": "FLOAT",
            }

            for campo, tipo in campos_novos.items():
                if campo not in columns:
                    print(f"Adicionando campo '{campo}'...")
                    with db.engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE pedidos ADD COLUMN {campo} {tipo}"))
                        conn.commit()
                    print(f"✓ Campo '{campo}' adicionado")
                else:
                    print(f"✓ Campo '{campo}' já existe")

            # Criar tabela de rotas otimizadas se não existir
            if "rotas_otimizadas" not in inspector.get_table_names():
                print("\nCriando tabela 'rotas_otimizadas'...")
                db.create_all()  # Isso criará a tabela baseada no modelo
                print("✓ Tabela 'rotas_otimizadas' criada")
            else:
                print("✓ Tabela 'rotas_otimizadas' já existe")

            print("\n" + "=" * 60)
            print("✓ Migração concluída com sucesso!")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Erro na migração: {e}")
            import traceback

            traceback.print_exc()
            return False

    return True


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
