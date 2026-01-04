# -*- coding: utf-8 -*-
"""
Script de migração para adicionar coluna 'impresso' à tabela 'pedidos'
Este script adiciona o campo impresso (BOOLEAN) se ele não existir
"""
import sqlite3
from pathlib import Path


def add_impresso_column():
    """Adiciona a coluna 'impresso' se não existir"""
    # Caminho do banco de dados (backend/database.db)
    backend_dir = Path(__file__).parent.parent.parent
    db_path = backend_dir / 'database.db'

    if not db_path.exists():
        print(f"[ERRO] Banco de dados nao encontrado em: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(pedidos)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'impresso' in columns:
            print("[OK] Coluna 'impresso' ja existe na tabela 'pedidos'")
            conn.close()
            return True

        # Adicionar a coluna 'impresso'
        print("[INFO] Adicionando coluna 'impresso' a tabela 'pedidos'...")
        cursor.execute("ALTER TABLE pedidos ADD COLUMN impresso BOOLEAN DEFAULT 0")
        conn.commit()

        print("[OK] Coluna 'impresso' adicionada com sucesso!")
        print("   - Todos os pedidos existentes terao impresso = False (nao impressos)")

        conn.close()
        return True

    except Exception as e:
        print(f"[ERRO] Erro ao adicionar coluna: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Migração: Adicionar coluna 'impresso'")
    print("=" * 60)
    add_impresso_column()
    print("=" * 60)
