# -*- coding: utf-8 -*-
"""
Re-enqueue Meta CAPI outbox entries (Purchase + Lead) sent yesterday/today.

Use-case: after fixing the access_token auth bug (was sent in Authorization
header instead of query param), events were "received" by Meta (200) but
silently dropped. This script resets those entries to pending so the worker
re-sends them with the correct auth.

Idempotent: running multiple times is safe (only affects 'sent' entries).
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402


def _reset_outbox(connection, table: str, days_back: int = 2) -> int:
    """Reset 'sent' entries to 'pending' for the last N days. Returns count."""
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    result = connection.execute(
        text(
            f"UPDATE {table} "
            "SET status = 'pending', attempts = 0, sent_at = NULL, "
            "    last_error = NULL, error_type = NULL, updated_at = NOW() "
            "WHERE status = 'sent' AND sent_at >= :cutoff"
        ),
        {"cutoff": cutoff},
    )
    return result.rowcount


def run() -> None:
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            purchase_count = _reset_outbox(conn, "meta_capi_outbox")
            lead_count = _reset_outbox(conn, "meta_capi_lead_outbox")

        print(f"[RE-ENQUEUE] meta_capi_outbox: {purchase_count} entries reset to pending")
        print(f"[RE-ENQUEUE] meta_capi_lead_outbox: {lead_count} entries reset to pending")
        print(f"[SUCCESS] Re-enqueue completo. O worker ira reenviar nos proximos ciclos.")


if __name__ == "__main__":
    run()
