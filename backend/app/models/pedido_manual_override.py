# -*- coding: utf-8 -*-
"""
Modelo para rastrear campos editados manualmente em pedidos.

Quando um usuário edita manualmente um campo de um pedido importado
(ex: Nuvemshop), o override é registrado aqui para evitar que
sincronizações posteriores sobrescrevam a edição manual.
"""

from app import db
from app.models.pedido import datetime_now_brazil
from app.services.tenant_scope import TenantScoped


class PedidoManualOverride(TenantScoped, db.Model):
    """
    Registra campos de pedidos que foram editados manualmente.

    Cada registro representa um campo específico de um pedido que
    foi alterado manualmente e deve ser preservado mesmo quando
    webhooks de atualização chegarem.
    """

    __tablename__ = "pedido_manual_overrides"

    id = db.Column(db.Integer, primary_key=True)

    # Referência ao pedido
    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=False,
        index=True,
        comment="ID do pedido que teve campo editado manualmente",
    )

    # Nome do campo editado (ex: "dia_entrega", "horario", "endereco")
    field_name = db.Column(
        db.String(50),
        nullable=False,
        index=True,
        comment="Nome do campo que foi editado manualmente",
    )

    # Valor do campo (armazenado como texto para flexibilidade)
    field_value = db.Column(
        db.Text, nullable=True, comment="Valor do campo após edição manual (serializado como texto)"
    )

    # Quem editou (usuário/actor)
    edited_by = db.Column(db.String(100), nullable=True, comment="Usuário que fez a edição manual")

    # Quando foi editado
    edited_at = db.Column(
        db.DateTime,
        default=datetime_now_brazil,
        nullable=False,
        comment="Data/hora da edição manual",
    )

    # Constraint única: apenas um override por campo por pedido
    __table_args__ = (
        db.UniqueConstraint(
            "pedido_id", "field_name", name="uq_pedido_manual_override_pedido_field"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PedidoManualOverride pedido={self.pedido_id} "
            f"field={self.field_name} by={self.edited_by}>"
        )

    @classmethod
    def get_overridden_fields(cls, pedido_id: int) -> set:
        """
        Retorna conjunto de nomes de campos que têm override para um pedido.

        Args:
            pedido_id: ID do pedido

        Returns:
            Set com nomes dos campos com override (ex: {"dia_entrega", "horario"})
        """
        overrides = cls.query.filter_by(pedido_id=pedido_id).all()
        return {o.field_name for o in overrides}

    @classmethod
    def has_override(cls, pedido_id: int, field_name: str) -> bool:
        """
        Verifica se um campo específico tem override manual.

        Args:
            pedido_id: ID do pedido
            field_name: Nome do campo a verificar

        Returns:
            True se o campo tem override manual
        """
        return cls.query.filter_by(pedido_id=pedido_id, field_name=field_name).first() is not None

    @classmethod
    def set_override(
        cls,
        pedido_id: int,
        field_name: str,
        field_value: str,
        edited_by: str = None,
        store_ref_id: int | None = None,
    ) -> "PedidoManualOverride":
        """
        Cria ou atualiza um override manual para um campo.

        Args:
            pedido_id: ID do pedido
            field_name: Nome do campo
            field_value: Valor do campo (será convertido para string)
            edited_by: Usuário que fez a edição

        Returns:
            Instância do override criado/atualizado
        """
        override = cls.query.filter_by(pedido_id=pedido_id, field_name=field_name).first()

        if override:
            override.field_value = str(field_value) if field_value is not None else None
            override.edited_by = edited_by
            override.edited_at = datetime_now_brazil()
        else:
            if store_ref_id is None:
                from app.models.pedido import Pedido

                pedido = (
                    Pedido.query.execution_options(include_all_tenants=True)
                    .filter(Pedido.id == pedido_id)
                    .first()
                )
                store_ref_id = pedido.store_ref_id if pedido else None
            override = cls(
                pedido_id=pedido_id,
                store_ref_id=store_ref_id,
                field_name=field_name,
                field_value=str(field_value) if field_value is not None else None,
                edited_by=edited_by,
                edited_at=datetime_now_brazil(),
            )
            db.session.add(override)

        return override

    @classmethod
    def remove_override(cls, pedido_id: int, field_name: str) -> bool:
        """
        Remove um override manual de um campo.

        Args:
            pedido_id: ID do pedido
            field_name: Nome do campo

        Returns:
            True se o override existia e foi removido
        """
        override = cls.query.filter_by(pedido_id=pedido_id, field_name=field_name).first()

        if override:
            db.session.delete(override)
            return True
        return False
