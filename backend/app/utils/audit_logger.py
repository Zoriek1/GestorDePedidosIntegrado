# -*- coding: utf-8 -*-
"""
Logger de Auditoria (P0.3)
Registra eventos críticos no sistema para trilha de auditoria
"""
import json
from datetime import datetime

from app import db
from app.models.audit_log import AuditLog


def log_action(
    action: str,
    entity_type: str,
    entity_id: int,
    actor: str = None,
    metadata: dict = None,
):
    """
    Registra uma ação na trilha de auditoria

    Args:
        action: Tipo de ação (CREATE/UPDATE/DELETE/RESTORE/OVERRIDE_DELETE)
        entity_type: Tipo de entidade ('pedido', 'cliente', etc)
        entity_id: ID da entidade afetada
        actor: Quem executou a ação (usuário/cliente/terminal)
        metadata: Dados adicionais (dicionário será convertido para JSON)
    """
    try:
        # Converter metadata para JSON string se for dict
        metadata_str = None
        if metadata:
            if isinstance(metadata, dict):
                metadata_str = json.dumps(metadata, ensure_ascii=False)
            else:
                metadata_str = str(metadata)

        audit_entry = AuditLog(
            ts=datetime.utcnow(),
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata_str,
        )

        db.session.add(audit_entry)
        db.session.commit()

    except Exception as e:
        # Não falhar a operação principal se auditoria falhar
        db.session.rollback()
        print(f"[AVISO] Erro ao registrar auditoria: {e}")
        # Logar mas não levantar exceção
