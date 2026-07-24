# -*- coding: utf-8 -*-
"""Validacao dos campos da integracao Mercado Pago."""

from __future__ import annotations

from typing import Callable, Optional

HttpGet = Callable[[str, float], tuple[int, dict | str]]


def validate_mercado_pago_access_token(
    value: str | None,
    *,
    http_get: Optional[HttpGet] = None,
) -> tuple[bool, str | None]:
    """Valida o Access Token do Mercado Pago via chamada a /users/me."""
    if not value or not value.strip():
        return False, "Access Token e obrigatorio"

    token = value.strip()
    if len(token) < 20:
        return False, "Access Token muito curto"

    if http_get is None:
        try:
            import requests

            resp = requests.get(
                "https://api.mercadopago.com/users/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            status_code = resp.status_code
            try:
                data = resp.json()
            except Exception:
                data = {}
        except Exception as exc:
            return False, f"Erro de conexao com Mercado Pago: {exc}"
    else:
        status_code, data = http_get(
            "https://api.mercadopago.com/users/me",
            10.0,
        )

    if status_code == 200:
        return True, None
    if status_code == 401:
        return False, "Access Token invalido ou expirado"
    return False, f"Mercado Pago retornou status {status_code}"


def validate_mercado_pago_public_key(
    value: str | None,
    *,
    http_get: Optional[HttpGet] = None,
) -> tuple[bool, str | None]:
    """Valida formato da Public Key do Mercado Pago."""
    if not value or not value.strip():
        return True, None

    key = value.strip()
    if not key.startswith("APP_USR-") and not key.startswith("TEST-"):
        return False, "Public Key deve comecar com APP_USR- ou TEST-"
    if len(key) < 20:
        return False, "Public Key muito curta"
    return True, None


def validate_mercado_pago_client_id(
    value: str | None,
    *,
    http_get: Optional[HttpGet] = None,
) -> tuple[bool, str | None]:
    """Valida formato do Client ID do Mercado Pago."""
    if not value or not value.strip():
        return True, None

    cid = value.strip()
    if len(cid) < 10:
        return False, "Client ID muito curto"
    return True, None


def validate_mercado_pago_client_secret(
    value: str | None,
    *,
    http_get: Optional[HttpGet] = None,
) -> tuple[bool, str | None]:
    """Valida formato do Client Secret do Mercado Pago."""
    if not value or not value.strip():
        return True, None

    secret = value.strip()
    if len(secret) < 10:
        return False, "Client Secret muito curto"
    return True, None
