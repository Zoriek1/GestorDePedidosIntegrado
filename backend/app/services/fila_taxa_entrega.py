# -*- coding: utf-8 -*-
"""
Fila para cálculo de taxa de entrega após o cálculo de distância.
Quando a distância é calculada (em qualquer fluxo), o pedido_id é enfileirado
e um worker em background calcula e persiste a taxa, sem alterar a lógica de distância.
"""
import queue
import threading

_queue = queue.Queue()
_app_ref = None
_worker_started = False
_lock = threading.Lock()


def start_worker(app):
    """Inicia o worker da fila (chamado pelo factory após create_app)."""
    global _app_ref, _worker_started
    with _lock:
        if _worker_started:
            return
        _app_ref = app
        _worker_started = True
    t = threading.Thread(target=_worker_loop, daemon=True)
    t.start()


def enfileirar_calculo_taxa(pedido_id: int) -> None:
    """Coloca o pedido na fila para cálculo de taxa de entrega (após distância já calculada)."""
    try:
        _queue.put_nowait(pedido_id)
    except queue.Full:
        pass


def _worker_loop():
    while True:
        try:
            pedido_id = _queue.get()
        except Exception:
            continue
        app = _app_ref
        if not app:
            continue
        with app.app_context():
            _processar_taxa(pedido_id)


def _processar_taxa(pedido_id: int) -> None:
    """Calcula e persiste taxa para o pedido (usa distância já salva)."""
    from app.extensions import db

    try:
        from app.models.pedido import Pedido
        from app.services.taxa_entrega import taxa_entrega_service

        pedido = Pedido.query.get(pedido_id)
        if not pedido or pedido.distancia_km is None:
            return
        taxa = taxa_entrega_service.calcular_taxa(pedido.distancia_km)
        pedido.taxa_entrega = taxa
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print(f"[FILA_TAXA] Erro ao calcular taxa pedido {pedido_id}: {e}")
