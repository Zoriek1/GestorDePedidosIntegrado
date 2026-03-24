# -*- coding: utf-8 -*-
"""
Utilitários para token de rastreio do WhatsApp.
"""
from __future__ import annotations

import re
from urllib.parse import unquote

CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_TOKEN_RE = re.compile(r"^[A-Z0-9]{10}$")
_COD_RE = re.compile(r"\[Cod:\s*([A-Z0-9]{10})\]", re.IGNORECASE)


def normalize_tracking_token(value: object) -> str | None:
    if value is None:
        return None
    token = str(value).strip().upper()
    return token or None


def calculate_checksum(base_token: str) -> str:
    sum_a = 0
    sum_b = 0
    for i, ch in enumerate(base_token):
        v = CHARS.find(ch)
        if v < 0:
            continue
        sum_a += v * (i + 1)
        sum_b += v * (i + 3)
    first = CHARS[sum_a % len(CHARS)]
    second = CHARS[(sum_a + sum_b) % len(CHARS)]
    return f"{first}{second}"


def is_tracking_token_valid(token: str | None) -> bool:
    if not token:
        return False
    t = token.strip().upper()
    if not _TOKEN_RE.fullmatch(t):
        return False
    base = t[:8]
    checksum = t[8:]
    return calculate_checksum(base) == checksum


def extract_tracking_token_from_text(text: str | None) -> str | None:
    if not text:
        return None

    decoded = unquote(str(text))
    match = _COD_RE.search(decoded)
    if match:
        return match.group(1).upper()

    raw = normalize_tracking_token(decoded)
    if raw and _TOKEN_RE.fullmatch(raw):
        return raw
    return None
