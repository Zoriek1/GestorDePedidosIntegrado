# -*- coding: utf-8 -*-
"""Status e reprocessamento administrativo das conversões WhatsApp."""

from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

from app import db
from app.middleware import requires_any_role
from app.models.events_outbox import EventsOutbox
from app.models.marketing_conversion_outbox import MarketingConversionOutbox
from app.services.marketing_diagnostics_service import MarketingDiagnosticsService

marketing_conversions_bp = Blueprint(
    "marketing_conversions", __name__, url_prefix="/api/admin/marketing-conversions"
)


def _tenant_store_id() -> int | None:
    """Loja da request, resolvida por `prime_request_tenant`.

    None cai na loja default dentro de `runtime_config` (single-store/bootstrap).
    """
    return getattr(g, "tenant_store_id", None)


@marketing_conversions_bp.route("/config", methods=["GET"])
@requires_any_role("admin")
def config_status():
    service = MarketingDiagnosticsService(store_ref_id=_tenant_store_id())
    return jsonify({"ok": True, **service.config_status()})


@marketing_conversions_bp.route("/diagnostics/<destination>", methods=["POST"])
@requires_any_role("admin")
def run_diagnostic(destination: str):
    data = request.get_json(silent=True) or {}
    service = MarketingDiagnosticsService(store_ref_id=_tenant_store_id())
    result = service.run(
        destination,
        meta_test_event_code=str(data.get("meta_test_event_code") or "") or None,
    )
    return jsonify({"ok": True, "result": result})


@marketing_conversions_bp.route("", methods=["GET"])
@requires_any_role("admin")
def list_status():
    query = MarketingConversionOutbox.query
    destino = (request.args.get("destino") or "").strip()
    status = (request.args.get("status") or "").strip()
    if destino:
        query = query.filter_by(destino=destino)
    if status:
        query = query.filter_by(status=status)
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)
    except ValueError:
        limit = 100
    rows = query.order_by(MarketingConversionOutbox.created_at.desc()).limit(limit).all()
    # Also query unified events_outbox
    events_query = EventsOutbox.query
    if destino:
        events_query = events_query.filter_by(destino=destino)
    if status:
        events_query = events_query.filter_by(status=status)
    events_rows = events_query.order_by(EventsOutbox.created_at.desc()).limit(limit).all()

    # Merge: convert events_outbox rows to same format
    all_items = [row.to_dict() for row in rows]
    for er in events_rows:
        all_items.append({
            "id": er.id,
            "pedido_id": er.pedido_id,
            "destino": er.destino,
            "evento": er.evento,
            "status": er.status,
            "last_http_status": None,
            "last_error": er.last_error,
            "request_id": None,
            "next_status_check_at": None,
            "created_at": er.created_at.isoformat() if er.created_at else None,
        })
    # Sort by created_at desc and limit
    all_items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    all_items = all_items[:limit]
    counts = (
        db.session.query(
            MarketingConversionOutbox.destino,
            MarketingConversionOutbox.status,
            func.count(MarketingConversionOutbox.id),
        )
        .group_by(MarketingConversionOutbox.destino, MarketingConversionOutbox.status)
        .all()
    )
    return jsonify(
        {
            "ok": True,
            "counts": [
                {"destino": item[0], "status": item[1], "total": item[2]} for item in counts
            ],
            "items": all_items,
        }
    )


@marketing_conversions_bp.route("/retry", methods=["POST"])
@requires_any_role("admin")
def retry():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids")
    force = bool(data.get("force", False))
    query = MarketingConversionOutbox.query
    if isinstance(ids, list) and ids:
        safe_ids = [value for value in ids[:500] if isinstance(value, int)]
        query = query.filter(MarketingConversionOutbox.id.in_(safe_ids))
    else:
        query = query.filter_by(status="failed")
    destino = str(data.get("destino") or "").strip()
    if destino:
        query = query.filter_by(destino=destino)
    rows = query.limit(500).all()
    changed = 0
    for row in rows:
        if row.status == "sent" and not force:
            continue
        row.status = "pending"
        row.request_id = None
        row.validation_only = False
        row.status_check_attempts = 0
        row.last_status_check_at = None
        row.next_status_check_at = None
        row.submitted_at = None
        row.sent_at = None
        row.last_http_status = None
        row.last_error = None
        changed += 1
    db.session.commit()
    return jsonify({"ok": True, "requeued": changed})
