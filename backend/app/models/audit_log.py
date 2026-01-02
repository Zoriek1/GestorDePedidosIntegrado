# -*- coding: utf-8 -*-
"""
Modelo de Auditoria (P0.3)
Registra todas as operações críticas no sistema para trilha de auditoria
"""
from app import db
from datetime import datetime


class AuditLog(db.Model):
    """Modelo de log de auditoria"""
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    actor = db.Column(db.String(100), nullable=True, comment='Usuário/cliente/terminal que executou a ação')
    action = db.Column(db.String(50), nullable=False, index=True, comment='CREATE/UPDATE/DELETE/RESTORE/OVERRIDE_DELETE')
    entity_type = db.Column(db.String(50), nullable=False, index=True, comment='Tipo de entidade: pedido, cliente, etc')
    entity_id = db.Column(db.Integer, nullable=True, index=True, comment='ID da entidade afetada')
    metadata_json = db.Column(db.Text, nullable=True, comment='JSON ou texto com informações adicionais (diffs, resumo)')
    
    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type}#{self.entity_id} @ {self.ts}>'
    
    def to_dict(self):
        """Converte para dicionário (para API JSON)"""
        return {
            'id': self.id,
            'ts': self.ts.strftime('%Y-%m-%d %H:%M:%S') if self.ts else '',
            'actor': self.actor or '',
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'metadata': self.metadata_json or ''  # Mantém 'metadata' na API para compatibilidade
        }

