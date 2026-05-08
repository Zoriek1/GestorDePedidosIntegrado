# -*- coding: utf-8 -*-
"""
Cleanup one-shot: marca como failed_permanent todos os outboxes Meta CAPI
em estado pending/failed_retryable cujo pedido é de fonte site/Nuvemshop.

Esses pedidos têm tracking próprio (pixel da Nuvemshop), então enviar
Purchase via CAPI duplica conversões.

Uso:
    python backend/scripts/migrations/cleanup_meta_capi_site_outboxes.py [--dry-run]
"""
import sys

from app import create_app, db
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.models.pedido import Pedido, datetime_now_brazil
from app.utils.meta_capi_helper import should_skip_purchase_for_meta_capi


def cleanup(dry_run: bool = False) -> int:
    candidates = (
        db.session.query(MetaCapiOutbox)
        .filter(MetaCapiOutbox.status.in_(["pending", "failed"]))
        .all()
    )

    marked = 0
    for entry in candidates:
        pedido = Pedido.query.get(entry.order_id)
        if not pedido:
            continue
        if not should_skip_purchase_for_meta_capi(pedido):
            continue

        print(
            f"[CLEANUP] outbox #{entry.id} (pedido #{pedido.id}, "
            f"fonte={pedido.fonte_pedido!r}, status={entry.status}) → failed_permanent"
        )

        if not dry_run:
            entry.status = "failed"
            entry.error_type = "permanent"
            entry.last_error = "Ignorado por origem site/nuvemshop (cleanup)"
            entry.updated_at = datetime_now_brazil()
        marked += 1

    if not dry_run and marked > 0:
        db.session.commit()

    return marked


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv

    with create_app().app_context():
        n = cleanup(dry_run=dry_run)
        prefix = "[DRY-RUN] " if dry_run else ""
        print(f"{prefix}{n} outbox(es) marcadas como failed_permanent")
