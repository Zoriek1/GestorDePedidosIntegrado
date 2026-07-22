# -*- coding: utf-8 -*-
"""
Re-enqueue Meta CAPI outbox entries (Purchase + Lead) sent yesterday/today.

Use-case: after fixing the access_token auth bug (was sent in Authorization
header instead of query param), events were "received" by Meta (200) but
silently dropped. This script resets those entries to pending so the worker
re-sends them with the correct auth.

Idempotent: running multiple times is safe (only affects 'sent' entries).

Usage:
  python scripts/migrations/reenqueue_capi_outboxes.py --dry-run   # preview only
  python scripts/migrations/reenqueue_capi_outboxes.py             # apply
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402


def _preview_outbox(connection, table: str, days_back: int = 2) -> list[dict]:
    """List 'sent' entries from the last N days without modifying anything."""
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    rows = connection.execute(
        text(
            f"SELECT id, event_id, order_id, event_time, sent_at, attempts "
            f"FROM {table} WHERE status = 'sent' AND sent_at >= :cutoff "
            f"ORDER BY sent_at DESC"
        ),
        {"cutoff": cutoff},
    ).fetchall()
    return [dict(row) for row in rows]


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
    dry_run = "--dry-run" in sys.argv
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            if dry_run:
                print("=== DRY RUN — nenhuma alteracao sera feita ===\n")

                purchases = _preview_outbox(conn, "meta_capi_outbox")
                print(f"[PREVIEW] meta_capi_outbox: {len(purchases)} entries serao resetadas")
                for row in purchases:
                    print(
                        f"  id={row['id']} order_id={row['order_id']} "
                        f"event_id={row['event_id']} "
                        f"sent_at={row['sent_at']} attempts={row['attempts']}"
                    )

                leads = _preview_outbox(conn, "meta_capi_lead_outbox")
                print(f"\n[PREVIEW] meta_capi_lead_outbox: {len(leads)} entries serao resetadas")
                for row in leads:
                    print(
                        f"  id={row['id']} lead_id={row.get('order_id', 'N/A')} "
                        f"event_id={row['event_id']} "
                        f"sent_at={row['sent_at']} attempts={row['attempts']}"
                    )

                print(f"\nTotal: {len(purchases) + len(leads)} entries.")
                print("Para aplicar, rode sem --dry-run.")
            else:
                purchase_count = _reset_outbox(conn, "meta_capi_outbox")
                lead_count = _reset_outbox(conn, "meta_capi_lead_outbox")

                print(f"[RE-ENQUEUE] meta_capi_outbox: {purchase_count} entries reset to pending")
                print(f"[RE-ENQUEUE] meta_capi_lead_outbox: {lead_count} entries reset to pending")
                print(f"[SUCCESS] Re-enqueue completo. O worker ira reenviar nos proximos ciclos.")


if __name__ == "__main__":
    run()
