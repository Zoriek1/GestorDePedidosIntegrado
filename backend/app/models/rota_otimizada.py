# -*- coding: utf-8 -*-
"""
Modelo de dados para Rotas Otimizadas
Armazena rotas calculadas com múltiplos pedidos
"""
import json
from datetime import datetime

from app import db
from app.services.tenant_scope import TenantScoped


class RotaOtimizada(TenantScoped, db.Model):
    """Modelo de Rota Otimizada com sequência de pedidos"""

    __tablename__ = "rotas_otimizadas"

    # Identificador único
    id = db.Column(db.Integer, primary_key=True)

    # Informações da rota
    nome = db.Column(db.String(200), nullable=True, comment="Nome/descrição da rota")
    distancia_total_km = db.Column(db.Float, nullable=False, comment="Distância total em km")
    duracao_total_min = db.Column(db.Float, nullable=False, comment="Duração total em minutos")

    # Sequência de pedidos (JSON array de IDs)
    sequencia_pedidos = db.Column(
        db.Text,
        nullable=False,
        comment="JSON array com IDs dos pedidos na ordem otimizada",
    )

    # Coordenadas da origem (floricultura)
    origem_lat = db.Column(db.Float, nullable=False, comment="Latitude da origem")
    origem_lon = db.Column(db.Float, nullable=False, comment="Longitude da origem")

    # Coordenadas dos waypoints (JSON array de [lat, lon])
    waypoints_coords = db.Column(
        db.Text,
        nullable=True,
        comment="JSON array com coordenadas dos waypoints na ordem otimizada",
    )

    # Metadados
    num_pedidos = db.Column(db.Integer, nullable=False, comment="Número de pedidos na rota")
    metodo_otimizacao = db.Column(
        db.String(50),
        nullable=True,
        comment="Método usado (exata, nearest_neighbor, etc)",
    )

    # Status
    ativa = db.Column(db.Boolean, default=True, comment="Se True, rota está ativa")

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="Data de criação")
    updated_at = db.Column(
        db.DateTime,
        nullable=True,
        onupdate=datetime.utcnow,
        comment="Última atualização",
    )

    def __repr__(self):
        return (
            f"<RotaOtimizada #{self.id} - {self.num_pedidos} pedidos, {self.distancia_total_km} km>"
        )

    def get_sequencia_pedidos(self):
        """Retorna lista de IDs de pedidos"""
        try:
            return json.loads(self.sequencia_pedidos)
        except (ValueError, TypeError):
            return []

    def set_sequencia_pedidos(self, lista_ids):
        """Define lista de IDs de pedidos"""
        self.sequencia_pedidos = json.dumps(lista_ids)

    def get_waypoints_coords(self):
        """Retorna lista de coordenadas dos waypoints"""
        try:
            return json.loads(self.waypoints_coords) if self.waypoints_coords else []
        except (ValueError, TypeError):
            return []

    def set_waypoints_coords(self, lista_coords):
        """Define lista de coordenadas dos waypoints"""
        self.waypoints_coords = json.dumps(lista_coords)

    def to_dict(self):
        """Converte a rota para dicionário (para API JSON)"""
        return {
            "id": self.id,
            "nome": self.nome or "",
            "distancia_total_km": self.distancia_total_km,
            "duracao_total_min": self.duracao_total_min,
            "sequencia_pedidos": self.get_sequencia_pedidos(),
            "origem_lat": self.origem_lat,
            "origem_lon": self.origem_lon,
            "waypoints_coords": self.get_waypoints_coords(),
            "num_pedidos": self.num_pedidos,
            "metodo_otimizacao": self.metodo_otimizacao or "",
            "ativa": self.ativa,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }

    @staticmethod
    def get_rotas_ativas():
        """Retorna todas as rotas ativas"""
        return (
            RotaOtimizada.query.filter_by(ativa=True)
            .order_by(RotaOtimizada.created_at.desc())
            .all()
        )

    @staticmethod
    def get_ultima_rota():
        """Retorna a última rota criada"""
        return RotaOtimizada.query.order_by(RotaOtimizada.created_at.desc()).first()
