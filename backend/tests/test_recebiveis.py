# -*- coding: utf-8 -*-
"""
Testes do módulo de Recebíveis — Auth JWT, Ledger e Comissões.

Cenários cobertos (spec seção 7):
  1. Login com credenciais válidas → 200 + JWT
  2. Login com senha errada → 401
  3. GET /api/ledger/balance sem token → 401
  4. Vendedor não pode ver saldo de outro vendedor (recebe os próprios dados)
  5. Admin registra pagamento (DEBIT) → saldo diminui
  6. Pedido WhatsApp concluído com 3% de comissão → CREDIT criado automaticamente
  7. Gerar semana duplicada → idempotente (sem duplicatas)
  8. pedido_id duplicado no ledger → UNIQUE constraint impede
"""
import os
from datetime import date, timedelta

import pytest

# Bcrypt com poucas rounds para testes rápidos.
# Precisa ser definido ANTES do primeiro import de auth_service.
os.environ.setdefault("BCRYPT_LOG_ROUNDS", "4")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-recebiveis")

from app.models.fonte_pedido import FontePedido  # noqa: E402
from app.models.ledger_entry import LedgerEntry  # noqa: E402
from app.models.pedido import Pedido  # noqa: E402
from app.models.user import CommissionConfig, PayrollConfig, User  # noqa: E402
from app.services.auth_service import generate_token, hash_password  # noqa: E402
from app.services.commission_service import get_monday, map_fonte_to_source  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(session, email, password="pass1234", role="vendedor", name="Teste"):
    """Cria e persiste um User com hash bcrypt."""
    user = User(name=name, email=email, password_hash=hash_password(password), role=role)
    session.add(user)
    session.commit()
    return user


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def do_login(client, email, password):
    """Faz POST /api/auth/login e retorna o response JSON."""
    return client.post("/api/auth/login", json={"email": email, "password": password})


def get_token(client, email, password):
    """Login e extrai access_token."""
    resp = do_login(client, email, password)
    return resp.get_json()["access_token"]


# ---------------------------------------------------------------------------
# 1. Autenticação JWT
# ---------------------------------------------------------------------------

class TestAuthJWT:
    """Cenários 1 e 2 da spec."""

    def test_login_valido_retorna_jwt_e_user(self, client, session):
        """Login com credenciais válidas retorna 200, access_token e dados do user."""
        make_user(session, "joao@test.com", "minha_senha", role="vendedor", name="João")
        resp = do_login(client, "joao@test.com", "minha_senha")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "access_token" in data
        assert data["user"]["email"] == "joao@test.com"
        assert data["user"]["role"] == "vendedor"

    def test_login_senha_errada_retorna_401(self, client, session):
        """Cenário 2: senha incorreta → 401."""
        make_user(session, "maria@test.com", "senha_correta")
        resp = do_login(client, "maria@test.com", "senha_errada")
        assert resp.status_code == 401

    def test_login_email_inexistente_retorna_401(self, client):
        """Email não cadastrado e sem env-var Basic Auth correspondente → 401."""
        resp = do_login(client, "naoexiste@puf.com", "qualquer")
        assert resp.status_code == 401

    def test_login_usuario_inativo_nao_autentica(self, client, session):
        """Usuário com is_active=False não deve conseguir login JWT."""
        user = make_user(session, "inativo@test.com", "pass1234")
        user.is_active = False
        session.commit()
        resp = do_login(client, "inativo@test.com", "pass1234")
        # Deve cair no fallback Basic Auth que também falhará → 401
        assert resp.status_code == 401

    def test_me_com_jwt_valido_retorna_user(self, client, session):
        """GET /api/auth/me com JWT válido retorna dados do usuário."""
        user = make_user(session, "ana@test.com", "pass1234", role="admin", name="Ana")
        token = generate_token(user)
        resp = client.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.get_json()["user"]["email"] == "ana@test.com"

    def test_me_sem_token_retorna_401(self, client):
        """GET /api/auth/me sem Authorization → 401."""
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Controle de Acesso ao Ledger
# ---------------------------------------------------------------------------

class TestLedgerAccess:
    """Cenários 3 e 4 da spec."""

    def test_balance_sem_token_retorna_401(self, client):
        """Cenário 3: sem token → 401."""
        resp = client.get("/api/ledger/balance")
        assert resp.status_code == 401

    def test_entries_sem_token_retorna_401(self, client):
        """Acesso ao extrato sem token → 401."""
        resp = client.get("/api/ledger/entries")
        assert resp.status_code == 401

    def test_viewer_nao_pode_acessar_ledger(self, client, session):
        """Role 'viewer' não tem acesso ao ledger → 403."""
        viewer = make_user(session, "viewer@test.com", "pass1234", role="viewer")
        token = generate_token(viewer)
        resp = client.get("/api/ledger/balance", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_vendedor_ve_proprio_saldo(self, client, session):
        """Vendedor autenticado consegue ver seu próprio saldo."""
        vendedor = make_user(session, "vend@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)
        resp = client.get("/api/ledger/balance", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.get_json()["user_id"] == vendedor.id

    def test_vendedor_nao_ve_saldo_de_outro(self, client, session):
        """Cenário 4: vendedor solicitando ?user_id de outro recebe os próprios dados (não 403)."""
        v1 = make_user(session, "v1@test.com", "pass1234", role="vendedor", name="V1")
        v2 = make_user(session, "v2@test.com", "pass1234", role="vendedor", name="V2")
        token_v1 = generate_token(v1)
        resp = client.get(f"/api/ledger/balance?user_id={v2.id}", headers=auth_headers(token_v1))
        assert resp.status_code == 200
        # Deve receber os dados de V1, não V2
        assert resp.get_json()["user_id"] == v1.id

    def test_admin_ve_saldo_de_outro_usuario(self, client, session):
        """Admin com ?user_id=X consegue ver saldo de outro usuário."""
        admin = make_user(session, "admin@test.com", "pass1234", role="admin", name="Admin")
        vendedor = make_user(session, "vendadm@test.com", "pass1234", role="vendedor")
        token = generate_token(admin)
        resp = client.get(
            f"/api/ledger/balance?user_id={vendedor.id}", headers=auth_headers(token)
        )
        assert resp.status_code == 200
        assert resp.get_json()["user_id"] == vendedor.id


# ---------------------------------------------------------------------------
# 3. Operações de Ledger (saldo e lançamentos manuais)
# ---------------------------------------------------------------------------

class TestLedgerOperations:
    """Cenário 5 da spec: registrar pagamento via DEBIT."""

    def test_saldo_inicial_zerado(self, client, session):
        """Vendedor sem lançamentos tem saldo zero."""
        vendedor = make_user(session, "zero@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)
        resp = client.get("/api/ledger/balance", headers=auth_headers(token))
        data = resp.get_json()
        assert data["balance"] == 0.0
        assert data["total_credits"] == 0.0
        assert data["total_debits"] == 0.0

    def test_admin_cria_credito_aumenta_saldo(self, client, session):
        """Admin cria CREDIT → saldo do vendedor aumenta."""
        admin = make_user(session, "adminop@test.com", "pass1234", role="admin", name="Admin")
        vendedor = make_user(session, "vendop@test.com", "pass1234", role="vendedor")
        admin_token = generate_token(admin)
        vendedor_token = generate_token(vendedor)

        resp = client.post(
            "/api/ledger/entries",
            json={
                "user_id": vendedor.id,
                "type": "CREDIT",
                "category": "fixo_semanal",
                "amount": 500.0,
                "week_ref": "2025-01-06",
                "description": "Salário semanal teste",
            },
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 201

        resp2 = client.get("/api/ledger/balance", headers=auth_headers(vendedor_token))
        data = resp2.get_json()
        assert data["total_credits"] == 500.0
        assert data["balance"] == 500.0

    def test_admin_registra_pagamento_reduz_saldo(self, client, session):
        """Cenário 5: DEBIT de pagamento reduz saldo devedor."""
        admin = make_user(session, "adminpg@test.com", "pass1234", role="admin", name="AdminPg")
        vendedor = make_user(session, "vendpg@test.com", "pass1234", role="vendedor")
        admin_token = generate_token(admin)
        vendedor_token = generate_token(vendedor)

        # Crédito inicial
        client.post(
            "/api/ledger/entries",
            json={
                "user_id": vendedor.id,
                "type": "CREDIT",
                "category": "fixo_semanal",
                "amount": 300.0,
                "week_ref": "2025-01-06",
            },
            headers=auth_headers(admin_token),
        )

        # Registra pagamento
        resp = client.post(
            "/api/ledger/entries",
            json={
                "user_id": vendedor.id,
                "type": "DEBIT",
                "category": "pagamento",
                "amount": 200.0,
                "week_ref": "2025-01-06",
                "description": "Pagamento semanal",
            },
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 201

        resp2 = client.get("/api/ledger/balance", headers=auth_headers(vendedor_token))
        data = resp2.get_json()
        assert data["total_credits"] == 300.0
        assert data["total_debits"] == 200.0
        assert data["balance"] == 100.0

    def test_vendedor_nao_pode_criar_entry(self, client, session):
        """POST /api/ledger/entries requer role admin → vendedor recebe 403."""
        vendedor = make_user(session, "vendnocr@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)
        resp = client.post(
            "/api/ledger/entries",
            json={
                "user_id": vendedor.id,
                "type": "CREDIT",
                "category": "fixo_semanal",
                "amount": 100.0,
                "week_ref": "2025-01-06",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_extrato_retorna_entries_do_vendedor(self, client, session):
        """GET /api/ledger/entries retorna lançamentos do vendedor."""
        admin = make_user(session, "adminex@test.com", "pass1234", role="admin", name="AdminEx")
        vendedor = make_user(session, "vendex@test.com", "pass1234", role="vendedor")
        admin_token = generate_token(admin)
        vendedor_token = generate_token(vendedor)

        client.post(
            "/api/ledger/entries",
            json={
                "user_id": vendedor.id,
                "type": "CREDIT",
                "category": "fixo_semanal",
                "amount": 400.0,
                "week_ref": "2025-02-10",
            },
            headers=auth_headers(admin_token),
        )

        resp = client.get("/api/ledger/entries", headers=auth_headers(vendedor_token))
        assert resp.status_code == 200
        entries = resp.get_json()["entries"]
        assert len(entries) == 1
        assert entries[0]["category"] == "fixo_semanal"
        assert entries[0]["amount"] == 400.0

    def test_pending_retorna_atrasados_e_apenas_proximo_futuro(self, client, session):
        """GET /api/ledger/pending inclui atrasados e somente o próximo dia futuro."""
        admin = make_user(session, "adminpd@test.com", "pass1234", role="admin", name="AdminPd")
        vendedor = make_user(session, "vendpd@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)

        today = date.today()
        week_ref = today

        e1 = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="fixo_semanal",
            amount=100.0,
            week_ref=week_ref,
            due_date=today - timedelta(days=1),
            status="pendente",
            created_by=admin.id,
        )
        e2 = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="almoco",
            amount=80.0,
            week_ref=week_ref,
            due_date=today + timedelta(days=2),
            status="pendente",
            created_by=admin.id,
        )
        e3 = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="transporte",
            amount=60.0,
            week_ref=week_ref,
            due_date=today + timedelta(days=7),
            status="pendente",
            created_by=admin.id,
        )
        e4 = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="fixo_mensal",
            amount=200.0,
            week_ref=week_ref,
            due_date=today + timedelta(days=2),
            status="pendente",
            created_by=admin.id,
        )
        session.add_all([e1, e2, e3, e4])
        session.commit()

        resp = client.get("/api/ledger/pending", headers=auth_headers(token))
        assert resp.status_code == 200
        entries = resp.get_json()["entries"]
        categories = [entry["category"] for entry in entries]

        assert "fixo_semanal" in categories
        assert "almoco" in categories
        assert "fixo_mensal" in categories
        assert "transporte" not in categories

    def test_balance_nao_soma_creditos_pendentes_futuros(self, client, session):
        """Saldo não deve incluir pendentes com due_date no futuro."""
        admin = make_user(session, "adminbal@test.com", "pass1234", role="admin", name="AdminBal")
        vendedor = make_user(session, "vendbal@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)

        today = date.today()
        entry = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="fixo_semanal",
            amount=500.0,
            week_ref=today,
            due_date=today + timedelta(days=2),
            status="pendente",
            created_by=admin.id,
        )
        session.add(entry)
        session.commit()

        resp = client.get("/api/ledger/balance", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["pending_credits"] == pytest.approx(0.0, abs=0.01)
        assert body["overdue_credits"] == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# 4. Comissões
# ---------------------------------------------------------------------------

class TestCommission:
    """Cenários 6 e 8 da spec."""

    def _setup_vendedor_com_comissao(self, session, email, rate=0.03):
        """Cria vendedor com CommissionConfig para whatsapp."""
        vendedor = make_user(session, email, "pass1234", role="vendedor", name="Comissionado")
        commission = CommissionConfig(user_id=vendedor.id, source="whatsapp", rate=rate)
        session.add(commission)
        session.commit()
        return vendedor

    def _make_pedido_whatsapp(
        self,
        session,
        vendedor_id,
        valor="R$ 100,00",
        status_pagamento=None,
    ):
        """Cria Pedido com FontePedido='WhatsApp' e vendedor_id.
        Cada teste tem seu próprio banco SQLite, logo não há conflito de unicidade.
        """
        from app.models.pedido import Pedido as PedidoModel
        from app.models.fonte_pedido import FontePedido as FonteModel

        fonte = FonteModel(nome="WhatsApp")
        session.add(fonte)
        session.flush()
        pedido = PedidoModel(
            cliente="Cliente Teste",
            telefone_cliente="11999999999",
            destinatario="Destinatário",
            produto="Buquê",
            valor=valor,
            dia_entrega=date(2025, 2, 10),  # 2025-02-10 é segunda-feira
            horario="10:00",
            status="agendado",
            status_pagamento=status_pagamento,
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor_id,
        )
        session.add(pedido)
        session.commit()
        # Re-fetch para garantir que a relationship fonte_pedido_rel está carregada
        return PedidoModel.query.get(pedido.id)

    # --- Utilitários ---

    def test_map_fonte_whatsapp(self):
        assert map_fonte_to_source("WhatsApp") == "whatsapp"

    def test_map_fonte_balcao(self):
        assert map_fonte_to_source("Balcão") == "balcao"

    def test_map_fonte_indicacao(self):
        assert map_fonte_to_source("Indicação") == "indicacao"

    def test_map_fonte_site(self):
        assert map_fonte_to_source("Site") == "site"

    def test_map_fonte_vazio(self):
        assert map_fonte_to_source("") == ""

    # --- Geração de comissão ---

    def test_fechar_pedido_whatsapp_gera_comissao(self, session):
        """Cenário 6: pedido WhatsApp com 3% de comissão → CREDIT entry criada."""
        from app.services.commission_service import generate_commission

        vendedor = self._setup_vendedor_com_comissao(session, "comv1@test.com", rate=0.03)
        pedido = self._make_pedido_whatsapp(session, vendedor.id, valor="R$ 100,00")

        generate_commission(pedido, vendedor.id)

        entries = LedgerEntry.query.filter_by(user_id=vendedor.id).all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.type == "CREDIT"
        assert entry.category == "comissao_whatsapp"
        assert entry.amount == pytest.approx(3.0, abs=0.01)
        assert entry.pedido_id == pedido.id
        # week_ref deve seguir a data de referência (criação/pagamento)
        assert entry.week_ref == get_monday(pedido.created_at.date())

    def test_comissao_idempotente_por_pedido_id(self, session):
        """Cenário 8 (service layer): segunda chamada com mesmo pedido → sem duplicata."""
        from app.services.commission_service import generate_commission

        vendedor = self._setup_vendedor_com_comissao(session, "comv2@test.com", rate=0.05)
        pedido = self._make_pedido_whatsapp(session, vendedor.id, valor="R$ 200,00")

        generate_commission(pedido, vendedor.id)
        generate_commission(pedido, vendedor.id)  # segunda chamada idempotente

        assert LedgerEntry.query.filter_by(user_id=vendedor.id).count() == 1

    def test_lucro_bruto_nao_gera_comissao(self, session):
        """Source 'lucro_bruto' é placeholder — não gera entry automática."""
        from app.services.commission_service import generate_commission

        vendedor = make_user(session, "comv3@test.com", "pass1234", role="vendedor")
        commission = CommissionConfig(user_id=vendedor.id, source="lucro_bruto", rate=0.10)
        session.add(commission)
        fonte = FontePedido(nome="Lucro-Bruto-Placeholder")
        session.add(fonte)
        session.flush()
        pedido = Pedido(
            cliente="C",
            telefone_cliente="11111111111",
            destinatario="D",
            produto="P",
            valor="R$ 500,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            status="agendado",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido)
        session.commit()

        generate_commission(pedido, vendedor.id)

        assert LedgerEntry.query.filter_by(user_id=vendedor.id).count() == 0

    def test_sem_config_comissao_nao_gera_entry(self, session):
        """Sem CommissionConfig cadastrada para a fonte → nenhuma entry criada."""
        from app.services.commission_service import generate_commission

        vendedor = make_user(session, "nocom@test.com", "pass1234", role="vendedor")
        pedido = self._make_pedido_whatsapp(session, vendedor.id)

        generate_commission(pedido, vendedor.id)

        assert LedgerEntry.query.filter_by(user_id=vendedor.id).count() == 0

    def test_valor_zero_nao_gera_comissao(self, session):
        """Pedido com valor inválido/zero → nenhuma entry criada."""
        from app.services.commission_service import generate_commission

        vendedor = self._setup_vendedor_com_comissao(session, "comv4@test.com", rate=0.03)
        pedido = self._make_pedido_whatsapp(session, vendedor.id, valor="")

        generate_commission(pedido, vendedor.id)

        assert LedgerEntry.query.filter_by(user_id=vendedor.id).count() == 0

    def test_pedido_id_unique_constraint_no_banco(self, session):
        """Cenário 8: UNIQUE constraint em pedido_id impede inserção direta duplicada."""
        from sqlalchemy.exc import IntegrityError

        vendedor = make_user(session, "uniq@test.com", "pass1234", role="vendedor")
        pedido = self._make_pedido_whatsapp(session, vendedor.id)
        week = date(2025, 2, 10)

        entry1 = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_whatsapp",
            amount=3.0,
            week_ref=week,
            created_by=vendedor.id,
            pedido_id=pedido.id,
        )
        session.add(entry1)
        session.commit()

        entry2 = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_whatsapp",
            amount=3.0,
            week_ref=week,
            created_by=vendedor.id,
            pedido_id=pedido.id,
        )
        session.add(entry2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_ledger_pedidos_retorna_pedidos_atribuidos_sem_entry(self, client, session):
        """GET /api/ledger/pedidos usa pedidos com vendedor_id, sem depender de ledger_entry."""
        vendedor = self._setup_vendedor_com_comissao(session, "comv5@test.com", rate=0.03)
        self._make_pedido_whatsapp(session, vendedor.id, valor="R$ 100,00")

        token = generate_token(vendedor)
        resp = client.get("/api/ledger/pedidos", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["total"] == 1
        assert len(body["pedidos"]) == 1
        pedido_row = body["pedidos"][0]
        assert pedido_row["fonte"] == "whatsapp"
        assert pedido_row["rate"] == 3.0
        assert pedido_row["commission_amount"] == pytest.approx(3.0, abs=0.01)
        assert pedido_row["status"] == "pendente"

    def test_ledger_pedidos_sem_config_retorna_comissao_zero(self, client, session):
        """Sem config de comissão, o pedido atribuído ainda aparece com comissão zero."""
        vendedor = make_user(session, "comv6@test.com", "pass1234", role="vendedor")
        self._make_pedido_whatsapp(session, vendedor.id, valor="R$ 100,00")

        token = generate_token(vendedor)
        resp = client.get("/api/ledger/pedidos", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["total"] == 1
        pedido_row = body["pedidos"][0]
        assert pedido_row["rate"] is None
        assert pedido_row["commission_amount"] == 0.0

    def test_ledger_pedidos_pago_usa_data_referencia_do_pagamento(self, client, session):
        """
        Pedido pago deve usar data de criação/pagamento como referência de comissão,
        não a data de entrega.
        """
        vendedor = self._setup_vendedor_com_comissao(session, "comv7@test.com", rate=0.03)
        pedido = self._make_pedido_whatsapp(
            session,
            vendedor.id,
            valor="R$ 100,00",
            status_pagamento="Pago",
        )

        token = generate_token(vendedor)
        resp = client.get("/api/ledger/pedidos", headers=auth_headers(token))

        assert resp.status_code == 200
        row = resp.get_json()["pedidos"][0]
        expected_ref_date = pedido.created_at.date().isoformat()
        assert row["due_date"] == expected_ref_date
        assert row["week_ref"] == get_monday(pedido.created_at.date()).isoformat()

    def test_balance_inclui_comissao_live_sem_ledger_entry(self, client, session):
        """Saldo deve incluir comissão de pedido pago mesmo sem entry persistida."""
        vendedor = self._setup_vendedor_com_comissao(session, "comv8@test.com", rate=0.03)
        self._make_pedido_whatsapp(
            session,
            vendedor.id,
            valor="R$ 100,00",
            status_pagamento="Pago",
        )

        token = generate_token(vendedor)
        resp = client.get("/api/ledger/balance", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["confirmed_credits"] == pytest.approx(3.0, abs=0.01)
        assert body["total_credits"] == pytest.approx(3.0, abs=0.01)
        assert body["balance"] == pytest.approx(3.0, abs=0.01)


# ---------------------------------------------------------------------------
# 5. Créditos Semanais Fixos
# ---------------------------------------------------------------------------

class TestWeeklyCredits:
    """Cenário 7 da spec: idempotência ao gerar semana duplicada."""

    def test_gera_creditos_semanais_para_vendedor(self, session):
        """generate_weekly_credits cria entry para cada config semanal ativa."""
        from app.services.ledger_service import generate_weekly_credits

        admin = make_user(session, "adminwk@test.com", "pass1234", role="admin", name="AdminWk")
        vendedor = make_user(session, "vendwk@test.com", "pass1234", role="vendedor")
        payroll = PayrollConfig(
            user_id=vendedor.id,
            category="fixo_semanal",
            label="Salário Semanal",
            amount=400.0,
            frequency="semanal",
        )
        session.add(payroll)
        session.commit()

        week = date(2025, 2, 10)
        result = generate_weekly_credits(week, created_by=admin.id)

        assert result["created"] == 1
        assert result["skipped"] == 0

        entries = LedgerEntry.query.filter_by(user_id=vendedor.id).all()
        assert len(entries) == 1
        assert entries[0].amount == 400.0
        assert entries[0].category == "fixo_semanal"
        assert entries[0].week_ref == date(2025, 2, 10)

    def test_gera_creditos_semanais_idempotente(self, session):
        """Cenário 7: segunda chamada na mesma semana não cria duplicata."""
        from app.services.ledger_service import generate_weekly_credits

        admin = make_user(session, "adminwk2@test.com", "pass1234", role="admin", name="Admin2")
        vendedor = make_user(session, "vendwk2@test.com", "pass1234", role="vendedor")
        payroll = PayrollConfig(
            user_id=vendedor.id,
            category="fixo_semanal",
            label="Salário Semanal",
            amount=400.0,
            frequency="semanal",
        )
        session.add(payroll)
        session.commit()

        week = date(2025, 2, 10)
        r1 = generate_weekly_credits(week, created_by=admin.id)
        r2 = generate_weekly_credits(week, created_by=admin.id)

        assert r1["created"] == 1
        assert r2["created"] == 0
        assert r2["skipped"] == 1
        assert LedgerEntry.query.filter_by(user_id=vendedor.id).count() == 1

    def test_config_mensal_nao_gerada_semanalmente(self, session):
        """PayrollConfig frequency='mensal' é ignorada em generate_weekly_credits."""
        from app.services.ledger_service import generate_weekly_credits

        admin = make_user(session, "adminwk3@test.com", "pass1234", role="admin", name="Admin3")
        vendedor = make_user(session, "vendwk3@test.com", "pass1234", role="vendedor")
        payroll = PayrollConfig(
            user_id=vendedor.id,
            category="fixo_mensal",
            label="Salário Mensal",
            amount=2000.0,
            frequency="mensal",
        )
        session.add(payroll)
        session.commit()

        result = generate_weekly_credits(date(2025, 2, 10), created_by=admin.id)

        assert result["created"] == 0
        assert LedgerEntry.query.filter_by(user_id=vendedor.id).count() == 0

    def test_semanas_diferentes_geram_entries_separadas(self, session):
        """Mesma config, semanas diferentes → duas entries distintas (não idempotente)."""
        from app.services.ledger_service import generate_weekly_credits

        admin = make_user(session, "adminwk4@test.com", "pass1234", role="admin", name="Admin4")
        vendedor = make_user(session, "vendwk4@test.com", "pass1234", role="vendedor")
        payroll = PayrollConfig(
            user_id=vendedor.id,
            category="fixo_semanal",
            label="Salário Semanal",
            amount=400.0,
            frequency="semanal",
        )
        session.add(payroll)
        session.commit()

        generate_weekly_credits(date(2025, 2, 10), created_by=admin.id)
        generate_weekly_credits(date(2025, 2, 17), created_by=admin.id)  # semana seguinte

        assert LedgerEntry.query.filter_by(user_id=vendedor.id).count() == 2

    def test_generate_weekly_via_api(self, client, session):
        """POST /api/ledger/generate-weekly via HTTP requer admin e retorna resultado."""
        admin = make_user(session, "adminapi@test.com", "pass1234", role="admin", name="AdminAPI")
        vendedor = make_user(session, "vendapi@test.com", "pass1234", role="vendedor")
        payroll = PayrollConfig(
            user_id=vendedor.id,
            category="fixo_semanal",
            label="Salário",
            amount=350.0,
            frequency="semanal",
        )
        session.add(payroll)
        session.commit()

        token = generate_token(admin)
        resp = client.post(
            "/api/ledger/generate-weekly",
            json={"week_ref": "2025-03-03"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["created"] >= 1

    def test_generate_weekly_proibido_para_vendedor(self, client, session):
        """Vendedor não pode disparar generate-weekly → 403."""
        vendedor = make_user(session, "vendnogen@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)
        resp = client.post(
            "/api/ledger/generate-weekly",
            json={"week_ref": "2025-03-03"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 403
