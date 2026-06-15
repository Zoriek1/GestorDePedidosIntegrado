# -*- coding: utf-8 -*-
import base64
from datetime import date

from app.models.cliente import Cliente
from app.models.lead import Lead
from app.models.pedido import Pedido

_ADMIN_AUTH = {"Authorization": f"Basic {base64.b64encode(b'admin:testpass').decode()}"}
_VALID_TOKEN = "A3F9B7K20K"
_SECOND_VALID_TOKEN = "B7K2L9M1S0"


def test_criar_pedido_vincula_lead_por_codigo_whatsapp(client, session):
    lead = Lead(
        dedup_key="lead-token-create",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        fbclid="IwARcreate123",
        fbp="fb.1.1711111111111.555666777888",
    )
    session.add(lead)
    session.commit()

    payload = {
        "cliente": "Cliente Teste",
        "telefone_cliente": "(62) 99999-0000",
        "destinatario": "Destinatário",
        "tipo_pedido": "Entrega",
        "produto": "Buquê Premium",
        "dia_entrega": date.today().isoformat(),
        "horario": "10:00",
        "codigo_whatsapp": _VALID_TOKEN.lower(),
    }

    r = client.post("/api/pedidos", json=payload, headers=_ADMIN_AUTH)
    assert r.status_code == 201

    session.refresh(lead)
    assert lead.phone == "62999990000"
    assert lead.status == "compra_realizada"


def test_atualizar_pedido_vincula_lead_por_codigo_whatsapp(client, session):
    lead = Lead(
        dedup_key="lead-token-update",
        token_rastreio=_SECOND_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
    )
    pedido = Pedido(
        cliente="Cliente Update",
        telefone_cliente="61988887777",
        destinatario="Destinatário",
        tipo_pedido="Entrega",
        produto="Arranjo",
        dia_entrega=date.today(),
        horario="11:00",
        status="agendado",
        status_pagamento="Pendente",
    )
    session.add_all([lead, pedido])
    session.commit()

    r = client.put(
        f"/api/pedidos/{pedido.id}",
        json={"codigo_whatsapp": _SECOND_VALID_TOKEN.lower()},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200

    session.refresh(lead)
    assert lead.phone == "61988887777"
    assert lead.status == "compra_realizada"


def test_pedido_fecha_lead_confirmado_independente_da_situacao(client, session):
    """Pedido sobrescreve para compra_realizada mesmo num lead confirmado com situação."""
    lead = Lead(
        dedup_key="lead-token-situacao",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="whatsapp_iniciado",
        situacao="orcamento_enviado",
        phone="62999990000",
    )
    session.add(lead)
    session.commit()

    payload = {
        "cliente": "Cliente Funil",
        "telefone_cliente": "(62) 99999-0000",
        "destinatario": "Destinatário",
        "tipo_pedido": "Entrega",
        "produto": "Buquê Premium",
        "dia_entrega": date.today().isoformat(),
        "horario": "10:00",
        "codigo_whatsapp": _VALID_TOKEN.lower(),
    }

    r = client.post("/api/pedidos", json=payload, headers=_ADMIN_AUTH)
    assert r.status_code == 201

    session.refresh(lead)
    assert lead.status == "compra_realizada"
    # situacao permanece gravada mas é irrelevante (getLeadGroup ignora p/ fechados).
    assert lead.situacao == "orcamento_enviado"


def test_codigo_whatsapp_inexistente_nao_bloqueia_criacao_pedido(client, session):
    payload = {
        "cliente": "Cliente Sem Lead",
        "telefone_cliente": "(62) 98888-7777",
        "destinatario": "Destinatário",
        "tipo_pedido": "Entrega",
        "produto": "Buquê",
        "dia_entrega": date.today().isoformat(),
        "horario": "14:00",
        "codigo_whatsapp": "INEXISTENTE",
    }

    r = client.post("/api/pedidos", json=payload, headers=_ADMIN_AUTH)
    assert r.status_code == 201
    assert session.query(Lead).count() == 0


def test_criar_pedido_aceita_cliente_id_numerico(client, session):
    cliente = Cliente(nome="Cliente ID", telefone="62999991111")
    session.add(cliente)
    session.commit()

    payload = {
        "cliente": "Cliente ID",
        "cliente_id": cliente.id,
        "telefone_cliente": "(62) 99999-1111",
        "destinatario": "Destinatário",
        "tipo_pedido": "Entrega",
        "produto": "Buquê",
        "dia_entrega": date.today().isoformat(),
        "horario": "15:00",
    }

    r = client.post("/api/pedidos", json=payload, headers=_ADMIN_AUTH)
    assert r.status_code == 201
    data = r.get_json()
    assert data["success"] is True
    assert data["pedido"]["cliente_id"] == cliente.id
