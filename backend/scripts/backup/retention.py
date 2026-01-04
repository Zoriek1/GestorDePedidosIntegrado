# -*- coding: utf-8 -*-
"""
Módulo de Retenção GFS (Grandfather-Father-Son) (P1.2)
Implementa política de retenção tipo GFS para backups
"""
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class BackupSlot(Enum):
    """Slot de retenção GFS"""
    HOURLY = 'hourly'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'


@dataclass
class GFSRetentionPolicy:
    """Política de retenção GFS"""
    hourly: int = 48
    daily: int = 30
    weekly: int = 12
    monthly: int = 12


def extract_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """
    Extrai timestamp do nome do arquivo de backup

    Formato esperado: database_YYYYMMDD_HHMMSS.*

    Returns:
        datetime ou None se não conseguir extrair
    """
    pattern = r'database_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})'
    match = re.search(pattern, filename)

    if not match:
        return None

    try:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        second = int(match.group(6))

        return datetime(year, month, day, hour, minute, second)
    except (ValueError, IndexError):
        return None


def categorize_backup_slot(dt: datetime) -> BackupSlot:
    """
    Categoriza backup em slot GFS

    Args:
        dt: Timestamp do backup

    Returns:
        BackupSlot correspondente
    """
    now = datetime.now()

    # Se backup é muito antigo (mais de 1 mês), sempre MONTHLY
    if (now - dt).days > 30:
        return BackupSlot.MONTHLY

    # Se backup é de hoje, HOURLY
    if dt.date() == now.date():
        return BackupSlot.HOURLY

    # Se backup é desta semana, DAILY
    # Usar ISO week (segunda-feira = início da semana)
    dt_week = dt.isocalendar()[1]
    dt_year = dt.isocalendar()[0]
    now_week = now.isocalendar()[1]
    now_year = now.isocalendar()[0]

    if dt_week == now_week and dt_year == now_year:
        return BackupSlot.DAILY

    # Se backup é deste mês mas não desta semana, WEEKLY
    if dt.month == now.month and dt.year == now.year:
        return BackupSlot.WEEKLY

    # Caso contrário, MONTHLY
    return BackupSlot.MONTHLY


def apply_gfs_retention(
    files: List[Path],
    policy: GFSRetentionPolicy
) -> Dict[str, List[Path]]:
    """
    Aplica política de retenção GFS

    Args:
        files: Lista de arquivos de backup
        policy: Política de retenção GFS

    Returns:
        Dict com 'keep' e 'delete' (listas de Path)
    """
    # Extrair timestamps e categorizar
    backups_with_slots = []

    for file_path in files:
        timestamp = extract_timestamp_from_filename(file_path.name)
        if not timestamp:
            # Se não conseguir extrair timestamp, manter (não deletar)
            backups_with_slots.append((file_path, timestamp, BackupSlot.HOURLY))
            continue

        slot = categorize_backup_slot(timestamp)
        backups_with_slots.append((file_path, timestamp, slot))

    # Ordenar por timestamp (mais recente primeiro)
    backups_with_slots.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)

    # Agrupar por slot
    slots = {
        BackupSlot.HOURLY: [],
        BackupSlot.DAILY: [],
        BackupSlot.WEEKLY: [],
        BackupSlot.MONTHLY: []
    }

    for file_path, timestamp, slot in backups_with_slots:
        slots[slot].append((file_path, timestamp))

    # Aplicar limites por slot
    to_keep = []
    to_delete = []

    slot_limits = {
        BackupSlot.HOURLY: policy.hourly,
        BackupSlot.DAILY: policy.daily,
        BackupSlot.WEEKLY: policy.weekly,
        BackupSlot.MONTHLY: policy.monthly
    }

    for slot, limit in slot_limits.items():
        backups_in_slot = slots[slot]

        # Manter N mais recentes
        keep_count = min(len(backups_in_slot), limit)
        for i in range(keep_count):
            to_keep.append(backups_in_slot[i][0])

        # Deletar o resto
        for i in range(keep_count, len(backups_in_slot)):
            to_delete.append(backups_in_slot[i][0])

    return {
        'keep': to_keep,
        'delete': to_delete
    }

