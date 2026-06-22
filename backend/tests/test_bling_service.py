# -*- coding: utf-8 -*-
"""Testes das correcoes de robustez/seguranca da integracao Bling.

Os imports de ``app.*`` sao feitos dentro de cada teste (lazy) de proposito:
importar ``app`` no topo do modulo interfere com a fixture ``app`` do conftest
(o factory faz ``import app.models``), padrao ja usado por outros testes do repo.
"""

import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def bling_app(monkeypatch):
    """App Flask minimo com ``db`` proprio e as tabelas Bling.

    Independe do ``create_app`` do projeto (cujo fixture do conftest esbarra num
    detalhe de import do factory neste ambiente). Aqui montamos so o necessario
    para exercitar o BlingIntegrationService com banco real em memoria."""
    from flask import Flask

    import app.models  # noqa: F401  (registra os models no metadata)
    from app import db

    monkeypatch.setenv("SQLITE_FOREIGN_KEYS", "OFF")

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


def test_token_expiration_accepts_naive_database_datetime(bling_app):
    from app import db
    from app.integrations.bling.token_service import BlingTokenService
    from app.models.bling_credential import BlingCredential
    from app.models.pedido import datetime_now_brazil

    credential = BlingCredential(
        store_id="default",
        access_token_encrypted=BlingTokenService.encrypt("token-valido"),
        refresh_token_encrypted=BlingTokenService.encrypt("refresh-token"),
        active=True,
        expires_at=(datetime_now_brazil() + timedelta(hours=1)).replace(tzinfo=None),
    )
    db.session.add(credential)
    db.session.commit()

    assert BlingTokenService.get_valid_access_token() == "token-valido"


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


def test_sync_financial_accounts_marks_inactive_statuses(bling_app):
    from app.integrations.bling.service import BlingIntegrationService
    from app.models.bling_financial_account import BlingFinancialAccount

    service = BlingIntegrationService()
    count = service._sync_financial_accounts(
        [
            {"id": "1", "descricao": "Conta ativa", "situacao": "Ativo"},
            {"id": "2", "descricao": "Conta inativa texto", "situacao": "Inativo"},
            {
                "id": "3",
                "descricao": "Conta inativa objeto",
                "situacao": {"id": 2, "nome": "Inativo"},
            },
            {"id": "4", "descricao": "Conta inativa bool", "ativo": False},
        ]
    )

    assert count == 4
    by_id = {
        account.bling_id: account.ativo
        for account in BlingFinancialAccount.query.order_by(BlingFinancialAccount.bling_id)
    }
    assert by_id == {"1": True, "2": False, "3": False, "4": False}


def test_enqueue_bling_for_new_order_requires_connection(bling_app):
    from app.models.bling_outbox import BlingOutbox
    from app.utils.bling_helper import enqueue_bling_for_new_order

    pedido = SimpleNamespace(id=77)

    assert enqueue_bling_for_new_order(pedido) is False
    assert BlingOutbox.query.count() == 0


def test_enqueue_bling_for_new_order_creates_pending_once(bling_app):
    from app import db
    from app.integrations.bling.token_service import BlingTokenService
    from app.models.bling_credential import BlingCredential
    from app.models.bling_outbox import BlingOutbox
    from app.utils.bling_helper import enqueue_bling_for_new_order

    credential = BlingCredential(
        store_id="default",
        access_token_encrypted=BlingTokenService.encrypt("access-token"),
        refresh_token_encrypted=BlingTokenService.encrypt("refresh-token"),
        active=True,
    )
    db.session.add(credential)
    db.session.commit()

    pedido = SimpleNamespace(id=88)

    assert enqueue_bling_for_new_order(pedido) is True
    assert enqueue_bling_for_new_order(pedido) is False

    outboxes = BlingOutbox.query.all()
    assert len(outboxes) == 1
    assert outboxes[0].pedido_id == 88
    assert outboxes[0].status == "pending"
    assert outboxes[0].step == "pending"


# --- Contato por cliente (Bling exige contato.id na venda) ------------------

def test_ensure_contact_uses_configured_id(bling_app):
    from app.integrations.bling.service import BlingIntegrationService

    bling_app.config["BLING_DEFAULT_CONTACT_ID"] = "12345"

    class _NoClient:
        def search_contacts(self, *a, **k):
            raise AssertionError("nao deveria chamar a API com id fixo")

    pedido = SimpleNamespace(cliente="Maria", telefone_cliente="6299")
    assert BlingIntegrationService().ensure_contact_for_pedido(pedido, _NoClient()) == "12345"


def test_ensure_contact_creates_with_customer_name(bling_app):
    from app.integrations.bling.service import BlingIntegrationService

    bling_app.config["BLING_DEFAULT_CONTACT_ID"] = ""

    class _Client:
        def __init__(self):
            self.created = []

        def search_contacts(self, _params):
            return {"data": []}

        def create_contact(self, payload):
            self.created.append(payload)
            return {"data": {"id": 777}}

    client = _Client()
    pedido = SimpleNamespace(cliente="Maria Souza", telefone_cliente="62988887777")
    assert BlingIntegrationService().ensure_contact_for_pedido(pedido, client) == "777"
    assert client.created[0]["nome"] == "Maria Souza"
    assert client.created[0]["situacao"] == "A"
    assert client.created[0]["telefone"] == "62988887777"


def test_ensure_contact_omits_invalid_phone(bling_app):
    from app.integrations.bling.service import BlingIntegrationService

    bling_app.config["BLING_DEFAULT_CONTACT_ID"] = ""

    class _Client:
        def __init__(self):
            self.created = []

        def search_contacts(self, _params):
            return {"data": []}

        def create_contact(self, payload):
            self.created.append(payload)
            return {"data": {"id": 777}}

    client = _Client()
    # Telefone invalido (celular nao comeca com 9): contato e criado sem telefone.
    pedido = SimpleNamespace(cliente="TESTE", telefone_cliente="62099999999")
    assert BlingIntegrationService().ensure_contact_for_pedido(pedido, client) == "777"
    assert "telefone" not in client.created[0]
    assert client.created[0]["situacao"] == "A"


def test_ensure_contact_reuses_existing_by_name(bling_app):
    from app.integrations.bling.service import BlingIntegrationService

    bling_app.config["BLING_DEFAULT_CONTACT_ID"] = ""

    class _Client:
        def search_contacts(self, _params):
            return {"data": [{"id": 42, "nome": "Maria Souza"}]}

        def create_contact(self, _payload):
            raise AssertionError("nao deveria criar se ja existe")

    pedido = SimpleNamespace(cliente="Maria Souza", telefone_cliente="")
    assert BlingIntegrationService().ensure_contact_for_pedido(pedido, _Client()) == "42"


def test_contact_marked_as_cliente_type(bling_app):
    from app.integrations.bling.service import BlingIntegrationService

    bling_app.config["BLING_DEFAULT_CONTACT_ID"] = ""

    class _Client:
        def __init__(self):
            self.created = []

        def search_contacts(self, _p):
            return {"data": []}

        def list_contact_types(self):
            return {"data": [{"id": 5, "descricao": "Fornecedor"}, {"id": 9, "descricao": "Cliente"}]}

        def create_contact(self, payload):
            self.created.append(payload)
            return {"data": {"id": 1}}

    client = _Client()
    pedido = SimpleNamespace(cliente="Joao", telefone_cliente="")
    BlingIntegrationService().ensure_contact_for_pedido(pedido, client)
    assert client.created[0]["tiposContato"] == [{"id": 9}]


def test_cliente_contact_type_uses_config_override(bling_app):
    from app.integrations.bling.service import BlingIntegrationService

    bling_app.config["BLING_CONTACT_TYPE_ID"] = "77"

    class _NoList:
        def list_contact_types(self):
            raise AssertionError("nao deveria consultar tipos com override configurado")

    assert BlingIntegrationService()._cliente_contact_type_id(_NoList()) == "77"


# --- Cancelamento (apagar recebimento -> apagar conta -> apagar venda) -------

class _CancelClient:
    def __init__(self, fail_delete_order_404=False):
        self.calls = []
        self.fail_delete_order_404 = fail_delete_order_404

    def list_cash_entries(self, params):
        pesquisa = params.get("pesquisa", "")
        return {"data": [{"id": "C1", "historico": f"{pesquisa}-PAGO - baixa Gestor"}]}

    def delete_cash_entry(self, cid):
        self.calls.append(("del_caixa", str(cid)))
        return {}

    def list_receivables(self, _params):
        return {"data": []}

    def delete_receivable(self, rid):
        self.calls.append(("del_recv", str(rid)))
        return {}

    def delete_order(self, oid):
        self.calls.append(("del_order", str(oid)))
        if self.fail_delete_order_404:
            from app.integrations.bling.errors import BlingApiError

            raise BlingApiError("nao encontrado", status_code=404)
        return {}


def test_cancel_does_nothing_without_order(bling_app, monkeypatch):
    from app import db
    from app.integrations.bling.service import BlingIntegrationService
    from app.models.bling_outbox import BlingOutbox

    cancel = BlingOutbox(pedido_id=500, operation="cancel_order", status="pending", step="pending")
    db.session.add(cancel)
    db.session.commit()

    svc = BlingIntegrationService()
    monkeypatch.setattr(svc, "client", lambda: (_ for _ in ()).throw(AssertionError("nao deveria abrir client")))
    svc.process_cancel(cancel.id)

    db.session.refresh(cancel)
    assert cancel.status == "completed"


def test_cancel_deletes_receipt_then_receivable_then_order(bling_app, monkeypatch):
    from app import db
    from app.integrations.bling.service import BlingIntegrationService
    from app.models.bling_outbox import BlingOutbox

    send = BlingOutbox(
        pedido_id=501,
        operation="send_order",
        status="completed",
        step="completed",
        bling_order_id="900",
        bling_receivable_ids_json=json.dumps([{"marker": "GESTOR-501-PAGO", "id": "111"}]),
    )
    cancel = BlingOutbox(pedido_id=501, operation="cancel_order", status="pending", step="pending")
    db.session.add_all([send, cancel])
    db.session.commit()

    svc = BlingIntegrationService()
    client = _CancelClient()
    monkeypatch.setattr(svc, "client", lambda: client)
    svc.process_cancel(cancel.id)

    # Ordem: apagar recebimento (caixa) -> apagar conta -> apagar venda.
    assert client.calls == [("del_caixa", "C1"), ("del_recv", "111"), ("del_order", "900")]
    db.session.refresh(cancel)
    assert cancel.status == "completed"


def test_cancel_is_idempotent_on_404(bling_app, monkeypatch):
    from app import db
    from app.integrations.bling.service import BlingIntegrationService
    from app.models.bling_outbox import BlingOutbox

    send = BlingOutbox(
        pedido_id=502, operation="send_order", status="completed", step="completed",
        bling_order_id="901",
    )
    cancel = BlingOutbox(pedido_id=502, operation="cancel_order", status="pending", step="pending")
    db.session.add_all([send, cancel])
    db.session.commit()

    svc = BlingIntegrationService()
    monkeypatch.setattr(svc, "client", lambda: _CancelClient(fail_delete_order_404=True))
    svc.process_cancel(cancel.id)

    db.session.refresh(cancel)
    assert cancel.status == "completed"  # 404 ao apagar venda = tratado como ja feito


# --- Mensagem de erro do Bling (campos de validacao) ------------------------

def test_error_message_inclui_fields_de_validacao():
    from app.integrations.bling.client import BlingClient

    payload = {
        "error": {
            "type": "VALIDATION_ERROR",
            "message": "Nao foi possivel salvar a venda",
            "description": "Dados invalidos",
            "fields": [
                {"element": "contato.numeroDocumento", "msg": "e obrigatorio"},
            ],
        }
    }
    msg = BlingClient._error_message(payload)
    assert "Nao foi possivel salvar a venda" in msg
    assert "contato.numeroDocumento" in msg
    assert "obrigatorio" in msg


def test_accounts_already_launched_detects_code_62():
    from app.integrations.bling.errors import BlingApiError
    from app.integrations.bling.service import BlingIntegrationService

    dup = BlingApiError(
        "Nao foi possivel lancar conta",
        status_code=400,
        payload={"error": {"fields": [{"code": 62, "msg": "contas ja foram lancadas"}]}},
    )
    other = BlingApiError(
        "outro erro", status_code=400, payload={"error": {"fields": [{"code": 10}]}}
    )
    assert BlingIntegrationService._accounts_already_launched(dup) is True
    assert BlingIntegrationService._accounts_already_launched(other) is False


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
