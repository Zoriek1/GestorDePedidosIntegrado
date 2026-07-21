# -*- coding: utf-8 -*-
"""Servicos de validacao isolada por canal de integracao.

Cada funcao `validate_<channel>_<field>` recebe o valor bruto (string) e
retorna `(ok: bool, error: str | None)`. Implementacoes NAO devem ecoar
segredos em mensagens de erro ou logs.

Timeouts curtos (5s) para nao bloquear a request do admin.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

# Funcao injetavel para HTTP GET (permite mock em testes).
HttpGet = Callable[[str, float], tuple[int, dict | str]]

DEFAULT_TIMEOUT_S = 5.0


def _safe_message(prefix: str, exc: Exception) -> str:
    """Mensagem curta e sem segredos."""
    return f"{prefix}: {type(exc).__name__}"


# =============================================================================
# Meta CAPI
# =============================================================================

META_PIXEL_ID_RE = re.compile(r"^\d{6,30}$")
META_TOKEN_MIN_LEN = 20


def validate_meta_pixel_id(value: str | None) -> tuple[bool, str | None]:
    if not value:
        return False, "Meta Pixel ID vazio"
    if not META_PIXEL_ID_RE.match(value):
        return False, "Meta Pixel ID deve ter 6-30 digitos"
    return True, None


def validate_meta_capi_access_token(
    value: str | None,
    *,
    http_get: Optional[HttpGet] = None,
) -> tuple[bool, str | None]:
    if not value:
        return False, "Token vazio"
    if len(value) < META_TOKEN_MIN_LEN:
        return False, "Token muito curto"
    get = http_get or _default_http_get
    try:
        status, _ = get(
            "https://graph.facebook.com/v18.0/me?fields=id",
            DEFAULT_TIMEOUT_S,
        )
    except Exception as exc:
        return False, _safe_message("Falha ao contatar Meta", exc)
    if status == 200:
        return True, None
    if status in (401, 403):
        return False, "Token invalido ou expirado"
    return False, f"Meta respondeu HTTP {status}"


def _default_http_get(url: str, timeout: float) -> tuple[int, dict | str]:
    """Wrapper sobre requests.get para mock via injecao."""
    import requests

    response = requests.get(url, timeout=timeout, headers={"Accept": "application/json"})
    try:
        body: dict | str = response.json()
    except ValueError:
        body = response.text
    return response.status_code, body
