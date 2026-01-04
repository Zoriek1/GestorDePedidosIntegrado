# -*- coding: utf-8 -*-
"""
Script de migração para adicionar colunas de endereço à tabela 'pedidos'
Este script adiciona os campos: cep, rua, numero, bairro, cidade
"""
import sqlite3
from pathlib import Path


def add_endereco_columns():
    """Adiciona as colunas de endereço se não existirem"""
    # Caminho do banco de dados
    db_path = Path(__file__).parent / 'database.db'

    if not db_path.exists():
        print(f"❌ Banco de dados não encontrado em: {db_path}")
        return False

    # Colunas a serem adicionadas
    new_columns = [
        ('cep', 'VARCHAR(10)'),
        ('rua', 'VARCHAR(200)'),
        ('numero', 'VARCHAR(20)'),
        ('bairro', 'VARCHAR(100)'),
        ('cidade', 'VARCHAR(100)')
    ]

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Verificar quais colunas já existem
        cursor.execute("PRAGMA table_info(pedidos)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        columns_added = 0

        for col_name, col_type in new_columns:
            if col_name in existing_columns:
                print(f"✅ Coluna '{col_name}' já existe na tabela 'pedidos'")
            else:
                print(f"🔄 Adicionando coluna '{col_name}' ({col_type})...")
                cursor.execute(f"ALTER TABLE pedidos ADD COLUMN {col_name} {col_type}")
                columns_added += 1
                print(f"   ✅ Coluna '{col_name}' adicionada com sucesso!")

        conn.commit()
        conn.close()

        if columns_added > 0:
            print(f"\n✅ {columns_added} coluna(s) adicionada(s) com sucesso!")
            print("   Os pedidos existentes terão esses campos vazios.")
        else:
            print("\n✅ Todas as colunas já existem. Nenhuma alteração necessária.")

        return True

    except Exception as e:
        print(f"❌ Erro ao adicionar colunas: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Migração: Adicionar colunas de endereço")
    print("=" * 60)
    add_endereco_columns()
    print("=" * 60)

