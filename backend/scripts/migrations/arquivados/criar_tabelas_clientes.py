# -*- coding: utf-8 -*-
"""
Script para criar tabelas de clientes e adicionar coluna cliente_id
Execute este script ANTES de rodar a migração

Uso:
    python criar_tabelas_clientes.py
"""
from sqlalchemy import text

from app import create_app, db


def criar_tabelas():
    """Cria tabelas e adiciona coluna cliente_id"""
    app = create_app()

    with app.app_context():
        try:
            print("\n" + "="*60)
            print("CRIANDO TABELAS E COLUNAS - Sistema de Clientes")
            print("="*60)

            # 1) Adicionar coluna cliente_id em pedidos (se não existir)
            print("\n[1/5] Adicionando coluna cliente_id em pedidos...")
            try:
                db.session.execute(text("""
                    ALTER TABLE pedidos ADD COLUMN cliente_id INTEGER
                """))
                db.session.commit()
                print("  ✓ Coluna cliente_id adicionada!")
            except Exception as e:
                error_msg = str(e).lower()
                if "duplicate column name" in error_msg or "already exists" in error_msg:
                    print("  ℹ Coluna cliente_id já existe (OK)")
                else:
                    # SQLite pode retornar erro diferente, tentar verificar se coluna existe
                    try:
                        # Verificar se coluna já existe
                        result = db.session.execute(text("PRAGMA table_info(pedidos)"))
                        colunas = [row[1] for row in result]
                        if 'cliente_id' in colunas:
                            print("  ℹ Coluna cliente_id já existe (OK)")
                        else:
                            raise
                    except Exception as e:
                        print(f"  ⚠ Erro ao adicionar coluna: {e}")
                        print("  Tentando continuar...")

            # 2) Criar tabela clientes
            print("\n[2/5] Criando tabela clientes...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome VARCHAR(100) NOT NULL,
                    telefone VARCHAR(20) NOT NULL UNIQUE,
                    email VARCHAR(100),
                    observacoes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            """))
            db.session.commit()
            print("  ✓ Tabela clientes criada!")

            # 3) Criar tabela enderecos_clientes
            print("\n[3/5] Criando tabela enderecos_clientes...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS enderecos_clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER NOT NULL,
                    apelido VARCHAR(50),
                    cep VARCHAR(10),
                    rua VARCHAR(200),
                    numero VARCHAR(20),
                    complemento VARCHAR(100),
                    bairro VARCHAR(100),
                    cidade VARCHAR(100),
                    estado VARCHAR(2),
                    principal BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
                )
            """))
            db.session.commit()
            print("  ✓ Tabela enderecos_clientes criada!")

            # 4) Criar índices
            print("\n[4/5] Criando índices...")
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos(cliente_id)",
                "CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome)",
                "CREATE INDEX IF NOT EXISTS idx_clientes_telefone ON clientes(telefone)",
                "CREATE INDEX IF NOT EXISTS idx_enderecos_cliente ON enderecos_clientes(cliente_id)"
            ]

            for idx_sql in indices:
                try:
                    db.session.execute(text(idx_sql))
                except Exception as e:
                    print(f"  ⚠ Aviso ao criar índice: {e}")

            db.session.commit()
            print("  ✓ Índices criados!")

            # 5) Verificar
            print("\n[5/5] Verificando estrutura...")
            from sqlalchemy import inspect
            inspector = inspect(db.engine)

            tabelas = inspector.get_table_names()
            print(f"\n  Tabelas encontradas: {len(tabelas)}")
            tabelas_clientes = [t for t in tabelas if 'cliente' in t.lower()]
            if tabelas_clientes:
                for tabela in tabelas_clientes:
                    print(f"    ✓ {tabela}")
            else:
                print("    ⚠ Nenhuma tabela de cliente encontrada")

            # Verificar coluna cliente_id em pedidos
            try:
                colunas_pedidos = [col['name'] for col in inspector.get_columns('pedidos')]
                if 'cliente_id' in colunas_pedidos:
                    print("    ✓ Coluna cliente_id em pedidos: OK")
                else:
                    print("    ⚠ Coluna cliente_id não encontrada em pedidos")
            except Exception as e:
                print(f"    ⚠ Erro ao verificar colunas: {e}")

            print("\n" + "="*60)
            print("✅ SUCESSO! Tabelas e colunas criadas com sucesso!")
            print("="*60)
            print("\nPróximos passos:")
            print("  1. Teste a migração:")
            print("     python scripts/migrar_clientes.py --dry-run")
            print("\n  2. Aplique a migração:")
            print("     python scripts/migrar_clientes.py")
            print("\n  3. Reinicie o servidor Flask")
            print()

        except Exception as e:
            db.session.rollback()
            print("\n" + "="*60)
            print("❌ ERRO ao criar tabelas!")
            print("="*60)
            print(f"\nErro: {e}")
            print("\nDetalhes:")
            import traceback
            traceback.print_exc()
            print("\n" + "="*60)
            print("\nSugestões:")
            print("  1. Verifique se o banco de dados está acessível")
            print("  2. Faça backup: python scripts/backup.py")
            print("  3. Verifique permissões do arquivo database.db")
            print()
            raise

if __name__ == '__main__':
    criar_tabelas()

