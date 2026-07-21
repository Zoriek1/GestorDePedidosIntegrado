# -*- coding: utf-8 -*-
"""Validacoes isoladas do canal GA4."""

from __future__ import annotations

import re
from typing import Optional

from .meta_capi import DEFAULT_TIMEOUT_S, HttpGet, _default_http_get, _safe_message

GA4_MEASUREMENT_ID_RE = re.compile(r"^G-[A-Z0-9]{4,12}$", re.IGNORECASE)
GA4_API_SECRET_MIN_LEN = 16


def validate_ga4_measurement_id(value: str | None) -> tuple[bool, str | None]:
    if not value:
        return False, "Measurement ID vazio"
    if not GA4_MEASUREMENT_ID_RE.match(value):
        return False, "Measurement ID deve estar no formato G-XXXXX"
    return True, None


def validate_ga4_api_secret(
    value: str | None,
    *,
    measurement_id: str | None = None,
    http_get: Optional[HttpGet] = None,
) -> tuple[bool, str | None]:
    if not value:
        return False, "API secret vazio"
    if len(value) < GA4_API_SECRET_MIN_LEN:
        return False, "API secret deve ter ao menos 16 caracteres"
    # Auth check real usa measurement_id + secret via Measurement Protocol
    # validation endpoint; sem rede o teste reduz-se a formato.
    if not measurement_id:
        return True, None
    get = http_get or _default_http_get
    url = (
        "https://www.google-analytics.com/debug/collect"
        f"?measurement_id={measurement_id}&api_secret={value}"
    )
    try:
        status, body = get(url, DEFAULT_TIMEOUT_S)
    except Exception as exc:
        return False, _safe_message("Falha ao contatar GA4", exc)
    if status == 200:
        # GA4 devolve 200 mesmo para payload invalido; em sucesso, body nao traz erro fatal.
        if isinstance(body, dict) and body.get("validationMessages"):
            return False, "API secret rejeitado pela GA4"
        return True, None
    return False, f"GA4 respondeu HTTP {status}"
