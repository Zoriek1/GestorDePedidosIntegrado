# -*- coding: utf-8 -*-
"""Logger transacional da trilha de auditoria."""

import json
import logging
from datetime import datetime

from flask import g, has_app_context, has_request_context

from app import db
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def _store_from_entity(entity, entity_type: str, entity_id: int) -> int | None:
    if entity is not None:
        return getattr(entity, "store_ref_id", None)
    if not has_app_context() or entity_id is None:
        return None

    model = None
    if entity_type == "pedido":
        from app.models.pedido import Pedido

        model = Pedido
    elif entity_type == "cliente":
        from app.models.cliente import Cliente

        model = Cliente

    if model is None:
        return None

    audited = (
        model.query.execution_options(include_all_tenants=True)
        .filter(model.id == entity_id)
        .first()
    )
    return getattr(audited, "store_ref_id", None) if audited else None


def _resolve_store_ref_id(
    store_ref_id: int | None,
    entity,
    entity_type: str,
    entity_id: int,
) -> int | None:
    if store_ref_id is not None:
        return int(store_ref_id)

    entity_store_id = _store_from_entity(entity, entity_type, entity_id)
    if entity_store_id is not None:
        return int(entity_store_id)

    if has_request_context():
        request_store_id = getattr(g, "tenant_store_id", None)
        if request_store_id is not None:
            return int(request_store_id)

    if not has_app_context():
        return None

    from app.models.store import Store
    from app.services.tenancy import is_multi_store

    if is_multi_store():
        return None
    default_store = Store.query.filter_by(slug="default").first()
    return default_store.id if default_store else None


def log_action(
    action: str,
    entity_type: str,
    entity_id: int,
    actor: str = None,
    metadata: dict = None,
    store_ref_id: int = None,
    entity=None,
):
    """Registra uma acao sem interromper a operacao principal se a auditoria falhar."""
    try:
        resolved_store_id = _resolve_store_ref_id(
            store_ref_id,
            entity,
            entity_type,
            entity_id,
        )

        if has_app_context():
            from app.services.tenancy import is_multi_store

            if is_multi_store() and resolved_store_id is None:
                logger.error(
                    "audit.tenant_unresolved action=%s entity_type=%s entity_id=%s",
                    action,
                    entity_type,
                    entity_id,
                )
                return None

        metadata_str = None
        if metadata:
            metadata_str = (
                json.dumps(metadata, ensure_ascii=False)
                if isinstance(metadata, dict)
                else str(metadata)
            )

        audit_entry = AuditLog(
            store_ref_id=resolved_store_id,
            ts=datetime.utcnow(),
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata_str,
        )

        db.session.add(audit_entry)
        db.session.commit()
        return audit_entry
    except Exception as exc:
        db.session.rollback()
        logger.warning("audit.write_failed error=%s", exc, exc_info=True)
        return None
