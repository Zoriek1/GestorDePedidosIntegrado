# -*- coding: utf-8 -*-
"""
Script de migração para adicionar coluna 'oculto' à tabela 'pedidos'
Este script adiciona o campo oculto (BOOLEAN) se ele não existir
"""
import sqlite3
from pathlib import Path


def add_oculto_column():
    """Adiciona a coluna 'oculto' se não existir"""
    # Caminho do banco de dados
    db_path = Path(__file__).parent / "database.db"

    if not db_path.exists():
        print(f"❌ Banco de dados não encontrado em: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(pedidos)")
        columns = [col[1] for col in cursor.fetchall()]

        if "oculto" in columns:
            print("✅ Coluna 'oculto' já existe na tabela 'pedidos'")
            conn.close()
            return True

        # Adicionar a coluna 'oculto'
        print("🔄 Adicionando coluna 'oculto' à tabela 'pedidos'...")
        cursor.execute("ALTER TABLE pedidos ADD COLUMN oculto BOOLEAN DEFAULT 0")
        conn.commit()

        print("✅ Coluna 'oculto' adicionada com sucesso!")
        print("   - Todos os pedidos existentes terão oculto = False (visíveis)")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Erro ao adicionar coluna: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Migração: Adicionar coluna 'oculto'")
    print("=" * 60)
    add_oculto_column()
    print("=" * 60)
