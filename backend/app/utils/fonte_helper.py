# -*- coding: utf-8 -*-
"""
Helper para gerenciar tabelas de pedidos por fonte
Funções utilitárias para normalização de nomes e gerenciamento de tabelas dinâmicas
"""
import re

from sqlalchemy import text

from app import db
from app.models.fonte_pedido import FontePedido


def normalizar_nome_fonte(nome_fonte):
    """
    Normaliza nome de fonte para nome de tabela válido

    Exemplos:
    - "WhatsApp (Paula)" → "whatsapp_paula"
    - "Ifood" → "ifood"
    - "Site" → "site"
    - "Catálogo" → "catalogo"

    Args:
        nome_fonte (str): Nome da fonte (ex: "WhatsApp (Paula)")

    Returns:
        str: Nome normalizado para tabela (ex: "whatsapp_paula")
    """
    if not nome_fonte:
        return None

    # Converter para minúsculas
    nome = nome_fonte.lower().strip()

    # Remover parênteses e conteúdo dentro
    nome = re.sub(r"\([^)]*\)", "", nome)

    # Remover caracteres especiais, manter apenas letras, números e espaços
    nome = re.sub(r"[^a-z0-9\s]", "", nome)

    # Substituir espaços múltiplos por underscore único
    nome = re.sub(r"\s+", "_", nome)

    # Remover underscores no início e fim
    nome = nome.strip("_")

    # Se ficar vazio, usar "fonte" como padrão
    if not nome:
        nome = "fonte"

    return nome


def get_tabela_fonte(fonte_id):
    """
    Retorna nome da tabela para uma fonte específica

    Args:
        fonte_id (int): ID da fonte em fontes_pedido

    Returns:
        str: Nome da tabela (ex: "pedidos_whatsapp_paula") ou None se fonte não existe
    """
    fonte = FontePedido.query.get(fonte_id)
    if not fonte:
        return None

    nome_normalizado = normalizar_nome_fonte(fonte.nome)
    return f"pedidos_{nome_normalizado}"


def _table_exists(nome_tabela):
    """Verifica se tabela existe (SQLite ou PostgreSQL)"""
    dialect = db.engine.dialect.name
    with db.engine.connect() as conn:
        if dialect == "sqlite":
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": nome_tabela},
            )
        else:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = :name"
                ),
                {"name": nome_tabela},
            )
        return result.fetchone() is not None


def criar_tabela_fonte(nome_tabela):
    """
    Cria tabela SQL dinamicamente para uma fonte específica.
    Suporta SQLite e PostgreSQL.

    Estrutura:
    - id (PK, autoincrement)
    - pedido_id (INTEGER, UNIQUE, FK para pedidos.id)
    - numero_sequencial (INTEGER)
    - valor (VARCHAR)
    - created_at (TIMESTAMP)

    Args:
        nome_tabela (str): Nome da tabela (ex: "pedidos_whatsapp_paula")

    Returns:
        bool: True se tabela foi criada, False se já existia
    """
    if _table_exists(nome_tabela):
        return False

    dialect = db.engine.dialect.name
    if dialect == "sqlite":
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {nome_tabela} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL UNIQUE,
                numero_sequencial INTEGER NOT NULL,
                valor VARCHAR(20),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
            )
        """
    else:
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {nome_tabela} (
                id SERIAL PRIMARY KEY,
                pedido_id INTEGER NOT NULL UNIQUE REFERENCES pedidos(id),
                numero_sequencial INTEGER NOT NULL,
                valor VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

    with db.engine.connect() as conn:
        conn.execute(text(create_sql))
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS idx_{nome_tabela}_pedido_id "
                f"ON {nome_tabela}(pedido_id)"
            )
        )
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS idx_{nome_tabela}_numero_sequencial "
                f"ON {nome_tabela}(numero_sequencial)"
            )
        )
        conn.commit()

    return True


def get_proximo_numero_sequencial(nome_tabela):
    """
    Obtém o próximo número sequencial para uma fonte

    Args:
        nome_tabela (str): Nome da tabela da fonte

    Returns:
        int: Próximo número sequencial (começa em 1 se tabela estiver vazia)
    """
    with db.engine.connect() as conn:
        result = conn.execute(
            text(
                f"""
            SELECT MAX(numero_sequencial) FROM {nome_tabela}
        """
            )
        )
        max_num = result.fetchone()[0]
        return (max_num or 0) + 1


def inserir_pedido_fonte(pedido_id, fonte_id, valor):
    """
    Insere pedido na tabela auxiliar da fonte correspondente

    Args:
        pedido_id (int): ID do pedido na tabela principal
        fonte_id (int): ID da fonte do pedido
        valor (str): Valor do pedido (ex: "R$ 50,00")

    Returns:
        dict: Informações do registro criado ou None se erro
    """
    if not fonte_id:
        return None

    # Obter nome da tabela
    nome_tabela = get_tabela_fonte(fonte_id)
    if not nome_tabela:
        return None

    # Garantir que tabela existe
    criar_tabela_fonte(nome_tabela)

    # Obter próximo número sequencial
    numero_sequencial = get_proximo_numero_sequencial(nome_tabela)

    # Inserir registro
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    f"""
                INSERT INTO {nome_tabela} (pedido_id, numero_sequencial, valor, created_at)
                VALUES (:pedido_id, :numero_sequencial, :valor, CURRENT_TIMESTAMP)
            """
                ),
                {
                    "pedido_id": pedido_id,
                    "numero_sequencial": numero_sequencial,
                    "valor": valor or "",
                },
            )
            conn.commit()

        return {
            "pedido_id": pedido_id,
            "numero_sequencial": numero_sequencial,
            "valor": valor,
            "tabela": nome_tabela,
        }
    except Exception as e:
        print(f"[ERRO] Erro ao inserir pedido na tabela {nome_tabela}: {e}")
        return None


def buscar_pedidos_fonte(fonte_id, limit=None, offset=0):
    """
    Busca pedidos de uma fonte específica

    Args:
        fonte_id (int): ID da fonte
        limit (int, optional): Limite de resultados
        offset (int): Offset para paginação

    Returns:
        list: Lista de dicionários com informações dos pedidos
    """
    nome_tabela = get_tabela_fonte(fonte_id)
    if not nome_tabela:
        return []

    query = f"""
        SELECT pf.pedido_id, pf.numero_sequencial, pf.valor, pf.created_at,
               p.cliente, p.destinatario, p.produto, p.status
        FROM {nome_tabela} pf
        JOIN pedidos p ON pf.pedido_id = p.id
        ORDER BY pf.numero_sequencial DESC
    """

    if limit:
        query += f" LIMIT {limit} OFFSET {offset}"

    with db.engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()

        return [
            {
                "pedido_id": row[0],
                "numero_sequencial": row[1],
                "valor": row[2],
                "created_at": row[3],
                "cliente": row[4],
                "destinatario": row[5],
                "produto": row[6],
                "status": row[7],
            }
            for row in rows
        ]


def get_estatisticas_fonte(fonte_id):
    """
    Retorna estatísticas consolidadas de uma fonte

    Args:
        fonte_id (int): ID da fonte

    Returns:
        dict: Estatísticas (total_pedidos, total_vendas, etc)
    """
    nome_tabela = get_tabela_fonte(fonte_id)
    if not nome_tabela:
        return {"total_pedidos": 0, "total_vendas": 0, "ultimo_numero": 0}

    with db.engine.connect() as conn:
        # Total de pedidos
        result = conn.execute(
            text(
                f"""
            SELECT COUNT(*) FROM {nome_tabela}
        """
            )
        )
        total_pedidos = result.fetchone()[0] or 0

        # Último número sequencial
        result = conn.execute(
            text(
                f"""
            SELECT MAX(numero_sequencial) FROM {nome_tabela}
        """
            )
        )
        ultimo_numero = result.fetchone()[0] or 0

        # Total de vendas (soma dos valores - precisa converter string para número)
        # Por enquanto retornamos apenas contagem, conversão de valor pode ser feita depois
        total_vendas = 0  # TODO: Implementar conversão de valores se necessário

    return {
        "total_pedidos": total_pedidos,
        "total_vendas": total_vendas,
        "ultimo_numero": ultimo_numero,
    }
