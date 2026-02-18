# -*- coding: utf-8 -*-
"""
Modelo de Outbox para Meta Conversions API
Garante entrega de eventos Purchase para Meta com retry e idempotência
"""

from app import db
from app.models.pedido import datetime_now_brazil


class MetaCapiOutbox(db.Model):
    """
    Outbox para eventos Meta Conversions API
    Armazena eventos Purchase pendentes/enviados/falhados
    """

    __tablename__ = "meta_capi_outbox"

    # Identificador único
    id = db.Column(db.Integer, primary_key=True)

    # Relacionamento com pedido
    order_id = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=False,
        index=True,
        comment="ID do pedido",
    )

    # Identificação do evento
    event_id = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="ID único do evento (formato: order_<id>)",
    )

    # Timestamp do evento
    event_time = db.Column(
        db.DateTime,
        nullable=False,
        comment="Timestamp real da compra (paid_at ou updated_at quando status mudou)",
    )

    # Payload serializado (SEM PII em claro, apenas hashes)
    payload_json = db.Column(
        db.Text,
        nullable=False,
        comment="Payload completo serializado (sem telefone/nome em claro)",
    )

    # Status do envio
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Status: pending|sent|failed",
    )

    # Controle de tentativas
    attempts = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        comment="Número de tentativas de envio",
    )

    # Informações de erro
    last_error = db.Column(
        db.Text,
        nullable=True,
        comment="Último erro (inclui código HTTP quando disponível)",
    )

    error_type = db.Column(
        db.String(20),
        nullable=True,
        index=True,
        comment="Tipo de erro: retryable|permanent",
    )

    # Timestamp de envio
    sent_at = db.Column(
        db.DateTime,
        nullable=True,
        comment="Data/hora em que foi enviado com sucesso",
    )

    # Timestamps
    created_at = db.Column(
        db.DateTime,
        default=datetime_now_brazil,
        nullable=False,
        comment="Data de criação",
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=True,
        onupdate=datetime_now_brazil,
        comment="Última atualização",
    )

    # Relacionamento
    pedido = db.relationship("Pedido", backref="meta_capi_outbox_entries", foreign_keys=[order_id])

    def __repr__(self):
        return f"<MetaCapiOutbox #{self.id} - order_{self.order_id} ({self.status})>"

    def to_dict(self):
        """Converte para dicionário (para API JSON)"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "event_id": self.event_id,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "status": self.status,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "error_type": self.error_type,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
