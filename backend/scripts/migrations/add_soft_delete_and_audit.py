# -*- coding: utf-8 -*-
"""
Migração: Adicionar Soft Delete e Tabela de Auditoria (P0.3)

Adiciona:
- Coluna deleted_at na tabela pedidos
- Tabela audit_log para trilha de auditoria

Uso:
    python scripts/migrations/add_soft_delete_and_audit.py
"""
import sys
import sqlite3
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import Config


def check_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Verifica se coluna existe na tabela"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def check_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Verifica se tabela existe"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def migrate():
    """Executa a migração"""
    db_path = Config.DATABASE_PATH
    
    if not db_path.exists():
        print(f"[ERRO] Banco de dados não encontrado: {db_path}")
        return False
    
    print("=" * 60)
    print("MIGRAÇÃO: Soft Delete e Auditoria (P0.3)")
    print("=" * 60)
    print(f"\nBanco de dados: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 1. Adicionar coluna deleted_at na tabela pedidos
        print("\n[1/2] Verificando coluna deleted_at em pedidos...")
        if check_column_exists(conn, 'pedidos', 'deleted_at'):
            print("  ✓ Coluna deleted_at já existe")
        else:
            print("  → Adicionando coluna deleted_at...")
            cursor.execute("ALTER TABLE pedidos ADD COLUMN deleted_at DATETIME NULL")
            conn.commit()
            print("  ✓ Coluna deleted_at adicionada")
        
        # 2. Criar tabela audit_log
        print("\n[2/2] Verificando tabela audit_log...")
        if check_table_exists(conn, 'audit_log'):
            print("  ✓ Tabela audit_log já existe")
        else:
            print("  → Criando tabela audit_log...")
            cursor.execute("""
                CREATE TABLE audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    actor TEXT,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER,
                    metadata_json TEXT
                )
            """)
            
            # Criar índices para melhor performance
            cursor.execute("CREATE INDEX idx_audit_log_ts ON audit_log(ts)")
            cursor.execute("CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id)")
            cursor.execute("CREATE INDEX idx_audit_log_action ON audit_log(action)")
            
            conn.commit()
            print("  ✓ Tabela audit_log criada com índices")
        
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

