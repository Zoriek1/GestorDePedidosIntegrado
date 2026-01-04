# -*- coding: utf-8 -*-
"""
Modelo para gerenciar pedidos por fonte
Gerencia tabelas dinâmicas separadas para cada fonte de pedido
"""
from app import db
from app.models.fonte_pedido import FontePedido
from app.utils.fonte_helper import buscar_pedidos_fonte as helper_buscar_pedidos_fonte
from app.utils.fonte_helper import (
    criar_tabela_fonte,
    get_proximo_numero_sequencial,
    get_tabela_fonte,
)
from app.utils.fonte_helper import get_estatisticas_fonte as helper_get_estatisticas_fonte
from app.utils.fonte_helper import inserir_pedido_fonte as helper_inserir_pedido_fonte


class PedidoFonte:
    """
    Classe para gerenciar pedidos por fonte
    Não é um modelo SQLAlchemy tradicional, mas uma classe utilitária
    que gerencia tabelas dinâmicas por fonte
    """

    @staticmethod
    def criar_tabela_para_fonte(fonte_id):
        """
        Cria tabela para uma fonte específica se não existir

        Args:
            fonte_id (int): ID da fonte

        Returns:
            tuple: (bool, str) - (sucesso, nome_tabela)
        """
        fonte = FontePedido.query.get(fonte_id)
        if not fonte:
            return False, None

        nome_tabela = get_tabela_fonte(fonte_id)
        if not nome_tabela:
            return False, None

        criar_tabela_fonte(nome_tabela)
        return True, nome_tabela

    @staticmethod
    def adicionar_pedido(pedido_id, fonte_id, valor):
        """
        Adiciona pedido à tabela da fonte correspondente

        Args:
            pedido_id (int): ID do pedido na tabela principal
            fonte_id (int): ID da fonte do pedido
            valor (str): Valor do pedido

        Returns:
            dict: Informações do registro criado ou None
        """
        return helper_inserir_pedido_fonte(pedido_id, fonte_id, valor)

    @staticmethod
    def obter_pedidos(fonte_id, limit=None, offset=0):
        """
        Obtém lista de pedidos de uma fonte

        Args:
            fonte_id (int): ID da fonte
            limit (int, optional): Limite de resultados
            offset (int): Offset para paginação

        Returns:
            list: Lista de pedidos da fonte
        """
        return helper_buscar_pedidos_fonte(fonte_id, limit, offset)

    @staticmethod
    def obter_estatisticas(fonte_id):
        """
        Obtém estatísticas consolidadas de uma fonte

        Args:
            fonte_id (int): ID da fonte

        Returns:
            dict: Estatísticas (total_pedidos, total_vendas, ultimo_numero)
        """
        return helper_get_estatisticas_fonte(fonte_id)

    @staticmethod
    def obter_numero_sequencial(fonte_id):
        """
        Obtém o próximo número sequencial para uma fonte

        Args:
            fonte_id (int): ID da fonte

        Returns:
            int: Próximo número sequencial
        """
        nome_tabela = get_tabela_fonte(fonte_id)
        if not nome_tabela:
            return 1

        # Garantir que tabela existe
        criar_tabela_fonte(nome_tabela)

        return get_proximo_numero_sequencial(nome_tabela)

    @staticmethod
    def criar_tabelas_para_todas_fontes():
        """
        Cria tabelas para todas as fontes ativas

        Returns:
            dict: Relatório de criação (fonte_id: nome_tabela)
        """
        fontes = FontePedido.query.filter_by(ativo=True).all()
        resultado = {}

        for fonte in fontes:
            sucesso, nome_tabela = PedidoFonte.criar_tabela_para_fonte(fonte.id)
            if sucesso:
                resultado[fonte.id] = {
                    'nome_fonte': fonte.nome,
                    'tabela': nome_tabela,
                    'criada': nome_tabela is not None
                }

        return resultado

    @staticmethod
    def verificar_pedido_na_fonte(pedido_id, fonte_id):
        """
        Verifica se um pedido já está registrado na tabela da fonte

        Args:
            pedido_id (int): ID do pedido
            fonte_id (int): ID da fonte

        Returns:
            dict: Informações do registro ou None se não encontrado
        """
        nome_tabela = get_tabela_fonte(fonte_id)
        if not nome_tabela:
            return None

        from sqlalchemy import text

        with db.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT pedido_id, numero_sequencial, valor, created_at
                FROM {nome_tabela}
                WHERE pedido_id = :pedido_id
            """), {'pedido_id': pedido_id})

            row = result.fetchone()
            if row:
                return {
                    'pedido_id': row[0],
                    'numero_sequencial': row[1],
                    'valor': row[2],
                    'created_at': row[3]
                }

        return None
