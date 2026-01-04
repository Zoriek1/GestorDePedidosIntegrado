# -*- coding: utf-8 -*-
"""
Migração: Adicionar Tabela app_meta e schema_version (P1.1)

Adiciona:
- Tabela app_meta para metadados do aplicativo
- Registro de schema_version

Uso:
    python scripts/migrations/add_app_meta_schema_version.py
"""
import sqlite3
import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import Config  # noqa: E402


def check_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Verifica se tabela existe"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def check_key_exists(conn: sqlite3.Connection, key: str) -> bool:
    """Verifica se chave existe em app_meta"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM app_meta WHERE key=?", (key,))
    return cursor.fetchone()[0] > 0


def migrate():
    """Executa a migração"""
    db_path = Config.DATABASE_PATH

    if not db_path.exists():
        print(f"[ERRO] Banco de dados não encontrado: {db_path}")
        return False

    print("=" * 60)
    print("MIGRAÇÃO: app_meta e schema_version (P1.1)")
    print("=" * 60)
    print(f"\nBanco de dados: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. Criar tabela app_meta se não existir
        print("\n[1/2] Verificando tabela app_meta...")
        if check_table_exists(conn, 'app_meta'):
            print("  ✓ Tabela app_meta já existe")
        else:
            print("  → Criando tabela app_meta...")
            cursor.execute("""
                CREATE TABLE app_meta (
                    key VARCHAR(50) PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
            print("  ✓ Tabela app_meta criada")

        # 2. Inserir schema_version se não existir
        print("\n[2/2] Verificando schema_version...")
        schema_version = Config.APP_SCHEMA_VERSION
        if check_key_exists(conn, 'schema_version'):
            print("  ✓ schema_version já existe")
            # Atualizar valor se diferente
            cursor.execute("SELECT value FROM app_meta WHERE key='schema_version'")
            current_version = cursor.fetchone()[0]
            if current_version != schema_version:
                print(f"  → Atualizando schema_version de '{current_version}' para '{schema_version}'...")
                cursor.execute(
                    "UPDATE app_meta SET value=? WHERE key='schema_version'",
                    (schema_version,)
                )
                conn.commit()
                print(f"  ✓ schema_version atualizado para '{schema_version}'")
        else:
            print(f"  → Inserindo schema_version='{schema_version}'...")
            cursor.execute(
                "INSERT INTO app_meta (key, value) VALUES (?, ?)",
                ('schema_version', schema_version)
            )
            conn.commit()
            print(f"  ✓ schema_version inserido: '{schema_version}'")

        # Verificar integridade
        print("\n[VERIFICAÇÃO] Executando integrity check...")
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result[0] == 'ok':
            print("  ✓ Integridade verificada")
        else:
            print(f"  ✗ Integridade falhou: {result[0]}")
            return False

        print("\n" + "=" * 60)
        print("[OK] Migração concluída com sucesso!")
        print("=" * 60)
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n[ERRO] Falha na migração: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)

