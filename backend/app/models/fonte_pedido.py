# -*- coding: utf-8 -*-
"""
Model de Fonte de Pedido - Sistema de Gestão de Fontes
Permite controlar de onde vem cada pedido (Ifood, Site, WhatsApp, etc)
"""
from datetime import datetime

from app import db


class FontePedido(db.Model):
    """
    Model de Fonte de Pedido
    Representa a origem/fonte de um pedido (Ifood, Site, WhatsApp, etc)
    """

    __tablename__ = "fontes_pedido"

    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f"<FontePedido #{self.id} - {self.nome} ({status})>"

    def to_dict(self):
        """Converte a fonte para dicionário (para API JSON)"""
        return {
            "id": self.id,
            "nome": self.nome,
            "ativo": self.ativo,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }

    @staticmethod
    def get_ativas():
        """Retorna todas as fontes ativas"""
        return FontePedido.query.filter_by(ativo=True).order_by(FontePedido.nome).all()

    @staticmethod
    def get_all():
        """Retorna todas as fontes (ativas e inativas)"""
        return FontePedido.query.order_by(FontePedido.nome).all()
