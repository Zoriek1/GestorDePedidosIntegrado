# -*- coding: utf-8 -*-
"""
Repository de Pedidos - Isolamento de acesso ao banco para Pedidos
"""
import re
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app import db
from app.models import Pedido
from app.models.pedido import datetime_now_brazil
from app.repositories.base_repository import BaseRepository


class PedidoRepository(BaseRepository):
    """Repository para operações com Pedidos"""

    def __init__(self):
        super().__init__(Pedido)

    def buscar_por_status(
        self, status: str, excluir_ocultos: bool = True, excluir_deletados: bool = True
    ) -> List[Pedido]:
        """Busca pedidos por status"""
        query = self.model.query.filter_by(status=status)
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        if excluir_ocultos:
            query = query.filter_by(oculto=False)
        return query.all()

    def buscar_por_data(
        self,
        data_inicio: date,
        data_fim: date,
        excluir_ocultos: bool = True,
        excluir_deletados: bool = True,
    ) -> List[Pedido]:
        """Busca pedidos por intervalo de datas"""
        query = self.model.query.filter(
            Pedido.dia_entrega >= data_inicio, Pedido.dia_entrega <= data_fim
        )
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        if excluir_ocultos:
            query = query.filter_by(oculto=False)
        return query.all()

    def buscar_por_data_criacao(
        self,
        data_inicio: date,
        data_fim_exclusivo: date,
        excluir_ocultos: bool = False,  # Ocultos ENTRAM por padrão
        excluir_deletados: bool = True,
    ) -> List[Pedido]:
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
            Pedido.status != "cancelado",  # Excluir cancelados
        )
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        if excluir_ocultos:
            query = query.filter_by(oculto=False)

        return query.order_by(Pedido.created_at.desc()).all()

    def buscar_por_cliente(
        self,
        telefone: str,
        excluir_ocultos: bool = True,
        excluir_deletados: bool = True,
    ) -> List[Pedido]:
        """Busca pedidos por telefone do cliente"""
        query = self.model.query.filter_by(telefone_cliente=telefone)
        if excluir_deletados:
            query = query.filter(Pedido.deleted_at.is_(None))
        if excluir_ocultos:
            query = query.filter_by(oculto=False)
        return query.all()

    def buscar_com_filtros(
        self,
        status: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        search: Optional[str] = None,
        excluir_ocultos: bool = True,
        excluir_deletados: bool = True,
        ordenar_por: str = "dia_entrega",
        ordenar_direcao: str = "asc",
        filtrar_por_criacao: bool = False,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Tuple[List[Pedido], int]:
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

            query = query.filter(func.lower(func.trim(Pedido.status)) != "cancelado")
        elif status:
            # Suportar múltiplos status separados por vírgula
            if "," in status:
                status_list = [s.strip() for s in status.split(",") if s.strip()]
                if status_list:
                    query = query.filter(Pedido.status.in_(status_list))
            else:
                query = query.filter_by(status=status)
        else:
            # "Todos" (sem filtro de status): pedidos em rota ficam apenas
            # na aba "Em Rota" e na tela de Rotas. Evita poluir a lista geral.
            query = query.filter(Pedido.status != "em_rota")

        if filtrar_por_criacao and data_inicio and data_fim:
            # Filtrar por created_at com intervalo exclusivo [início, fim_exclusivo)
            inicio_datetime = datetime.combine(data_inicio, datetime.min.time())
            # data_fim já vem como fim_exclusivo (dia seguinte 00:00:00)
            fim_datetime = datetime.combine(data_fim, datetime.min.time())
            query = query.filter(
                Pedido.created_at >= inicio_datetime,
                Pedido.created_at < fim_datetime,  # Exclusivo
            )
        else:
            # Filtro padrão por dia_entrega
            if data_inicio:
                query = query.filter(Pedido.dia_entrega >= data_inicio)

            if data_fim:
                query = query.filter(Pedido.dia_entrega <= data_fim)

        if search:
            # BUS-01: busca multi-campo, insensível a caixa/acento, somando id e telefone.
            # Postgres usa f_unaccent + ILIKE (índices trigram); SQLite (testes) cai para
            # lower()/LIKE sem unaccent/trigram. Guarda por dialeto.
            from sqlalchemy import func

            search = search.strip()
            digits = re.sub(r"\D", "", search)
            is_postgres = db.engine.dialect.name == "postgresql"

            text_cols = (Pedido.cliente, Pedido.destinatario, Pedido.produto, Pedido.endereco)
            conds = []
            if is_postgres:
                unaccent_term = func.f_unaccent(f"%{search}%")
                conds.extend(func.f_unaccent(col).ilike(unaccent_term) for col in text_cols)
            else:
                lowered = f"%{search.lower()}%"
                conds.extend(func.lower(col).like(lowered) for col in text_cols)

            # Número visível por empresa; id só é fallback para legado sem número.
            if search.isdigit():
                number = int(search)
                conds.append(Pedido.numero_pedido == number)
                conds.append(
                    db.and_(Pedido.numero_pedido.is_(None), Pedido.id == number)
                )

            # Telefone ignorando máscara.
            if digits:
                if is_postgres:
                    conds.append(
                        db.text("telefone_digits LIKE :tel").bindparams(tel=f"%{digits}%")
                    )
                else:
                    conds.append(Pedido.telefone_cliente.like(f"%{digits}%"))

            query = query.filter(db.or_(*conds))

        # Ordenação
        ordenar_direcao_lower = ordenar_direcao.lower() if ordenar_direcao else "asc"
        is_desc = ordenar_direcao_lower == "desc"

        if filtrar_por_criacao:
            if is_desc:
                query = query.order_by(Pedido.created_at.desc())
            else:
                query = query.order_by(Pedido.created_at.asc())
        elif ordenar_por == "dia_entrega":
            # INT-01: ordenar pelo horário REAL (slot_inicio, Time) e não pela string
            # lexicográfica de `horario` ("9:00" vinha depois de "10:00"). slot_inicio é a
            # chave primária de horário (NULLS LAST para pedidos sem horário parseável) e
            # `horario` fica só como desempate residual.
            # Para "mais próximos primeiro": ASC (hoje antes de amanhã, mais cedo primeiro).
            # Para "mais distantes primeiro": DESC.
            if is_desc:
                query = query.order_by(
                    Pedido.dia_entrega.desc(),
                    Pedido.slot_inicio.desc().nullslast(),
                    Pedido.horario.desc(),
                )
            else:
                query = query.order_by(
                    Pedido.dia_entrega.asc(),
                    Pedido.slot_inicio.asc().nullslast(),
                    Pedido.horario.asc(),
                )
        elif ordenar_por == "created_at":
            if is_desc:
                query = query.order_by(Pedido.created_at.desc())
            else:
                query = query.order_by(Pedido.created_at.asc())
        elif ordenar_por == "valor":
            # Ordenar por valor (precisa converter string para float)
            from sqlalchemy import Float, cast, func

            if is_desc:
                query = query.order_by(cast(Pedido.valor, Float).desc().nullslast())
            else:
                query = query.order_by(cast(Pedido.valor, Float).asc().nullslast())
        elif ordenar_por == "cliente":
            if is_desc:
                query = query.order_by(Pedido.cliente.desc())
            else:
                query = query.order_by(Pedido.cliente.asc())

        # Paginação
        total = query.count()
        if page is not None and per_page is not None:
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

        return query.all(), total

    def atualizar_status(self, pedido_id: int, novo_status: str) -> Optional[Pedido]:
        """
        Atualiza status de um pedido.

        Hooks disparados aqui:
        - Meta CAPI outbox quando status_pagamento → Pago/Parcial
        - UTMify quando status_pagamento → Pago/Parcial
        - Comissão quando status_pagamento transita para Pago/Parcial (Q2)
        - paid_at setado uma única vez na transição para Pago/Parcial
        """
        pedido = self.get_by_id(pedido_id)
        if not pedido:
            return None

        status_anterior = pedido.status
        status_pagamento_anterior = pedido.status_pagamento

        update_fields = {"status": novo_status, "updated_at": datetime_now_brazil()}

        # Auto-pagar ao concluir se pagamento ainda pendente
        if novo_status == "concluido" and (
            not pedido.status_pagamento or pedido.status_pagamento.upper() == "PENDENTE"
        ):
            update_fields["status_pagamento"] = "Pago"

        # Setar paid_at na primeira transição para Pago/Parcial (imutável após isso)
        novo_sp = update_fields.get("status_pagamento") or pedido.status_pagamento or ""
        novo_sp_lower = novo_sp.strip().lower()
        sp_ant_lower = (status_pagamento_anterior or "").strip().lower()
        transitando_para_pago = (
            novo_sp_lower in ("pago", "parcial") and sp_ant_lower not in ("pago", "parcial")
        )
        if transitando_para_pago and not pedido.paid_at:
            update_fields["paid_at"] = datetime_now_brazil()

        pedido_atualizado = self.update(pedido, **update_fields)

        # Meta CAPI: Purchase é disparado na criação do pedido, não em update.

        try:
            from app.utils.utmify_helper import send_utmify_if_purchase

            send_utmify_if_purchase(pedido_atualizado, status_anterior, status_pagamento_anterior)
        except Exception as e:
            print(f"[AVISO] Erro ao enviar UTMify para pedido #{pedido_id}: {e}")

        # Gerar comissão quando status_pagamento transita para Pago/Parcial (Q2)
        if transitando_para_pago and pedido_atualizado.vendedor_id:
            try:
                from app.services.commission_service import generate_commission

                generate_commission(pedido_atualizado, pedido_atualizado.vendedor_id)
            except Exception as e:
                print(f"[AVISO] Erro ao gerar comissão para pedido #{pedido_id}: {e}")

        return pedido_atualizado

    def _campos_comissao_mudaram(self, pedido: Pedido, campos_novos: dict) -> bool:
        """Verifica se algum campo que afeta comissão foi alterado."""
        sensíveis = {"vendedor_id", "fonte_pedido_id", "valor", "tipo_pedido", "taxa_entrega"}
        return any(
            k in sensíveis and campos_novos.get(k) != getattr(pedido, k, None)
            for k in campos_novos
        )

    def atualizar_pedido_com_estorno(
        self, pedido_id: int, campos: dict, actor_id: int
    ) -> Optional[Pedido]:
        """
        Atualiza campos gerais de um pedido e, se tiver comissão ativa e campos
        que afetam a comissão mudaram, estorna e recria (Q3).

        Também dispara paid_at e comissão nova se status_pagamento transitar para Pago/Parcial.
        """
        pedido = self.get_by_id(pedido_id)
        if not pedido:
            return None

        sp_ant_lower = (pedido.status_pagamento or "").strip().lower()
        novo_sp_lower = (campos.get("status_pagamento") or pedido.status_pagamento or "").strip().lower()
        transitando_para_pago = (
            novo_sp_lower in ("pago", "parcial") and sp_ant_lower not in ("pago", "parcial")
        )

        if transitando_para_pago and not pedido.paid_at:
            campos["paid_at"] = datetime_now_brazil()

        campos["updated_at"] = datetime_now_brazil()
        pedido_atualizado = self.update(pedido, **campos)

        vendedor_id = pedido_atualizado.vendedor_id or actor_id

        # Estorno se campos de comissão mudaram e já há entrada ativa
        if self._campos_comissao_mudaram(pedido, campos):
            try:
                from app.services.commission_service import void_and_recreate_commission

                void_and_recreate_commission(pedido_atualizado, vendedor_id)
            except Exception as e:
                print(f"[AVISO] Erro ao estornar/recriar comissão pedido #{pedido_id}: {e}")
        elif transitando_para_pago and vendedor_id:
            try:
                from app.services.commission_service import generate_commission

                generate_commission(pedido_atualizado, vendedor_id)
            except Exception as e:
                print(f"[AVISO] Erro ao gerar comissão pedido #{pedido_id}: {e}")

        return pedido_atualizado

    def buscar_atrasados(self) -> List[Pedido]:
        """Busca pedidos atrasados (excluindo ocultos, concluídos e deletados)"""
        pedidos = self.model.query.filter(
            Pedido.status != "concluido",
            ~Pedido.oculto,  # noqa: E712 - SQLAlchemy comparison
            Pedido.deleted_at.is_(None),
        ).all()

        # Filtrar por lógica de atraso
        return [p for p in pedidos if p.is_overdue()]

    def buscar_por_fonte(
        self,
        fonte_id: int,
        excluir_ocultos: bool = True,
        excluir_deletados: bool = True,
    ) -> List[Pedido]:
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
            ~Pedido.oculto, Pedido.deleted_at.is_(None)
        )  # noqa: E712 - SQLAlchemy comparison

        return {
            "total": base_query.count(),
            "agendado": base_query.filter_by(status="agendado").count(),
            "em_producao": base_query.filter_by(status="em_producao").count(),
            "pronto_entrega": base_query.filter_by(status="pronto_entrega").count(),
            "em_rota": base_query.filter_by(status="em_rota").count(),
            "pronto_retirada": base_query.filter_by(status="pronto_retirada").count(),
            "concluido": base_query.filter_by(status="concluido").count(),
            "atrasados": len(self.buscar_atrasados()),
        }

    def arquivar_antigos(self, dias: int = 1) -> int:
        """Arquiva (oculta) pedidos concluídos há mais de X dias"""
        cutoff_date = datetime_now_brazil() - timedelta(days=dias)
        old_pedidos = self.model.query.filter(
            Pedido.status == "concluido",
            Pedido.updated_at < cutoff_date,
            ~Pedido.oculto,  # noqa: E712 - SQLAlchemy comparison
        ).all()

        count = len(old_pedidos)
        for pedido in old_pedidos:
            self.update(pedido, oculto=True, updated_at=datetime_now_brazil())

        return count

    def ocultar_concluidos(self) -> int:
        """Oculta todos os pedidos concluídos (independente da data)"""
        concluidos = self.model.query.filter(
            Pedido.status == "concluido",
            ~Pedido.oculto,  # noqa: E712 - SQLAlchemy comparison
            Pedido.deleted_at.is_(None),  # Não ocultar pedidos já deletados
        ).all()

        count = len(concluidos)
        print(f"[REPOSITORY] Encontrados {count} pedidos concluídos para ocultar")

        if count > 0:
            # Atualizar todos de uma vez e fazer commit único
            for pedido in concluidos:
                pedido.oculto = True
                pedido.updated_at = datetime_now_brazil()
                print(f"[REPOSITORY] Marcando pedido #{pedido.id} como oculto")

            try:
                db.session.commit()
                print(f"[REPOSITORY] Commit realizado com sucesso para {count} pedidos")
            except Exception as e:
                print(f"[REPOSITORY] Erro ao fazer commit: {str(e)}")
                db.session.rollback()
                raise

        return count

    def buscar_deletados(self) -> List[Pedido]:
        """Busca pedidos soft-deleted (P0.3)"""
        return (
            self.model.query.filter(Pedido.deleted_at.isnot(None))
            .order_by(Pedido.deleted_at.desc())
            .all()
        )

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
                action="DELETE",
                entity_type="pedido",
                entity_id=pedido_id,
                actor=actor or "system",
                store_ref_id=pedido.store_ref_id,
                entity=pedido,
                metadata={
                    "cliente": pedido.cliente,
                    "destinatario": pedido.destinatario,
                },
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
                action="RESTORE",
                entity_type="pedido",
                entity_id=pedido_id,
                actor=actor or "system",
                store_ref_id=pedido.store_ref_id,
                entity=pedido,
                metadata={
                    "cliente": pedido.cliente,
                    "destinatario": pedido.destinatario,
                },
            )
        except Exception as e:
            print(f"[AVISO] Erro ao registrar auditoria: {e}")

        return pedido
