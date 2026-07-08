# -*- coding: utf-8 -*-
"""
Testes do endpoint GET /api/ledger/commissions — comissões agregadas por vendedor.
"""
from datetime import date

from app.models.ledger_entry import LedgerEntry
from app.models.pedido import Pedido
from app.models.user import User
from app.services.auth_service import generate_token, hash_password


def make_user(session, email, role="vendedor", name=None):
    # Nome único por padrão (respeita o índice único users.name).
    user = User(
        name=name or f"U {email}",
        email=email,
        password_hash=hash_password("pass1234"),
        role=role,
        is_active=True,
    )
    session.add(user)
    session.commit()
    return user


def make_pedido(session, dia_entrega, cliente="Cliente"):
    p = Pedido(
        cliente=cliente,
        telefone_cliente="11999999999",
        destinatario="Maria",
        tipo_pedido="Entrega",
        produto="Buquê",
        valor="R$ 100,00",
        dia_entrega=dia_entrega,
        horario="10:00",
        status="agendado",
        status_pagamento="Pago",
    )
    session.add(p)
    session.flush()
    return p


def make_commission(
    session,
    user_id,
    amount,
    week_ref,
    *,
    category="comissao_whatsapp",
    status="active",
    pedido_id=None,
    due_date=None,
    source="whatsapp",
):
    e = LedgerEntry(
        user_id=user_id,
        type="CREDIT",
        category=category,
        amount=amount,
        week_ref=week_ref,
        due_date=due_date,
        status=status,
        pedido_id=pedido_id,
        commission_source=source,
        created_by=user_id,
    )
    session.add(e)
    session.commit()
    return e


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Acesso
# ---------------------------------------------------------------------------
def test_commissions_sem_token_retorna_401(client):
    assert client.get("/api/ledger/commissions").status_code == 401


def test_commissions_vendedor_retorna_403(client, session):
    v = make_user(session, "v@test.com", role="vendedor")
    resp = client.get("/api/ledger/commissions", headers=auth(generate_token(v)))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Agregação por vendedor (base = competência / week_ref)
# ---------------------------------------------------------------------------
def test_agrega_por_vendedor_no_periodo(client, session):
    admin = make_user(session, "admin@test.com", role="admin")
    va = make_user(session, "va@test.com", role="vendedor", name="Vendedora A")
    vb = make_user(session, "vb@test.com", role="vendedor", name="Vendedora B")

    wk = date(2026, 5, 4)  # segunda dentro do período
    fora = date(2026, 4, 6)  # fora do período

    make_commission(session, va.id, 30, wk, category="comissao_whatsapp", status="active", source="whatsapp")
    make_commission(session, va.id, 20, wk, category="comissao_whatsapp", status="settled", source="whatsapp")
    make_commission(session, va.id, 50, wk, category="comissao_site", status="active", source="site")
    make_commission(session, vb.id, 10, wk, category="comissao_whatsapp", status="active", source="whatsapp")
    make_commission(session, va.id, 999, fora, category="comissao_whatsapp", status="active", source="whatsapp")

    resp = client.get(
        "/api/ledger/commissions?date_basis=competencia&from=2026-05-01&to=2026-05-31&detail=true",
        headers=auth(generate_token(admin)),
    )
    assert resp.status_code == 200
    data = resp.get_json()

    # Totais globais (exclui o 999 fora do período)
    assert data["totals"]["total_commission"] == 110.0
    assert data["totals"]["orders_count"] == 4
    assert data["totals"]["vendedores_count"] == 2

    # Ordenado por total desc → A (100) antes de B (10)
    vendedores = data["vendedores"]
    assert [v["user_id"] for v in vendedores] == [va.id, vb.id]

    a = vendedores[0]
    assert a["total_commission"] == 100.0
    assert a["paid_commission"] == 20.0
    assert a["pending_commission"] == 80.0
    assert a["orders_count"] == 3
    assert len(a["items"]) == 3  # detail=true

    # by_source: whatsapp 50 (30+20) e site 50, cada um
    by_source = {s["source"]: s["total"] for s in a["by_source"]}
    assert by_source == {"whatsapp": 50.0, "site": 50.0}


def test_filtra_por_user_id(client, session):
    admin = make_user(session, "admin2@test.com", role="admin")
    va = make_user(session, "va2@test.com", role="vendedor")
    vb = make_user(session, "vb2@test.com", role="vendedor")
    wk = date(2026, 5, 4)
    make_commission(session, va.id, 30, wk)
    make_commission(session, vb.id, 10, wk)

    resp = client.get(
        f"/api/ledger/commissions?date_basis=competencia&user_id={vb.id}",
        headers=auth(generate_token(admin)),
    )
    assert resp.status_code == 200
    vendedores = resp.get_json()["vendedores"]
    assert len(vendedores) == 1
    assert vendedores[0]["user_id"] == vb.id
    assert vendedores[0]["total_commission"] == 10.0


# ---------------------------------------------------------------------------
# Base = data de entrega do pedido
# ---------------------------------------------------------------------------
def test_base_data_entrega(client, session):
    admin = make_user(session, "admin3@test.com", role="admin")
    va = make_user(session, "va3@test.com", role="vendedor")

    p_maio = make_pedido(session, date(2026, 5, 11))
    p_junho = make_pedido(session, date(2026, 6, 20))
    session.commit()

    wk = date(2026, 5, 4)
    make_commission(session, va.id, 40, wk, pedido_id=p_maio.id)
    make_commission(session, va.id, 77, wk, pedido_id=p_junho.id)

    resp = client.get(
        "/api/ledger/commissions?date_basis=entrega&from=2026-05-01&to=2026-05-31",
        headers=auth(generate_token(admin)),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    # Só o pedido entregue em maio conta.
    assert data["totals"]["total_commission"] == 40.0
    assert data["totals"]["orders_count"] == 1
