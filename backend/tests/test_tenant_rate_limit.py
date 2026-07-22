"""Testes para rate limiting por tenant nos workers (Tarefa 4.5)."""

from datetime import date

import pytest

# =============================================================================
# Fixtures específicas (não usam conftest.app — precisam de BLING_ENABLED etc.)
# =============================================================================


def _pedido(session, numero: int = 1):
    """Cria um Pedido mínimo para satisfazer FKs."""
    from app.models.pedido import Pedido

    p = Pedido(
        numero_pedido=numero,
        cliente=f"Cliente {numero}",
        telefone_cliente="11999999999",
        destinatario="Destino",
        produto="Flores",
        valor="R$ 50,00",
        dia_entrega=date.today(),
        horario="10:00",
    )
    session.add(p)
    session.commit()
    return p


@pytest.fixture
def bling_app():
    """App Flask minimo com Bling habilitado para testes de process_pending."""
    from flask import Flask

    import app.models  # noqa: F401  (registra os models no metadata)
    from app import db

    flask_app = Flask(__name__)
    flask_app.config.update(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SECRET_KEY": "test-secret-key",
            "BLING_ENABLED": True,
            "BLING_STORE_ID": "default",
            "TESTING": True,
        }
    )
    db.init_app(flask_app)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def bling_session(bling_app):
    """Sessão para os testes Bling (usa o banco do bling_app)."""
    from app import db as _db

    yield _db.session
    _db.session.rollback()


@pytest.fixture
def meta_capi_app():
    """App Flask minimo para testes de outbox Meta CAPI."""
    from flask import Flask

    import app.models  # noqa: F401
    from app import db

    flask_app = Flask(__name__)
    flask_app.config.update(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SECRET_KEY": "test-secret-key",
            "TESTING": True,
        }
    )
    db.init_app(flask_app)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def meta_session(meta_capi_app):
    """Sessão para os testes Meta CAPI (usa o banco do meta_capi_app)."""
    from app import db as _db

    yield _db.session
    _db.session.rollback()


# =============================================================================
# Bling - process_pending com store_ref_id
# =============================================================================


class TestBlingProcessPendingPerStore:
    def test_process_pending_filters_by_store_ref_id(self, bling_app, bling_session):
        from app.integrations.bling.service import BlingIntegrationService
        from app.models.bling_outbox import BlingOutbox
        from app.models.store import Store

        store_a = Store(name="Loja A", slug="loja-a", active=True)
        store_b = Store(name="Loja B", slug="loja-b", active=True)
        bling_session.add(store_a)
        bling_session.add(store_b)
        bling_session.commit()

        pedidos_a = [_pedido(bling_session, i) for i in range(3)]
        pedidos_b = [_pedido(bling_session, i + 10) for i in range(3)]

        for p in pedidos_a:
            bling_session.add(
                BlingOutbox(
                    pedido_id=p.id,
                    store_ref_id=store_a.id,
                    operation="send_order",
                    status="pending",
                )
            )
        for p in pedidos_b:
            bling_session.add(
                BlingOutbox(
                    pedido_id=p.id,
                    store_ref_id=store_b.id,
                    operation="send_order",
                    status="pending",
                )
            )
        bling_session.commit()

        svc = BlingIntegrationService()
        result_a = svc.process_pending(limit=10, store_ref_id=store_a.id)
        result_b = svc.process_pending(limit=10, store_ref_id=store_b.id)

        assert result_a["processed"] == 3
        assert result_b["processed"] == 3
        assert all(r.get("store_ref_id") == store_a.id for r in result_a["results"])
        assert all(r.get("store_ref_id") == store_b.id for r in result_b["results"])

    def test_process_pending_global_when_no_store_ref_id(self, bling_app, bling_session):
        from app.integrations.bling.service import BlingIntegrationService
        from app.models.bling_outbox import BlingOutbox
        from app.models.store import Store

        store = Store(name="Loja", slug="loja", active=True)
        bling_session.add(store)
        bling_session.commit()

        pedidos = [_pedido(bling_session, i) for i in range(5)]
        for p in pedidos:
            bling_session.add(
                BlingOutbox(
                    pedido_id=p.id, store_ref_id=store.id, operation="send_order", status="pending"
                )
            )
        bling_session.commit()

        svc = BlingIntegrationService()
        result = svc.process_pending(limit=10)
        assert result["processed"] == 5


# =============================================================================
# Meta CAPI - repositórios com store_ref_id
# =============================================================================


class TestMetaCapiRepositoriesPerStore:
    def _store(self, session, name, slug):
        from app.models.store import Store

        store = Store(name=name, slug=slug, active=True)
        session.add(store)
        session.commit()
        return store

    def test_get_pending_filters_by_store(self, meta_capi_app, meta_session):
        from datetime import datetime

        from app.models.meta_capi_outbox import MetaCapiOutbox
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        store_a = self._store(meta_session, "Loja A", "loja-a")
        store_b = self._store(meta_session, "Loja B", "loja-b")
        now = datetime.now()

        for i in range(3):
            pedido = _pedido(meta_session, i)
            meta_session.add(
                MetaCapiOutbox(
                    order_id=pedido.id,
                    store_ref_id=store_a.id,
                    event_id=f"e{i}",
                    event_time=now,
                    payload_json="{}",
                    status="pending",
                )
            )
        for i in range(3, 6):
            pedido = _pedido(meta_session, i)
            meta_session.add(
                MetaCapiOutbox(
                    order_id=pedido.id,
                    store_ref_id=store_b.id,
                    event_id=f"e{i}",
                    event_time=now,
                    payload_json="{}",
                    status="pending",
                )
            )
        meta_session.commit()

        repo = MetaCapiOutboxRepository()
        pending_a = repo.get_pending(limit=10, store_ref_id=store_a.id)
        pending_b = repo.get_pending(limit=10, store_ref_id=store_b.id)

        assert len(pending_a) == 3
        assert len(pending_b) == 3
        assert all(e.store_ref_id == store_a.id for e in pending_a)
        assert all(e.store_ref_id == store_b.id for e in pending_b)

    def test_get_pending_global_when_no_store(self, meta_capi_app, meta_session):
        from datetime import datetime

        from app.models.meta_capi_outbox import MetaCapiOutbox
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        store = self._store(meta_session, "Loja", "loja")
        now = datetime.now()

        for i in range(5):
            pedido = _pedido(meta_session, i)
            meta_session.add(
                MetaCapiOutbox(
                    order_id=pedido.id,
                    store_ref_id=store.id,
                    event_id=f"e{i}",
                    event_time=now,
                    payload_json="{}",
                    status="pending",
                )
            )
        meta_session.commit()

        repo = MetaCapiOutboxRepository()
        pending = repo.get_pending(limit=10)
        assert len(pending) == 5

    def test_get_failed_retryable_filters_by_store(self, meta_capi_app, meta_session):
        from datetime import datetime

        from app.models.meta_capi_outbox import MetaCapiOutbox
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        store = self._store(meta_session, "Loja", "loja")
        outra_store = self._store(meta_session, "Outra Loja", "outra-loja")
        now = datetime.now()

        for i in range(3):
            pedido = _pedido(meta_session, i)
            meta_session.add(
                MetaCapiOutbox(
                    order_id=pedido.id,
                    store_ref_id=store.id,
                    event_id=f"e{i}",
                    event_time=now,
                    payload_json="{}",
                    status="failed",
                    error_type="retryable",
                    attempts=1,
                )
            )
        pedido_outro = _pedido(meta_session, 99)
        meta_session.add(
            MetaCapiOutbox(
                order_id=pedido_outro.id,
                store_ref_id=outra_store.id,
                event_id="e99",
                event_time=now,
                payload_json="{}",
                status="failed",
                error_type="retryable",
                attempts=1,
            )
        )
        meta_session.commit()

        repo = MetaCapiOutboxRepository()
        result = repo.get_failed_retryable(limit=10, store_ref_id=store.id)
        assert len(result) == 3
        assert all(e.store_ref_id == store.id for e in result)


# =============================================================================
# SendDailyPurchasesToMetaCommand - process_outbox_cycle com store_ref_id
# =============================================================================


class TestSendDailyPurchasesToMetaCommandPerStore:
    def test_process_outbox_cycle_respects_store_ref_id(self, meta_capi_app, meta_session):
        from datetime import datetime

        from app.commands.send_daily_purchases_to_meta_command import (
            SendDailyPurchasesToMetaCommand,
        )
        from app.models.meta_capi_outbox import MetaCapiOutbox
        from app.models.store import Store

        store_a = Store(name="Loja A", slug="loja-a", active=True)
        store_b = Store(name="Loja B", slug="loja-b", active=True)
        meta_session.add(store_a)
        meta_session.add(store_b)
        meta_session.commit()
        now = datetime.now()

        for i in range(3):
            pedido = _pedido(meta_session, i)
            meta_session.add(
                MetaCapiOutbox(
                    order_id=pedido.id,
                    store_ref_id=store_a.id,
                    event_id=f"e{i}",
                    event_time=now,
                    payload_json="{}",
                    status="pending",
                )
            )
        for i in range(3, 6):
            pedido = _pedido(meta_session, i)
            meta_session.add(
                MetaCapiOutbox(
                    order_id=pedido.id,
                    store_ref_id=store_b.id,
                    event_id=f"e{i}",
                    event_time=now,
                    payload_json="{}",
                    status="pending",
                )
            )
        meta_session.commit()

        cmd = SendDailyPurchasesToMetaCommand()
        stats_a = cmd.process_outbox_cycle(limit=10, store_ref_id=store_a.id)
        stats_b = cmd.process_outbox_cycle(limit=10, store_ref_id=store_b.id)

        assert stats_a["pending_processed"] == 3
        assert stats_b["pending_processed"] == 3
