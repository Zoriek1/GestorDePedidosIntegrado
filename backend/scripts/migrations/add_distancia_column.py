# -*- coding: utf-8 -*-
"""
Script de migração para adicionar coluna 'distancia_km' à tabela 'pedidos'
"""
import sqlite3
from pathlib import Path


def add_distancia_column():
    """Adiciona a coluna 'distancia_km' se não existir"""
    db_path = Path(__file__).parent / "database.db"

    if not db_path.exists():
        print(f"Banco de dados não encontrado em: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(pedidos)")
        columns = [col[1] for col in cursor.fetchall()]

        if "distancia_km" in columns:
            print("Coluna 'distancia_km' já existe na tabela 'pedidos'")
            conn.close()
            return True

        # Adicionar a coluna
        print("Adicionando coluna 'distancia_km' à tabela 'pedidos'...")
        cursor.execute("ALTER TABLE pedidos ADD COLUMN distancia_km FLOAT")
        conn.commit()

        print("Coluna 'distancia_km' adicionada com sucesso!")
        conn.close()
        return True

    except Exception as e:
        print(f"Erro ao adicionar coluna: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Migração: Adicionar coluna 'distancia_km'")
    print("=" * 60)
    add_distancia_column()
    print("=" * 60)
