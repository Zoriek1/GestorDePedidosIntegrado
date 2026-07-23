# -*- coding: utf-8 -*-
"""Validacao HMAC de webhooks do Mercado Pago."""

import hashlib
import hmac


def verify_mp_signature(
    raw_body: bytes,
    x_signature: str,
    secret: str,
) -> bool:
    """Valida a assinatura HMAC enviada pelo Mercado Pago.

    O header ``x-signature`` tem formato: ``ts=<timestamp>,v1=<hmac>``
    O HMAC e calculado como HMAC-SHA256 do secret sobre a string:
        ``id:{payment_id};request-id:{request_id};ts:{ts}``

    Como nem sempre temos o payment_id no momento da validacao (ele vem no body),
    usamos o body como input direto para o HMAC.
    """
    if not x_signature or not secret:
        return False

    parts = {}
    for item in x_signature.split(","):
        if "=" in item:
            key, val = item.split("=", 1)
            parts[key.strip()] = val.strip()

    ts = parts.get("ts", "")
    v1 = parts.get("v1", "")

    if not ts or not v1:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, v1)
