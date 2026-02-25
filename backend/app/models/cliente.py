# -*- coding: utf-8 -*-
"""
Model de Cliente - Sistema de Gestão de Clientes
Permite gerenciar clientes, calcular LTV e evitar duplicação
"""
import re
from datetime import datetime

from app import db


class Cliente(db.Model):
    """
    Model de Cliente com relacionamentos para Pedidos e Endereços
    """

    __tablename__ = "clientes"

    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    telefone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relacionamentos (lazy='dynamic' permite queries)
    enderecos = db.relationship(
        "EnderecoCliente",
        backref="cliente",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    pedidos = db.relationship(
        "Pedido",
        backref="cliente_rel",
        lazy="dynamic",
        foreign_keys="Pedido.cliente_id",
    )

    def __repr__(self):
        return f"<Cliente #{self.id} - {self.nome} ({self.telefone})>"

    def calcular_ltv(self):
        """
        Calcula Lifetime Value (LTV) - Total gasto pelo cliente

        Returns:
            float: Valor total gasto em R$
        """
        total = 0.0

        for pedido in self.pedidos:
            if pedido.valor:
                try:
                    # Parse valor de qualquer formato
                    valor_str = str(pedido.valor).strip().replace("R$", "").strip()
                    if not valor_str:
                        continue

                    # Detectar formato brasileiro (tem vírgula)
                    if "," in valor_str:
                        # Formato BR: "65,00" ou "1.234,56"
                        valor_limpo = valor_str.replace(".", "").replace(",", ".")
                    elif "." in valor_str:
                        # Formato US: "10.00" ou número simples
                        dot_count = valor_str.count(".")
                        if dot_count == 1:
                            # Um ponto = decimal: "10.00"
                            valor_limpo = valor_str
                        else:
                            # Múltiplos pontos = separadores de milhar
                            valor_limpo = valor_str.replace(".", "")
                    else:
                        # String simples: "10"
                        valor_limpo = valor_str

                    total += float(valor_limpo)
                except (ValueError, AttributeError, TypeError):
                    # Se não conseguir converter, pula
                    continue

        return round(total, 2)

    def get_total_pedidos(self):
        """
        Retorna total de pedidos do cliente

        Returns:
            int: Número de pedidos
        """
        return self.pedidos.count()

    def get_endereco_principal(self):
        """
        Retorna o endereço marcado como principal ou o primeiro

        Returns:
            EnderecoCliente ou None
        """
        endereco_principal = self.enderecos.filter_by(principal=True).first()
        if endereco_principal:
            return endereco_principal
        return self.enderecos.first()

    def get_ultimo_pedido(self):
        """
        Retorna o pedido mais recente do cliente

        Returns:
            Pedido ou None
        """
        return self.pedidos.order_by(db.desc("created_at")).first()

    def to_dict(self, include_stats=False):
        """
        Converte cliente para dicionário (para API JSON)

        Args:
            include_stats: Se True, inclui estatísticas (LTV, total de pedidos)

        Returns:
            dict: Dados do cliente
        """
        data = {
            "id": self.id,
            "nome": self.nome,
            "telefone": self.telefone,
            "email": self.email or "",
            "observacoes": self.observacoes or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_stats:
            ultimo_pedido = self.get_ultimo_pedido()
            data.update(
                {
                    "total_pedidos": self.get_total_pedidos(),
                    "ltv": self.calcular_ltv(),
                    "ultimo_pedido": ultimo_pedido.created_at.isoformat()
                    if ultimo_pedido
                    else None,
                }
            )

        return data

    def to_dict_autocomplete(self):
        """
        Versão compacta para autocomplete

        Returns:
            dict: Dados mínimos para autocomplete
        """
        return {
            "id": self.id,
            "nome": self.nome,
            "telefone": self.telefone,
            "total_pedidos": self.get_total_pedidos(),
        }

    @staticmethod
    def buscar_por_telefone(telefone):
        """
        Busca cliente por telefone (remove formatação)

        Args:
            telefone: Telefone a buscar (com ou sem formatação)

        Returns:
            Cliente ou None
        """
        # Remover formatação do telefone
        telefone_limpo = re.sub(r"[^\d]", "", telefone)

        # Buscar por telefone exato ou limpo
        return Cliente.query.filter(
            db.or_(Cliente.telefone == telefone, Cliente.telefone == telefone_limpo)
        ).first()

    @staticmethod
    def get_statistics():
        """
        Retorna estatísticas gerais dos clientes

        Returns:
            dict: Estatísticas
        """
        from datetime import datetime

        from sqlalchemy import func

        total_clientes = Cliente.query.count()

        # Clientes novos este mês
        inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        novos_mes = Cliente.query.filter(Cliente.created_at >= inicio_mes).count()

        # Cliente com mais pedidos
        # Usar subquery para contar pedidos
        from app.models.pedido import Pedido

        cliente_mais_pedidos = (
            db.session.query(Cliente, func.count(Pedido.id).label("total"))
            .outerjoin(Pedido, Cliente.id == Pedido.cliente_id)
            .group_by(Cliente.id)
            .order_by(db.desc("total"))
            .first()
        )

        stats = {
            "total_clientes": total_clientes,
            "novos_este_mes": novos_mes,
            "cliente_mais_pedidos": None,
        }

        if cliente_mais_pedidos:
            cliente, total = cliente_mais_pedidos
            stats["cliente_mais_pedidos"] = {
                "id": cliente.id,
                "nome": cliente.nome,
                "telefone": cliente.telefone,
                "total_pedidos": total,
                "ltv": cliente.calcular_ltv(),
            }

        return stats
