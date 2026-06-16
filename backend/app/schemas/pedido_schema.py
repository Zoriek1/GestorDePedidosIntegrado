# -*- coding: utf-8 -*-
"""
Schemas de Pedido - Validação e serialização com Marshmallow
"""
import re

from marshmallow import Schema, ValidationError, fields, validate, validates


class PedidoSchema(Schema):
    """Schema para validação e serialização de Pedidos"""

    id = fields.Int(dump_only=True)

    # Step 1 - Dados do Cliente
    cliente = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    telefone_cliente = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    destinatario = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    tipo_pedido = fields.Str(
        validate=validate.OneOf(["Entrega", "Retirada"]), load_default="Entrega"
    )

    # Step 2 - Produto e Agendamento
    produto = fields.Str(required=True)
    flores_cor = fields.Str(allow_none=True)
    valor = fields.Str(allow_none=True)
    dia_entrega = fields.Date(required=True)
    horario = fields.Str(required=True)

    # Step 3 - Logística
    cep = fields.Str(allow_none=True, validate=validate.Length(max=10))
    rua = fields.Str(allow_none=True, validate=validate.Length(max=200))
    numero = fields.Str(allow_none=True, validate=validate.Length(max=20))
    tipo_local = fields.Str(
        allow_none=True, validate=validate.OneOf(["casa", "predio", "comercial"])
    )
    nome_local = fields.Str(allow_none=True, validate=validate.Length(max=120))
    apto = fields.Str(allow_none=True, validate=validate.Length(max=50))
    bloco = fields.Str(allow_none=True, validate=validate.Length(max=50))
    torre = fields.Str(allow_none=True, validate=validate.Length(max=50))
    andar = fields.Str(allow_none=True, validate=validate.Length(max=50))
    quadra = fields.Str(allow_none=True, validate=validate.Length(max=50))
    lote = fields.Str(allow_none=True, validate=validate.Length(max=50))
    complemento = fields.Str(allow_none=True, validate=validate.Length(max=100))
    bairro = fields.Str(allow_none=True, validate=validate.Length(max=100))
    cidade = fields.Str(allow_none=True, validate=validate.Length(max=100))
    endereco = fields.Str(allow_none=True)
    obs_entrega = fields.Str(allow_none=True)

    # Step 4 - Finalização
    mensagem = fields.Str(allow_none=True)
    pagamento = fields.Str(allow_none=True, validate=validate.Length(max=50))
    observacoes = fields.Str(allow_none=True)

    # Controle
    status = fields.Str(
        validate=validate.OneOf(
            [
                "agendado",
                "em_producao",
                "pronto_entrega",
                "em_rota",
                "pronto_retirada",
                "concluido",
                "cancelado",
            ]
        ),
        load_default="agendado",
    )
    quantidade = fields.Int(load_default=1)
    oculto = fields.Bool(load_default=False)
    impresso = fields.Bool(load_default=False)

    # Relacionamentos
    fonte_pedido_id = fields.Int(allow_none=True)
    cliente_id = fields.Int(allow_none=True)
    status_pagamento = fields.Str(allow_none=True, validate=validate.Length(max=50))

    # Plataforma e Canal (integrações)
    plataforma = fields.Str(allow_none=True, validate=validate.Length(max=50))
    canal = fields.Str(allow_none=True, validate=validate.Length(max=50))

    # Distância e Taxa
    distancia_km = fields.Float(allow_none=True)
    taxa_entrega = fields.Float(allow_none=True)
    coords_lat = fields.Float(allow_none=True)
    coords_lon = fields.Float(allow_none=True)

    # Frete (vindo da Order API - Nuvemshop, etc)
    frete_cobrado_cliente = fields.Float(allow_none=True)
    desconto_frete = fields.Float(allow_none=True)
    frete_liquido_cliente = fields.Float(allow_none=True)

    # Timestamps
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates("horario")
    def validate_horario(self, value, **kwargs):
        """Valida formato de horário HH:MM ou intervalo HH:MM - HH:MM"""
        if not value:
            return

        # Padrão para horário simples: HH:MM
        pattern_simples = r"^([01]?\d|2[0-3]):[0-5]\d$"
        # Padrão para intervalo: HH:MM - HH:MM
        pattern_intervalo = r"^([01]?\d|2[0-3]):[0-5]\d\s*-\s*([01]?\d|2[0-3]):[0-5]\d$"

        if not (re.match(pattern_simples, value) or re.match(pattern_intervalo, value)):
            raise ValidationError(
                "Formato de horário inválido. Use HH:MM (ex: 14:30) ou intervalo HH:MM - HH:MM (ex: 08:00 - 10:00)"
            )

        # Se for intervalo, validar que horário final é depois do inicial
        if " - " in value:
            partes = value.split(" - ")
            if len(partes) == 2:
                try:
                    h1, m1 = map(int, partes[0].strip().split(":"))
                    h2, m2 = map(int, partes[1].strip().split(":"))
                    minutos_inicial = h1 * 60 + m1
                    minutos_final = h2 * 60 + m2
                    if minutos_final <= minutos_inicial:
                        raise ValidationError("O horário final deve ser depois do horário inicial")
                except (ValueError, IndexError) as err:
                    raise ValidationError("Formato de intervalo inválido") from err


class PedidoCreateSchema(PedidoSchema):
    """Schema para criação de pedido - campos obrigatórios validados"""

    pass


class PedidoUpdateSchema(Schema):
    """Schema para atualização de pedido - todos campos opcionais"""

    cliente = fields.Str(validate=validate.Length(max=100))
    telefone_cliente = fields.Str(validate=validate.Length(max=20))
    destinatario = fields.Str(validate=validate.Length(max=100))
    tipo_pedido = fields.Str(validate=validate.OneOf(["Entrega", "Retirada"]))
    produto = fields.Str()
    flores_cor = fields.Str(allow_none=True)
    valor = fields.Str(allow_none=True)
    dia_entrega = fields.Date()
    horario = fields.Str()
    cep = fields.Str(allow_none=True)
    rua = fields.Str(allow_none=True)
    numero = fields.Str(allow_none=True)
    tipo_local = fields.Str(allow_none=True, validate=validate.OneOf(["casa", "predio", "comercial"]))
    nome_local = fields.Str(allow_none=True, validate=validate.Length(max=120))
    apto = fields.Str(allow_none=True, validate=validate.Length(max=50))
    bloco = fields.Str(allow_none=True, validate=validate.Length(max=50))
    torre = fields.Str(allow_none=True, validate=validate.Length(max=50))
    andar = fields.Str(allow_none=True, validate=validate.Length(max=50))
    quadra = fields.Str(allow_none=True, validate=validate.Length(max=50))
    lote = fields.Str(allow_none=True, validate=validate.Length(max=50))
    complemento = fields.Str(allow_none=True, validate=validate.Length(max=100))
    bairro = fields.Str(allow_none=True)
    cidade = fields.Str(allow_none=True)
    endereco = fields.Str(allow_none=True)
    obs_entrega = fields.Str(allow_none=True)
    mensagem = fields.Str(allow_none=True)
    pagamento = fields.Str(allow_none=True)
    observacoes = fields.Str(allow_none=True)
    status = fields.Str(
        validate=validate.OneOf(
            [
                "agendado",
                "em_producao",
                "pronto_entrega",
                "em_rota",
                "pronto_retirada",
                "concluido",
                "cancelado",
            ]
        )
    )
    quantidade = fields.Int()
    oculto = fields.Bool()
    impresso = fields.Bool()
    fonte_pedido_id = fields.Int(allow_none=True)
    cliente_id = fields.Int(allow_none=True)
    status_pagamento = fields.Str(allow_none=True)
    plataforma = fields.Str(allow_none=True)
    canal = fields.Str(allow_none=True)
    distancia_km = fields.Float(allow_none=True)
    taxa_entrega = fields.Float(allow_none=True)
    frete_cobrado_cliente = fields.Float(allow_none=True)
    desconto_frete = fields.Float(allow_none=True)
    frete_liquido_cliente = fields.Float(allow_none=True)
    coords_lat = fields.Float(allow_none=True)
    coords_lon = fields.Float(allow_none=True)
    vendedor_id = fields.Int(allow_none=True)

    @validates("horario")
    def validate_horario(self, value, **kwargs):
        """Valida formato de horário HH:MM ou intervalo HH:MM - HH:MM"""
        if not value:
            return

        # Padrão para horário simples: HH:MM
        pattern_simples = r"^([01]?\d|2[0-3]):[0-5]\d$"
        # Padrão para intervalo: HH:MM - HH:MM
        pattern_intervalo = r"^([01]?\d|2[0-3]):[0-5]\d\s*-\s*([01]?\d|2[0-3]):[0-5]\d$"

        if not (re.match(pattern_simples, value) or re.match(pattern_intervalo, value)):
            raise ValidationError(
                "Formato de horário inválido. Use HH:MM (ex: 14:30) ou intervalo HH:MM - HH:MM (ex: 08:00 - 10:00)"
            )

        # Se for intervalo, validar que horário final é depois do inicial
        if " - " in value:
            partes = value.split(" - ")
            if len(partes) == 2:
                try:
                    h1, m1 = map(int, partes[0].strip().split(":"))
                    h2, m2 = map(int, partes[1].strip().split(":"))
                    minutos_inicial = h1 * 60 + m1
                    minutos_final = h2 * 60 + m2
                    if minutos_final <= minutos_inicial:
                        raise ValidationError("O horário final deve ser depois do horário inicial")
                except (ValueError, IndexError) as err:
                    raise ValidationError("Formato de intervalo inválido") from err
