# -*- coding: utf-8 -*-
"""
Modelo de dados para Pedidos - PWA v3.0
Model completo com todos os campos do formulário de 4 steps
"""
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback para Python < 3.9
    from backports.zoneinfo import ZoneInfo

from app import db

# Timezone do Brasil (São Paulo - GMT-3)
TIMEZONE_BRASIL = ZoneInfo("America/Sao_Paulo")


def datetime_now_brazil():
    """Retorna datetime atual com timezone do Brasil (GMT-3)"""
    return datetime.now(TIMEZONE_BRASIL)


class Pedido(db.Model):
    """Modelo de Pedido com todos os campos necessários para o PWA"""

    __tablename__ = "pedidos"

    # Identificador único
    id = db.Column(db.Integer, primary_key=True)

    # Step 1 - Dados do Cliente
    cliente = db.Column(db.String(100), nullable=False, comment="Quem enviou (remetente)")
    telefone_cliente = db.Column(db.String(20), nullable=False, comment="Telefone do cliente")
    destinatario = db.Column(db.String(100), nullable=False, comment="Para quem (destinatário)")
    tipo_pedido = db.Column(db.String(20), default="Entrega", comment="Entrega ou Retirada")

    # Step 2 - Produto e Agendamento
    produto = db.Column(db.Text, nullable=False, comment="Nome do produto")
    flores_cor = db.Column(db.Text, nullable=True, comment="Flores que vão e cor")
    valor = db.Column(db.String(20), nullable=True, comment="Valor total (R$)")
    dia_entrega = db.Column(db.Date, nullable=False, comment="Data de entrega")
    horario = db.Column(
        db.String(20),
        nullable=False,
        comment="Horário de entrega (HH:MM ou HH:MM - HH:MM)",
    )

    # Step 3 - Logística (campos separados de endereço)
    cep = db.Column(db.String(10), nullable=True, comment="CEP")
    rua = db.Column(db.String(200), nullable=True, comment="Rua/Logradouro")
    numero = db.Column(db.String(20), nullable=True, comment="Número")
    bairro = db.Column(db.String(100), nullable=True, comment="Bairro")
    cidade = db.Column(db.String(100), nullable=True, comment="Cidade")
    endereco = db.Column(db.Text, nullable=True, comment="Endereço completo (gerado ou manual)")
    obs_entrega = db.Column(db.Text, nullable=True, comment="Como entregar/Observações de entrega")

    # Step 4 - Finalização
    mensagem = db.Column(db.Text, nullable=True, comment="Carta/Mensagem")
    pagamento = db.Column(db.String(50), nullable=True, comment="Forma de pagamento")
    parcelas_cartao = db.Column(
        db.Integer,
        nullable=True,
        comment="Número de parcelas no cartão de crédito (1 para à vista)",
    )
    taxa_cartao_valor = db.Column(
        db.Float,
        nullable=True,
        default=0.0,
        comment="Snapshot do valor da taxa do adquirente cobrada (R$)",
    )
    observacoes = db.Column(db.Text, nullable=True, comment="Observações gerais")

    # Novos campos solicitados
    fonte_pedido = db.Column(
        db.String(50),
        nullable=True,
        comment="Fonte do pedido (Ifood, Site, etc) - DEPRECATED: usar fonte_pedido_id",
    )
    fonte_pedido_id = db.Column(
        db.Integer,
        db.ForeignKey("fontes_pedido.id"),
        nullable=True,
        index=True,
        comment="ID da fonte do pedido (referência)",
    )
    status_pagamento = db.Column(
        db.String(50),
        nullable=True,
        comment="Status do pagamento (Realizado, Pendente, etc)",
    )

    # Plataforma e Canal (para integrações como Nuvemshop)
    plataforma = db.Column(
        db.String(50),
        nullable=True,
        comment="Plataforma de origem (Nuvemshop, Sistema, etc)",
    )
    canal = db.Column(
        db.String(50),
        nullable=True,
        comment="Canal de venda (Site, PDV, Mercado Livre, etc)",
    )

    # Controle e Status
    status = db.Column(db.String(30), default="agendado", comment="Status do pedido")
    quantidade = db.Column(db.Integer, default=1, comment="Quantidade (compatibilidade)")
    oculto = db.Column(
        db.Boolean,
        default=False,
        comment="Se True, pedido está oculto/arquivado (não aparece na lista)",
    )
    impresso = db.Column(
        db.Boolean, default=False, comment="Se True, pedido já foi impresso no painel"
    )
    cartao_impresso = db.Column(
        db.Boolean,
        default=False,
        comment="Se True, o cartão/cartinha do pedido já foi impresso",
    )

    # Relacionamentos
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id"),
        nullable=True,
        index=True,
        comment="ID do cliente (sistema novo)",
    )
    vendedor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="Vendedor responsável pela venda (módulo recebíveis)",
    )
    entregador_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="Entregador atribuído (módulo entrega)",
    )
    delivery_assigned_at = db.Column(
        db.DateTime,
        nullable=True,
        comment="Momento da atribuição da entrega ao entregador",
    )
    delivery_completed_at = db.Column(
        db.DateTime,
        nullable=True,
        comment="Momento em que o entregador deu baixa na entrega (imutável após set)",
    )
    fonte_pedido_rel = db.relationship(
        "FontePedido", backref="pedidos", lazy="joined", foreign_keys=[fonte_pedido_id]
    )

    # Distância calculada (GraphHopper/OpenRouteService)
    distancia_km = db.Column(
        db.Float,
        nullable=True,
        comment="Distância em km da floricultura até o endereço",
    )

    # Taxa de entrega calculada (operacional - custo interno)
    taxa_entrega = db.Column(
        db.Float, nullable=True, comment="Taxa de entrega operacional calculada (R$)"
    )

    # Frete cobrado do cliente (vindo da Order API - Nuvemshop, etc)
    frete_cobrado_cliente = db.Column(
        db.Float,
        nullable=True,
        comment="Frete cobrado do cliente na compra (R$)",
    )
    desconto_frete = db.Column(
        db.Float,
        nullable=True,
        comment="Desconto aplicado no frete (R$)",
    )
    frete_liquido_cliente = db.Column(
        db.Float,
        nullable=True,
        comment="Frete efetivo pago pelo cliente (R$)",
    )

    # Coordenadas do endereço (cache para evitar geocodificação repetida)
    coords_lat = db.Column(db.Float, nullable=True, comment="Latitude do endereço")
    coords_lon = db.Column(db.Float, nullable=True, comment="Longitude do endereço")

    # Meta Pixel parameters (para melhorar qualidade de correspondência de eventos)
    # fbc: Facebook Click ID (vem do parâmetro fbclid na URL)
    # fbp: Facebook Browser ID (vem do cookie _fbp criado pelo Pixel)
    fbc = db.Column(db.String(255), nullable=True, comment="Facebook Click ID (fbclid)")
    fbp = db.Column(db.String(255), nullable=True, comment="Facebook Browser ID (cookie _fbp)")

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime_now_brazil, comment="Data de criação")
    updated_at = db.Column(
        db.DateTime,
        nullable=True,
        onupdate=datetime_now_brazil,
        comment="Última atualização",
    )
    # Setado uma única vez quando status_pagamento transita para Pago/Parcial
    paid_at = db.Column(
        db.DateTime,
        nullable=True,
        comment="Momento real do pagamento (imutável após ser definido)",
    )

    # Soft Delete (P0.3)
    deleted_at = db.Column(
        db.DateTime, nullable=True, index=True, comment="Data de exclusão (soft delete)"
    )

    def __repr__(self):
        return f"<Pedido #{self.id} - {self.cliente} → {self.destinatario} ({self.status})>"

    def to_dict(self):
        """Converte o pedido para dicionário (para API JSON)"""
        return {
            "id": self.id,
            # Step 1
            "cliente": self.cliente or "",
            "telefone_cliente": self.telefone_cliente or "",
            "destinatario": self.destinatario or "",
            "tipo_pedido": self.tipo_pedido or "Entrega",
            # Step 2
            "produto": self.produto or "",
            "flores_cor": self.flores_cor or "",
            "valor": self.valor or "",
            "dia_entrega": self.dia_entrega.strftime("%Y-%m-%d") if self.dia_entrega else "",
            "horario": self.horario or "",
            # Step 3 - Endereço
            "cep": self.cep or "",
            "rua": self.rua or "",
            "numero": self.numero or "",
            "bairro": self.bairro or "",
            "cidade": self.cidade or "",
            "endereco": self.endereco or "",
            "obs_entrega": self.obs_entrega or "",
            # Step 4
            "mensagem": self.mensagem or "",
            "pagamento": self.pagamento or "",
            "parcelas_cartao": self.parcelas_cartao,
            "taxa_cartao_valor": float(self.taxa_cartao_valor or 0.0),
            "observacoes": self.observacoes or "",
            "fonte_pedido": self.fonte_pedido or "",  # Mantido para compatibilidade
            "fonte_pedido_id": self.fonte_pedido_id,
            "fonte_pedido_nome": self.fonte_pedido_rel.nome if self.fonte_pedido_rel else "",
            "status_pagamento": self.status_pagamento or "",
            # Plataforma e Canal (integrações)
            "plataforma": self.plataforma or "",
            "canal": self.canal or "",
            # Controle
            "status": self.status or "agendado",
            "quantidade": self.quantidade or 1,
            "oculto": self.oculto or False,
            "impresso": self.impresso or False,
            "cartao_impresso": self.cartao_impresso or False,
            "cliente_id": self.cliente_id,
            "vendedor_id": self.vendedor_id,
            "entregador_id": self.entregador_id,
            "delivery_assigned_at": self.delivery_assigned_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.delivery_assigned_at
            else None,
            "delivery_completed_at": self.delivery_completed_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.delivery_completed_at
            else None,
            "distancia_km": self.distancia_km,
            "taxa_entrega": self.taxa_entrega,
            # Frete (vindo da Order API)
            "frete_cobrado_cliente": self.frete_cobrado_cliente,
            "desconto_frete": self.desconto_frete,
            "frete_liquido_cliente": self.frete_liquido_cliente,
            "coords_lat": self.coords_lat,
            "coords_lon": self.coords_lon,
            "fbc": self.fbc or "",
            "fbp": self.fbp or "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
            "deleted_at": self.deleted_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.deleted_at
            else None,
        }

    def total_pago(self) -> float:
        """
        Retorna valor final do pedido em float

        Usa parse_brl_money() no campo valor.
        Considera regras de negócio: frete, desconto, taxa (se aplicável).
        Por enquanto, retorna apenas o valor do pedido.

        Returns:
            float: Valor final do pedido, ou 0.0 se valor inválido
        """
        from app.utils.money import parse_brl_money

        if not self.valor:
            return 0.0

        valor_base = parse_brl_money(self.valor)

        # TODO: Adicionar lógica de frete, desconto, taxa se necessário
        # Por enquanto, retorna apenas o valor base
        return round(valor_base, 2)

    def is_overdue(self):
        """Verifica se o pedido está atrasado"""
        if self.status == "concluido":
            return False

        try:
            # Verificar se é intervalo ou horário simples
            if " - " in self.horario:
                # Intervalo: usar o horário final para verificar atraso
                partes = self.horario.split(" - ")
                if len(partes) == 2:
                    horario_final = partes[1].strip()
                    delivery_datetime = datetime.combine(
                        self.dia_entrega,
                        datetime.strptime(horario_final, "%H:%M").time(),
                    )
                else:
                    return False
            else:
                # Horário simples
                delivery_datetime = datetime.combine(
                    self.dia_entrega, datetime.strptime(self.horario, "%H:%M").time()
                )
            return datetime.now() > delivery_datetime
        except Exception:
            return False

    @staticmethod
    def get_statistics():
        """Retorna estatísticas dos pedidos (excluindo ocultos e deletados)"""
        # Filtrar apenas pedidos não deletados (soft delete) e não ocultos
        base_query = Pedido.query.filter(
            Pedido.oculto == False, Pedido.deleted_at.is_(None)  # noqa: E712
        )
        stats = {
            "total": base_query.count(),
            "agendado": base_query.filter_by(status="agendado").count(),
            "em_producao": base_query.filter_by(status="em_producao").count(),
            "pronto_entrega": base_query.filter_by(status="pronto_entrega").count(),
            "em_rota": base_query.filter_by(status="em_rota").count(),
            "pronto_retirada": base_query.filter_by(status="pronto_retirada").count(),
            "concluido": base_query.filter_by(status="concluido").count(),
        }
        return stats

    @staticmethod
    def get_overdue_pedidos():
        """Retorna pedidos atrasados (excluindo ocultos e deletados)"""
        all_pedidos = Pedido.query.filter(
            Pedido.status != "concluido",
            Pedido.oculto == False,  # noqa: E712
            Pedido.deleted_at.is_(None),
        ).all()
        return [p for p in all_pedidos if p.is_overdue()]

    @property
    def is_deleted(self):
        """Verifica se pedido está soft-deleted"""
        return self.deleted_at is not None

    def soft_delete(self):
        """Marca pedido como deletado (soft delete)"""
        if not self.is_deleted:
            self.deleted_at = datetime_now_brazil()
            self.updated_at = datetime_now_brazil()

    def restore(self):
        """Restaura pedido deletado (reverte soft delete)"""
        if self.is_deleted:
            self.deleted_at = None
            self.updated_at = datetime_now_brazil()

    @staticmethod
    def cleanup_old_pedidos(days=1):
        """Arquiva (oculta) pedidos concluídos há mais de X dias - NÃO deleta do banco"""
        cutoff_date = datetime_now_brazil() - timedelta(days=days)
        old_pedidos = Pedido.query.filter(
            Pedido.status == "concluido",
            Pedido.updated_at < cutoff_date,
            Pedido.oculto is False,
            Pedido.deleted_at.is_(None),  # Não arquivar pedidos já deletados
        ).all()

        count = len(old_pedidos)
        for pedido in old_pedidos:
            pedido.oculto = True
            pedido.updated_at = datetime_now_brazil()

        db.session.commit()
        return count
