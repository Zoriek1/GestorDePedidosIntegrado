# -*- coding: utf-8 -*-
"""Token público curto e assinado para acompanhamento de pedido.

Formato compacto (#14): ``base62(pedido_id)`` + assinatura HMAC-SHA256 truncada
(``_SIG_LEN`` chars). Ex.: ``1fAb3kZ9Qw`` (~12-14 chars, vs dezenas do formato antigo
baseado em itsdangerous). Sem coluna nova nem migration — funciona em qualquer pedido.

Enumeração/forja é inviável sem a SECRET_KEY (a assinatura depende dela); a rota responde
404 genérico para não revelar ids. Revogação em massa = trocar o sufixo de ``_SALT`` (v2…).

Diferença vs versão anterior: o token **não expira mais** (o formato compacto não embute
timestamp). Links antigos (formato itsdangerous) deixam de validar — reenvie o link.
"""
import base64
import hashlib
import hmac
import os

from flask import current_app

# Trocar o sufixo (v2…) invalida todos os links antigos.
_SALT = "pedido-track-v1"
# Tamanho da assinatura truncada (chars base64url). 10 chars ~= 60 bits — suficiente para
# um link público sem dados sensíveis, combinado com 404 genérico.
_SIG_LEN = 10

_B62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


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


def _b62_encode(n: int) -> str:
    if n <= 0:
        return "0"
    out = []
    while n > 0:
        n, r = divmod(n, 62)
        out.append(_B62[r])
    return "".join(reversed(out))


def _b62_decode(s: str) -> int:
    n = 0
    for ch in s:
        n = n * 62 + _B62.index(ch)  # ValueError se char inválido — tratado pelo caller
    return n


def _sign(pid_b62: str) -> str:
    key = _secret_key().encode("utf-8")
    msg = f"{_SALT}:{pid_b62}".encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha256).digest()
    b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return b64[:_SIG_LEN]


def make_track_token(pedido_id: int) -> str:
    """Gera o token público curto e assinado para o pedido."""
    pid_b62 = _b62_encode(int(pedido_id))
    return f"{pid_b62}{_sign(pid_b62)}"


def build_track_url(pedido_id: int) -> str:
    """Monta a URL pública de acompanhamento (base via env, sem hardcode)."""
    base = (
        os.environ.get("PUBLIC_BASE_URL")
        or os.environ.get("NUVEMSHOP_PUBLIC_BASE_URL")
        or "https://gestaopedidos.planteumaflor.online"
    )
    return f"{base.rstrip('/')}/acompanhar/{make_track_token(pedido_id)}"


def parse_track_token(token: str) -> int | None:
    """Retorna o pedido_id, ou None se o token for inválido/forjado."""
    try:
        if not token or len(token) <= _SIG_LEN:
            return None
        pid_b62 = token[:-_SIG_LEN]
        sig = token[-_SIG_LEN:]
        if not pid_b62 or not hmac.compare_digest(sig, _sign(pid_b62)):
            return None
        return _b62_decode(pid_b62)
    except (ValueError, TypeError):
        return None
