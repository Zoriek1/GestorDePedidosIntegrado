# -*- coding: utf-8 -*-
"""Admin debug endpoints for tenant health monitoring."""

import logging

from flask import Blueprint, jsonify

from app.middleware import requires_role

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
logger = logging.getLogger(__name__)

# Tables that should have store_ref_id
_TENANT_TABLES = [
    "pedidos", "leads", "clientes", "fontes_pedido", "enderecos_clientes",
    "pedido_external_refs", "audit_log", "push_subscriptions",
    "users", "bling_credentials", "nuvemshop_stores",
]


@admin_bp.route("/debug/tenant-health", methods=["GET"])
@requires_role("admin")
def tenant_health():
    """Returns tenant health metrics for monitoring."""
    from app import db

    null_store_refs = {}
    orphans = {}

    for table in _TENANT_TABLES:
        try:
            null_count = db.session.execute(
                db.text(f"SELECT COUNT(*) FROM {table} WHERE store_ref_id IS NULL")
            ).scalar()
            null_store_refs[table] = null_count
        except Exception:
            null_store_refs[table] = "error"

    for table in _TENANT_TABLES:
        try:
            orphan_count = db.session.execute(
                db.text(
                    f"SELECT COUNT(*) FROM {table} t "
                    f"WHERE t.store_ref_id IS NOT NULL "
                    f"AND NOT EXISTS (SELECT 1 FROM stores s WHERE s.id = t.store_ref_id)"
                )
            ).scalar()
            orphans[table] = orphan_count
        except Exception:
            orphans[table] = "error"

    # Outbox pending by tenant
    outbox_pending = {}
    try:
        rows = db.session.execute(
            db.text(
                "SELECT COALESCE(store_ref_id::text, 'null') as tenant, COUNT(*) "
                "FROM meta_capi_outbox WHERE status='PENDING' "
                "GROUP BY store_ref_id"
            )
        ).fetchall()
        for row in rows:
            outbox_pending[row[0]] = row[1]
    except Exception:
        outbox_pending["error"] = "query_failed"

    logger.info(
        "tenant.health_check null_total=%s orphan_total=%s",
        sum(v for v in null_store_refs.values() if isinstance(v, int)),
        sum(v for v in orphans.values() if isinstance(v, int)),
    )

    return jsonify({
        "success": True,
        "null_store_refs": null_store_refs,
        "orphans": orphans,
        "outbox_pending_by_tenant": outbox_pending,
    })