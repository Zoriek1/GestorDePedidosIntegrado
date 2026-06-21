# -*- coding: utf-8 -*-
"""Worker simples para processar outbox Bling."""

import os
import time

from app import create_app
from app.integrations.bling.service import BlingIntegrationService


def main() -> None:
    app = create_app()
    interval = int(os.environ.get("BLING_WORKER_INTERVAL_SECONDS", "10"))
    limit = int(os.environ.get("BLING_WORKER_LIMIT", "20"))
    print(f"[BLING_WORKER] iniciado interval={interval}s limit={limit}", flush=True)
    while True:
        with app.app_context():
            try:
                result = BlingIntegrationService().process_pending(limit=limit)
                if result.get("processed"):
                    print(f"[BLING_WORKER] {result}", flush=True)
            except Exception as exc:
                print(f"[BLING_WORKER] erro: {type(exc).__name__}: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
