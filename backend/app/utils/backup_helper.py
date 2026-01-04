# -*- coding: utf-8 -*-
"""
Utilitário de Backup para uso programático
Permite criar backups a partir do código Python com logging de auditoria
"""
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar o diretório scripts ao path para importar BackupManager
backend_dir = Path(__file__).parent.parent.parent
scripts_dir = backend_dir / 'scripts' / 'backup'
sys.path.insert(0, str(scripts_dir))

try:
    from backup import BackupManager
except ImportError:
    # Fallback: importar diretamente
    import importlib.util
    backup_module_path = scripts_dir / 'backup.py'
    spec = importlib.util.spec_from_file_location("backup", backup_module_path)
    backup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backup_module)
    BackupManager = backup_module.BackupManager


class BackupAuditLogger:
    """Logger de auditoria para operações de backup"""

    def __init__(self, log_dir=None):
        """
        Inicializa o logger de auditoria

        Args:
            log_dir: Diretório para salvar logs (padrão: backend/instance/logs)
        """
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = backend_dir / 'instance' / 'logs'

        # Criar diretório de logs se não existir
        self.log_dir.mkdir(exist_ok=True)

        # Configurar logger
        log_file = self.log_dir / 'backup_audit.log'

        # Criar logger
        self.logger = logging.getLogger('backup_audit')
        self.logger.setLevel(logging.INFO)

        # Evitar duplicação de handlers
        if not self.logger.handlers:
            # Handler para arquivo
            file_handler = logging.FileHandler(
                log_file,
                encoding='utf-8',
                mode='a'
            )
            file_handler.setLevel(logging.INFO)

            # Formato do log
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

    def log_backup_created(self, backup_path, reason='manual', size_mb=None):
        """
        Registra criação de backup

        Args:
            backup_path: Caminho do arquivo de backup criado
            reason: Motivo do backup (manual, automatic, critical_operation, startup, etc)
            size_mb: Tamanho do backup em MB
        """
        backup_name = Path(backup_path).name if backup_path else 'N/A'
        size_info = f" ({size_mb:.2f} MB)" if size_mb else ""
        self.logger.info(
            f"BACKUP CRIADO | Arquivo: {backup_name} | "
            f"Motivo: {reason} | Tamanho: {size_info}"
        )

    def log_backup_failed(self, reason, error_msg):
        """
        Registra falha na criação de backup

        Args:
            reason: Motivo do backup que falhou
            error_msg: Mensagem de erro
        """
        self.logger.error(
            f"BACKUP FALHOU | Motivo: {reason} | Erro: {error_msg}"
        )

    def log_restore_attempt(self, backup_path, user_confirmed=False):
        """
        Registra tentativa de restauração

        Args:
            backup_path: Caminho do backup a ser restaurado
            user_confirmed: Se o usuário confirmou a operação
        """
        backup_name = Path(backup_path).name if backup_path else 'N/A'
        status = "CONFIRMADO" if user_confirmed else "CANCELADO"
        self.logger.warning(
            f"RESTORE TENTATIVA | Arquivo: {backup_name} | Status: {status}"
        )

    def log_restore_completed(self, backup_path, success=True):
        """
        Registra conclusão de restauração

        Args:
            backup_path: Caminho do backup restaurado
            success: Se a restauração foi bem-sucedida
        """
        backup_name = Path(backup_path).name if backup_path else 'N/A'
        status = "SUCESSO" if success else "FALHA"
        self.logger.warning(
            f"RESTORE {status} | Arquivo: {backup_name}"
        )


# Instância global do logger de auditoria
_audit_logger = None

def get_audit_logger():
    """Retorna instância global do logger de auditoria"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = BackupAuditLogger()
    return _audit_logger


def create_backup(reason='automatic', compress=True, silent=False):
    """
    Cria um backup do banco de dados programaticamente

    Args:
        reason: Motivo do backup (automatic, critical_operation, startup, etc)
        compress: Se True, comprime o backup
        silent: Se True, não imprime mensagens no console

    Returns:
        Path do arquivo de backup criado ou None em caso de erro
    """
    try:
        # Importar Config para obter o caminho correto do banco de dados
        from app.config import Config

        # Usar o caminho correto do banco de dados (pode estar em %USERPROFILE%/var/lib/database/database.db)
        db_path = Config.DATABASE_PATH

        # Diretório de backups continua em backend/instance/backups
        backend_dir = Path(__file__).parent.parent.parent
        instance_dir = backend_dir / 'instance'
        backup_dir = instance_dir / 'backups'

        # Criar diretórios se não existirem
        instance_dir.mkdir(exist_ok=True)
        backup_dir.mkdir(exist_ok=True)

        # Criar gerenciador de backups com caminhos explícitos
        backup_mgr = BackupManager(db_path=db_path, backup_dir=backup_dir)

        # Criar backup
        backup_path = backup_mgr.create_backup(compress=compress)

        if backup_path:
            # Registrar no log de auditoria
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            get_audit_logger().log_backup_created(
                backup_path,
                reason=reason,
                size_mb=size_mb
            )

            if not silent:
                print(f"[BACKUP] Backup criado: {backup_path.name} ({reason})")

            return backup_path
        else:
            # Registrar falha
            get_audit_logger().log_backup_failed(
                reason,
                "Falha ao criar backup (retornou None)"
            )
            return None

    except Exception as e:
        # Registrar erro
        error_msg = str(e)
        get_audit_logger().log_backup_failed(reason, error_msg)

        if not silent:
            print(f"[ERRO] Falha ao criar backup: {error_msg}")

        return None


def get_last_backup_time():
    """
    Retorna informações sobre o último backup criado

    Returns:
        Tupla (path, datetime, size_mb) ou None se não houver backups
    """
    try:
        # Importar Config para obter o caminho correto do banco de dados
        from app.config import Config

        # Usar o caminho correto do banco de dados
        db_path = Config.DATABASE_PATH

        # Diretório de backups continua em backend/instance/backups
        backend_dir = Path(__file__).parent.parent.parent
        instance_dir = backend_dir / 'instance'
        backup_dir = instance_dir / 'backups'
        backup_mgr = BackupManager(db_path=db_path, backup_dir=backup_dir)
        backups = backup_mgr.list_backups()

        if backups:
            backup_path, size_mb, mod_time = backups[0]
            return (backup_path, mod_time, size_mb)
        return None
    except Exception as e:
        print(f"[ERRO] Erro ao obter último backup: {e}")
        return None


def has_recent_backup(hours=24):
    """
    Verifica se há backup recente (dentro das últimas N horas)

    Args:
        hours: Número de horas para considerar "recente" (padrão: 24)

    Returns:
        True se há backup recente, False caso contrário
    """
    last_backup = get_last_backup_time()

    if not last_backup:
        return False

    _, mod_time, _ = last_backup
    cutoff_time = datetime.now() - timedelta(hours=hours)

    return mod_time >= cutoff_time


def get_backup_stats():
    """
    Retorna estatísticas dos backups

    Returns:
        Dicionário com estatísticas
    """
    try:
        # Importar Config para obter o caminho correto do banco de dados
        from app.config import Config

        # Usar o caminho correto do banco de dados
        db_path = Config.DATABASE_PATH

        # Diretório de backups continua em backend/instance/backups
        backend_dir = Path(__file__).parent.parent.parent
        instance_dir = backend_dir / 'instance'
        backup_dir = instance_dir / 'backups'
        backup_mgr = BackupManager(db_path=db_path, backup_dir=backup_dir)
        return backup_mgr.get_backup_stats()
    except Exception as e:
        print(f"[ERRO] Erro ao obter estatísticas: {e}")
        return {
            'count': 0,
            'total_size_mb': 0,
            'oldest': None,
            'newest': None
        }

