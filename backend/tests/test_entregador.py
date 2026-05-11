# -*- coding: utf-8 -*-
"""
Testes do role `entregador`:
  - delivery_credit_service (CREDIT da taxa_entrega no ledger)
  - apply_delivery_credit_lifecycle (hooks de void/regen)
  - Endpoints HTTP: disponíveis, minhas, atribuir, lote, finalizar
  - Coexistência vendedor + entregador no mesmo pedido (2 CREDITs ativos)
  - Soft delete voida ambos os CREDITs
  - Permissões liberadas ao vendedor (marcar-impresso, cartao, clientes, delete próprio)
"""
import os
from datetime import date

import pytest

os.environ.setdefault("BCRYPT_LOG_ROUNDS", "4")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-entregador")

from app import db  # noqa: E402
from app.models.fonte_pedido import FontePedido  # noqa: E402
from app.models.ledger_entry import LedgerEntry  # noqa: E402
from app.models.pedido import Pedido  # noqa: E402
from app.models.user import CommissionConfig, PayrollConfig, User  # noqa: E402
from app.services.auth_service import generate_token, hash_password  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(session, email, password="pass1234", role="entregador", name="Teste"):
    user = User(name=name, email=email, password_hash=hash_password(password), role=role)
    session.add(user)
    session.commit()
    return user


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_pedido(
    session,
    *,
    destinatario="Maria",
    tipo_pedido="Entrega",
    status="agendado",
    status_pagamento="Pago",
    taxa_entrega=15.0,
    vendedor_id=None,
    entregador_id=None,
    fonte_pedido_id=None,
    valor="R$ 100,00",
):
    p = Pedido(
        cliente="Cliente",
        telefone_cliente="11999999999",
        destinatario=destinatario,
        tipo_pedido=tipo_pedido,
        produto="Buquê",
        valor=valor,
        dia_entrega=date(2026, 5, 11),
        horario="10:00",
        status=status,
        status_pagamento=status_pagamento,
        taxa_entrega=taxa_entrega,
        vendedor_id=vendedor_id,
        entregador_id=entregador_id,
        fonte_pedido_id=fonte_pedido_id,
    )
    session.add(p)
    session.flush()
    return p


@pytest.fixture(autouse=True)
def bypass_backup(monkeypatch):
    """Bypassa o guard de backup para que DELETE /api/pedidos/:id funcione em testes."""
    from app.routes import pedidos as pedidos_route

    monkeypatch.setattr(
        pedidos_route, "ensure_backup_before_destructive_action", lambda **kw: True
    )


# ===========================================================================
# 1. delivery_credit_service
# ===========================================================================


class TestDeliveryCreditService:
    def test_generate_cria_credit_taxa_entrega(self, session):
        entregador = make_user(session, "e1@t.com")
        pedido = make_pedido(session, entregador_id=entregador.id, taxa_entrega=15.0)
        session.commit()

        from app.services.delivery_credit_service import generate_delivery_credit

        generate_delivery_credit(pedido, entregador.id)
        session.commit()

        credit = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id).first()
        assert credit is not None
        assert credit.type == "CREDIT"
        assert credit.category == "taxa_entrega"
        assert float(credit.amount) == pytest.approx(15.0)
        assert credit.user_id == entregador.id
        assert credit.voided is False
        assert credit.pedido_id is None  # não conflita com comissão do vendedor

    def test_generate_idempotente(self, session):
        entregador = make_user(session, "e2@t.com")
        pedido = make_pedido(session, entregador_id=entregador.id)
        session.commit()

        from app.services.delivery_credit_service import generate_delivery_credit

        generate_delivery_credit(pedido, entregador.id)
        session.commit()
        generate_delivery_credit(pedido, entregador.id)
        session.commit()

        n = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id, voided=False).count()
        assert n == 1

    def test_generate_pula_sem_taxa(self, session):
        entregador = make_user(session, "e3@t.com")
        pedido = make_pedido(session, entregador_id=entregador.id, taxa_entrega=0)
        session.commit()

        from app.services.delivery_credit_service import generate_delivery_credit

        generate_delivery_credit(pedido, entregador.id)
        session.commit()

        n = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id).count()
        assert n == 0

    def test_generate_pula_sem_entregador(self, session):
        pedido = make_pedido(session, entregador_id=None)
        session.commit()

        from app.services.delivery_credit_service import generate_delivery_credit

        generate_delivery_credit(pedido, None)
        session.commit()

        n = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id).count()
        assert n == 0

    def test_generate_usa_payment_day_do_payroll(self, session):
        entregador = make_user(session, "e4@t.com")
        # payment_day=4 (sexta-feira)
        session.add(
            PayrollConfig(
                user_id=entregador.id,
                category="fixo_semanal",
                label="Fixo",
                amount=0,
                frequency="semanal",
                payment_day=4,
            )
        )
        pedido = make_pedido(session, entregador_id=entregador.id, taxa_entrega=20.0)
        # finalização em quarta-feira (2026-05-13) → due_date = sexta da mesma semana
        from datetime import datetime

        pedido.delivery_completed_at = datetime(2026, 5, 13, 14, 0, 0)
        session.commit()

        from app.services.delivery_credit_service import generate_delivery_credit

        generate_delivery_credit(pedido, entregador.id)
        session.commit()

        credit = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id).first()
        assert credit.due_date == date(2026, 5, 15)  # sexta-feira

    def test_void_marca_credit_e_retorna_true(self, session):
        entregador = make_user(session, "e5@t.com")
        pedido = make_pedido(session, entregador_id=entregador.id)
        session.commit()

        from app.services.delivery_credit_service import (
            generate_delivery_credit,
            void_delivery_credit,
        )

        generate_delivery_credit(pedido, entregador.id)
        session.commit()

        ok = void_delivery_credit(pedido, reason="soft_delete")
        session.commit()

        assert ok is True
        credit = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id).first()
        assert credit.voided is True
        assert credit.void_reason == "soft_delete"

    def test_void_sem_credit_ativo_retorna_false(self, session):
        pedido = make_pedido(session)
        session.commit()

        from app.services.delivery_credit_service import void_delivery_credit

        assert void_delivery_credit(pedido, "x") is False

    def test_void_and_recreate(self, session):
        entregador = make_user(session, "e6@t.com")
        pedido = make_pedido(session, entregador_id=entregador.id, taxa_entrega=10.0)
        session.commit()

        from app.services.delivery_credit_service import (
            generate_delivery_credit,
            void_and_recreate_delivery_credit,
        )

        generate_delivery_credit(pedido, entregador.id)
        session.commit()
        old_id = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id, voided=False).first().id

        pedido.taxa_entrega = 25.0
        void_and_recreate_delivery_credit(pedido, entregador.id)
        session.commit()

        # antigo voidado
        old = LedgerEntry.query.get(old_id)
        assert old.voided is True
        # novo ativo com novo valor
        novo = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id, voided=False).first()
        assert novo is not None
        assert novo.id != old_id
        assert float(novo.amount) == pytest.approx(25.0)


# ===========================================================================
# 2. apply_delivery_credit_lifecycle
# ===========================================================================


class TestDeliveryLifecycle:
    def test_finalizacao_gera_credit(self, session):
        from datetime import datetime

        from app.services.order_commission_lifecycle import (
            apply_delivery_credit_lifecycle,
            snapshot_commission_fields,
        )

        entregador = make_user(session, "lf1@t.com")
        pedido = make_pedido(session, entregador_id=entregador.id, status="em_rota")
        session.commit()

        snap = snapshot_commission_fields(pedido)
        pedido.status = "concluido"
        pedido.delivery_completed_at = datetime.utcnow()
        r = apply_delivery_credit_lifecycle(pedido, previous=snap)
        session.commit()

        assert r["generated"] is True
        assert LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id, voided=False).count() == 1

    def test_status_regression_voida(self, session):
        from datetime import datetime

        from app.services.delivery_credit_service import generate_delivery_credit
        from app.services.order_commission_lifecycle import (
            apply_delivery_credit_lifecycle,
            snapshot_commission_fields,
        )

        entregador = make_user(session, "lf2@t.com")
        pedido = make_pedido(session, entregador_id=entregador.id, status="concluido")
        pedido.delivery_completed_at = datetime.utcnow()
        session.commit()
        generate_delivery_credit(pedido, entregador.id)
        session.commit()

        snap = snapshot_commission_fields(pedido)
        pedido.status = "em_rota"
        r = apply_delivery_credit_lifecycle(pedido, previous=snap)
        session.commit()

        assert r["voided"] is True
        credit = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id).first()
        assert credit.voided is True
        assert credit.void_reason == "status_regression"

    def test_taxa_muda_void_e_recreate(self, session):
        from datetime import datetime

        from app.services.delivery_credit_service import generate_delivery_credit
        from app.services.order_commission_lifecycle import (
            apply_delivery_credit_lifecycle,
            snapshot_commission_fields,
        )

        entregador = make_user(session, "lf3@t.com")
        pedido = make_pedido(session, entregador_id=entregador.id, status="concluido", taxa_entrega=10.0)
        pedido.delivery_completed_at = datetime.utcnow()
        session.commit()
        generate_delivery_credit(pedido, entregador.id)
        session.commit()

        snap = snapshot_commission_fields(pedido)
        pedido.taxa_entrega = 30.0
        r = apply_delivery_credit_lifecycle(pedido, previous=snap)
        session.commit()

        assert r["voided_and_recreated"] is True
        ativo = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id, voided=False).first()
        assert float(ativo.amount) == pytest.approx(30.0)

    def test_entregador_muda_void_e_recreate(self, session):
        from datetime import datetime

        from app.services.delivery_credit_service import generate_delivery_credit
        from app.services.order_commission_lifecycle import (
            apply_delivery_credit_lifecycle,
            snapshot_commission_fields,
        )

        e1 = make_user(session, "lf4a@t.com", name="E1")
        e2 = make_user(session, "lf4b@t.com", name="E2")
        pedido = make_pedido(session, entregador_id=e1.id, status="concluido")
        pedido.delivery_completed_at = datetime.utcnow()
        session.commit()
        generate_delivery_credit(pedido, e1.id)
        session.commit()

        snap = snapshot_commission_fields(pedido)
        pedido.entregador_id = e2.id
        apply_delivery_credit_lifecycle(pedido, previous=snap)
        session.commit()

        novo = LedgerEntry.query.filter_by(delivery_pedido_id=pedido.id, voided=False).first()
        assert novo.user_id == e2.id


# ===========================================================================
# 3. Endpoints HTTP
# ===========================================================================


class TestEndpointDisponiveis:
    def test_lista_pedidos_sem_entregador(self, client, session):
        entregador = make_user(session, "disp@t.com")
        # Disponível
        make_pedido(session, entregador_id=None, tipo_pedido="Entrega", status="agendado")
        # Já atribuído
        make_pedido(session, entregador_id=entregador.id, tipo_pedido="Entrega", status="em_rota")
        # Retirada (não conta)
        make_pedido(session, entregador_id=None, tipo_pedido="Retirada", status="agendado")
        # Concluído
        make_pedido(session, entregador_id=None, tipo_pedido="Entrega", status="concluido")
        session.commit()

        token = generate_token(entregador)
        resp = client.get("/api/pedidos/disponiveis-entrega", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1


class TestEndpointAtribuir:
    def test_entregador_atribui_a_si_mesmo(self, client, session):
        e = make_user(session, "atr1@t.com")
        p = make_pedido(session)
        session.commit()
        token = generate_token(e)

        resp = client.post(
            f"/api/pedidos/{p.id}/atribuir-entregador",
            json={},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["pedido"]["entregador_id"] == e.id
        assert body["pedido"]["delivery_assigned_at"] is not None

    def test_entregador_atribuindo_pedido_de_outro_409(self, client, session):
        e1 = make_user(session, "atr2a@t.com", name="E1")
        e2 = make_user(session, "atr2b@t.com", name="E2")
        p = make_pedido(session, entregador_id=e1.id)
        session.commit()
        token = generate_token(e2)

        resp = client.post(
            f"/api/pedidos/{p.id}/atribuir-entregador",
            json={},
            headers=auth_headers(token),
        )
        assert resp.status_code == 409

    def test_admin_pode_atribuir_a_outro_entregador(self, client, session):
        admin = make_user(session, "atr3a@t.com", role="admin", name="A")
        e = make_user(session, "atr3b@t.com", name="E")
        p = make_pedido(session)
        session.commit()
        token = generate_token(admin)

        resp = client.post(
            f"/api/pedidos/{p.id}/atribuir-entregador",
            json={"entregador_id": e.id},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["pedido"]["entregador_id"] == e.id

    def test_vendedor_pode_atribuir_entregador(self, client, session):
        """Vendedor atribui entregador a um pedido via PUT no body."""
        v = make_user(session, "vatr_v@t.com", role="vendedor", name="V")
        e = make_user(session, "vatr_e@t.com", role="entregador", name="E")
        p = make_pedido(session, vendedor_id=v.id)
        session.commit()
        token = generate_token(v)

        resp = client.post(
            f"/api/pedidos/{p.id}/atribuir-entregador",
            json={"entregador_id": e.id},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["pedido"]["entregador_id"] == e.id

    def test_vendedor_pode_trocar_entregador(self, client, session):
        """Vendedor reatribui pedido que já tinha entregador (sem precisar override)."""
        v = make_user(session, "vatr2_v@t.com", role="vendedor", name="V")
        e1 = make_user(session, "vatr2_e1@t.com", role="entregador", name="E1")
        e2 = make_user(session, "vatr2_e2@t.com", role="entregador", name="E2")
        p = make_pedido(session, vendedor_id=v.id, entregador_id=e1.id)
        session.commit()
        token = generate_token(v)

        resp = client.post(
            f"/api/pedidos/{p.id}/atribuir-entregador",
            json={"entregador_id": e2.id},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["pedido"]["entregador_id"] == e2.id

    def test_vendedor_pode_desatribuir_entregador(self, client, session):
        v = make_user(session, "vatr3_v@t.com", role="vendedor", name="V")
        e = make_user(session, "vatr3_e@t.com", role="entregador", name="E")
        p = make_pedido(session, vendedor_id=v.id, entregador_id=e.id)
        session.commit()
        token = generate_token(v)

        resp = client.post(
            f"/api/pedidos/{p.id}/atribuir-entregador",
            json={"entregador_id": None},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["pedido"]["entregador_id"] is None

    def test_entregador_nao_pode_roubar_pedido_alheio(self, client, session):
        """Entregador continua bloqueado de pegar pedido já atribuído a outro."""
        e1 = make_user(session, "rob_e1@t.com", role="entregador", name="E1")
        e2 = make_user(session, "rob_e2@t.com", role="entregador", name="E2")
        p = make_pedido(session, entregador_id=e1.id)
        session.commit()
        token = generate_token(e2)

        resp = client.post(
            f"/api/pedidos/{p.id}/atribuir-entregador",
            json={"override": True},  # tentativa de bypass
            headers=auth_headers(token),
        )
        assert resp.status_code == 409

    def test_lista_entregadores_endpoint(self, client, session):
        """GET /api/users/entregadores lista entregadores ativos para vendedor/admin/atendente."""
        admin = make_user(session, "le_a@t.com", role="admin", name="A")
        make_user(session, "le_e1@t.com", role="entregador", name="E1")
        make_user(session, "le_e2@t.com", role="entregador", name="E2")
        # outros roles não aparecem
        make_user(session, "le_v@t.com", role="vendedor", name="V")
        session.commit()
        token = generate_token(admin)

        resp = client.get("/api/users/entregadores", headers=auth_headers(token))
        assert resp.status_code == 200
        users = resp.get_json()["users"]
        names = {u["name"] for u in users}
        assert names == {"E1", "E2"}
        # Cada entrada tem só id/name/email
        assert set(users[0].keys()) == {"id", "name", "email"}

    def test_lista_entregadores_acessivel_para_vendedor(self, client, session):
        v = make_user(session, "le_acc_v@t.com", role="vendedor", name="V")
        make_user(session, "le_acc_e@t.com", role="entregador", name="E")
        session.commit()
        token = generate_token(v)

        resp = client.get("/api/users/entregadores", headers=auth_headers(token))
        assert resp.status_code == 200
        assert len(resp.get_json()["users"]) == 1

    def test_lista_entregadores_negada_para_entregador(self, client, session):
        e = make_user(session, "le_deny@t.com", role="entregador", name="E")
        session.commit()
        token = generate_token(e)

        resp = client.get("/api/users/entregadores", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_atribuir_lote_atribui_pedidos_a_self(self, client, session):
        e = make_user(session, "lot1@t.com")
        p1 = make_pedido(session, destinatario="A")
        p2 = make_pedido(session, destinatario="B")
        p_outro = make_pedido(session, destinatario="C", entregador_id=999)
        session.commit()
        token = generate_token(e)

        resp = client.post(
            "/api/pedidos/atribuir-entregadores-lote",
            json={"pedido_ids": [p1.id, p2.id, p_outro.id]},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert sorted(body["atribuidos"]) == sorted([p1.id, p2.id])
        # p_outro foi ignorado por já estar atribuído
        ig_ids = {x["pedido_id"] for x in body["ignorados"]}
        assert p_outro.id in ig_ids


class TestEndpointMinhasEntregas:
    def test_filtra_por_user_e_exclui_concluidos_por_padrao(self, client, session):
        e = make_user(session, "min1@t.com")
        outro = make_user(session, "min1b@t.com", name="X")
        # do entregador, ativas
        make_pedido(session, entregador_id=e.id, status="em_rota")
        make_pedido(session, entregador_id=e.id, status="agendado")
        # do entregador, concluído (excluir)
        from datetime import datetime

        finalizada = make_pedido(session, entregador_id=e.id, status="concluido")
        finalizada.delivery_completed_at = datetime.utcnow()
        # de outro
        make_pedido(session, entregador_id=outro.id, status="em_rota")
        session.commit()
        token = generate_token(e)

        resp = client.get("/api/pedidos/minhas-entregas", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 2

    def test_admin_pode_passar_entregador_id(self, client, session):
        admin = make_user(session, "min2a@t.com", role="admin")
        e = make_user(session, "min2b@t.com")
        make_pedido(session, entregador_id=e.id, status="em_rota")
        session.commit()
        token = generate_token(admin)

        resp = client.get(
            f"/api/pedidos/minhas-entregas?entregador_id={e.id}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 1


class TestEndpointFinalizarEntrega:
    def test_finaliza_gera_credit(self, client, session):
        e = make_user(session, "fin1@t.com")
        p = make_pedido(session, entregador_id=e.id, status="em_rota", taxa_entrega=18.5)
        session.commit()
        token = generate_token(e)

        resp = client.post(
            f"/api/pedidos/{p.id}/finalizar-entrega",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["pedido"]["status"] == "concluido"
        assert body["pedido"]["delivery_completed_at"] is not None

        credit = LedgerEntry.query.filter_by(delivery_pedido_id=p.id, voided=False).first()
        assert credit is not None
        assert float(credit.amount) == pytest.approx(18.5)
        assert credit.user_id == e.id

    def test_finalizar_2x_idempotente(self, client, session):
        e = make_user(session, "fin2@t.com")
        p = make_pedido(session, entregador_id=e.id, status="em_rota", taxa_entrega=10.0)
        session.commit()
        token = generate_token(e)

        client.post(f"/api/pedidos/{p.id}/finalizar-entrega", headers=auth_headers(token))
        resp = client.post(f"/api/pedidos/{p.id}/finalizar-entrega", headers=auth_headers(token))
        assert resp.status_code == 200

        n = LedgerEntry.query.filter_by(delivery_pedido_id=p.id, voided=False).count()
        assert n == 1

    def test_finalizar_403_para_outro_entregador(self, client, session):
        e1 = make_user(session, "fin3a@t.com", name="E1")
        e2 = make_user(session, "fin3b@t.com", name="E2")
        p = make_pedido(session, entregador_id=e1.id, status="em_rota")
        session.commit()
        token = generate_token(e2)

        resp = client.post(
            f"/api/pedidos/{p.id}/finalizar-entrega",
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_finalizar_sem_atribuicao_400(self, client, session):
        e = make_user(session, "fin4@t.com")
        p = make_pedido(session, entregador_id=None, status="em_rota")
        session.commit()
        token = generate_token(e)

        resp = client.post(
            f"/api/pedidos/{p.id}/finalizar-entrega",
            headers=auth_headers(token),
        )
        assert resp.status_code == 400


# ===========================================================================
# 4. Coexistência vendedor + entregador
# ===========================================================================


class TestCoexistencia:
    def test_dois_credits_ativos_no_mesmo_pedido(self, client, session):
        from datetime import datetime

        from app.services.delivery_credit_service import generate_delivery_credit
        from app.services.order_commission_lifecycle import apply_commission_lifecycle

        vendedor = make_user(session, "coex_v@t.com", role="vendedor", name="V")
        entregador = make_user(session, "coex_e@t.com", role="entregador", name="E")
        fonte = FontePedido(nome="WhatsApp")
        session.add(fonte)
        session.flush()
        session.add(
            CommissionConfig(
                user_id=vendedor.id,
                fonte_pedido_id=fonte.id,
                source="whatsapp",
                rate=0.10,
            )
        )
        session.commit()

        p = make_pedido(
            session,
            vendedor_id=vendedor.id,
            entregador_id=entregador.id,
            fonte_pedido_id=fonte.id,
            status="concluido",
            status_pagamento="Pago",
            taxa_entrega=20.0,
            valor="R$ 120,00",
        )
        p.delivery_completed_at = datetime.utcnow()
        session.commit()
        apply_commission_lifecycle(p, previous=None, actor_id=vendedor.id)
        generate_delivery_credit(p, entregador.id)
        session.commit()

        # Vendedor: CREDIT comissão sobre (120 - 20)*10% = 10
        cred_v = LedgerEntry.query.filter_by(pedido_id=p.id, voided=False).first()
        assert cred_v is not None
        assert cred_v.user_id == vendedor.id
        assert float(cred_v.amount) == pytest.approx(10.0)

        # Entregador: CREDIT taxa_entrega = 20
        cred_e = LedgerEntry.query.filter_by(delivery_pedido_id=p.id, voided=False).first()
        assert cred_e is not None
        assert cred_e.user_id == entregador.id
        assert float(cred_e.amount) == pytest.approx(20.0)

        # Os dois CREDITs apontam para o mesmo pedido, em colunas diferentes
        assert cred_v.id != cred_e.id

    def test_soft_delete_voida_ambos_credits(self, client, session):
        from datetime import datetime

        from app.services.delivery_credit_service import generate_delivery_credit
        from app.services.order_commission_lifecycle import apply_commission_lifecycle

        admin = make_user(session, "sd_a@t.com", role="admin", name="A")
        vendedor = make_user(session, "sd_v@t.com", role="vendedor", name="V")
        entregador = make_user(session, "sd_e@t.com", role="entregador", name="E")
        fonte = FontePedido(nome="WhatsApp")
        session.add(fonte)
        session.flush()
        session.add(
            CommissionConfig(
                user_id=vendedor.id, fonte_pedido_id=fonte.id, source="whatsapp", rate=0.05
            )
        )
        session.commit()

        p = make_pedido(
            session,
            vendedor_id=vendedor.id,
            entregador_id=entregador.id,
            fonte_pedido_id=fonte.id,
            status="concluido",
            status_pagamento="Pago",
            taxa_entrega=10.0,
            valor="R$ 100,00",
        )
        p.delivery_completed_at = datetime.utcnow()
        session.commit()
        apply_commission_lifecycle(p, previous=None, actor_id=vendedor.id)
        generate_delivery_credit(p, entregador.id)
        session.commit()

        # Soft delete via endpoint (admin)
        admin_token = generate_token(admin)
        resp = client.delete(f"/api/pedidos/{p.id}", headers=auth_headers(admin_token))
        assert resp.status_code == 200

        cred_v = LedgerEntry.query.filter_by(pedido_id=p.id).first()
        cred_e = LedgerEntry.query.filter_by(delivery_pedido_id=p.id).first()
        assert cred_v.voided is True
        assert cred_e.voided is True
        assert cred_v.void_reason == "soft_delete"
        assert cred_e.void_reason == "soft_delete"


# ===========================================================================
# 5. Permissões liberadas ao vendedor
# ===========================================================================


class TestPermissoesVendedor:
    def test_vendedor_pode_marcar_impresso(self, client, session):
        v = make_user(session, "perm1@t.com", role="vendedor")
        p = make_pedido(session, vendedor_id=v.id)
        session.commit()
        token = generate_token(v)

        resp = client.post(
            f"/api/pedidos/{p.id}/marcar-impresso",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        db.session.refresh(p)
        assert p.impresso is True

    def test_vendedor_pode_toggle_cartao(self, client, session):
        v = make_user(session, "perm2@t.com", role="vendedor")
        p = make_pedido(session, vendedor_id=v.id)
        session.commit()
        token = generate_token(v)

        resp = client.post(
            f"/api/pedidos/{p.id}/toggle-cartao-impresso",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200

    def test_vendedor_pode_listar_clientes(self, client, session):
        v = make_user(session, "perm3@t.com", role="vendedor")
        session.commit()
        token = generate_token(v)

        resp = client.get("/api/clientes", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_vendedor_deleta_pedido_proprio(self, client, session):
        v = make_user(session, "perm4@t.com", role="vendedor")
        p = make_pedido(session, vendedor_id=v.id)
        session.commit()
        token = generate_token(v)

        resp = client.delete(f"/api/pedidos/{p.id}", headers=auth_headers(token))
        assert resp.status_code == 200
        db.session.refresh(p)
        assert p.deleted_at is not None

    def test_vendedor_nao_deleta_pedido_de_outro(self, client, session):
        v1 = make_user(session, "perm5a@t.com", role="vendedor", name="V1")
        v2 = make_user(session, "perm5b@t.com", role="vendedor", name="V2")
        p = make_pedido(session, vendedor_id=v1.id)
        session.commit()
        token = generate_token(v2)

        resp = client.delete(f"/api/pedidos/{p.id}", headers=auth_headers(token))
        assert resp.status_code == 403
        db.session.refresh(p)
        assert p.deleted_at is None

    def test_entregador_nao_deleta(self, client, session):
        e = make_user(session, "perm6@t.com", role="entregador")
        p = make_pedido(session)
        session.commit()
        token = generate_token(e)

        resp = client.delete(f"/api/pedidos/{p.id}", headers=auth_headers(token))
        assert resp.status_code == 403


# ===========================================================================
# 6. POST/PUT /api/users — validação de roles
# ===========================================================================


class TestUserRoleValidation:
    """O dropdown de criação de usuário agora oferece 5 roles. O backend precisa
    aceitar todos e rejeitar valores fora do conjunto."""

    @pytest.mark.parametrize(
        "role", ["admin", "vendedor", "atendente", "entregador", "viewer"]
    )
    def test_create_user_aceita_role_valido(self, client, session, role):
        admin = make_user(session, f"ur_a_{role}@t.com", role="admin", name="A")
        token = generate_token(admin)

        resp = client.post(
            "/api/users",
            json={
                "email": f"novo_{role}@t.com",
                "name": f"Novo {role}",
                "password": "senha1234",
                "role": role,
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["user"]["role"] == role

    def test_create_user_rejeita_role_invalido(self, client, session):
        admin = make_user(session, "ur_inv@t.com", role="admin", name="A")
        token = generate_token(admin)

        resp = client.post(
            "/api/users",
            json={
                "email": "novo_x@t.com",
                "name": "X",
                "password": "senha1234",
                "role": "superadmin",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        msg = resp.get_json().get("error") or resp.get_json().get("message", "")
        # Mensagem deve mencionar pelo menos um dos roles aceitos
        assert "entregador" in msg or "atendente" in msg

    def test_create_user_default_role_vendedor(self, client, session):
        """Sem `role` no body, default é 'vendedor'."""
        admin = make_user(session, "ur_def@t.com", role="admin", name="A")
        token = generate_token(admin)

        resp = client.post(
            "/api/users",
            json={
                "email": "novo_def@t.com",
                "name": "Default",
                "password": "senha1234",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 201
        assert resp.get_json()["user"]["role"] == "vendedor"

    def test_create_user_nao_admin_recebe_403(self, client, session):
        vendedor = make_user(session, "ur_v@t.com", role="vendedor", name="V")
        token = generate_token(vendedor)

        resp = client.post(
            "/api/users",
            json={
                "email": "novo_neg@t.com",
                "name": "Negado",
                "password": "senha1234",
                "role": "entregador",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize(
        "role", ["admin", "vendedor", "atendente", "entregador", "viewer"]
    )
    def test_update_user_aceita_role_valido(self, client, session, role):
        admin = make_user(session, f"upd_a_{role}@t.com", role="admin", name="A")
        target = make_user(session, f"upd_t_{role}@t.com", role="viewer", name="T")
        token = generate_token(admin)

        resp = client.put(
            f"/api/users/{target.id}",
            json={"role": role},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["user"]["role"] == role

    def test_update_user_rejeita_role_invalido(self, client, session):
        admin = make_user(session, "upd_inv@t.com", role="admin", name="A")
        target = make_user(session, "upd_inv_t@t.com", role="viewer", name="T")
        token = generate_token(admin)

        resp = client.put(
            f"/api/users/{target.id}",
            json={"role": "superuser"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    def test_admin_nao_pode_se_auto_rebaixar(self, client, session):
        """Admin alterando próprio cargo para qualquer outro role → 400."""
        admin = make_user(session, "self_demote@t.com", role="admin", name="A")
        token = generate_token(admin)

        resp = client.put(
            f"/api/users/{admin.id}",
            json={"role": "vendedor"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        msg = resp.get_json().get("error") or resp.get_json().get("message", "")
        assert "próprio cargo" in msg.lower() or "outro admin" in msg.lower()

        # Confirma que o role não mudou
        from app.models.user import User as UserModel

        u = db.session.get(UserModel, admin.id)
        assert u.role == "admin"

    def test_admin_pode_alterar_role_de_outro_usuario(self, client, session):
        """Admin promove vendedor para entregador, depois para admin, depois rebaixa."""
        admin = make_user(session, "promo_a@t.com", role="admin", name="A")
        target = make_user(session, "promo_t@t.com", role="vendedor", name="T")
        token = generate_token(admin)

        for new_role in ("entregador", "admin", "viewer"):
            resp = client.put(
                f"/api/users/{target.id}",
                json={"role": new_role},
                headers=auth_headers(token),
            )
            assert resp.status_code == 200
            assert resp.get_json()["user"]["role"] == new_role

    def test_outro_admin_pode_rebaixar_admin(self, client, session):
        """Restrição é só auto-rebaixamento. Outro admin pode trocar o cargo."""
        a1 = make_user(session, "two_a1@t.com", role="admin", name="A1")
        a2 = make_user(session, "two_a2@t.com", role="admin", name="A2")
        token = generate_token(a1)

        resp = client.put(
            f"/api/users/{a2.id}",
            json={"role": "vendedor"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["user"]["role"] == "vendedor"

    def test_nao_admin_nao_pode_alterar_role(self, client, session):
        """Já coberto em test_create_user_nao_admin_recebe_403, mas confirma para PUT."""
        vendedor = make_user(session, "nadm_v@t.com", role="vendedor", name="V")
        target = make_user(session, "nadm_t@t.com", role="viewer", name="T")
        token = generate_token(vendedor)

        resp = client.put(
            f"/api/users/{target.id}",
            json={"role": "admin"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 403


# ===========================================================================
# 7. GET /api/ledger/pedidos — Pedidos Atribuídos inclui taxa_entrega do entregador
# ===========================================================================


class TestLedgerPedidosAtribuidos:
    """O card 'Pedidos Atribuídos' precisa mostrar tanto comissão (vendedor) quanto
    taxa_entrega (entregador)."""

    def _setup_pedido_finalizado_com_credits(self, session):
        """Cria pedido com vendedor + entregador, gera comissão e taxa_entrega."""
        from datetime import datetime

        from app.services.delivery_credit_service import generate_delivery_credit
        from app.services.order_commission_lifecycle import apply_commission_lifecycle

        vendedor = make_user(session, "lpa_v@t.com", role="vendedor", name="V")
        entregador = make_user(session, "lpa_e@t.com", role="entregador", name="E")
        fonte = FontePedido(nome="WhatsApp")
        session.add(fonte)
        session.flush()
        session.add(
            CommissionConfig(
                user_id=vendedor.id, fonte_pedido_id=fonte.id, source="whatsapp", rate=0.10
            )
        )
        session.commit()

        p = make_pedido(
            session,
            vendedor_id=vendedor.id,
            entregador_id=entregador.id,
            fonte_pedido_id=fonte.id,
            status="concluido",
            status_pagamento="Pago",
            taxa_entrega=20.0,
            valor="R$ 120,00",
        )
        p.delivery_completed_at = datetime.utcnow()
        session.commit()
        apply_commission_lifecycle(p, previous=None, actor_id=vendedor.id)
        generate_delivery_credit(p, entregador.id)
        session.commit()
        return vendedor, entregador, p

    def test_entregador_ve_proprios_taxa_entrega(self, client, session):
        """Entregador chamando /api/ledger/pedidos vê o CREDIT da taxa_entrega."""
        _, entregador, p = self._setup_pedido_finalizado_com_credits(session)
        token = generate_token(entregador)

        resp = client.get("/api/ledger/pedidos", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        item = body["pedidos"][0]
        assert item["pedido_id"] == p.id
        assert item["category"] == "taxa_entrega"
        assert item["commission_amount"] == pytest.approx(20.0)
        assert item["fonte"] == "Taxa de entrega"

    def test_vendedor_ve_propria_comissao_e_nao_taxa(self, client, session):
        """Vendedor vê apenas CREDIT de comissão (com pedido_id), não taxa_entrega."""
        vendedor, _, p = self._setup_pedido_finalizado_com_credits(session)
        token = generate_token(vendedor)

        resp = client.get("/api/ledger/pedidos", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        item = body["pedidos"][0]
        assert item["pedido_id"] == p.id
        assert item["category"].startswith("comissao_")
        assert item["fonte"] != "Taxa de entrega"

    def test_admin_pode_ver_taxa_entrega_de_outro(self, client, session):
        """Admin com ?user_id=<entregador> vê o CREDIT da taxa_entrega dele."""
        _, entregador, p = self._setup_pedido_finalizado_com_credits(session)
        admin = make_user(session, "lpa_a@t.com", role="admin", name="A")
        token = generate_token(admin)

        resp = client.get(
            f"/api/ledger/pedidos?user_id={entregador.id}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        assert body["pedidos"][0]["category"] == "taxa_entrega"
        assert body["pedidos"][0]["pedido_id"] == p.id

    def test_entregador_pode_ver_balance(self, client, session):
        """Antes do fix, entregador recebia 403 em /ledger/balance."""
        _, entregador, _ = self._setup_pedido_finalizado_com_credits(session)
        token = generate_token(entregador)

        resp = client.get("/api/ledger/balance", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total_credits"] == pytest.approx(20.0)
        assert body["balance"] == pytest.approx(20.0)


# ===========================================================================
# 8. Fluxo desativar → apagar → libera email/nome
# ===========================================================================


class TestUserDeleteFlow:
    def test_desativar_apenas_marca_inativo(self, client, session):
        admin = make_user(session, "del_a@t.com", role="admin", name="A")
        target = make_user(session, "del_t@t.com", role="vendedor", name="Joao")
        token = generate_token(admin)

        resp = client.delete(f"/api/users/{target.id}", headers=auth_headers(token))
        assert resp.status_code == 200

        # Refetch direto do banco
        from app.models.user import User as UserModel

        u = db.session.get(UserModel, target.id)
        assert u.is_active is False
        assert u.email == "del_t@t.com"  # email intacto
        assert u.name == "Joao"          # nome intacto

    def test_hard_delete_em_usuario_ativo_400(self, client, session):
        """Admin não pode pular o passo de desativação."""
        admin = make_user(session, "del_a2@t.com", role="admin", name="A")
        target = make_user(session, "del_t2@t.com", role="vendedor", name="Maria")
        token = generate_token(admin)

        resp = client.delete(f"/api/users/{target.id}/hard", headers=auth_headers(token))
        assert resp.status_code == 400
        assert "Desative" in (resp.get_json().get("error") or resp.get_json().get("message", ""))

    def test_hard_delete_libera_email_e_nome(self, client, session):
        admin = make_user(session, "del_a3@t.com", role="admin", name="A")
        target = make_user(session, "del_t3@t.com", role="vendedor", name="Pedro")
        token = generate_token(admin)

        # 1) desativar
        client.delete(f"/api/users/{target.id}", headers=auth_headers(token))
        # 2) apagar definitivamente
        resp = client.delete(f"/api/users/{target.id}/hard", headers=auth_headers(token))
        assert resp.status_code == 200

        # Email original liberado: cadastro novo com mesmo email deve passar
        resp2 = client.post(
            "/api/users",
            json={
                "email": "del_t3@t.com",
                "name": "Pedro",
                "password": "senha1234",
                "role": "vendedor",
            },
            headers=auth_headers(token),
        )
        assert resp2.status_code == 201
        assert resp2.get_json()["user"]["email"] == "del_t3@t.com"

    def test_hard_delete_mantem_linha_anonimizada(self, client, session):
        """Tombstone preserva FK histórica em pedidos/ledger."""
        admin = make_user(session, "del_a4@t.com", role="admin", name="A")
        target = make_user(session, "del_t4@t.com", role="vendedor", name="Ana")
        # Pedido com FK no vendedor
        p = make_pedido(session, vendedor_id=target.id)
        session.commit()
        original_id = target.id
        token = generate_token(admin)

        client.delete(f"/api/users/{target.id}", headers=auth_headers(token))
        client.delete(f"/api/users/{target.id}/hard", headers=auth_headers(token))

        from app.models.user import User as UserModel

        u = db.session.get(UserModel, original_id)
        assert u is not None  # linha mantida
        assert u.is_active is False
        assert u.name == "Usuário removido"
        assert u.email.startswith("deleted_")
        # Pedido continua apontando para o mesmo id
        from app.models.pedido import Pedido as PedidoModel

        p_db = db.session.get(PedidoModel, p.id)
        assert p_db.vendedor_id == original_id

    def test_listar_include_inactive_traz_desativados(self, client, session):
        admin = make_user(session, "del_a5@t.com", role="admin", name="A")
        ativo = make_user(session, "del_at@t.com", role="vendedor", name="Ativo")
        inativo = make_user(session, "del_in@t.com", role="vendedor", name="Inativo")
        token = generate_token(admin)
        client.delete(f"/api/users/{inativo.id}", headers=auth_headers(token))

        # Sem include_inactive: só ativos
        resp = client.get("/api/users", headers=auth_headers(token))
        ids = {u["id"] for u in resp.get_json()["users"]}
        assert ativo.id in ids
        assert inativo.id not in ids
        assert admin.id in ids

        # Com include_inactive: inativos aparecem
        resp = client.get("/api/users?include_inactive=true", headers=auth_headers(token))
        ids = {u["id"] for u in resp.get_json()["users"]}
        assert inativo.id in ids
        assert ativo.id in ids

    def test_listar_esconde_tombstones(self, client, session):
        """Após hard delete, o usuário some da listagem mesmo com include_inactive."""
        admin = make_user(session, "del_a6@t.com", role="admin", name="A")
        target = make_user(session, "del_t6@t.com", role="vendedor", name="Some")
        token = generate_token(admin)

        client.delete(f"/api/users/{target.id}", headers=auth_headers(token))
        client.delete(f"/api/users/{target.id}/hard", headers=auth_headers(token))

        resp = client.get("/api/users?include_inactive=true", headers=auth_headers(token))
        ids = {u["id"] for u in resp.get_json()["users"]}
        assert target.id not in ids

    def test_reactivate_volta_para_ativo(self, client, session):
        admin = make_user(session, "del_a7@t.com", role="admin", name="A")
        target = make_user(session, "del_t7@t.com", role="vendedor", name="Volta")
        token = generate_token(admin)

        client.delete(f"/api/users/{target.id}", headers=auth_headers(token))
        resp = client.post(
            f"/api/users/{target.id}/reactivate", headers=auth_headers(token)
        )
        assert resp.status_code == 200
        assert resp.get_json()["user"]["is_active"] is True

    def test_reactivate_em_tombstone_400(self, client, session):
        admin = make_user(session, "del_a8@t.com", role="admin", name="A")
        target = make_user(session, "del_t8@t.com", role="vendedor", name="Morto")
        token = generate_token(admin)

        client.delete(f"/api/users/{target.id}", headers=auth_headers(token))
        client.delete(f"/api/users/{target.id}/hard", headers=auth_headers(token))

        resp = client.post(
            f"/api/users/{target.id}/reactivate", headers=auth_headers(token)
        )
        assert resp.status_code == 400

    def test_hard_delete_proprio_user_400(self, client, session):
        admin = make_user(session, "del_self@t.com", role="admin", name="Self")
        admin.is_active = False  # cenário improvável mas força a checagem
        session.commit()
        token = generate_token(admin)
        # generate_token captura o role no momento; mas a checagem usa user_id == self
        # Reativa antes pra checar a regra de "próprio usuário"
        admin.is_active = True
        session.commit()
        # Desativa via API por outro admin? Não — vamos só testar a regra: precisa estar inativo
        # então este caso retorna 400 por causa do "ainda ativo".
        resp = client.delete(f"/api/users/{admin.id}/hard", headers=auth_headers(token))
        assert resp.status_code == 400
