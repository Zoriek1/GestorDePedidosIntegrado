# -*- coding: utf-8 -*-
"""Token público assinado e com expiração para acompanhamento de pedido (itsdangerous).

Deriva o token do id do pedido + assinatura HMAC com timestamp embutido. Sem coluna
nova nem migration: funciona em todos os pedidos (inclusive antigos). Enumeração é
inviável sem a SECRET_KEY. Revogação em massa = trocar o sufixo de ``_SALT`` (v2…).
Links expiram após ``TRACK_TOKEN_MAX_AGE_DAYS`` (default 60 dias).
"""
import os

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

# Trocar o sufixo (v2…) invalida todos os links antigos.
_SALT = "pedido-track-v1"


def _max_age_seconds() -> int:
    try:
        days = int(os.environ.get("TRACK_TOKEN_MAX_AGE_DAYS") or 60)
    except (ValueError, TypeError):
        days = 60
    return days * 86400


def _secret_key() -> str:
    # Mesma resolução do auth_service: config["SECRET_KEY"] pode estar "".
    key = (
        os.environ.get("JWT_SECRET_KEY")
        or os.environ.get("SECRET_KEY")
        or current_app.config.get("SECRET_KEY")
    )
    if not key:
        raise RuntimeError(
            "SECRET_KEY/JWT_SECRET_KEY não configurada para gerar o token de acompanhamento."
        )
    return key


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_secret_key(), salt=_SALT)


def make_track_token(pedido_id: int) -> str:
    """Gera o token público assinado para o pedido."""
    return _serializer().dumps({"pid": int(pedido_id)})


def parse_track_token(token: str) -> int | None:
    """Retorna o pedido_id, ou None se o token for inválido OU expirado (> max_age)."""
    try:
        data = _serializer().loads(token, max_age=_max_age_seconds())
        return int(data["pid"])
    except (SignatureExpired, BadSignature, KeyError, ValueError, TypeError):
        return None
