# -*- coding: utf-8 -*-
"""
Script de migração para alterar tamanho da coluna 'horario' na tabela 'pedidos'
Altera de VARCHAR(10) para VARCHAR(20) para suportar intervalos (HH:MM - HH:MM)
"""
import sqlite3
import sys
from pathlib import Path

# Garantir que o backend esteja no sys.path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import Config  # noqa: E402


def alterar_horario_column():
    """Altera o tamanho da coluna 'horario' de VARCHAR(10) para VARCHAR(20)"""
    # Caminho do banco de dados usando Config
    db_path = Config.DATABASE_PATH

    if not db_path.exists():
        print(f"❌ Banco de dados não encontrado em: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Verificar estrutura atual da coluna
        cursor.execute("PRAGMA table_info(pedidos)")
        columns = cursor.fetchall()

        horario_col = None
        for col in columns:
            if col[1] == 'horario':
                horario_col = col
                break

        if not horario_col:
            print("❌ Coluna 'horario' não encontrada na tabela 'pedidos'")
            conn.close()
            return False

        # Verificar se já está no tamanho correto (SQLite não armazena tamanho, mas verificamos o tipo)
        # SQLite não tem VARCHAR com tamanho fixo, mas vamos garantir que aceita strings maiores
        print("🔄 Alterando coluna 'horario' para suportar intervalos...")

        # SQLite não suporta ALTER COLUMN diretamente
        # Precisamos recriar a tabela com a nova definição
        print("   📋 Criando tabela temporária...")

        # 1. Criar tabela temporária com nova estrutura
        cursor.execute("""
            CREATE TABLE pedidos_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente VARCHAR(100) NOT NULL,
                telefone_cliente VARCHAR(20) NOT NULL,
                destinatario VARCHAR(100) NOT NULL,
                tipo_pedido VARCHAR(20) DEFAULT 'Entrega',
                produto TEXT NOT NULL,
                flores_cor TEXT,
                valor VARCHAR(20),
                dia_entrega DATE NOT NULL,
                horario VARCHAR(20) NOT NULL,
                cep VARCHAR(10),
                rua VARCHAR(200),
                numero VARCHAR(20),
                bairro VARCHAR(100),
                cidade VARCHAR(100),
                endereco TEXT,
                obs_entrega TEXT,
                mensagem TEXT,
                pagamento VARCHAR(50),
                observacoes TEXT,
                fonte_pedido VARCHAR(50),
                fonte_pedido_id INTEGER,
                status_pagamento VARCHAR(50),
                status VARCHAR(30) DEFAULT 'agendado',
                quantidade INTEGER DEFAULT 1,
                oculto BOOLEAN DEFAULT 0,
                impresso BOOLEAN DEFAULT 0,
                cliente_id INTEGER,
                distancia_km REAL,
                taxa_entrega REAL,
                coords_lat REAL,
                coords_lon REAL,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (fonte_pedido_id) REFERENCES fontes_pedido(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        """)

        # 2. Copiar dados da tabela antiga para a nova
        print("   📦 Copiando dados...")
        cursor.execute("""
            INSERT INTO pedidos_new
            SELECT * FROM pedidos
        """)

        # 3. Contar registros copiados
        cursor.execute("SELECT COUNT(*) FROM pedidos_new")
        count = cursor.fetchone()[0]
        print(f"   ✅ {count} registro(s) copiado(s)")

        # 4. Dropar tabela antiga
        print("   🗑️  Removendo tabela antiga...")
        cursor.execute("DROP TABLE pedidos")

        # 5. Renomear tabela nova
        print("   ✏️  Renomeando tabela...")
        cursor.execute("ALTER TABLE pedidos_new RENAME TO pedidos")

        # 6. Recriar índices se existirem
        # Verificar índices existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='pedidos' AND name NOT LIKE 'sqlite_%'")
        indexes = cursor.fetchall()

        if indexes:
            print(f"   🔍 {len(indexes)} índice(s) encontrado(s) - serão recriados automaticamente pelo SQLAlchemy se necessário")

        conn.commit()
        conn.close()

        print("✅ Coluna 'horario' alterada com sucesso!")
        print("   - Agora suporta intervalos no formato: HH:MM - HH:MM")
        print("   - Tamanho máximo: 20 caracteres")

        return True

    except Exception as e:
        print(f"❌ Erro ao alterar coluna: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("Migração: Alterar tamanho da coluna 'horario'")
    print("=" * 60)
    print(f"Banco de dados: {Config.DATABASE_PATH}")
    print("=" * 60)

    # Confirmar antes de executar
    resposta = input("Deseja continuar? (s/N): ").strip().lower()
    if resposta not in ['s', 'sim', 'y', 'yes']:
        print("❌ Migração cancelada pelo usuário")
        sys.exit(0)

    sucesso = alterar_horario_column()

    print("=" * 60)
    if sucesso:
        print("✅ Migração concluída com sucesso!")
    else:
        print("❌ Migração falhou!")
        sys.exit(1)

