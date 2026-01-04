# -*- coding: utf-8 -*-
"""
Repository de Pedidos - Isolamento de acesso ao banco para Pedidos
"""
from datetime import date, datetime
from typing import Dict, List, Optional

from app import db
from app.models import Pedido
from app.repositories.base_repository import BaseRepository


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

    def buscar_por_data_criacao(self, data_inicio: date, data_fim_exclusivo: date,
                               excluir_ocultos: bool = False,  # Ocultos ENTRAM por padrão
                               excluir_deletados: bool = True) -> List[Pedido]:
        """
        Busca pedidos por intervalo de datas de criação (created_at)

        Args:
            data_inicio: Data inicial (inclusiva, 00:00:00)
            data_fim_exclusivo: Data final (exclusiva, 00:00:00 do dia seguinte)
            excluir_ocultos: Se False, inclui pedidos ocultos (padrão para vendas)
            excluir_deletados: Se True, exclui soft-deleted

        Returns:
            Lista de pedidos (excluindo cancelados automaticamente)
        """
        inicio_datetime = datetime.combine(data_inicio, datetime.min.time())
        fim_datetime = datetime.combine(data_fim_exclusivo, datetime.min.time())

        query = self.model.query.filter(
            Pedido.created_at >= inicio_datetime,
            Pedido.created_at < fim_datetime,  # Exclusivo
            Pedido.status != 'cancelado'  # Excluir cancelados
        )
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        if excluir_ocultos:
            query = query.filter_by(oculto=False)

        return query.order_by(Pedido.created_at.desc()).all()

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
                          ordenar_por: str = 'dia_entrega',
                          filtrar_por_criacao: bool = False) -> List[Pedido]:
        """
        Busca pedidos com múltiplos filtros

        Args:
            status: Filtrar por status
            data_inicio: Data inicial
            data_fim: Data final (ou data_fim_exclusivo se filtrar_por_criacao=True)
            search: Busca textual (cliente, destinatário, produto, endereço)
            excluir_ocultos: Se True, exclui pedidos ocultos (IGNORADO quando filtrar_por_criacao=True)
            excluir_deletados: Se True, exclui pedidos soft-deleted (P0.3)
            ordenar_por: Campo para ordenação ('dia_entrega' ou 'created_at')
            filtrar_por_criacao: Se True, filtra por created_at ao invés de dia_entrega.
                                Quando True, FORÇA excluir_ocultos=False (vendas incluem todos os pedidos)

        Returns:
            Lista de pedidos
        """
        query = self.model.query

        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))

        # REGRA CRÍTICA: Quando filtrar_por_criacao=True, ocultos SEMPRE ENTRAM (são vendas válidas)
        # O campo 'oculto' é usado apenas para limpeza visual na tela de pedidos.
        # Na funcionalidade de vendas (filtrar_por_criacao=True), TODOS os pedidos do mês devem aparecer,
        # independentemente do campo oculto, pois são vendas válidas que devem contar nas estatísticas.
        #
        # IMPORTANTE: Forçar excluir_ocultos=False quando filtrar_por_criacao=True, ignorando o parâmetro recebido.
        if filtrar_por_criacao:
            # Forçar inclusão de ocultos - vendas devem mostrar todos os pedidos do mês
            excluir_ocultos = False
            # Não aplicar filtro de ocultos - incluir todos (ocultos e não ocultos)
        elif excluir_ocultos:
            # Só aplicar filtro de ocultos se NÃO estiver filtrando por criação E excluir_ocultos=True
            query = query.filter_by(oculto=False)

        # Sempre excluir cancelados quando filtrar_por_criacao=True
        # Normalizar comparação para evitar problemas com variações de case/espaços
        if filtrar_por_criacao:
            from sqlalchemy import func
            query = query.filter(func.lower(func.trim(Pedido.status)) != 'cancelado')
        elif status:
            query = query.filter_by(status=status)

        if filtrar_por_criacao and data_inicio and data_fim:
            # Filtrar por created_at com intervalo exclusivo [início, fim_exclusivo)
            inicio_datetime = datetime.combine(data_inicio, datetime.min.time())
            # data_fim já vem como fim_exclusivo (dia seguinte 00:00:00)
            fim_datetime = datetime.combine(data_fim, datetime.min.time())
            query = query.filter(
                Pedido.created_at >= inicio_datetime,
                Pedido.created_at < fim_datetime  # Exclusivo
            )
        else:
            # Filtro padrão por dia_entrega
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
        if filtrar_por_criacao:
            query = query.order_by(Pedido.created_at.desc())
        elif ordenar_por == 'dia_entrega':
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
            Pedido.oculto is False,
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
            Pedido.oculto is False,
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
            Pedido.oculto is False
        ).all()

        count = len(old_pedidos)
        for pedido in old_pedidos:
            self.update(pedido, oculto=True, updated_at=datetime.utcnow())

        return count

    def ocultar_concluidos(self) -> int:
        """Oculta todos os pedidos concluídos (independente da data)"""
        concluidos = self.model.query.filter(
            Pedido.status == 'concluido',
            Pedido.oculto is False,
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

