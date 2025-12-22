# -*- coding: utf-8 -*-
"""Schemas de validação/normalização para inputs de pedidos."""
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class PedidoBaseSchema(BaseModel):
    """Campos comuns entre criação e edição."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    cliente: Optional[str] = None
    telefone_cliente: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("telefone_cliente", "telefone"),
    )
    destinatario: Optional[str] = None
    tipo_pedido: Optional[str] = "Entrega"
    fonte_pedido_id: Any = None
    fonte_pedido: Optional[str] = None
    produto: Optional[str] = None
    flores_cor: Optional[str] = None
    valor: Optional[str] = None
    horario: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("horario", "hora_entrega"),
    )
    dia_entrega: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("dia_entrega", "data_entrega"),
    )
    cep: Optional[str] = None
    rua: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    endereco: Optional[str] = None
    obs_entrega: Optional[str] = None
    mensagem: Optional[str] = None
    pagamento: Optional[str] = None
    observacoes: Optional[str] = None
    status_pagamento: Optional[str] = None
    status: Optional[str] = None
    quantidade: Any = 1
    cliente_id: Any = None

    @field_validator(
        "cliente",
        "telefone_cliente",
        "destinatario",
        "tipo_pedido",
        "fonte_pedido",
        "produto",
        "flores_cor",
        "valor",
        "horario",
        "dia_entrega",
        "cep",
        "rua",
        "numero",
        "bairro",
        "cidade",
        "endereco",
        "obs_entrega",
        "mensagem",
        "pagamento",
        "observacoes",
        "status_pagamento",
        "status",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()


class PedidoCreateSchema(PedidoBaseSchema):
    """Schema para criação de pedido."""


class PedidoUpdateSchema(PedidoBaseSchema):
    """Schema para edição de pedido."""
