# -*- coding: utf-8 -*-
"""
Módulo de Verificação Remota de Backup (P1.3)
Verifica que backup foi realmente recebido no diretório remoto
"""
import hashlib
import shutil
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def copy_and_verify_remote(
    source: Path,
    dest_dir: Path,
    check_hash: bool = False,
    stability_wait_seconds: int = 3,
) -> Tuple[bool, Optional[str]]:
    """
    Copia arquivo para diretório remoto e verifica recebimento

    Args:
        source: Caminho do arquivo de origem
        dest_dir: Diretório de destino (remoto)
        check_hash: Se True, verifica hash SHA-256 (mais lento)
        stability_wait_seconds: Segundos para esperar antes de stability check

    Returns:
        (success, error_message) - success=True se tudo OK, error_message=None se sucesso
    """
    if not source.exists():
        return False, f"Arquivo de origem não existe: {source}"

    # Garantir que diretório de destino existe
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return False, f"Não foi possível criar diretório de destino: {e}"

    # Copiar arquivo
    dest_file = dest_dir / source.name
    try:
        shutil.copy2(source, dest_file)
    except Exception as e:
        return False, f"Erro ao copiar arquivo: {e}"

    # 1. Verificar arquivo existe no destino
    if not dest_file.exists():
        return False, "Arquivo não encontrado no destino após cópia"

    # 2. Verificar tamanho bate com origem
    source_size = source.stat().st_size
    dest_size = dest_file.stat().st_size

    if source_size != dest_size:
        return False, f"Tamanho diferente: origem={source_size}, destino={dest_size}"

    # 3. Stability check: re-checar tamanho após alguns segundos
    if stability_wait_seconds > 0:
        time.sleep(stability_wait_seconds)
        dest_size_after = dest_file.stat().st_size

        if dest_size_after != source_size:
            return (
                False,
                f"Tamanho mudou após stability check: {dest_size_after} != {source_size} (arquivo ainda sendo escrito?)",
            )

    # 4. Hash opcional (SHA-256)
    if check_hash:
        try:
            source_hash = _calculate_file_hash(source)
            dest_hash = _calculate_file_hash(dest_file)

            if source_hash != dest_hash:
                return (
                    False,
                    f"Hash diferente: origem={source_hash[:16]}..., destino={dest_hash[:16]}...",
                )
        except Exception as e:
            return False, f"Erro ao calcular hash: {e}"

    return True, None


def _calculate_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Calcula hash SHA-256 de arquivo

    Args:
        file_path: Caminho do arquivo
        chunk_size: Tamanho do chunk para leitura

    Returns:
        Hash hexadecimal SHA-256
    """
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest()
