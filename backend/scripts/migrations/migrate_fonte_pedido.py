# -*- coding: utf-8 -*-
"""
Script de migração para criar tabela fontes_pedido e migrar dados
Este script:
1. Cria tabela fontes_pedido
2. Popula com fontes iniciais
3. Adiciona coluna fonte_pedido_id em pedidos
4. Migra dados existentes (associa IDs)
5. Pedidos sem fonte ou desconhecidos → WhatsApp (Caio)
"""
import sqlite3
from datetime import datetime
from pathlib import Path


def migrate_fonte_pedido():
    """Executa migração completa de fontes de pedido"""
    # Caminho do banco de dados (backend/database.db)
    backend_dir = Path(__file__).parent.parent.parent
    db_path = backend_dir / 'database.db'

    if not db_path.exists():
        print(f"[ERRO] Banco de dados não encontrado em: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        print("=" * 60)
        print("Migração: Criar tabela fontes_pedido e migrar dados")
        print("=" * 60)

        # 1. Criar tabela fontes_pedido se não existir
        print("\n[1/5] Criando tabela fontes_pedido...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fontes_pedido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome VARCHAR(100) NOT NULL UNIQUE,
                ativo BOOLEAN DEFAULT 1,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)
        conn.commit()
        print("[OK] Tabela fontes_pedido criada/verificada")

        # 2. Popular com fontes iniciais
        print("\n[2/5] Populando fontes iniciais...")
        fontes_iniciais = [
            'Ifood',
            'Site',
            'Catálogo',
            'WhatsApp (Caio)',
            'WhatsApp (Paula)'
        ]

        fonte_whatsapp_caio_id = None
        for fonte_nome in fontes_iniciais:
            # Verificar se já existe
            cursor.execute("SELECT id FROM fontes_pedido WHERE nome = ?", (fonte_nome,))
            existe = cursor.fetchone()

            if not existe:
                cursor.execute("""
                    INSERT INTO fontes_pedido (nome, ativo, created_at)
                    VALUES (?, 1, ?)
                """, (fonte_nome, datetime.utcnow().isoformat()))
                print(f"   - Fonte '{fonte_nome}' criada")
            else:
                print(f"   - Fonte '{fonte_nome}' já existe (ID: {existe[0]})")

            # Guardar ID do WhatsApp (Caio) para usar como padrão
            if fonte_nome == 'WhatsApp (Caio)':
                if not existe:
                    fonte_whatsapp_caio_id = cursor.lastrowid
                else:
                    fonte_whatsapp_caio_id = existe[0]

        conn.commit()
        print("[OK] Fontes iniciais populadas")

        # 3. Adicionar coluna fonte_pedido_id em pedidos
        print("\n[3/5] Adicionando coluna fonte_pedido_id em pedidos...")
        cursor.execute("PRAGMA table_info(pedidos)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'fonte_pedido_id' not in columns:
            cursor.execute("ALTER TABLE pedidos ADD COLUMN fonte_pedido_id INTEGER")
            conn.commit()
            print("[OK] Coluna fonte_pedido_id adicionada")
        else:
            print("[OK] Coluna fonte_pedido_id já existe")

        # 4. Migrar dados existentes
        print("\n[4/5] Migrando dados existentes...")

        # Buscar todos os pedidos
        cursor.execute("SELECT id, fonte_pedido FROM pedidos")
        pedidos = cursor.fetchall()

        # Criar mapeamento de nome -> id
        cursor.execute("SELECT id, nome FROM fontes_pedido")
        fontes_map = {nome: id for id, nome in cursor.fetchall()}

        migrados = 0
        sem_fonte = 0

        for pedido_id, fonte_pedido_str in pedidos:
            fonte_id = None

            if fonte_pedido_str and fonte_pedido_str.strip():
                # Buscar fonte pelo nome
                fonte_id = fontes_map.get(fonte_pedido_str.strip())

            # Se não encontrou, usar WhatsApp (Caio) como padrão
            if not fonte_id:
                fonte_id = fonte_whatsapp_caio_id
                sem_fonte += 1

            # Atualizar pedido
            cursor.execute("""
                UPDATE pedidos
                SET fonte_pedido_id = ?
                WHERE id = ?
            """, (fonte_id, pedido_id))

            migrados += 1

        conn.commit()
        print(f"[OK] {migrados} pedidos migrados")
        print(f"   - {sem_fonte} pedidos sem fonte ou com fonte desconhecida → associados a 'WhatsApp (Caio)'")

        # 5. NOTA: Não vamos remover a coluna fonte_pedido ainda para manter compatibilidade
        # A coluna será mantida mas não será mais usada
        print("\n[5/5] Migração concluída!")
        print("   - Coluna fonte_pedido (String) mantida para compatibilidade")
        print("   - Use fonte_pedido_id (Integer) para novos pedidos")

        conn.close()
        return True

    except Exception as e:
        print(f"\n[ERRO] Erro durante migração: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = migrate_fonte_pedido()
    print("=" * 60)
    if success:
        print("Migração concluída com sucesso!")
    else:
        print("Migração falhou. Verifique os erros acima.")
    print("=" * 60)

