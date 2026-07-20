# -*- coding: utf-8 -*-
"""OAuth `state` assinado e amarrado ao tenant (Fase B).

O `state` carrega a loja interna (`store_ref_id`) que iniciou o fluxo OAuth, é
assinado com HMAC-SHA256 (derivado de `JWT_SECRET_KEY`/`SECRET_KEY`) e expira. No
callback (sem sessão) validamos assinatura, expiração e provedor antes de associar a
credencial/instalação — assim um fluxo iniciado pela loja A não conclui na loja B, e
o state não pode ser reaproveitado entre provedores (Bling ⇆ Nuvemshop).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

DEFAULT_TTL_SECONDS = 600


def _secret() -> bytes:
    key = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not key:
        raise RuntimeError(
            "JWT_SECRET_KEY (ou SECRET_KEY) não configurada para assinar o OAuth state."
        )
    return key.encode("utf-8")


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _signature(body: str) -> str:
    return _b64e(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())


def sign_state(store_ref_id: int, provider: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Gera um `state` assinado para `provider`, amarrado a `store_ref_id`."""
    payload = {
        "srid": int(store_ref_id),
        "prv": provider,
        "exp": int(time.time()) + int(ttl_seconds),
        "nonce": secrets.token_urlsafe(8),
    }
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return f"{body}.{_signature(body)}"


def verify_state(state: Optional[str], provider: str) -> Optional[dict]:
    """Valida assinatura, provedor e expiração. Retorna o payload ou None."""
    if not state or "." not in state:
        return None
    body, _, signature = state.partition(".")
    if not hmac.compare_digest(signature, _signature(body)):
        return None
    try:
        payload = json.loads(_b64d(body))
    except Exception:
        return None
    if payload.get("prv") != provider:
        return None
    try:
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        payload["srid"] = int(payload["srid"])
    except (TypeError, ValueError):
        return None
    return payload
