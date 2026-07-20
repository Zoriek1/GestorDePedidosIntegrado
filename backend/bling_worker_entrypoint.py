# -*- coding: utf-8 -*-
"""Worker que processa a fila (outbox) da integracao Bling.

Loga de forma legivel: o que processou, de qual pedido, em qual passo e, em caso
de falha, o motivo exato devolvido pelo Bling. Quando ocioso, emite um heartbeat
esparso para mostrar que esta vivo sem poluir o console.
"""

import os
import time
import traceback
from datetime import datetime

from app import create_app
from app.integrations.bling.service import BlingIntegrationService
from app.models.bling_outbox import BlingOutbox


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _status_tag(status: str) -> str:
    if status == "completed":
        return "OK   "
    if status == "failed_retryable":
        return "RETRY"
    if status.startswith("failed"):
        return "FALHA"
    return status.upper()


def _count_pending() -> int:
    return BlingOutbox.query.filter(
        BlingOutbox.status.in_(["pending", "failed_retryable"])
    ).count()


def _log_results(result: dict) -> None:
    print(
        f"[BLING_WORKER {_ts()}] ciclo: {result.get('processed', 0)} processado(s), "
        f"{result.get('failed', 0)} falha(s)",
        flush=True,
    )
    for r in result.get("results") or []:
        print(
            f"   {_status_tag(r['status'])} pedido #{r['pedido_id']} "
            f"loja={r.get('store_ref_id')} {r['operation']} "
            f"-> {r['status']} (step={r['step']})",
            flush=True,
        )
        if r.get("error_message"):
            print(f"        motivo: {r['error_message']}", flush=True)


def main() -> None:
    app = create_app()
    interval = max(1, int(os.environ.get("BLING_WORKER_INTERVAL_SECONDS", "10")))
    limit = int(os.environ.get("BLING_WORKER_LIMIT", "20"))
    heartbeat_every = max(1, 300 // interval)  # ~5 min ocioso

    with app.app_context():
        enabled = bool(app.config.get("BLING_ENABLED"))
        api = app.config.get("BLING_API_BASE_URL") or "?"
    print(
        f"[BLING_WORKER {_ts()}] iniciado | intervalo={interval}s | limite={limit} | "
        f"BLING_ENABLED={enabled} | api={api}",
        flush=True,
    )

    idle_cycles = 0
    disabled_warned = False

    while True:
        with app.app_context():
            if not app.config.get("BLING_ENABLED"):
                if not disabled_warned:
                    print(
                        f"[BLING_WORKER {_ts()}] BLING_ENABLED=false -> ocioso. "
                        "Defina BLING_ENABLED=true para processar a fila.",
                        flush=True,
                    )
                    disabled_warned = True
            else:
                disabled_warned = False
                try:
                    result = BlingIntegrationService().process_pending(limit=limit)
                    if result.get("results"):
                        idle_cycles = 0
                        _log_results(result)
                    else:
                        idle_cycles += 1
                        if idle_cycles % heartbeat_every == 0:
                            print(
                                f"[BLING_WORKER {_ts()}] ocioso ({_count_pending()} na fila)",
                                flush=True,
                            )
                except Exception as exc:  # noqa: BLE001 - worker nao pode morrer
                    print(
                        f"[BLING_WORKER {_ts()}] ERRO no ciclo: {type(exc).__name__}: {exc}",
                        flush=True,
                    )
                    traceback.print_exc()
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[BLING_WORKER] encerrado.", flush=True)
