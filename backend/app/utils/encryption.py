"""
Utilidades de encriptação para backups.

Algoritmo: AES-256-GCM (via cryptography AESGCM)
- Chave 32 bytes, armazenada em BACKUP_ENCRYPTION_KEY (base64 urlsafe)
- Formato do arquivo encriptado: b'v1' + nonce(12) + ciphertext+tag
"""
import base64
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv

from app.config import Config

ENV_KEY_NAME = "BACKUP_ENCRYPTION_KEY"
DEFAULT_ENV_PATH = Config.BASE_DIR / ".env"
HEADER = b"v1"
NONCE_SIZE = 12
KEY_SIZE = 32  # 256 bits


class EncryptionError(Exception):
    """Erro genérico de encriptação."""


def _decode_key(key_str: str) -> bytes:
    try:
        key_bytes = base64.urlsafe_b64decode(key_str)
    except Exception as exc:
        raise EncryptionError(f"Chave inválida (base64): {exc}") from exc

    if len(key_bytes) != KEY_SIZE:
        raise EncryptionError(f"Chave deve ter {KEY_SIZE} bytes (atual: {len(key_bytes)}).")
    return key_bytes


def generate_key() -> str:
    """Gera chave AES-256 (base64 urlsafe)."""
    return base64.urlsafe_b64encode(os.urandom(KEY_SIZE)).decode("utf-8")


def ensure_env_key(env_path: Optional[Path] = None) -> str:
    """
    Retorna a chave a partir da variável de ambiente ou cria/insere no .env.
    """
    env_path = env_path or DEFAULT_ENV_PATH

    # Carregar .env se existir
    load_dotenv(env_path)
    key = os.environ.get(ENV_KEY_NAME)
    if key:
        return key

    # Gerar nova chave e persistir no .env
    key = generate_key()
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Acrescentar ao .env preservando conteúdo existente
    existing = ""
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")
        if existing and not existing.endswith("\n"):
            existing += "\n"
    env_path.write_text(f"{existing}{ENV_KEY_NAME}={key}\n", encoding="utf-8")

    # Atualizar variável de ambiente atual
    os.environ[ENV_KEY_NAME] = key
    return key


def encrypt_file(src: Path, dst: Optional[Path] = None, key: Optional[str] = None) -> Path:
    """
    Encripta arquivo com AES-256-GCM.
    Args:
        src: arquivo de origem
        dst: destino (padrão: src + '.enc')
        key: chave base64 urlsafe (32 bytes). Se None, usa ensure_env_key().
    """
    src = Path(src)
    if not src.exists():
        raise EncryptionError(f"Arquivo não encontrado: {src}")

    key = key or ensure_env_key()
    key_bytes = _decode_key(key)

    data = src.read_bytes()
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, data, associated_data=None)

    dst = dst or src.with_suffix(src.suffix + ".enc")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(HEADER + nonce + ciphertext)
    return dst


def decrypt_file(src: Path, dst: Optional[Path] = None, key: Optional[str] = None) -> Path:
    """
    Desencripta arquivo gerado por encrypt_file.
    """
    src = Path(src)
    if not src.exists():
        raise EncryptionError(f"Arquivo não encontrado: {src}")

    blob = src.read_bytes()
    if not blob.startswith(HEADER):
        raise EncryptionError("Formato de arquivo encriptado inválido (header).")

    key = key or ensure_env_key()
    key_bytes = _decode_key(key)

    nonce = blob[len(HEADER) : len(HEADER) + NONCE_SIZE]
    ciphertext = blob[len(HEADER) + NONCE_SIZE :]

    aesgcm = AESGCM(key_bytes)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    except Exception as exc:
        raise EncryptionError(f"Falha ao desencriptar: {exc}") from exc

    dst = dst or src.with_suffix("")  # remove .enc
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(plaintext)
    return dst


__all__ = ["ensure_env_key", "encrypt_file", "decrypt_file", "EncryptionError", "generate_key"]

