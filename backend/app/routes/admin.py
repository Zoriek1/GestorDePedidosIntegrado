# -*- coding: utf-8 -*-
"""Admin debug endpoints for tenant health monitoring."""

import logging

from flask import Blueprint

from app import db
from app.decorators.auth_decorator import require_auth
from app.middleware import requires_role
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.models.pedido import Pedido, datetime_now_brazil
from app.models.store import Store
from app.schemas.common import success_response

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

    return success_response({
        "success": True,
        "null_store_refs": null_store_refs,
        "orphans": orphans,
        "outbox_pending_by_tenant": outbox_pending,
    })


@admin_bp.route("/tenant-health", methods=["GET"])
@require_auth(roles=["admin"])
def tenant_health_by_store():
    """Returns per-store health metrics using SQLAlchemy model queries."""
    now = datetime_now_brazil()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stores = Store.query.filter_by(active=True).all()

    stores_data = []
    for store in stores:
        pedidos_hoje = (
            db.session.query(Pedido)
            .execution_options(include_all_tenants=True)
            .filter(Pedido.store_ref_id == store.id, Pedido.created_at >= today_start)
            .count()
        )

        outbox_pendente = (
            db.session.query(MetaCapiOutbox)
            .execution_options(include_all_tenants=True)
            .filter(
                MetaCapiOutbox.store_ref_id == store.id,
                MetaCapiOutbox.status == "PENDING",
            )
            .count()
        )

        stores_data.append(
            {
                "store_id": store.id,
                "slug": store.slug,
                "name": store.name,
                "pedidos_hoje": pedidos_hoje,
                "outbox_pendente": outbox_pendente,
            }
        )

    return success_response({"stores": stores_data})
