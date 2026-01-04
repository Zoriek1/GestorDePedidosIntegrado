# -*- coding: utf-8 -*-
"""
Schemas - Validação e Serialização
Usa Marshmallow para validação de dados e serialização de respostas
"""
from app.schemas.cliente_schema import (
    ClienteAutocompleteSchema,
    ClienteCreateSchema,
    ClienteSchema,
    ClienteUpdateSchema,
)
from app.schemas.common import error_response, success_response
from app.schemas.pedido_schema import PedidoCreateSchema, PedidoSchema, PedidoUpdateSchema

__all__ = [
    'success_response',
    'error_response',
    'PedidoSchema', 'PedidoCreateSchema', 'PedidoUpdateSchema',
    'ClienteSchema', 'ClienteCreateSchema', 'ClienteUpdateSchema', 'ClienteAutocompleteSchema'
]

