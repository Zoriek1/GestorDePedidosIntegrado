# -*- coding: utf-8 -*-
"""
Modelo de dados para Pedidos - PWA v3.0
Model completo com todos os campos do formulário de 4 steps
"""
from app import db
from datetime import datetime, timedelta

class Pedido(db.Model):
    """Modelo de Pedido com todos os campos necessários para o PWA"""
    __tablename__ = 'pedidos'
    
    # Identificador único
    id = db.Column(db.Integer, primary_key=True)
    
    # Step 1 - Dados do Cliente
    cliente = db.Column(db.String(100), nullable=False, comment='Quem enviou (remetente)')
    telefone_cliente = db.Column(db.String(20), nullable=False, comment='Telefone do cliente')
    destinatario = db.Column(db.String(100), nullable=False, comment='Para quem (destinatário)')
    tipo_pedido = db.Column(db.String(20), default='Entrega', comment='Entrega ou Retirada')
    
    # Step 2 - Produto e Agendamento
    produto = db.Column(db.Text, nullable=False, comment='Nome do produto')
    flores_cor = db.Column(db.Text, nullable=True, comment='Flores que vão e cor')
    valor = db.Column(db.String(20), nullable=True, comment='Valor total (R$)')
    dia_entrega = db.Column(db.Date, nullable=False, comment='Data de entrega')
    horario = db.Column(db.String(10), nullable=False, comment='Horário de entrega (HH:MM)')
    
    # Step 3 - Logística (campos separados de endereço)
    cep = db.Column(db.String(10), nullable=True, comment='CEP')
    rua = db.Column(db.String(200), nullable=True, comment='Rua/Logradouro')
    numero = db.Column(db.String(20), nullable=True, comment='Número')
    bairro = db.Column(db.String(100), nullable=True, comment='Bairro')
    cidade = db.Column(db.String(100), nullable=True, comment='Cidade')
    endereco = db.Column(db.Text, nullable=True, comment='Endereço completo (gerado ou manual)')
    obs_entrega = db.Column(db.Text, nullable=True, comment='Como entregar/Observações de entrega')
    
    # Step 4 - Finalização
    mensagem = db.Column(db.Text, nullable=True, comment='Carta/Mensagem')
    pagamento = db.Column(db.String(50), nullable=True, comment='Forma de pagamento')
    observacoes = db.Column(db.Text, nullable=True, comment='Observações gerais')
    
    # Controle e Status
    status = db.Column(db.String(30), default='agendado', comment='Status do pedido')
    quantidade = db.Column(db.Integer, default=1, comment='Quantidade (compatibilidade)')
    oculto = db.Column(db.Boolean, default=False, comment='Se True, pedido está oculto/arquivado (não aparece na lista)')
    
    # Distância calculada (GraphHopper/OpenRouteService)
    distancia_km = db.Column(db.Float, nullable=True, comment='Distância em km da floricultura até o endereço')
    
    # Taxa de entrega calculada
    taxa_entrega = db.Column(db.Float, nullable=True, comment='Taxa de entrega calculada (R$)')
    
    # Coordenadas do endereço (cache para evitar geocodificação repetida)
    coords_lat = db.Column(db.Float, nullable=True, comment='Latitude do endereço')
    coords_lon = db.Column(db.Float, nullable=True, comment='Longitude do endereço')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='Data de criação')
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow, comment='Última atualização')
    
    def __repr__(self):
        return f'<Pedido #{self.id} - {self.cliente} → {self.destinatario} ({self.status})>'
    
    def to_dict(self):
        """Converte o pedido para dicionário (para API JSON)"""
        return {
            'id': self.id,
            # Step 1
            'cliente': self.cliente or '',
            'telefone_cliente': self.telefone_cliente or '',
            'destinatario': self.destinatario or '',
            'tipo_pedido': self.tipo_pedido or 'Entrega',
            # Step 2
            'produto': self.produto or '',
            'flores_cor': self.flores_cor or '',
            'valor': self.valor or '',
            'dia_entrega': self.dia_entrega.strftime('%Y-%m-%d') if self.dia_entrega else '',
            'horario': self.horario or '',
            # Step 3 - Endereço
            'cep': self.cep or '',
            'rua': self.rua or '',
            'numero': self.numero or '',
            'bairro': self.bairro or '',
            'cidade': self.cidade or '',
            'endereco': self.endereco or '',
            'obs_entrega': self.obs_entrega or '',
            # Step 4
            'mensagem': self.mensagem or '',
            'pagamento': self.pagamento or '',
            'observacoes': self.observacoes or '',
            # Controle
            'status': self.status or 'agendado',
            'quantidade': self.quantidade or 1,
            'oculto': self.oculto or False,
            'distancia_km': self.distancia_km,
            'taxa_entrega': self.taxa_entrega,
            'coords_lat': self.coords_lat,
            'coords_lon': self.coords_lon,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else ''
        }
    
    def is_overdue(self):
        """Verifica se o pedido está atrasado"""
        if self.status == 'concluido':
            return False
        
        try:
            # Combinar data e hora de entrega
            delivery_datetime = datetime.combine(
                self.dia_entrega,
                datetime.strptime(self.horario, '%H:%M').time()
            )
            return datetime.now() > delivery_datetime
        except Exception:
            return False
    
    @staticmethod
    def get_statistics():
        """Retorna estatísticas dos pedidos (excluindo ocultos)"""
        base_query = Pedido.query.filter_by(oculto=False)
        stats = {
            'total': base_query.count(),
            'agendado': base_query.filter_by(status='agendado').count(),
            'em_producao': base_query.filter_by(status='em_producao').count(),
            'pronto_entrega': base_query.filter_by(status='pronto_entrega').count(),
            'em_rota': base_query.filter_by(status='em_rota').count(),
            'pronto_retirada': base_query.filter_by(status='pronto_retirada').count(),
            'concluido': base_query.filter_by(status='concluido').count()
        }
        return stats
    
    @staticmethod
    def get_overdue_pedidos():
        """Retorna pedidos atrasados (excluindo ocultos)"""
        all_pedidos = Pedido.query.filter(
            Pedido.status != 'concluido',
            Pedido.oculto == False
        ).all()
        return [p for p in all_pedidos if p.is_overdue()]
    
    @staticmethod
    def cleanup_old_pedidos(days=1):
        """Arquiva (oculta) pedidos concluídos há mais de X dias - NÃO deleta do banco"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_pedidos = Pedido.query.filter(
            Pedido.status == 'concluido',
            Pedido.updated_at < cutoff_date,
            Pedido.oculto == False
        ).all()
        
        count = len(old_pedidos)
        for pedido in old_pedidos:
            pedido.oculto = True
            pedido.updated_at = datetime.utcnow()
        
        db.session.commit()
        return count

