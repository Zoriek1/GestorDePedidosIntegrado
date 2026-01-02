# -*- coding: utf-8 -*-
"""
Repository de Pedidos - Isolamento de acesso ao banco para Pedidos
"""
from typing import List, Optional, Dict
from datetime import datetime, date
from app.repositories.base_repository import BaseRepository
from app.models import Pedido
from app import db


class PedidoRepository(BaseRepository):
    """Repository para operações com Pedidos"""
    
    def __init__(self):
        super().__init__(Pedido)
    
    def buscar_por_status(self, status: str, excluir_ocultos: bool = True, excluir_deletados: bool = True) -> List[Pedido]:
        """Busca pedidos por status"""
        query = self.model.query.filter_by(status=status)
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        if excluir_ocultos:
            query = query.filter_by(oculto=False)
        return query.all()
    
    def buscar_por_data(self, data_inicio: date, data_fim: date, excluir_ocultos: bool = True, excluir_deletados: bool = True) -> List[Pedido]:
        """Busca pedidos por intervalo de datas"""
        query = self.model.query.filter(
            Pedido.dia_entrega >= data_inicio,
            Pedido.dia_entrega <= data_fim
        )
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        if excluir_ocultos:
            query = query.filter_by(oculto=False)
        return query.all()
    
    def buscar_por_cliente(self, telefone: str, excluir_ocultos: bool = True, excluir_deletados: bool = True) -> List[Pedido]:
        """Busca pedidos por telefone do cliente"""
        query = self.model.query.filter_by(telefone_cliente=telefone)
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        if excluir_ocultos:
            query = query.filter_by(oculto=False)
        return query.all()
    
    def buscar_com_filtros(self, status: Optional[str] = None, 
                          data_inicio: Optional[date] = None,
                          data_fim: Optional[date] = None,
                          search: Optional[str] = None,
                          excluir_ocultos: bool = True,
                          excluir_deletados: bool = True,
                          ordenar_por: str = 'dia_entrega') -> List[Pedido]:
        """
        Busca pedidos com múltiplos filtros
        
        Args:
            status: Filtrar por status
            data_inicio: Data inicial
            data_fim: Data final
            search: Busca textual (cliente, destinatário, produto, endereço)
            excluir_ocultos: Se True, exclui pedidos ocultos
            excluir_deletados: Se True, exclui pedidos soft-deleted (P0.3)
            ordenar_por: Campo para ordenação ('dia_entrega' ou 'created_at')
        
        Returns:
            Lista de pedidos
        """
        query = self.model.query
        
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        
        if excluir_ocultos:
            query = query.filter_by(oculto=False)
        
        if status:
            query = query.filter_by(status=status)
        
        if data_inicio:
            query = query.filter(Pedido.dia_entrega >= data_inicio)
        
        if data_fim:
            query = query.filter(Pedido.dia_entrega <= data_fim)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Pedido.cliente.like(search_term),
                    Pedido.destinatario.like(search_term),
                    Pedido.produto.like(search_term),
                    Pedido.endereco.like(search_term)
                )
            )
        
        # Ordenação
        if ordenar_por == 'dia_entrega':
            query = query.order_by(Pedido.dia_entrega.asc())
        elif ordenar_por == 'created_at':
            query = query.order_by(Pedido.created_at.desc())
        
        return query.all()
    
    def atualizar_status(self, pedido_id: int, novo_status: str) -> Optional[Pedido]:
        """Atualiza status de um pedido"""
        pedido = self.get_by_id(pedido_id)
        if pedido:
            return self.update(pedido, status=novo_status, updated_at=datetime.utcnow())
        return None
    
    def buscar_atrasados(self) -> List[Pedido]:
        """Busca pedidos atrasados (excluindo ocultos, concluídos e deletados)"""
        pedidos = self.model.query.filter(
            Pedido.status != 'concluido',
            Pedido.oculto == False,
            Pedido.deleted_at.is_(None)
        ).all()
        
        # Filtrar por lógica de atraso
        return [p for p in pedidos if p.is_overdue()]
    
    def buscar_por_fonte(self, fonte_id: int, excluir_ocultos: bool = True, excluir_deletados: bool = True) -> List[Pedido]:
        """Busca pedidos por fonte"""
        query = self.model.query.filter_by(fonte_pedido_id=fonte_id)
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        if excluir_ocultos:
            query = query.filter_by(oculto=False)
        return query.all()
    
    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas dos pedidos (excluindo deletados)"""
        base_query = self.model.query.filter(
            Pedido.oculto == False,
            Pedido.deleted_at.is_(None)
        )
        
        return {
            'total': base_query.count(),
            'agendado': base_query.filter_by(status='agendado').count(),
            'em_producao': base_query.filter_by(status='em_producao').count(),
            'pronto_entrega': base_query.filter_by(status='pronto_entrega').count(),
            'em_rota': base_query.filter_by(status='em_rota').count(),
            'pronto_retirada': base_query.filter_by(status='pronto_retirada').count(),
            'concluido': base_query.filter_by(status='concluido').count(),
            'atrasados': len(self.buscar_atrasados())
        }
    
    def arquivar_antigos(self, dias: int = 1) -> int:
        """Arquiva (oculta) pedidos concluídos há mais de X dias"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=dias)
        old_pedidos = self.model.query.filter(
            Pedido.status == 'concluido',
            Pedido.updated_at < cutoff_date,
            Pedido.oculto == False
        ).all()
        
        count = len(old_pedidos)
        for pedido in old_pedidos:
            self.update(pedido, oculto=True, updated_at=datetime.utcnow())
        
        return count
    
    def ocultar_concluidos(self) -> int:
        """Oculta todos os pedidos concluídos (independente da data)"""
        concluidos = self.model.query.filter(
            Pedido.status == 'concluido',
            Pedido.oculto == False,
            Pedido.deleted_at.is_(None)  # Não ocultar pedidos já deletados
        ).all()
        
        count = len(concluidos)
        for pedido in concluidos:
            self.update(pedido, oculto=True, updated_at=datetime.utcnow())
        
        return count
    
    def buscar_deletados(self) -> List[Pedido]:
        """Busca pedidos soft-deleted (P0.3)"""
        return self.model.query.filter(
            Pedido.deleted_at.isnot(None)
        ).order_by(Pedido.deleted_at.desc()).all()
    
    def soft_delete_pedido(self, pedido_id: int, actor: str = None) -> Optional[Pedido]:
        """
        Soft delete de pedido (P0.3)
        
        Args:
            pedido_id: ID do pedido
            actor: Quem executou a ação (para auditoria)
        
        Returns:
            Pedido atualizado ou None se não encontrado
        """
        pedido = self.get_by_id(pedido_id)
        if not pedido:
            return None
        
        if pedido.is_deleted:
            # Já está deletado
            return pedido
        
        # Soft delete
        pedido.soft_delete()
        db.session.commit()
        
        # Registrar em auditoria
        try:
            from app.utils.audit_logger import log_action
            log_action(
                action='DELETE',
                entity_type='pedido',
                entity_id=pedido_id,
                actor=actor or 'system',
                metadata={'cliente': pedido.cliente, 'destinatario': pedido.destinatario}
            )
        except Exception as e:
            print(f"[AVISO] Erro ao registrar auditoria: {e}")
        
        return pedido
    
    def restore_pedido(self, pedido_id: int, actor: str = None) -> Optional[Pedido]:
        """
        Restaura pedido soft-deleted (P0.3)
        
        Args:
            pedido_id: ID do pedido
            actor: Quem executou a ação (para auditoria)
        
        Returns:
            Pedido restaurado ou None se não encontrado
        """
        pedido = self.get_by_id(pedido_id)
        if not pedido:
            return None
        
        if not pedido.is_deleted:
            # Não está deletado
            return pedido
        
        # Restaurar
        pedido.restore()
        db.session.commit()
        
        # Registrar em auditoria
        try:
            from app.utils.audit_logger import log_action
            log_action(
                action='RESTORE',
                entity_type='pedido',
                entity_id=pedido_id,
                actor=actor or 'system',
                metadata={'cliente': pedido.cliente, 'destinatario': pedido.destinatario}
            )
        except Exception as e:
            print(f"[AVISO] Erro ao registrar auditoria: {e}")
        
        return pedido

