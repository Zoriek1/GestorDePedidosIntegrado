# -*- coding: utf-8 -*-
"""Gate de tenancy: decide quando o modo multi-tenant estrito está ativo.

Trigger data-driven (Fase B): o modo estrito liga sozinho quando existe **mais de
uma loja ATIVA**. Um override por ambiente (`FORCE_MULTI_TENANT`) permite forçar o
modo estrito em staging/testes antes de criar a segunda loja.

No modo single-store (uma loja ativa) os fallbacks single-tenant continuam valendo
(`.env`, `BLING_STORE_ID`, "última loja Nuvemshop ativa", state OAuth ausente cai na
loja default). No modo multi-store esses atalhos são desligados e a resolução de
tenant passa a ser obrigatória (fail-closed).
"""

from __future__ import annotations

from typing import Optional

from flask import current_app, has_app_context

from app import db
from app.models.store import Store


def _force_multi_tenant() -> bool:
    if has_app_context() and current_app.config.get("FORCE_MULTI_TENANT"):
        return True
    return False


def active_store_count() -> int:
    """Número de lojas com `active=True`."""
    return db.session.query(Store.id).filter(Store.active.is_(True)).count()


def is_multi_store() -> bool:
    """True quando o modo multi-tenant estrito deve valer.

    Ativado por override (`FORCE_MULTI_TENANT`) ou por existirem 2+ lojas ativas.
    Falha de banco degrada para single-store (comportamento atual), nunca para um
    estado que exponha outra loja.
    """
    if _force_multi_tenant():
        return True
    try:
        return active_store_count() > 1
    except Exception:
        db.session.rollback()
        return False


def is_store_inactive(store_ref_id: Optional[int]) -> bool:
    """True somente quando a empresa existe e está explicitamente ``active=False``.

    Usado pelos workers (sem ``g.current_store``) e pelos guards de enqueue para
    aplicar a política de empresa inativa: linha de empresa inativa não gera novo
    envio e, se já pendente, é invalidada.

    **Fail-open, de propósito:** ``store_ref_id`` ``None`` (linha legada
    single-tenant) ou empresa inexistente **não** é tratado como inativo, para
    preservar o comportamento single-tenant/legado. Só bloqueia quando há uma
    empresa real marcada ``active=False``. Usa a identity map da sessão
    (``session.get``), então repetir a chamada com o mesmo id no mesmo ciclo não
    gera nova query.
    """
    if store_ref_id is None:
        return False
    store = db.session.get(Store, store_ref_id)
    return store is not None and not store.active
