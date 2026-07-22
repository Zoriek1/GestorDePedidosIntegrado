# -*- coding: utf-8 -*-
"""Validacoes isoladas do canal Dados Operacionais."""

from __future__ import annotations

import re
from typing import Optional

from .meta_capi import DEFAULT_TIMEOUT_S, HttpGet, _default_http_get, _safe_message

LOJA_CEP_RE = re.compile(r"^\d{5}-?\d{3}$")
MAX_ENDERECO_LEN = 255


def validate_loja_cep(
    value: str | None,
    *,
    http_get: Optional[HttpGet] = None,
) -> tuple[bool, str | None]:
    if not value:
        return False, "CEP vazio"
    if not LOJA_CEP_RE.match(value):
        return False, "CEP deve estar no formato 00000-000"
    get = http_get or _default_http_get
    clean = re.sub(r"\D", "", value)
    try:
        status, body = get(
            f"https://viacep.com.br/ws/{clean}/json/",
            DEFAULT_TIMEOUT_S,
        )
    except Exception as exc:
        return False, _safe_message("Falha ao consultar ViaCEP", exc)
    if status != 200:
        return False, f"ViaCEP respondeu HTTP {status}"
    if not isinstance(body, dict):
        return False, "Resposta ViaCEP invalida"
    if body.get("erro") is True:
        return False, "CEP nao encontrado"
    return True, None


def validate_endereco_floricultura(value: str | None) -> tuple[bool, str | None]:
    if value and len(value) > MAX_ENDERECO_LEN:
        return False, f"Endereco excede {MAX_ENDERECO_LEN} caracteres"
    return True, None
