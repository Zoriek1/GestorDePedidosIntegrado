# -*- coding: utf-8 -*-
"""
Schemas Marshmallow para OpenAPI

Schemas para documentação dos endpoints prioritários do frontend_v2.
Inicialmente permissivos (fields.Raw) para não quebrar compatibilidade.
"""
from marshmallow import Schema, fields


class HealthResponseSchema(Schema):
    """Schema de resposta do health check"""

    success = fields.Bool(required=True, description="Indica se a requisição foi bem-sucedida")
    status = fields.Str(description="Status da API (healthy/unhealthy)")
    message = fields.Str(description="Mensagem de status")


class AuthCheckResponseSchema(Schema):
    """Schema de resposta da verificação de autenticação"""

    success = fields.Bool(required=True)
    data = fields.Dict(description="Dados de autenticação")
    message = fields.Str(description="Mensagem de resposta")


class AuthCheckDataSchema(Schema):
    """Schema dos dados de autenticação"""

    authenticated = fields.Bool(description="Indica se está autenticado")


class PedidosResponseSchema(Schema):
    """Schema de resposta da listagem de pedidos"""

    success = fields.Bool(required=True)
    data = fields.Dict(description="Dados dos pedidos")
    message = fields.Str(description="Mensagem opcional")


class PedidosDataSchema(Schema):
    """Schema dos dados de pedidos"""

    pedidos = fields.List(fields.Raw(), description="Lista de pedidos")
    total = fields.Int(description="Total de pedidos")


class StatsResponseSchema(Schema):
    """Schema de resposta das estatísticas"""

    success = fields.Bool(required=True)
    data = fields.Dict(description="Dados das estatísticas")
    message = fields.Str(description="Mensagem opcional")


class StatsDataSchema(Schema):
    """Schema dos dados de estatísticas"""

    stats = fields.Dict(description="Estatísticas dos pedidos")


class ClientesBuscarResponseSchema(Schema):
    """Schema de resposta da busca de clientes"""

    success = fields.Bool(required=True)
    data = fields.Dict(description="Dados dos clientes")
    message = fields.Str(description="Mensagem opcional")


class ClientesBuscarDataSchema(Schema):
    """Schema dos dados de busca de clientes"""

    clientes = fields.List(fields.Raw(), description="Lista de clientes encontrados")
    total = fields.Int(description="Total de clientes encontrados")


# Query parameters schemas
class PedidosQuerySchema(Schema):
    """Schema para query parameters de listagem de pedidos"""

    status = fields.Str(description="Filtrar por status", missing=None)
    data_inicio = fields.Str(description="Data inicial (YYYY-MM-DD)", missing=None)
    data_fim = fields.Str(description="Data final (YYYY-MM-DD)", missing=None)
    search = fields.Str(description="Busca textual", missing=None)


class ClientesBuscarQuerySchema(Schema):
    """Schema para query parameters de busca de clientes"""

    q = fields.Str(required=True, description="Termo de busca")
    limit = fields.Int(description="Limite de resultados", missing=10)
