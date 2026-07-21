# -*- coding: utf-8 -*-
"""Lock por `store_ref_id` para serializar PATCH/validate de configuracoes.

Defensivo: a aplicação tem 1 admin por loja, mas sessoes concorrentes
(superadmin/support) ou requests paralelos na mesma requisicao (ex.: "Salvar e
sair" disparando N PATCHs) nao podem gerar `validation_log` inconsistente
(estado entre canais).

Usa `threading.Lock` por chave em um dict compartilhado; suficiente para um
backend single-process (Waitress). Para Postgres real, `SELECT ... FOR UPDATE`
em `stores` ja oferece o mesmo efeito dentro de uma transacao; o lock em
memoria apenas cobre o gap entre commits.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

_locks: dict[int, threading.Lock] = {}
_locks_meta: dict[int, threading.Lock] = {}
_creation_lock = threading.Lock()


def _get_lock(store_ref_id: int) -> threading.Lock:
    lock = _locks.get(store_ref_id)
    if lock is not None:
        return lock
    with _creation_lock:
        lock = _locks.get(store_ref_id)
        if lock is None:
            lock = threading.Lock()
            _locks[store_ref_id] = lock
        return lock


@contextmanager
def store_lock(store_ref_id: int) -> Iterator[None]:
    """Serializa operacoes de configuracao por loja."""
    lock = _get_lock(store_ref_id)
    with lock:
        yield
