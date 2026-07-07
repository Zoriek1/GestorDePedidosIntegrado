# -*- coding: utf-8 -*-
"""Testes de recebiveis com lote misto (fixo + comissao)."""
import os
from datetime import date, timedelta

import pytest

os.environ.setdefault("BCRYPT_LOG_ROUNDS", "4")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-recebiveis")

from app.models.ledger_entry import LedgerEntry
from app.models.pedido import Pedido
from app.models.user import User
from app.services.auth_service import generate_token, hash_password
from app.utils.date_utils import get_monday


def make_user(session, email, password="pass1234", role="vendedor", name=None):
    # Nome único por padrão (derivado do email) — respeita o índice único users.name.
    user = User(name=name or f"Teste {email}", email=email, password_hash=hash_password(password), role=role)
    session.add(user)
    session.commit()
    return user


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_pending_mistura_fixos_e_comissoes_na_mesma_competencia(client, session, monkeypatch):
    """GET /api/ledger/pending deve listar CREDIT fixo + comissao na mesma competencia."""
    from app.repositories import ledger_repository

    fixed_today = date(2025, 2, 12)
    monkeypatch.setattr(ledger_repository, "today_brazil", lambda: fixed_today)

    admin = make_user(session, "adminmixpd@test.com", "pass1234", role="admin", name="AdminMixPd")
    vendedor = make_user(session, "vendmixpd@test.com", "pass1234", role="vendedor")
    token = generate_token(vendedor)

    pedido = Pedido(
        cliente="Cliente Mix",
        telefone_cliente="11999999999",
        destinatario="Dest Mix",
        produto="Buque",
        valor="R$ 200,00",
        dia_entrega=fixed_today,
        horario="10:00",
        status="agendado",
        status_pagamento="Pago",
        vendedor_id=vendedor.id,
    )
    session.add(pedido)
    session.flush()

    due = fixed_today + timedelta(days=8)
    session.add_all([
        LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="comissao_site",
            amount=70.0,
            week_ref=get_monday(due),
            due_date=due,
            status="active",
            created_by=admin.id,
            pedido_id=pedido.id,
        ),
        LedgerEntry(
            user_id=vendedor.id,
            type="CREDIT",
            category="fixo_semanal",
            amount=30.0,
            description="Salario semanal",
            week_ref=get_monday(due),
            due_date=due,
            status="active",
            created_by=admin.id,
        ),
    ])
    session.commit()

    iso = due.isocalendar()
    competencia = f"{iso.year}-W{iso.week:02d}"
    resp = client.get(
        f"/api/ledger/pending?competencia_tipo=semanal&competencia={competencia}&include_quitados=false",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["a_receber"]["total_pedidos"] == 2
    assert body["a_receber"]["total"] == pytest.approx(100.0, abs=0.01)

    categories = {item["category"] for item in body["a_receber"]["pedidos"]}
    assert "comissao_site" in categories
    assert "fixo_semanal" in categories
    assert any(item["pedido_id"] is None for item in body["a_receber"]["pedidos"])
    assert body["atrasado"]["total_pedidos"] == 0


def test_settle_por_entry_ids_quita_mix_fixo_e_comissao(client, session):
    """POST /api/ledger/settle deve quitar lote misto por entry_ids (fixo + comissao)."""
    admin = make_user(session, "settlemixadm@test.com", "pass1234", role="admin")
    vendedor = make_user(session, "settlemixvend@test.com", "pass1234", role="vendedor")
    token = generate_token(admin)

    pedido = Pedido(
        cliente="Cliente Mix Settle",
        telefone_cliente="11999999999",
        destinatario="Dest Mix",
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

    entry_comissao = LedgerEntry(
        user_id=vendedor.id,
        type="CREDIT",
        category="comissao_site",
        amount=80.0,
        week_ref=date(2025, 2, 10),
        status="active",
        created_by=admin.id,
        pedido_id=pedido.id,
    )
    entry_fixo = LedgerEntry(
        user_id=vendedor.id,
        type="CREDIT",
        category="fixo_semanal",
        amount=20.0,
        week_ref=date(2025, 2, 10),
        status="active",
        created_by=admin.id,
        description="Salario semanal",
    )
    session.add_all([entry_comissao, entry_fixo])
    session.commit()

    resp = client.post(
        "/api/ledger/settle",
        headers=auth_headers(token),
        json={
            "user_id": vendedor.id,
            "entry_ids": [entry_comissao.id, entry_fixo.id],
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()

    assert body["settled"] == 2
    assert body["amount"] == pytest.approx(100.0, abs=0.01)
    assert sorted(body["entry_ids_settled"]) == sorted([entry_comissao.id, entry_fixo.id])
    assert body["entry_ids_ignored"] == []
    assert body["pedido_ids_settled"] == [pedido.id]

    debits = LedgerEntry.query.filter_by(user_id=vendedor.id, type="DEBIT").all()
    assert len(debits) == 1
    assert float(debits[0].amount) == pytest.approx(100.0, abs=0.01)

    refreshed_comissao = LedgerEntry.query.get(entry_comissao.id)
    refreshed_fixo = LedgerEntry.query.get(entry_fixo.id)
    assert refreshed_comissao.status == "settled"
    assert refreshed_fixo.status == "settled"
    assert refreshed_comissao.settled_by_id == debits[0].id
    assert refreshed_fixo.settled_by_id == debits[0].id
