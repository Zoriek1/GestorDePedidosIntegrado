# -*- coding: utf-8 -*-
"""
Repository de Clientes - Isolamento de acesso ao banco para Clientes
"""
import re
from typing import List, Optional

from app import db
from app.models import Cliente
from app.repositories.base_repository import BaseRepository


class ClienteRepository(BaseRepository):
    """Repository para operações com Clientes"""

    def __init__(self):
        super().__init__(Cliente)

    def buscar_por_telefone(self, telefone: str) -> Optional[Cliente]:
        """
        Busca cliente por telefone (remove formatação)

        Args:
            telefone: Telefone a buscar (com ou sem formatação)

        Returns:
            Cliente ou None
        """
        # Remover formatação do telefone
        telefone_limpo = re.sub(r'[^\d]', '', telefone)

        # Buscar por telefone exato ou limpo
        return self.model.query.filter(
            db.or_(
                Cliente.telefone == telefone,
                Cliente.telefone == telefone_limpo
            )
        ).first()

    def buscar_por_nome(self, nome: str, limit: int = 10) -> List[Cliente]:
        """Busca clientes por nome (autocomplete)"""
        return self.model.query.filter(
            Cliente.nome.like(f"%{nome}%")
        ).limit(limit).all()

    def buscar_com_filtros(self, search: Optional[str] = None) -> List[Cliente]:
        """
        Busca clientes com filtros

        Args:
            search: Busca textual (nome, telefone, email)

        Returns:
            Lista de clientes
        """
        query = self.model.query

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Cliente.nome.like(search_term),
                    Cliente.telefone.like(search_term),
                    Cliente.email.like(search_term)
                )
            )

        return query.order_by(Cliente.nome.asc()).all()

    def criar_ou_buscar(self, nome: str, telefone: str, **kwargs) -> Cliente:
        """
        Cria cliente ou retorna existente se telefone já existe

        Args:
            nome: Nome do cliente
            telefone: Telefone do cliente
            **kwargs: Outros campos opcionais

        Returns:
            Cliente (novo ou existente)
        """
        # Verificar se já existe
        existente = self.buscar_por_telefone(telefone)
        if existente:
            return existente

        # Criar novo
        return self.create(nome=nome, telefone=telefone, **kwargs)

    def obter_estatisticas(self) -> dict:
        """Retorna estatísticas dos clientes"""
        from datetime import datetime

        from sqlalchemy import func

        from app.models.pedido import Pedido

        total_clientes = self.count()

        # Clientes novos este mês
        inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        novos_mes = self.model.query.filter(Cliente.created_at >= inicio_mes).count()

        # Cliente com mais pedidos
        cliente_mais_pedidos = db.session.query(
            Cliente,
            func.count(Pedido.id).label('total')
        ).outerjoin(Pedido, Cliente.id == Pedido.cliente_id).group_by(Cliente.id).order_by(db.desc('total')).first()

        stats = {
            'total_clientes': total_clientes,
            'novos_este_mes': novos_mes,
            'cliente_mais_pedidos': None
        }

        if cliente_mais_pedidos:
            cliente, total = cliente_mais_pedidos
            stats['cliente_mais_pedidos'] = {
                'id': cliente.id,
                'nome': cliente.nome,
                'telefone': cliente.telefone,
                'total_pedidos': total,
                'ltv': cliente.calcular_ltv()
            }

        return stats

