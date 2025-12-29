# -*- coding: utf-8 -*-
"""
Schemas - Validação e Serialização
Usa Marshmallow para validação de dados e serialização de respostas
"""
from app.schemas.common import success_response, error_response
from app.schemas.pedido_schema import (
    PedidoSchema, PedidoCreateSchema, PedidoUpdateSchema
)
from app.schemas.cliente_schema import (
    ClienteSchema, ClienteCreateSchema, ClienteUpdateSchema, ClienteAutocompleteSchema
)

__all__ = [
    'success_response', 
    'error_response',
    'PedidoSchema', 'PedidoCreateSchema', 'PedidoUpdateSchema',
    'ClienteSchema', 'ClienteCreateSchema', 'ClienteUpdateSchema', 'ClienteAutocompleteSchema'
]

