# -*- coding: utf-8 -*-
"""
Sugestão de correção de endereço feita pelo CLIENTE na página pública de acompanhamento.

Rota pública (token assinado) só GRAVA a sugestão — nunca altera o pedido. A equipe
revisa no painel e decide aplicar (copia o texto para ``pedido.endereco``) ou ignorar.
Mantém rastreabilidade de quem pediu o quê e quando.
"""

from app import db
from app.models.pedido import datetime_now_brazil
from app.services.tenant_scope import TenantScoped

STATUS_PENDENTE = "pendente"
STATUS_APLICADA = "aplicada"
STATUS_IGNORADA = "ignorada"


class PedidoSugestaoEndereco(TenantScoped, db.Model):
    __tablename__ = "pedido_sugestoes_endereco"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(
        db.Integer, db.ForeignKey("pedidos.id"), index=True, nullable=False
    )
    # Texto livre sugerido pelo cliente (endereço corrigido / instruções).
    texto = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.String(20),
        nullable=False,
        default=STATUS_PENDENTE,
        server_default=STATUS_PENDENTE,
        index=True,
        comment="pendente | aplicada | ignorada",
    )
    # Snapshot do endereço no momento da sugestão (contexto para a revisão).
    endereco_anterior = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime_now_brazil, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(
        db.String(100), nullable=True, comment="Nome/identificador do atendente que revisou"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pedido_id": self.pedido_id,
            "texto": self.texto,
            "status": self.status,
            "endereco_anterior": self.endereco_anterior,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
        }

    def __repr__(self) -> str:
        return (
            f"<PedidoSugestaoEndereco id={self.id} pedido_id={self.pedido_id} "
            f"status={self.status}>"
        )
