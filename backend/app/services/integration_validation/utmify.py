# -*- coding: utf-8 -*-
"""Validacoes isoladas do canal UTMify."""

from __future__ import annotations

UTMIFY_TOKEN_MIN_LEN = 16
UTMIFY_PLATFORMS = {"WhatsAppManual", "Loja", "Outro"}


def validate_utmify_api_token(value: str | None) -> tuple[bool, str | None]:
    if not value:
        return False, "Token vazio"
    if len(value) < UTMIFY_TOKEN_MIN_LEN:
        return False, "Token deve ter ao menos 16 caracteres"
    return True, None


def validate_utmify_platform(value: str | None) -> tuple[bool, str | None]:
    if not value:
        return False, "Plataforma vazia"
    if value not in UTMIFY_PLATFORMS:
        return False, f"Plataforma deve ser uma de: {', '.join(sorted(UTMIFY_PLATFORMS))}"
    return True, None
