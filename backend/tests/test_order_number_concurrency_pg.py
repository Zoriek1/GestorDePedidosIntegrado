# -*- coding: utf-8 -*-
"""Concorrência de `numero_pedido` em PostgreSQL real — gate de rollout Fase 0.

`allocate_order_number` serializa a numeração por empresa com
``SELECT ... FOR UPDATE`` na linha da ``Store`` (mutex por tenant), segurando o
lock até o commit do pedido. O SQLite não exercita isso (``FOR UPDATE`` é no-op e
a escrita é single-writer), então este teste **só roda contra um PostgreSQL real**.

Como rodar em staging (banco descartável):

    createdb gestor_conc_test
    TEST_DATABASE_URL=postgresql://user:pass@host:5432/gestor_conc_test \\
      python -m pytest tests/test_order_number_concurrency_pg.py -q

Ajuste a carga com ``ORDER_CONCURRENCY_THREADS`` e ``ORDER_CONCURRENCY_PER_THREAD``.
"""

import os
import threading
from datetime import date

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL.startswith("postgresql"),
    reason="Requer TEST_DATABASE_URL apontando para um PostgreSQL real",
)

THREADS = int(os.environ.get("ORDER_CONCURRENCY_THREADS", "8"))
PER_THREAD = int(os.environ.get("ORDER_CONCURRENCY_PER_THREAD", "40"))


@pytest.fixture
def pg_app():
    """App apontando para o Postgres de teste, com pool suficiente p/ as threads."""
    from app import create_app, db

    app = create_app(
        config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
            # Conexões suficientes para todas as threads contendendo no mutex.
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_size": THREADS + 4,
                "max_overflow": THREADS + 4,
                "pool_pre_ping": True,
            },
        }
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def _make_store(db, slug):
    from app.models.store import Store

    store = Store(name=slug, slug=slug, active=True)
    db.session.add(store)
    db.session.commit()
    return store.id


def _allocate_and_insert(app, store_id, count, results, errors, barrier):
    """Uma alocação = uma transação: FOR UPDATE + max()+1 + INSERT + COMMIT.

    Replica o fluxo de produção (routes/pedidos.py), onde o lock da linha da Store
    é segurado até o commit do pedido. Sem retry de propósito: se o mutex não
    segurar, o duplicado gera IntegrityError (unique composta) — capturado aqui.
    """
    from app import db
    from app.models.pedido import Pedido
    from app.services.order_number_allocator import allocate_order_number

    barrier.wait()
    for _ in range(count):
        with app.app_context():
            try:
                numero = allocate_order_number(store_id)
                db.session.add(
                    Pedido(
                        store_ref_id=store_id,
                        numero_pedido=numero,
                        cliente="Concorrência",
                        telefone_cliente="11999999999",
                        destinatario="Destino",
                        produto="Flores",
                        dia_entrega=date.today(),
                        horario="10:00",
                    )
                )
                db.session.commit()
                results.append(numero)
            except Exception as exc:  # noqa: BLE001 - queremos ver qualquer corrida
                db.session.rollback()
                errors.append(repr(exc))


def _run(app, assignments):
    """Dispara as threads (assignments = lista de (store_id, results, errors))."""
    barrier = threading.Barrier(len(assignments))
    threads = [
        threading.Thread(
            target=_allocate_and_insert,
            args=(app, store_id, PER_THREAD, results, errors, barrier),
        )
        for store_id, results, errors in assignments
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_numero_pedido_sem_duplicado_sob_concorrencia(pg_app):
    """K threads na MESMA loja produzem exatamente {1..K*PER_THREAD}, sem furos."""
    from app import db

    with pg_app.app_context():
        store_id = _make_store(db, "conc-single")

    results: list[int] = []
    errors: list[str] = []
    _run(pg_app, [(store_id, results, errors)] * THREADS)

    esperado = THREADS * PER_THREAD
    assert not errors, f"erros durante alocação concorrente: {errors[:5]}"
    assert len(results) == esperado
    assert sorted(results) == list(range(1, esperado + 1)), "número duplicado ou furo na sequência"


def test_numeracao_independente_entre_lojas_sob_concorrencia(pg_app):
    """Duas lojas em paralelo: cada uma reinicia em 1 e não bloqueia a outra."""
    from app import db

    with pg_app.app_context():
        store_a = _make_store(db, "conc-a")
        store_b = _make_store(db, "conc-b")

    res_a: list[int] = []
    res_b: list[int] = []
    err_a: list[str] = []
    err_b: list[str] = []
    half = max(1, THREADS // 2)
    assignments = [(store_a, res_a, err_a)] * half + [(store_b, res_b, err_b)] * half
    _run(pg_app, assignments)

    esperado = half * PER_THREAD
    assert not err_a and not err_b, f"erros: A={err_a[:3]} B={err_b[:3]}"
    assert sorted(res_a) == list(range(1, esperado + 1))
    assert sorted(res_b) == list(range(1, esperado + 1))
