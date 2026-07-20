"""Fase C.4 — isolamento de auditoria."""

from datetime import date

from flask import g

from app import db
from app.models.audit_log import AuditLog
from app.models.pedido import Pedido
from app.models.store import Store
from app.utils.audit_logger import log_action
from scripts.migrations.add_store_ref_to_audit_log import migrate


def _store(slug: str) -> Store:
    store = Store(name=slug, slug=slug, active=True)
    db.session.add(store)
    db.session.commit()
    return store


def _pedido(store: Store) -> Pedido:
    pedido = Pedido(
        store_ref_id=store.id,
        numero_pedido=1,
        cliente="Cliente",
        telefone_cliente="11999999999",
        destinatario="Destino",
        produto="Flores",
        valor="R$ 50,00",
        dia_entrega=date.today(),
        horario="10:00",
    )
    db.session.add(pedido)
    db.session.commit()
    return pedido


def test_audit_log_uses_explicit_store_and_is_filtered(app):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        log_action("UPDATE", "pedido", 1, store_ref_id=store_a.id)
        log_action("UPDATE", "pedido", 2, store_ref_id=store_b.id)

        with app.test_request_context("/"):
            g.tenant_store_id = store_a.id
            g.tenant_multi = True
            logs = AuditLog.query.all()
            assert [log.store_ref_id for log in logs] == [store_a.id]


def test_audit_log_derives_store_from_entity_before_request(app):
    with app.app_context():
        store_a = _store("a")
        store_b = _store("b")
        pedido = _pedido(store_a)
        pedido_id = pedido.id
        assert pedido.store_ref_id == store_a.id

        with app.test_request_context("/"):
            g.tenant_store_id = store_b.id
            g.tenant_multi = True
            entry = log_action("DELETE", "pedido", pedido_id, entity=pedido)

        assert entry.store_ref_id == store_a.id


def test_ambiguous_multi_store_audit_is_rejected(app, caplog):
    with app.app_context():
        _store("a")
        _store("b")

        entry = log_action("DELETE", "unknown", 999)

        assert entry is None
        assert AuditLog.query.execution_options(include_all_tenants=True).count() == 0
        assert "audit.tenant_unresolved" in caplog.text


def test_c4_migration_is_idempotent_on_fresh_schema(app):
    with app.app_context():
        store = _store("default")
        db.session.add(
            AuditLog(
                store_ref_id=store.id,
                action="CREATE",
                entity_type="pedido",
                entity_id=1,
            )
        )
        db.session.commit()

        migrate()
        migrate()

        assert AuditLog.query.count() == 1
