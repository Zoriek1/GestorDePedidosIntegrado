# -*- coding: utf-8 -*-
"""
Módulo de Status de Backup (P1.5)
Gerencia status persistente do sistema de backup
"""
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import Config  # noqa: E402


@dataclass
class BackupStatus:
    """Status do sistema de backup"""

    last_backup_ok_at: Optional[str] = None  # ISO format
    last_backup_error: Optional[str] = None
    last_remote_ok_at: Optional[str] = None  # ISO format
    last_remote_error: Optional[str] = None
    last_restore_test_ok_at: Optional[str] = None  # ISO format
    last_restore_test_error: Optional[str] = None
    last_cleanup_ok_at: Optional[str] = None  # ISO format
    last_cleanup_error: Optional[str] = None
    backups_local_count: int = 0
    backups_remote_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return asdict(self)


def get_status_file_path() -> Path:
    """Retorna caminho do arquivo de status"""
    return Config.INSTANCE_DIR / "backup_status.json"


def read_backup_status() -> BackupStatus:
    """
    Lê status de backup do arquivo JSON

    Returns:
        BackupStatus com dados do arquivo ou valores padrão
    """
    status_file = get_status_file_path()

    if not status_file.exists():
        return BackupStatus()

    try:
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Converter para BackupStatus
        return BackupStatus(**data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # Se arquivo corrompido, retornar status vazio
        print(f"[AVISO] Erro ao ler backup_status.json: {e}. Retornando status vazio.")
        return BackupStatus()


def update_backup_status(**kwargs) -> None:
    """
    Atualiza status de backup (escrita atômica)

    Args:
        **kwargs: Campos para atualizar (ex: last_backup_ok_at=datetime.now().isoformat())
    """
    status_file = get_status_file_path()

    # Garantir que diretório existe
    status_file.parent.mkdir(parents=True, exist_ok=True)

    # Ler status atual
    current_status = read_backup_status()

    # Atualizar campos
    for key, value in kwargs.items():
        if hasattr(current_status, key):
            # Converter datetime para ISO string se necessário
            if isinstance(value, datetime):
                value = value.isoformat()
            setattr(current_status, key, value)

    # Escrita atômica: escrever para temp e depois renomear
    temp_file = status_file.with_suffix(".json.tmp")

    try:
        # Escrever para arquivo temporário
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(current_status.to_dict(), f, indent=2, ensure_ascii=False)

        # Renomear (atômico no mesmo filesystem)
        if sys.platform == "win32":
            # Windows pode ter problemas com rename se arquivo existe
            if status_file.exists():
                status_file.unlink()
        temp_file.replace(status_file)

    except Exception as e:
        # Limpar temp file em caso de erro
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
        raise Exception(f"Erro ao atualizar backup_status.json: {e}") from e


def get_backup_health(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Calcula health do sistema de backup

    Args:
        max_age_hours: Idade máxima em horas para considerar backup válido

    Returns:
        Dict com 'health' ('OK'|'WARN'|'FAIL'), 'status', 'issues'
    """
    status = read_backup_status()
    issues = []
    health = "OK"

    now = datetime.now()
    max_age_delta = max_age_hours * 3600  # em segundos

    # Verificar último backup OK
    if status.last_backup_ok_at:
        try:
            last_backup_dt = datetime.fromisoformat(status.last_backup_ok_at)
            age_seconds = (now - last_backup_dt).total_seconds()
            if age_seconds > max_age_delta:
                issues.append(f"Último backup OK há mais de {max_age_hours} horas")
                health = "FAIL"
        except (ValueError, TypeError):
            issues.append("Data do último backup OK inválida")
            health = "FAIL"
    else:
        issues.append("Nenhum backup OK registrado")
        health = "FAIL"

    # Verificar último restore test
    if status.last_restore_test_error:
        issues.append(f"Último restore test falhou: {status.last_restore_test_error}")
        health = "FAIL"

    # Verificar remoto (WARN apenas)
    if status.last_remote_error:
        issues.append(f"Último backup remoto falhou: {status.last_remote_error}")
        if health == "OK":
            health = "WARN"
    elif status.last_remote_ok_at:
        try:
            last_remote_dt = datetime.fromisoformat(status.last_remote_ok_at)
            age_seconds = (now - last_remote_dt).total_seconds()
            if age_seconds > max_age_delta:
                issues.append(f"Último backup remoto OK há mais de {max_age_hours} horas")
                if health == "OK":
                    health = "WARN"
        except (ValueError, TypeError):
            pass  # Ignorar erro de parsing, não é crítico

    # Verificar cleanup (WARN apenas)
    if status.last_cleanup_error:
        issues.append(f"Último cleanup falhou: {status.last_cleanup_error}")
        if health == "OK":
            health = "WARN"

    return {"health": health, "status": status.to_dict(), "issues": issues}
