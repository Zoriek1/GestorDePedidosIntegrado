# -*- coding: utf-8 -*-
"""Testes das correcoes de robustez/seguranca da integracao Bling.

Os imports de ``app.*`` sao feitos dentro de cada teste (lazy) de proposito:
importar ``app`` no topo do modulo interfere com a fixture ``app`` do conftest
(o factory faz ``import app.models``), padrao ja usado por outros testes do repo.
"""

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def bling_app():
    """App Flask minimo com ``db`` proprio e as tabelas Bling.

    Independe do ``create_app`` do projeto (cujo fixture do conftest esbarra num
    detalhe de import do factory neste ambiente). Aqui montamos so o necessario
    para exercitar o BlingIntegrationService com banco real em memoria."""
    from flask import Flask

    from app import db
    import app.models  # noqa: F401  (registra os models no metadata)

    flask_app = Flask(__name__)
    flask_app.config.update(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SECRET_KEY": "test-secret-key",
            "BLING_ENABLED": True,
            "BLING_STORE_ID": "default",
        }
    )
    db.init_app(flask_app)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


# --- Fase 1.1: gate BLING_ENABLED -------------------------------------------

def test_send_order_blocked_when_disabled(bling_app):
    from app.integrations.bling.errors import BlingConfigError
    from app.integrations.bling.service import BlingIntegrationService

    bling_app.config["BLING_ENABLED"] = False
    with pytest.raises(BlingConfigError):
        BlingIntegrationService().send_order(1)


def test_process_pending_blocked_when_disabled(bling_app):
    from app.integrations.bling.errors import BlingConfigError
    from app.integrations.bling.service import BlingIntegrationService

    bling_app.config["BLING_ENABLED"] = False
    with pytest.raises(BlingConfigError):
        BlingIntegrationService().process_pending()


# --- Fase 1.2: dedupe falha fechado -----------------------------------------

def test_resolve_existing_order_id_fails_closed_on_query_error(bling_app):
    from app.integrations.bling.errors import BlingRetryableError
    from app.integrations.bling.service import BlingIntegrationService

    svc = BlingIntegrationService()
    pedido = SimpleNamespace(id=99)

    class BoomClient:
        def list_orders_by_store_number(self, _numero):
            raise RuntimeError("timeout de rede")

    # Sem conseguir verificar duplicidade, deve relancar retryable em vez de
    # devolver None (que levaria a criar um pedido duplicado).
    with pytest.raises(BlingRetryableError):
        svc._resolve_existing_order_id(BoomClient(), pedido)


# --- Fase 1.3: claim atomico ------------------------------------------------

def test_process_outbox_skips_already_completed(bling_app, monkeypatch):
    from app import db
    from app.integrations.bling.service import BlingIntegrationService
    from app.models.bling_outbox import BlingOutbox

    outbox = BlingOutbox(
        pedido_id=123, operation="send_order", status="completed", step="completed"
    )
    db.session.add(outbox)
    db.session.commit()

    svc = BlingIntegrationService()

    def boom_client():
        raise AssertionError("client nao deveria ser chamado para outbox concluido")

    monkeypatch.setattr(svc, "client", boom_client)
    # O claim condicional falha (status nao esta em pending/failed_retryable),
    # entao process_outbox retorna sem reprocessar -- protecao contra a corrida
    # worker x envio manual.
    svc.process_outbox(outbox.id)

    db.session.refresh(outbox)
    assert outbox.status == "completed"


# --- Fase 2.1: baixa idempotente --------------------------------------------

class _CountingSettleClient:
    def __init__(self):
        self.calls = 0

    def settle_receivable(self, _rid, _payload):
        self.calls += 1
        return {"ok": True}


def test_settle_is_idempotent_across_retries(bling_app):
    from app import db
    from app.integrations.bling.service import BlingIntegrationService
    from app.models.bling_outbox import BlingOutbox

    svc = BlingIntegrationService()
    outbox = BlingOutbox(
        pedido_id=1, operation="send_order", status="processing", step="settling_entry"
    )
    db.session.add(outbox)
    db.session.commit()

    pedido = SimpleNamespace(valor=Decimal("100.00"), taxa_cartao_valor=None)
    plan = [
        {
            "kind": "PAGO",
            "marker": "GESTOR-1-PAGO",
            "amount": Decimal("100.00"),
            "due_date": "2026-06-21",
            "payment_label": "Pix",
            "should_settle": True,
        }
    ]
    receivable_ids = [{"marker": "GESTOR-1-PAGO", "id": "555", "raw": {}}]
    fake_mapping = SimpleNamespace(
        financial_account=SimpleNamespace(bling_id="10"),
        category=SimpleNamespace(bling_id="20"),
    )
    context = {"mappings": {"Pix": fake_mapping}}
    client = _CountingSettleClient()

    # 1a passada: baixa a conta e marca settled.
    svc._settle_receivables_if_needed(client, pedido, outbox, plan, receivable_ids, context)
    assert client.calls == 1
    assert receivable_ids[0]["settled"] is True
    assert json.loads(outbox.bling_receivable_ids_json)[0]["settled"] is True

    # 2a passada (retry): nao baixa de novo.
    svc._settle_receivables_if_needed(client, pedido, outbox, plan, receivable_ids, context)
    assert client.calls == 1


# --- Fase 2.3: 401 dispara refresh + retry ----------------------------------

class _FakeResp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = json.dumps(body) if body is not None else ""

    def json(self):
        return self._body


def test_client_refreshes_token_once_on_401(monkeypatch):
    from app.integrations.bling import client as client_module
    from app.integrations.bling.client import BlingClient

    sent_auth_headers = []
    responses = [
        _FakeResp(401, {"error": {"message": "token expirado"}}),
        _FakeResp(200, {"data": {"id": 1}}),
    ]

    def fake_request(method, url, headers=None, json=None, params=None, timeout=None):
        sent_auth_headers.append(headers.get("Authorization"))
        return responses.pop(0)

    monkeypatch.setattr(client_module.requests, "request", fake_request)

    refreshed = {"count": 0}

    def on_unauthorized():
        refreshed["count"] += 1
        return "novo-token"

    client = BlingClient("token-antigo", "https://api", on_unauthorized=on_unauthorized)
    result = client.get("/qualquer")

    assert refreshed["count"] == 1
    assert result == {"data": {"id": 1}}
    assert sent_auth_headers == ["Bearer token-antigo", "Bearer novo-token"]


def test_client_does_not_loop_on_persistent_401(monkeypatch):
    from app.integrations.bling import client as client_module
    from app.integrations.bling.client import BlingClient
    from app.integrations.bling.errors import BlingApiError

    def always_401(method, url, headers=None, json=None, params=None, timeout=None):
        return _FakeResp(401, {"error": {"message": "revogado"}})

    monkeypatch.setattr(client_module.requests, "request", always_401)

    client = BlingClient("t", "https://api", on_unauthorized=lambda: "outro")
    # Apos 1 refresh, o segundo 401 vira erro (sem loop infinito).
    with pytest.raises(BlingApiError):
        client.get("/x")


# --- Produto generico auto-criado -------------------------------------------

class _FakeProductClient:
    def __init__(self, existing_codes=(), fail_create=False):
        self.existing = list(existing_codes)
        self.created = []
        self.fail_create = fail_create

    def search_products(self, params):
        code = params.get("codigo")
        return {"data": [{"id": 1, "codigo": c} for c in self.existing if c == code]}

    def create_product(self, payload):
        if self.fail_create:
            from app.integrations.bling.errors import BlingApiError

            raise BlingApiError("ja existe produto com este codigo", status_code=400)
        self.created.append(payload)
        self.existing.append(payload["codigo"])
        return {"data": {"id": 99}}


def test_ensure_default_product_creates_when_missing(bling_app):
    from app.integrations.bling.service import BlingIntegrationService

    client = _FakeProductClient(existing_codes=())
    result = BlingIntegrationService().ensure_default_product(client=client)

    assert result["created"] is True
    assert len(client.created) == 1
    assert client.created[0]["codigo"] == "PEDIDO-FLORICULTURA"


def test_ensure_default_product_skips_when_exists(bling_app):
    from app.integrations.bling.service import BlingIntegrationService

    client = _FakeProductClient(existing_codes=("PEDIDO-FLORICULTURA",))
    result = BlingIntegrationService().ensure_default_product(client=client)

    assert result["created"] is False
    assert client.created == []


def test_ensure_default_product_treats_duplicate_create_as_existing(bling_app):
    from app.integrations.bling.errors import BlingApiError
    from app.integrations.bling.service import BlingIntegrationService

    class _Client:
        def __init__(self):
            self.searches = 0

        def search_products(self, params):
            # 1a busca nao acha (filtro falhou); recheck pos-create acha.
            self.searches += 1
            if self.searches == 1:
                return {"data": []}
            return {"data": [{"id": 7, "codigo": params.get("codigo")}]}

        def create_product(self, _payload):
            raise BlingApiError("ja existe", status_code=400)

    result = BlingIntegrationService().ensure_default_product(client=_Client())
    assert result["created"] is False


# --- Fase 1.4: migration portavel -------------------------------------------

def test_migration_uses_portable_timestamp_type():
    path = (
        Path(__file__).parent.parent
        / "scripts"
        / "migrations"
        / "create_bling_integration.py"
    )
    src = path.read_text(encoding="utf-8")
    # Postgres nao reconhece DATETIME; as colunas de data devem usar TIMESTAMP.
    assert '("entrada_recebida_at", "TIMESTAMP")' in src
    assert '("saldo_recebido_at", "TIMESTAMP")' in src
    # Nenhuma *definicao de coluna* pode usar DATETIME (o comentario pode citar).
    assert '"DATETIME")' not in src
