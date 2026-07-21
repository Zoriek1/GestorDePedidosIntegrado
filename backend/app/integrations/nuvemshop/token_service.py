# -*- coding: utf-8 -*-
"""Encrypt/decrypt Nuvemshop access tokens at rest."""

from app.utils.crypto import decrypt_secret, encrypt_secret

NUVEMSHOP_CRYPTO_PURPOSE = b":nuvemshop-oauth"


def encrypt_token(value: str | None) -> str | None:
    """Encrypt a plaintext token. Returns v1:... format."""
    if not value:
        return None
    return encrypt_secret(value, NUVEMSHOP_CRYPTO_PURPOSE)


def decrypt_token(value: str | None) -> str | None:
    """Decrypt a token. Passes through non-v1: strings (backward compat)."""
    if not value:
        return None
    return decrypt_secret(value, NUVEMSHOP_CRYPTO_PURPOSE)
