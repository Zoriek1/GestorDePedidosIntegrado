# -*- coding: utf-8 -*-
"""
Repositories - Isolamento de acesso ao banco de dados
Camada de abstração para operações de banco de dados
"""
from app.repositories.base_repository import BaseRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.pedido_repository import PedidoRepository

__all__ = ['BaseRepository', 'PedidoRepository', 'ClienteRepository']

