# -*- coding: utf-8 -*-
"""
Schemas de Cliente - Validação e serialização
"""
from marshmallow import Schema, fields, validate


class ClienteSchema(Schema):
    """Schema para Cliente"""

    id = fields.Int(dump_only=True)
    nome = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    telefone = fields.Str(required=True, validate=validate.Length(min=10, max=20))
    email = fields.Email(allow_none=True, validate=validate.Length(max=100))
    observacoes = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ClienteCreateSchema(ClienteSchema):
    """Schema para criação de cliente"""
    pass


class ClienteUpdateSchema(Schema):
    """Schema para atualização de cliente - todos campos opcionais"""

    nome = fields.Str(validate=validate.Length(max=100))
    telefone = fields.Str(validate=validate.Length(max=20))
    email = fields.Email(allow_none=True, validate=validate.Length(max=100))
    observacoes = fields.Str(allow_none=True)


class ClienteAutocompleteSchema(Schema):
    """Schema compacto para autocomplete"""

    id = fields.Int()
    nome = fields.Str()
    telefone = fields.Str()
    total_pedidos = fields.Int()

