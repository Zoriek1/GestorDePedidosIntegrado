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
from app.services.commission_service import map_fonte_to_source  # noqa: E402
from app.utils.date_utils import get_monday  # noqa: E402

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

    def test_admin_registra_pagamento_nao_reduz_contas_a_receber(self, client, session):
        """Cenário 5: DEBIT é histórico e não reduz saldo de contas a receber."""
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
        assert data["balance"] == 300.0

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

    def test_pending_retorna_secoes_e_filtra_por_competencia(self, client, session, monkeypatch):
        """GET /api/ledger/pending separa atrasado/a_receber/quitado e filtra a_receber por competência."""
        from app.repositories import ledger_repository

        def iso_week_key(d: date) -> str:
            iso = d.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"

        fixed_today = date(2025, 2, 12)  # quarta
        monkeypatch.setattr(ledger_repository, "today_brazil", lambda: fixed_today)

        admin = make_user(session, "adminpd@test.com", "pass1234", role="admin", name="AdminPd")
        vendedor = make_user(session, "vendpd@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)

        pedidos = []
        for idx in range(1, 5):
            pedido = Pedido(
                cliente=f"Cliente {idx}",
                telefone_cliente="11999999999",
                destinatario=f"Dest {idx}",
                produto="Buque",
                valor="R$ 100,00",
                dia_entrega=fixed_today,
                horario="10:00",
                status="agendado",
                status_pagamento="Pago",
                vendedor_id=vendedor.id,
            )
            session.add(pedido)
            pedidos.append(pedido)
        session.flush()

        e_overdue = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_whatsapp",
            amount=100.0,
            week_ref=get_monday(fixed_today - timedelta(days=5)),
            due_date=fixed_today - timedelta(days=5),
            status="active",
            created_by=admin.id,
            pedido_id=pedidos[0].id,
        )
        e_current_week = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_site",
            amount=80.0,
            week_ref=get_monday(fixed_today + timedelta(days=1)),
            due_date=fixed_today + timedelta(days=1),
            status="active",
            created_by=admin.id,
            pedido_id=pedidos[1].id,
        )
        e_selected_week = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_site",
            amount=60.0,
            week_ref=get_monday(fixed_today + timedelta(days=8)),
            due_date=fixed_today + timedelta(days=8),
            status="active",
            created_by=admin.id,
            pedido_id=pedidos[2].id,
        )
        e_settled = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_whatsapp",
            amount=40.0,
            week_ref=get_monday(fixed_today - timedelta(days=2)),
            due_date=fixed_today - timedelta(days=2),
            status="settled",
            created_by=admin.id,
            pedido_id=pedidos[3].id,
        )
        session.add_all([e_overdue, e_current_week, e_selected_week, e_settled])
        session.commit()

        selected_competencia = iso_week_key(fixed_today + timedelta(days=8))
        resp = client.get(
            f"/api/ledger/pending?competencia_tipo=semanal&competencia={selected_competencia}&include_quitados=false",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["competencia_tipo"] == "semanal"
        assert body["competencia"] == selected_competencia
        assert body["atrasado"]["total_pedidos"] == 1
        assert body["a_receber"]["total_pedidos"] == 1
        assert body["quitado"]["total_pedidos"] == 0

        atrasado_ids = [p["pedido_id"] for p in body["atrasado"]["pedidos"]]
        a_receber_ids = [p["pedido_id"] for p in body["a_receber"]["pedidos"]]
        assert pedidos[0].id in atrasado_ids
        assert pedidos[2].id in a_receber_ids
        assert pedidos[1].id not in a_receber_ids

        resp_hist = client.get(
            f"/api/ledger/pending?competencia_tipo=semanal&competencia={selected_competencia}&include_quitados=true",
            headers=auth_headers(token),
        )
        assert resp_hist.status_code == 200
        body_hist = resp_hist.get_json()
        quitado_ids = [p["pedido_id"] for p in body_hist["quitado"]["pedidos"]]
        assert pedidos[3].id in quitado_ids

    def test_pending_competencia_mensal_filtra_somente_a_receber(self, client, session, monkeypatch):
        """competencia_tipo=mensal deve filtrar só a seção a_receber."""
        from app.repositories import ledger_repository

        fixed_today = date(2025, 2, 12)
        monkeypatch.setattr(ledger_repository, "today_brazil", lambda: fixed_today)

        admin = make_user(session, "adminpm@test.com", "pass1234", role="admin", name="AdminPm")
        vendedor = make_user(session, "vendpm@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)

        p_fev = Pedido(
            cliente="Cliente Fev",
            telefone_cliente="11999999999",
            destinatario="Dest Fev",
            produto="Buque",
            valor="R$ 100,00",
            dia_entrega=fixed_today,
            horario="10:00",
            status="agendado",
            status_pagamento="Pago",
            vendedor_id=vendedor.id,
        )
        p_mar = Pedido(
            cliente="Cliente Mar",
            telefone_cliente="11999999999",
            destinatario="Dest Mar",
            produto="Buque",
            valor="R$ 100,00",
            dia_entrega=fixed_today,
            horario="10:00",
            status="agendado",
            status_pagamento="Pago",
            vendedor_id=vendedor.id,
        )
        session.add_all([p_fev, p_mar])
        session.flush()

        session.add_all([
            LedgerEntry(
                user_id=vendedor.id,
                type="CREDIT",
                category="comissao_site",
                amount=50.0,
                week_ref=get_monday(date(2025, 2, 20)),
                due_date=date(2025, 2, 20),
                status="active",
                created_by=admin.id,
                pedido_id=p_fev.id,
            ),
            LedgerEntry(
                user_id=vendedor.id,
                type="CREDIT",
                category="comissao_site",
                amount=70.0,
                week_ref=get_monday(date(2025, 3, 5)),
                due_date=date(2025, 3, 5),
                status="active",
                created_by=admin.id,
                pedido_id=p_mar.id,
            ),
        ])
        session.commit()

        resp = client.get(
            "/api/ledger/pending?competencia_tipo=mensal&competencia=2025-03&include_quitados=false",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["a_receber"]["total_pedidos"] == 1
        assert body["a_receber"]["pedidos"][0]["pedido_id"] == p_mar.id

    def test_balance_credito_futuro_em_upcoming(self, client, session):
        """CREDIT active com due_date no futuro aparece em upcoming_credits e conta no balance."""
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
            status="active",
            created_by=admin.id,
        )
        session.add(entry)
        session.commit()

        resp = client.get("/api/ledger/balance", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["upcoming_credits"] == pytest.approx(500.0, abs=0.01)
        assert body["overdue_credits"] == pytest.approx(0.0, abs=0.01)
        assert body["balance"] == pytest.approx(500.0, abs=0.01)


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
        from app.models.fonte_pedido import FontePedido as FonteModel
        from app.models.pedido import Pedido as PedidoModel

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

    def test_comissao_por_fonte_pedido_id(self, session):
        """Config por fonte real (fonte_pedido_id) deve gerar comissão."""
        from app.services.commission_service import generate_commission

        fonte = FontePedido(nome="WhatsApp Oficial")
        session.add(fonte)
        session.flush()

        vendedor = make_user(session, "comv2b@test.com", "pass1234", role="vendedor")
        commission = CommissionConfig(
            user_id=vendedor.id,
            fonte_pedido_id=fonte.id,
            source="whatsapp_oficial",
            rate=0.04,
        )
        session.add(commission)
        session.commit()

        pedido = Pedido(
            cliente="Cliente Teste",
            telefone_cliente="11999999999",
            destinatario="Destinatário",
            produto="Buquê",
            valor="R$ 100,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            status="agendado",
            status_pagamento="Pago",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido)
        session.commit()

        generate_commission(pedido, vendedor.id)
        session.commit()

        entry = LedgerEntry.query.filter_by(user_id=vendedor.id, pedido_id=pedido.id).first()
        assert entry is not None
        assert entry.amount == pytest.approx(4.0, abs=0.01)
        assert entry.category.startswith("comissao_")

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

    def test_ledger_pedidos_retorna_entrada_apos_comissao(self, client, session):
        """GET /api/ledger/pedidos lê de ledger_entry — pedido aparece após generate_commission."""
        from app.services.commission_service import generate_commission

        vendedor = self._setup_vendedor_com_comissao(session, "comv5@test.com", rate=0.03)
        pedido = self._make_pedido_whatsapp(session, vendedor.id, valor="R$ 100,00")

        generate_commission(pedido, vendedor.id)

        token = generate_token(vendedor)
        resp = client.get("/api/ledger/pedidos", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["total"] == 1
        assert len(body["pedidos"]) == 1
        pedido_row = body["pedidos"][0]
        assert pedido_row["category"] == "comissao_whatsapp"
        assert pedido_row["commission_amount"] == pytest.approx(3.0, abs=0.01)
        assert pedido_row["status"] == "active"

    def test_ledger_pedidos_sem_config_nao_aparece(self, client, session):
        """Sem config de comissão, generate_commission não cria entry → /pedidos retorna vazio."""
        vendedor = make_user(session, "comv6@test.com", "pass1234", role="vendedor")
        self._make_pedido_whatsapp(session, vendedor.id, valor="R$ 100,00")

        token = generate_token(vendedor)
        resp = client.get("/api/ledger/pedidos", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["total"] == 0

    def test_ledger_pedidos_pago_usa_data_referencia_do_pagamento(self, client, session):
        """
        Pedido pago deve usar data de criação/pagamento como referência de comissão,
        não a data de entrega. Entry criada via generate_commission reflete isso.
        """
        from app.services.commission_service import generate_commission

        vendedor = self._setup_vendedor_com_comissao(session, "comv7@test.com", rate=0.03)
        pedido = self._make_pedido_whatsapp(
            session,
            vendedor.id,
            valor="R$ 100,00",
            status_pagamento="Pago",
        )

        generate_commission(pedido, vendedor.id)

        token = generate_token(vendedor)
        resp = client.get("/api/ledger/pedidos", headers=auth_headers(token))

        assert resp.status_code == 200
        rows = resp.get_json()["pedidos"]
        assert len(rows) == 1
        row = rows[0]
        assert row["week_ref"] == get_monday(pedido.created_at.date()).isoformat()

    def test_balance_inclui_comissao_apos_geracao(self, client, session):
        """Saldo reflete comissão após generate_commission persistir a CREDIT entry."""
        from app.services.commission_service import generate_commission

        vendedor = self._setup_vendedor_com_comissao(session, "comv8@test.com", rate=0.03)
        pedido = self._make_pedido_whatsapp(
            session,
            vendedor.id,
            valor="R$ 100,00",
            status_pagamento="Pago",
        )

        generate_commission(pedido, vendedor.id)

        token = generate_token(vendedor)
        resp = client.get("/api/ledger/balance", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total_credits"] == pytest.approx(3.0, abs=0.01)
        assert body["balance"] == pytest.approx(3.0, abs=0.01)

    def test_periods_agrupa_por_due_date_e_fonte(self, session):
        """Resumo de períodos deve agrupar por due_date e subtotalizar por fonte."""
        from app.services.ledger_service import get_period_summary

        admin = make_user(session, "adminperiod@test.com", "pass1234", role="admin")
        vendedor = make_user(session, "vendperiod@test.com", "pass1234", role="vendedor")
        fonte_w = FontePedido(nome="WhatsApp")
        fonte_s = FontePedido(nome="Site")
        session.add_all([fonte_w, fonte_s])
        session.flush()

        p1 = Pedido(
            cliente="C1",
            telefone_cliente="11111111111",
            destinatario="D1",
            produto="P1",
            valor="R$ 100,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            fonte_pedido_id=fonte_w.id,
            vendedor_id=vendedor.id,
        )
        p2 = Pedido(
            cliente="C2",
            telefone_cliente="22222222222",
            destinatario="D2",
            produto="P2",
            valor="R$ 200,00",
            dia_entrega=date(2025, 2, 10),
            horario="11:00",
            fonte_pedido_id=fonte_s.id,
            vendedor_id=vendedor.id,
        )
        session.add_all([p1, p2])
        session.flush()

        due = date(2025, 2, 14)
        e1 = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_whatsapp",
            amount=3.0,
            pedido_id=p1.id,
            week_ref=date(2025, 2, 10),
            due_date=due,
            status="active",
            created_by=admin.id,
        )
        e2 = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_site",
            amount=5.0,
            pedido_id=p2.id,
            week_ref=date(2025, 2, 10),
            due_date=due,
            status="settled",
            created_by=admin.id,
        )
        session.add_all([e1, e2])
        session.commit()

        summary = get_period_summary(vendedor.id)
        period = next(p for p in summary["periods"] if p["period_date"] == due.isoformat())
        assert period["total_commission"] == pytest.approx(8.0, abs=0.01)
        assert period["active_commission"] == pytest.approx(3.0, abs=0.01)
        assert period["settled_commission"] == pytest.approx(5.0, abs=0.01)
        assert period["orders_count"] == 2
        sources = {s["source"] for s in period["by_source"]}
        assert "WhatsApp" in sources
        assert "Site" in sources


# ---------------------------------------------------------------------------
# 4.1. Lifecycle de comissão e settle idempotente
# ---------------------------------------------------------------------------

class TestCommissionLifecycleAndSettle:
    def test_settle_idempotente_quando_sem_creditos(self, client, session):
        """POST /api/ledger/settle sem créditos elegíveis retorna settled=0 e não cria DEBIT."""
        vendedor = make_user(session, "settle0@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)

        resp = client.post(
            "/api/ledger/settle",
            headers=auth_headers(token),
            json={"pedido_ids": [999999]},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["settled"] == 0
        assert body["pedido_ids_settled"] == []
        assert body["pedido_ids_ignored"] == [999999]
        assert LedgerEntry.query.filter_by(user_id=vendedor.id, type="DEBIT").count() == 0

    def test_settle_idempotente_em_duas_chamadas(self, client, session):
        """Primeira quita os pedidos selecionados; segunda chamada não cria novo DEBIT."""
        admin = make_user(session, "settleadm@test.com", "pass1234", role="admin")
        vendedor = make_user(session, "settle1@test.com", "pass1234", role="vendedor")
        token = generate_token(vendedor)

        pedido = Pedido(
            cliente="Cliente Settle",
            telefone_cliente="11999999999",
            destinatario="Dest Settle",
            produto="Buque",
            valor="R$ 120,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            status="agendado",
            status_pagamento="Pago",
            vendedor_id=vendedor.id,
        )
        session.add(pedido)
        session.flush()

        credit = LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_site",
            amount=120.0,
            week_ref=date(2025, 2, 10),
            status="active",
            created_by=admin.id,
            pedido_id=pedido.id,
        )
        session.add(credit)
        session.commit()

        resp1 = client.post(
            "/api/ledger/settle",
            headers=auth_headers(token),
            json={"pedido_ids": [pedido.id]},
        )
        assert resp1.status_code == 200
        assert resp1.get_json()["settled"] == 1
        assert LedgerEntry.query.filter_by(user_id=vendedor.id, type="DEBIT").count() == 1
        credit_after = LedgerEntry.query.filter_by(id=credit.id).first()
        assert credit_after is not None
        assert credit_after.status == "settled"
        assert credit_after.settled_by_id is not None

        resp2 = client.post(
            "/api/ledger/settle",
            headers=auth_headers(token),
            json={"pedido_ids": [pedido.id]},
        )
        assert resp2.status_code == 200
        assert resp2.get_json()["settled"] == 0
        assert LedgerEntry.query.filter_by(user_id=vendedor.id, type="DEBIT").count() == 1

    def test_trigger_create_update_pago_parcial(self, session):
        """Create Pago e update para Pago/Parcial devem disparar comissão via lifecycle."""
        from app.services.order_commission_lifecycle import (
            apply_commission_lifecycle,
            snapshot_commission_fields,
        )

        vendedor = make_user(session, "life1@test.com", "pass1234", role="vendedor")
        fonte = FontePedido(nome="WhatsApp")
        session.add(fonte)
        session.flush()
        session.add(
            CommissionConfig(
                user_id=vendedor.id,
                fonte_pedido_id=fonte.id,
                source="whatsapp",
                rate=0.03,
            )
        )
        session.commit()

        pedido_create_paid = Pedido(
            cliente="Cliente A",
            telefone_cliente="11999999999",
            destinatario="Dest A",
            produto="Buquê",
            valor="R$ 100,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            status="agendado",
            status_pagamento="Pago",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido_create_paid)
        session.flush()
        result_create = apply_commission_lifecycle(
            pedido_create_paid, previous=None, actor_id=vendedor.id
        )
        session.commit()

        assert result_create["generated"] is True
        assert pedido_create_paid.paid_at is not None
        assert LedgerEntry.query.filter_by(pedido_id=pedido_create_paid.id, voided=False).count() == 1

        pedido_update_to_paid = Pedido(
            cliente="Cliente B",
            telefone_cliente="11888888888",
            destinatario="Dest B",
            produto="Rosa",
            valor="R$ 200,00",
            dia_entrega=date(2025, 2, 11),
            horario="11:00",
            status="agendado",
            status_pagamento="Pendente",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido_update_to_paid)
        session.flush()

        snapshot = snapshot_commission_fields(pedido_update_to_paid)
        pedido_update_to_paid.status_pagamento = "Parcial"
        result_update = apply_commission_lifecycle(
            pedido_update_to_paid, previous=snapshot, actor_id=vendedor.id
        )
        session.commit()

        assert result_update["transitioning_to_paid"] is True
        assert pedido_update_to_paid.paid_at is not None
        assert LedgerEntry.query.filter_by(pedido_id=pedido_update_to_paid.id, voided=False).count() == 1

    def test_estorno_e_recriacao_em_edicao_sensivel(self, session):
        """Mudança sensível em pedido com comissão ativa deve estornar e recriar."""
        from app.services.order_commission_lifecycle import (
            apply_commission_lifecycle,
            snapshot_commission_fields,
        )

        vendedor = make_user(session, "life2@test.com", "pass1234", role="vendedor")
        fonte = FontePedido(nome="Site")
        session.add(fonte)
        session.flush()
        session.add(
            CommissionConfig(
                user_id=vendedor.id,
                fonte_pedido_id=fonte.id,
                source="site",
                rate=0.10,
            )
        )
        session.commit()

        pedido = Pedido(
            cliente="Cliente C",
            telefone_cliente="11777777777",
            destinatario="Dest C",
            produto="Arranjo",
            valor="R$ 100,00",
            dia_entrega=date(2025, 2, 12),
            horario="12:00",
            status="agendado",
            status_pagamento="Pago",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido)
        session.flush()
        apply_commission_lifecycle(pedido, previous=None, actor_id=vendedor.id)
        session.commit()

        original_credit = LedgerEntry.query.filter_by(
            pedido_id=pedido.id, type="CREDIT", voided=False
        ).first()
        assert original_credit is not None
        assert float(original_credit.amount) == pytest.approx(10.0, abs=0.01)

        snapshot = snapshot_commission_fields(pedido)
        pedido.valor = "R$ 200,00"
        result = apply_commission_lifecycle(pedido, previous=snapshot, actor_id=vendedor.id)
        session.commit()

        assert result["voided_and_recreated"] is True

        old_credit = LedgerEntry.query.filter_by(id=original_credit.id).first()
        assert old_credit is not None
        assert old_credit.voided is True

        debit = (
            LedgerEntry.query.filter_by(
                user_id=vendedor.id,
                type="DEBIT",
                category="ajuste_debito",
            )
            .order_by(LedgerEntry.id.desc())
            .first()
        )
        assert debit is not None
        assert float(debit.amount) == pytest.approx(10.0, abs=0.01)

        new_credit = (
            LedgerEntry.query.filter_by(
                pedido_id=pedido.id,
                type="CREDIT",
                voided=False,
            )
            .order_by(LedgerEntry.id.desc())
            .first()
        )
        assert new_credit is not None
        assert new_credit.id != original_credit.id
        assert float(new_credit.amount) == pytest.approx(20.0, abs=0.01)

    def test_due_date_com_payment_day_aplicado_na_comissao(self, session):
        """generate_commission deve usar payment_day semanal para calcular due_date."""
        from app.services.commission_service import generate_commission

        vendedor = make_user(session, "life3@test.com", "pass1234", role="vendedor")
        fonte = FontePedido(nome="Indicação")
        session.add(fonte)
        session.flush()

        session.add(
            CommissionConfig(
                user_id=vendedor.id,
                fonte_pedido_id=fonte.id,
                source="indicacao",
                rate=0.10,
            )
        )
        session.add(
            PayrollConfig(
                user_id=vendedor.id,
                category="fixo_semanal",
                label="Semanal",
                amount=100.0,
                frequency="semanal",
                payment_day=4,  # sexta
                is_active=True,
            )
        )
        session.commit()

        pedido = Pedido(
            cliente="Cliente D",
            telefone_cliente="11666666666",
            destinatario="Dest D",
            produto="Girassol",
            valor="R$ 100,00",
            dia_entrega=date(2025, 2, 10),  # segunda
            horario="13:00",
            status="agendado",
            status_pagamento="Pago",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido)
        session.commit()

        generate_commission(pedido, vendedor.id, reference_date=date(2025, 2, 10))
        session.commit()

        entry = LedgerEntry.query.filter_by(pedido_id=pedido.id, type="CREDIT", voided=False).first()
        assert entry is not None
        assert entry.due_date == date(2025, 2, 14)


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


# ---------------------------------------------------------------------------
# 6. Correções da auditoria 2026-04 (bug Site/Nuvemshop + 11 críticos/altos)
# ---------------------------------------------------------------------------

class TestAuditFixes:
    """Cobre as correções aplicadas após a auditoria do sistema de comissão/salário."""

    def _setup_pedido_pago_com_comissao(self, session, source="site", rate=0.10):
        """Helper: vendedor + config + pedido Pago, com CREDIT já gerado."""
        from app.services.order_commission_lifecycle import apply_commission_lifecycle

        vendedor = make_user(
            session,
            f"audit_{source}_{rate}@test.com",
            "pass1234",
            role="vendedor",
        )
        fonte = FontePedido(nome=source.capitalize())
        session.add(fonte)
        session.flush()
        session.add(
            CommissionConfig(
                user_id=vendedor.id, fonte_pedido_id=fonte.id, source=source, rate=rate
            )
        )
        session.commit()

        pedido = Pedido(
            cliente="Cliente",
            telefone_cliente="11999999999",
            destinatario="Dest",
            produto="Prod",
            valor="R$ 100,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            status="agendado",
            status_pagamento="Pago",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido)
        session.flush()
        apply_commission_lifecycle(pedido, previous=None, actor_id=vendedor.id)
        session.commit()
        return vendedor, pedido

    # --- Snapshot no CREDIT (Fase 1.3) ---

    def test_credit_recebe_snapshot_de_rate_e_source(self, session):
        """generate_commission deve persistir commission_rate e commission_source."""
        vendedor, pedido = self._setup_pedido_pago_com_comissao(
            session, source="site", rate=0.07
        )
        credit = LedgerEntry.query.filter_by(pedido_id=pedido.id, voided=False).first()
        assert credit is not None
        assert float(credit.commission_rate) == pytest.approx(0.07, abs=1e-6)
        assert credit.commission_source == "site"

    # --- Regressão Pago → Pendente (Fase 3.1) ---

    def test_status_pago_para_pendente_voida_comissao_sem_debit(self, session):
        """Regressão de status_pagamento marca CREDIT voided sem criar DEBIT."""
        from app.services.order_commission_lifecycle import (
            apply_commission_lifecycle,
            snapshot_commission_fields,
        )

        vendedor, pedido = self._setup_pedido_pago_com_comissao(
            session, source="balcao", rate=0.05
        )
        credit_before = LedgerEntry.query.filter_by(pedido_id=pedido.id).first()
        debits_before = LedgerEntry.query.filter_by(
            user_id=vendedor.id, type="DEBIT"
        ).count()

        snapshot = snapshot_commission_fields(pedido)
        pedido.status_pagamento = "Pendente"
        result = apply_commission_lifecycle(pedido, previous=snapshot, actor_id=vendedor.id)
        session.commit()

        assert result["transitioning_from_paid"] is True
        assert result["voided"] is True
        credit_after = LedgerEntry.query.filter_by(id=credit_before.id).first()
        assert credit_after.voided is True
        assert credit_after.void_reason == "status_regression"
        debits_after = LedgerEntry.query.filter_by(
            user_id=vendedor.id, type="DEBIT"
        ).count()
        assert debits_after == debits_before  # nenhum DEBIT foi criado

    # --- Soft delete (Fase 3.2) ---

    def test_void_active_commission_helper(self, session):
        """void_active_commission marca CREDIT voided sem criar DEBIT."""
        from app.services.commission_service import void_active_commission

        vendedor, pedido = self._setup_pedido_pago_com_comissao(
            session, source="indicacao", rate=0.03
        )
        debits_before = LedgerEntry.query.filter_by(
            user_id=vendedor.id, type="DEBIT"
        ).count()

        ok = void_active_commission(pedido, reason="soft_delete")
        session.commit()

        assert ok is True
        credit = LedgerEntry.query.filter_by(pedido_id=pedido.id).first()
        assert credit.voided is True
        assert credit.void_reason == "soft_delete"
        debits_after = LedgerEntry.query.filter_by(
            user_id=vendedor.id, type="DEBIT"
        ).count()
        assert debits_after == debits_before

    def test_void_active_commission_ignora_credit_ja_quitado(self, session):
        """Soft delete/status regression não devem voidar crédito já settled."""
        from app.services.commission_service import void_active_commission

        _, pedido = self._setup_pedido_pago_com_comissao(
            session, source="site", rate=0.04
        )
        credit = LedgerEntry.query.filter_by(pedido_id=pedido.id, voided=False).first()
        credit.status = "settled"
        session.commit()

        ok = void_active_commission(pedido, reason="soft_delete")
        session.commit()

        credit_after = LedgerEntry.query.filter_by(id=credit.id).first()
        assert ok is False
        assert credit_after.voided is False

    def test_void_active_commission_sem_credit_retorna_false(self, session):
        """Helper retorna False quando não há CREDIT ativo."""
        from app.services.commission_service import void_active_commission

        vendedor = make_user(session, "novod@test.com", "pass1234", role="vendedor")
        fonte = FontePedido(nome="Site")
        session.add(fonte)
        session.flush()
        pedido = Pedido(
            cliente="X",
            telefone_cliente="11000000000",
            destinatario="X",
            produto="X",
            valor="R$ 50,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            status="agendado",
            status_pagamento="Pendente",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido)
        session.commit()

        assert void_active_commission(pedido, reason="soft_delete") is False

    # --- Balance exclui ajuste_debito (Fase 4.3) ---

    def test_balance_exclui_ajuste_debito(self, session):
        """DEBIT de categoria ajuste_debito não conta como pagamento no saldo."""
        from app.repositories.ledger_repository import LedgerRepository
        from app.services.order_commission_lifecycle import (
            apply_commission_lifecycle,
            snapshot_commission_fields,
        )

        vendedor, pedido = self._setup_pedido_pago_com_comissao(
            session, source="site", rate=0.10
        )
        # CREDIT inicial = R$10
        # Edição sensível: muda valor, gera estorno + nova comissão
        snapshot = snapshot_commission_fields(pedido)
        pedido.valor = "R$ 200,00"
        apply_commission_lifecycle(pedido, previous=snapshot, actor_id=vendedor.id)
        session.commit()

        # Após estorno: 1 CREDIT voided (10), 1 DEBIT ajuste_debito (10),
        # 1 CREDIT ativo (20). Saldo deve refletir SOMENTE o CREDIT ativo (20),
        # ignorando o DEBIT de ajuste.
        balance = LedgerRepository().get_balance(vendedor.id)
        assert balance["balance"] == pytest.approx(20.0, abs=0.01)
        assert balance["total_debits"] == pytest.approx(0.0, abs=0.01)

    def test_estorno_preserva_snapshot_no_credit_voidado(self, session):
        """Após estorno, o DEBIT de ajuste guarda rate/source históricos."""
        from app.services.order_commission_lifecycle import (
            apply_commission_lifecycle,
            snapshot_commission_fields,
        )

        vendedor, pedido = self._setup_pedido_pago_com_comissao(
            session, source="site", rate=0.10
        )
        snapshot = snapshot_commission_fields(pedido)
        pedido.valor = "R$ 300,00"
        apply_commission_lifecycle(pedido, previous=snapshot, actor_id=vendedor.id)
        session.commit()

        debit = (
            LedgerEntry.query.filter_by(
                user_id=vendedor.id,
                type="DEBIT",
                category="ajuste_debito",
            )
            .order_by(LedgerEntry.id.desc())
            .first()
        )
        assert debit is not None
        assert float(debit.commission_rate) == pytest.approx(0.10, abs=1e-6)
        assert debit.commission_source == "site"

    # --- settle_user_credits refatorado (Fase 4.1) ---

    def test_settle_credits_total_correto_apos_refactor(self, client, session):
        """Quitação parcial cria DEBIT com soma exata dos pedidos selecionados."""
        admin = make_user(session, "auditadm@test.com", "pass1234", role="admin")
        vendedor = make_user(session, "auditset@test.com", "pass1234", role="vendedor")
        token = generate_token(admin)

        pedidos = []
        for idx in range(1, 5):
            pedido = Pedido(
                cliente=f"Cliente {idx}",
                telefone_cliente="11999999999",
                destinatario=f"Dest {idx}",
                produto="Buque",
                valor="R$ 100,00",
                dia_entrega=date(2025, 3, 3),
                horario="10:00",
                status="agendado",
                status_pagamento="Pago",
                vendedor_id=vendedor.id,
            )
            session.add(pedido)
            pedidos.append(pedido)
        session.flush()

        amounts = [50.0, 75.5, 24.5, 10.0]
        for pedido, amount in zip(pedidos, amounts):
            session.add(
                LedgerEntry(
                    user_id=vendedor.id,
                    type="CREDIT",
                    category="comissao_site",
                    amount=amount,
                    week_ref=date(2025, 3, 3),
                    status="active",
                    created_by=admin.id,
                    pedido_id=pedido.id,
                )
            )
        session.commit()

        selected_ids = [pedidos[0].id, pedidos[1].id, pedidos[2].id]
        resp = client.post(
            "/api/ledger/settle",
            json={"user_id": vendedor.id, "pedido_ids": selected_ids},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["settled"] == 3
        assert body["pedido_ids_settled"] == selected_ids
        assert body["pedido_ids_ignored"] == []
        debits = LedgerEntry.query.filter_by(user_id=vendedor.id, type="DEBIT").all()
        assert len(debits) == 1
        assert float(debits[0].amount) == pytest.approx(150.0, abs=0.01)
        # Apenas os CREDITs selecionados apontam para o DEBIT
        for credit in LedgerEntry.query.filter_by(user_id=vendedor.id, type="CREDIT").all():
            if credit.pedido_id in selected_ids:
                assert credit.status == "settled"
                assert credit.settled_by_id == debits[0].id
            else:
                assert credit.status == "active"
                assert credit.settled_by_id is None

    def test_settle_sem_credits_ativos_nao_deixa_debit_orfao(self, client, session):
        """Quitar com pedido_ids sem elegibilidade não cria DEBIT."""
        admin = make_user(session, "audadm2@test.com", "pass1234", role="admin")
        vendedor = make_user(session, "audset2@test.com", "pass1234", role="vendedor")
        token = generate_token(admin)

        resp = client.post(
            "/api/ledger/settle",
            json={"user_id": vendedor.id, "pedido_ids": [123456]},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["settled"] == 0
        assert body["pedido_ids_ignored"] == [123456]
        assert LedgerEntry.query.filter_by(user_id=vendedor.id).count() == 0

    def test_generate_commission_permanece_idempotente_com_credit_ja_quitado(self, session):
        """Regerar comissão não duplica quando já existe CREDIT histórico settled."""
        from app.services.commission_service import generate_commission

        vendedor, pedido = self._setup_pedido_pago_com_comissao(
            session, source="site", rate=0.06
        )
        credit = LedgerEntry.query.filter_by(pedido_id=pedido.id, voided=False).first()
        credit.status = "settled"
        session.commit()

        generate_commission(pedido, vendedor.id)
        session.commit()

        credits = LedgerEntry.query.filter_by(
            pedido_id=pedido.id,
            type="CREDIT",
        ).all()
        assert len(credits) == 1

    def test_restore_regera_comissao_voidada_no_soft_delete(self, client, session):
        """Restore de pedido pago recompõe a comissão voidada no soft delete."""
        from app.services.commission_service import void_active_commission

        admin = make_user(session, "audrestore@test.com", "pass1234", role="admin")
        token = generate_token(admin)
        vendedor, pedido = self._setup_pedido_pago_com_comissao(
            session, source="site", rate=0.10
        )

        assert void_active_commission(pedido, reason="soft_delete") is True
        pedido.soft_delete()
        session.commit()

        assert (
            LedgerEntry.query.filter_by(
                pedido_id=pedido.id,
                type="CREDIT",
                voided=False,
            ).count()
            == 0
        )

        resp = client.post(
            f"/api/pedidos/{pedido.id}/restore",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200

        pedido_restaurado = Pedido.query.get(pedido.id)
        assert pedido_restaurado is not None
        assert pedido_restaurado.is_deleted is False

        active_credit = LedgerEntry.query.filter_by(
            pedido_id=pedido.id,
            type="CREDIT",
            voided=False,
        ).first()
        assert active_credit is not None
        assert float(active_credit.amount) == pytest.approx(10.0, abs=0.01)

    # --- Validação de inputs (Fase 1.1, 1.2) ---

    def test_payroll_rejeita_payment_day_invalido(self, client, session):
        """PUT /api/users/<id>/payroll rejeita payment_day fora de 0-6."""
        admin = make_user(session, "audval@test.com", "pass1234", role="admin")
        vendedor = make_user(session, "audval2@test.com", "pass1234", role="vendedor")
        token = generate_token(admin)

        resp = client.put(
            f"/api/users/{vendedor.id}/payroll",
            json={
                "category": "fixo_semanal",
                "label": "Salário",
                "amount": 500.0,
                "frequency": "semanal",
                "payment_day": 7,
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        assert "payment_day" in resp.get_json().get("error", "")

    def test_payroll_rejeita_semanal_sem_payment_day(self, client, session):
        """frequency='semanal' sem payment_day → 400."""
        admin = make_user(session, "audval3@test.com", "pass1234", role="admin")
        vendedor = make_user(session, "audval4@test.com", "pass1234", role="vendedor")
        token = generate_token(admin)

        resp = client.put(
            f"/api/users/{vendedor.id}/payroll",
            json={
                "category": "fixo_semanal",
                "label": "Salário",
                "amount": 500.0,
                "frequency": "semanal",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    def test_commission_rejeita_rate_negativa(self, client, session):
        """PUT /api/users/<id>/commission rejeita rate < 0."""
        admin = make_user(session, "audval5@test.com", "pass1234", role="admin")
        vendedor = make_user(session, "audval6@test.com", "pass1234", role="vendedor")
        fonte = FontePedido(nome="WhatsApp")
        session.add(fonte)
        session.commit()
        token = generate_token(admin)

        resp = client.put(
            f"/api/users/{vendedor.id}/commission",
            json={"fonte_pedido_id": fonte.id, "rate": -0.05},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    # --- Logging de config ausente (Fase 3.3) ---

    def test_pedido_sem_config_loga_warning(self, session, caplog):
        """generate_commission deve logar warning quando não há CommissionConfig."""
        from app.services.commission_service import generate_commission

        vendedor = make_user(session, "audwarn@test.com", "pass1234", role="vendedor")
        fonte = FontePedido(nome="Site")
        session.add(fonte)
        session.flush()
        pedido = Pedido(
            cliente="X",
            telefone_cliente="11000000000",
            destinatario="X",
            produto="X",
            valor="R$ 100,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            status="agendado",
            status_pagamento="Pago",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido)
        session.commit()

        with caplog.at_level("WARNING"):
            generate_commission(pedido, vendedor.id)

        assert any(
            "sem CommissionConfig" in rec.message for rec in caplog.records
        )
        assert LedgerEntry.query.filter_by(pedido_id=pedido.id).count() == 0

    # --- Bug primário Site/Nuvemshop (Fase 2) ---

    def test_nuvemshop_create_pago_gera_comissao(self, session):
        """_create_pedido com status Pago + vendedor → CREDIT é gerado pelo lifecycle."""
        # Simula o que service.py::_create_pedido faz: cria pedido + chama lifecycle.
        from app.services.order_commission_lifecycle import apply_commission_lifecycle

        vendedor = make_user(session, "audns1@test.com", "pass1234", role="vendedor")
        fonte = FontePedido(nome="Site")
        session.add(fonte)
        session.flush()
        session.add(
            CommissionConfig(
                user_id=vendedor.id, fonte_pedido_id=fonte.id, source="site", rate=0.08
            )
        )
        session.commit()

        pedido = Pedido(
            cliente="Cliente Site",
            telefone_cliente="11999999999",
            destinatario="Dest",
            produto="Prod",
            valor="R$ 250,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            status="agendado",
            status_pagamento="Pago",
            fonte_pedido_id=fonte.id,
            vendedor_id=vendedor.id,
        )
        session.add(pedido)
        session.flush()
        apply_commission_lifecycle(pedido, previous=None, actor_id=vendedor.id)
        session.commit()

        credit = LedgerEntry.query.filter_by(pedido_id=pedido.id, voided=False).first()
        assert credit is not None
        assert credit.category == "comissao_site"
        assert float(credit.amount) == pytest.approx(20.0, abs=0.01)

    def test_atribuicao_tardia_de_vendedor_em_pedido_pago_gera_comissao(self, session):
        """Pedido ja pago sem vendedor deve gerar comissão quando o vendedor for atribuido depois."""
        from app.services.order_commission_lifecycle import (
            apply_commission_lifecycle,
            snapshot_commission_fields,
        )

        vendedor = make_user(session, "audlatevendor@test.com", "pass1234", role="vendedor")
        fonte = FontePedido(nome="Site")
        session.add(fonte)
        session.flush()
        session.add(
            CommissionConfig(
                user_id=vendedor.id, fonte_pedido_id=fonte.id, source="site", rate=0.08
            )
        )
        session.commit()

        pedido = Pedido(
            cliente="Cliente Pago",
            telefone_cliente="11999999999",
            destinatario="Dest",
            produto="Prod",
            valor="R$ 250,00",
            dia_entrega=date(2025, 2, 10),
            horario="10:00",
            status="agendado",
            status_pagamento="Pago",
            fonte_pedido_id=fonte.id,
            vendedor_id=None,
        )
        session.add(pedido)
        session.flush()

        snapshot = snapshot_commission_fields(pedido)
        pedido.vendedor_id = vendedor.id
        result = apply_commission_lifecycle(pedido, previous=snapshot, actor_id=vendedor.id)
        session.commit()

        assert result["generated"] is True
        credit = LedgerEntry.query.filter_by(pedido_id=pedido.id, voided=False).first()
        assert credit is not None
        assert float(credit.amount) == pytest.approx(20.0, abs=0.01)
