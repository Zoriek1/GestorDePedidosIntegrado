# -*- coding: utf-8 -*-
"""Resolucao central da identidade autenticada (usuario + loja) por request.

Fase A do multi-tenant. Evita duplicacao entre os decorators de auth
(`require_auth` em decorators/auth_decorator.py e `requires_role`/`requires_any_role`/
`requires_edit_auth` em middleware.py).

Regras:
- O tenant NUNCA vem de body/query string/header comum: e sempre derivado do usuario
  autenticado no banco.
- Nao confiamos apenas nas claims do JWT: usuario e loja sao confirmados no banco.
- Compatibilidade de rollout: usuario com store_ref_id NULL resolve a loja `default`
  por slug; se nem a default existir (bancos de teste legados), a request segue com
  `g.current_store = None` (sem bloqueio). O bloqueio estrito por loja ausente fica no
  login e nas rotas com escopo de tenant.
"""

from __future__ import annotations

from typing import Optional, Tuple

from flask import g, request

from app import db
from app.models.store import Store
from app.models.user import User

DEFAULT_STORE_SLUG = "default"

# Tipo do resultado: (current_user_dict | None, error | None)
# error = (body_dict, status_code)
IdentityError = Tuple[dict, int]


def resolve_user_store(user: User) -> Optional[Store]:
    """Resolve a loja de um usuario.

    Usa `user.store_ref_id` quando presente; caso contrario cai na loja `default`
    (compat durante o rollout, enquanto a coluna e nullable).
    """
    store_ref_id = getattr(user, "store_ref_id", None)
    if store_ref_id is not None:
        return db.session.get(Store, store_ref_id)
    return Store.query.filter_by(slug=DEFAULT_STORE_SLUG).first()


def load_request_identity(
    payload: dict,
) -> Tuple[Optional[dict], Optional[IdentityError]]:
    """Carrega usuario + loja do banco a partir de um payload JWT ja decodificado.

    Em sucesso: popula `g.current_store` e `request.current_user` e retorna
    `(current_user, None)`. Em falha de autenticacao: retorna `(None, (body, status))`.
    """
    user_id = payload.get("user_id")
    user = User.query.filter_by(id=user_id, is_active=True).first() if user_id else None
    if not user:
        return None, (
            {
                "error": "Acesso negado",
                "message": "Usuario nao encontrado ou inativo. Faca login novamente.",
            },
            401,
        )

    store_ref_id = getattr(user, "store_ref_id", None)
    store = resolve_user_store(user)

    # store_ref_id explicito porem sem loja correspondente -> vinculo orfao.
    if store_ref_id is not None and store is None:
        return None, (
            {
                "error": "Acesso negado",
                "message": "Loja do usuario nao encontrada.",
            },
            403,
        )

    # Loja resolvida porem inativa -> bloqueia.
    if store is not None and not store.active:
        return None, (
            {
                "error": "Acesso negado",
                "message": "Loja inativa.",
            },
            403,
        )

    # store pode ser None apenas no fallback legado (sem loja default no banco).
    g.current_store = store

    current_user = dict(payload)
    current_user.update(
        {
            "user_id": user.id,
            "role": user.role,
            "name": user.name,
            "email": user.email,
            "store_ref_id": store.id if store else None,
            "store_slug": store.slug if store else None,
        }
    )
    request.current_user = current_user
    return current_user, None
