# -*- coding: utf-8 -*-
"""Criptografia versionada para segredos persistidos pela aplicacao."""

import base64
import hashlib
import os
from typing import Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app

Purpose = Union[str, bytes]


def _purpose_bytes(purpose: Purpose) -> bytes:
    raw = purpose.encode("utf-8") if isinstance(purpose, str) else purpose
    if not raw:
        raise ValueError("purpose obrigatorio para criptografia")
    return raw


def derive_key(purpose: Purpose) -> bytes:
    secret = (current_app.config.get("SECRET_KEY") or "").encode("utf-8")
    if not secret:
        raise RuntimeError("SECRET_KEY obrigatoria para criptografia")
    return hashlib.sha256(secret + _purpose_bytes(purpose)).digest()


def encrypt_secret(value: Optional[str], purpose: Purpose) -> Optional[str]:
    if not value:
        return None
    nonce = os.urandom(12)
    ciphertext = AESGCM(derive_key(purpose)).encrypt(
        nonce,
        value.encode("utf-8"),
        associated_data=None,
    )
    encoded = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"v1:{encoded}"


def decrypt_secret(value: Optional[str], purpose: Purpose) -> Optional[str]:
    if not value:
        return None
    if not value.startswith("v1:"):
        return value
    blob = base64.urlsafe_b64decode(value.split(":", 1)[1].encode("ascii"))
    if len(blob) < 13:
        raise ValueError("segredo criptografado invalido")
    return (
        AESGCM(derive_key(purpose))
        .decrypt(
            blob[:12],
            blob[12:],
            associated_data=None,
        )
        .decode("utf-8")
    )
