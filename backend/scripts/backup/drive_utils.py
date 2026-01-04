# -*- coding: utf-8 -*-
"""
Utilitários para Detecção de Drive (P1.4)
Detecta drives no Windows para verificar separação física
"""
import os
import sys
from pathlib import Path
from typing import List, Optional


def get_drive_letter(path: Path) -> Optional[str]:
    """
    Extrai letra do drive de um caminho (Windows)

    Args:
        path: Caminho do arquivo/diretório

    Returns:
        Letra do drive (ex: 'C:') ou None se não conseguir determinar
    """
    if sys.platform != "win32":
        # Apenas Windows tem drives (C:, D:, etc)
        return None

    try:
        drive, _ = os.path.splitdrive(str(path))
        return drive.upper() if drive else None
    except Exception:
        return None


def check_drive_separation(
    db_path: Path, backup_dir: Path, secondary_dir: Optional[Path] = None
) -> List[str]:
    """
    Verifica separação de drives e retorna warnings se necessário

    Args:
        db_path: Caminho do banco de dados
        backup_dir: Diretório de backups locais
        secondary_dir: Diretório secundário de backups (opcional)

    Returns:
        Lista de mensagens de warning (vazia se tudo OK)
    """
    warnings = []

    if sys.platform != "win32":
        # Apenas Windows - em outros sistemas não há conceito de drive
        return warnings

    db_drive = get_drive_letter(db_path)
    backup_drive = get_drive_letter(backup_dir)

    if not db_drive or not backup_drive:
        # Não foi possível determinar drives - não gerar warning
        return warnings

    # Verificar se DB e backup local estão no mesmo drive
    if db_drive == backup_drive:
        warnings.append(
            f"Banco de dados e backup local estão no mesmo drive ({db_drive}). "
            f"Considere usar BACKUP_SECONDARY_DIR em outro drive para proteção adicional."
        )

    # Verificar secondary_dir se definido
    if secondary_dir:
        secondary_drive = get_drive_letter(secondary_dir)

        if secondary_drive:
            if secondary_drive == db_drive:
                warnings.append(
                    f"Diretório secundário está no mesmo drive do banco ({db_drive}). "
                    f"Para proteção ideal, use um drive diferente."
                )
            if secondary_drive == backup_drive:
                warnings.append(
                    f"Diretório secundário está no mesmo drive do backup local ({backup_drive}). "
                    f"Para proteção ideal, use um drive diferente."
                )

    return warnings
