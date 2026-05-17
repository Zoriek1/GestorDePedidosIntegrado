# -*- coding: utf-8 -*-
"""
AuthService — JWT encoding/decoding e bcrypt hash/verify
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt


def _secret() -> str:
    key = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not key:
        raise RuntimeError(
            "JWT_SECRET_KEY (ou SECRET_KEY) não configurada. "
            "Defina a variável de ambiente para assinar tokens JWT."
        )
    return key


def _expiration_hours() -> int:
    try:
        return int(os.environ.get("JWT_EXPIRATION_HOURS") or 24)
    except (ValueError, TypeError):
        return 24


def _bcrypt_rounds() -> int:
    try:
        return int(os.environ.get("BCRYPT_LOG_ROUNDS") or 12)
    except (ValueError, TypeError):
        return 12


def hash_password(plain: str) -> str:
    """Retorna hash bcrypt da senha fornecida."""
    rounds = _bcrypt_rounds()
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica se a senha plain corresponde ao hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def generate_token(user) -> str:
    """Gera JWT HS256 com payload {user_id, role, exp}."""
    exp = datetime.now(timezone.utc) + timedelta(hours=_expiration_hours())
    payload = {
        "user_id": user.id,
        "role": user.role,
        "name": user.name,
        "email": user.email,
        "exp": exp,
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    """
    Decodifica e valida um JWT Bearer token.
    Retorna o payload dict ou None se inválido/expirado.
    """
    try:
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    """Extrai o token de um header 'Authorization: Bearer <token>'."""
    if not authorization_header:
        return None
    parts = authorization_header.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None
