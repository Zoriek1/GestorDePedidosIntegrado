# -*- coding: utf-8 -*-
"""
Guard para Operações Destrutivas (P0.2)
Garante que backup seja criado antes de operações que podem causar perda de dados.
"""
from app.utils.backup_helper import create_backup


class BackupRequiredException(Exception):
    """Exceção levantada quando backup é necessário mas falhou"""

    pass


def ensure_backup_before_destructive_action(
    reason: str, context: dict = None, allow_override: bool = False, actor: str = None
) -> bool:
    """
    Garante que um backup válido seja criado antes de operação destrutiva.

    Implementa fail-closed: se backup falhar, bloqueia a operação.
    Com allow_override=True, permite override mas registra em auditoria (P0.3).

    Args:
        reason: Motivo do backup (ex: 'delete_pedido', 'delete_cliente')
        context: Contexto adicional para logging (opcional)
        allow_override: Se True, permite operação mesmo se backup falhar (com auditoria)
        actor: Quem está executando a ação (para auditoria de override)

    Returns:
        True se backup foi criado com sucesso ou override foi permitido

    Raises:
        BackupRequiredException: Se backup falhar e override não permitido
    """
    context = context or {}
    full_reason = f"critical_operation_{reason}"

    print(f"[BACKUP GUARD] Tentando criar backup antes de operação destrutiva: {reason}")

    # Tentar criar backup
    try:
        backup_path = create_backup(reason=full_reason, compress=True, silent=True)
    except Exception as backup_exception:
        # Se create_backup levantar exceção, tratar como falha
        error_msg = f"Exceção ao criar backup: {str(backup_exception)}"
        print(f"[BACKUP GUARD] {error_msg}")
        backup_path = None

    if backup_path is None:
        # Backup falhou
        if allow_override:
            # Permitir override mas registrar em auditoria (P0.3)
            try:
                from app.utils.audit_logger import log_action

                entity_type = context.get("entity_type", "unknown")
                entity_id = (
                    context.get("entity_id")
                    or context.get("pedido_id")
                    or context.get("cliente_id")
                )

                log_action(
                    action="OVERRIDE_DELETE",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    actor=actor or "system",
                    metadata={
                        "reason": reason,
                        "backup_failed": True,
                        "override_allowed": True,
                        "context": context,
                    },
                )
            except Exception as audit_error:
                print(f"[AVISO] Erro ao registrar override em auditoria: {audit_error}")

            print(
                f"[AVISO] Override permitido para {reason} (backup falhou mas allow_override=True)"
            )
            return True
        else:
            # Bloquear operação
            error_msg = (
                f"Backup necessário antes de operação destrutiva ({reason}). "
                f"Falha ao criar backup. Operação bloqueada por segurança."
            )
            print(f"[BACKUP GUARD] BLOQUEANDO operação: {error_msg}")
            raise BackupRequiredException(error_msg)

    # Backup criado com sucesso
    print(f"[BACKUP GUARD] Backup criado com sucesso: {backup_path.name}")
    return True
