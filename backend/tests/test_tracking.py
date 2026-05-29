# -*- coding: utf-8 -*-
"""Acompanhamento público do pedido (token assinado) + guard de auth nos GETs internos."""
import base64
from datetime import date

import app.services.track_token as tt
from app.models.pedido import Pedido

_ADMIN_AUTH = {"Authorization": f"Basic {base64.b64encode(b'admin:testpass').decode()}"}

# Campos que NUNCA podem aparecer no payload público.
_PII_PROIBIDA = (
    "id",
    "telefone_cliente",
    "cliente",
    "endereco",
    "cep",
    "bairro",
    "mensagem",
    "valor",
    "pagamento",
    "fbc",
    "fbp",
    "vendedor_id",
    "entregador_id",
    "coords_lat",
    "coords_lon",
)


def _novo_pedido(session, **overrides) -> Pedido:
    base = {
        "cliente": "João da Silva",
        "telefone_cliente": "62999990000",
        "destinatario": "Maria Aparecida Souza",
        "tipo_pedido": "Entrega",
        "produto": "Buquê Premium",
        "dia_entrega": date.today(),
        "horario": "10:00 - 12:00",
        "mensagem": "Feliz aniversário, com amor.",
        "valor": "199,90",
        "endereco": "Rua das Flores, 123",
        "status": "em_producao",
    }
    base.update(overrides)
    pedido = Pedido(**base)
    session.add(pedido)
    session.commit()
    return pedido


# ---------------------------------------------------------------------------
# PARTE 1 — guard de auth
# ---------------------------------------------------------------------------
def test_obter_pedido_exige_auth(client, session):
    pedido = _novo_pedido(session)

    sem_auth = client.get(f"/api/pedidos/{pedido.id}")
    assert sem_auth.status_code == 401, "GET de pedido por id não pode ser público (vaza PII)"

    com_auth = client.get(f"/api/pedidos/{pedido.id}", headers=_ADMIN_AUTH)
    assert com_auth.status_code == 200


def test_listar_pedidos_exige_auth(client):
    assert client.get("/api/pedidos").status_code == 401


# ---------------------------------------------------------------------------
# PARTE 2 — token assinado
# ---------------------------------------------------------------------------
def test_track_token_roundtrip_e_adulterado(app):
    with app.app_context():
        token = tt.make_track_token(42)
        assert tt.parse_track_token(token) == 42

        adulterado = ("X" if token[-1] != "X" else "Y") + token[1:]
        assert tt.parse_track_token(adulterado) is None
        assert tt.parse_track_token("nao-e-um-token") is None


def test_track_token_expirado(app, monkeypatch):
    with app.app_context():
        token = tt.make_track_token(7)
        # Força max_age negativo: qualquer token (mesmo recém-criado) é considerado expirado.
        monkeypatch.setattr(tt, "_max_age_seconds", lambda: -1)
        assert tt.parse_track_token(token) is None


# ---------------------------------------------------------------------------
# PARTE 3 — endpoint público
# ---------------------------------------------------------------------------
def test_track_endpoint_so_campos_publicos(client, session, app):
    pedido = _novo_pedido(session)
    with app.app_context():
        token = tt.make_track_token(pedido.id)

    # SEM header de auth — rota pública.
    res = client.get(f"/api/pedidos/track/{token}")
    assert res.status_code == 200

    data = res.get_json()["pedido"]
    # Campos públicos esperados
    assert data["status"] == "Em preparação"  # status interno em_producao
    assert data["status_key"] == "em_producao"
    assert data["produto"] == "Buquê Premium"
    assert data["destinatario"] == "Maria"  # só o 1º nome
    assert data["tipo_pedido"] == "Entrega"
    # Nenhuma PII vaza
    for campo in _PII_PROIBIDA:
        assert campo not in data, f"Campo sensível '{campo}' não pode aparecer no payload público"


def test_track_endpoint_token_invalido_404(client):
    assert client.get("/api/pedidos/track/token-invalido").status_code == 404


def test_track_endpoint_id_inexistente_404(client, app):
    with app.app_context():
        token = tt.make_track_token(999999)  # token bem-assinado, mas sem pedido
    assert client.get(f"/api/pedidos/track/{token}").status_code == 404


def test_track_endpoint_oculto_ou_deletado_404(client, session, app):
    oculto = _novo_pedido(session, oculto=True)
    deletado = _novo_pedido(session)
    deletado.soft_delete()
    session.commit()

    with app.app_context():
        token_oculto = tt.make_track_token(oculto.id)
        token_deletado = tt.make_track_token(deletado.id)

    assert client.get(f"/api/pedidos/track/{token_oculto}").status_code == 404
    assert client.get(f"/api/pedidos/track/{token_deletado}").status_code == 404


def test_criar_pedido_retorna_track_url(client):
    payload = {
        "cliente": "Cliente Teste",
        "telefone_cliente": "(62) 99999-0000",
        "destinatario": "Destinatário Final",
        "tipo_pedido": "Entrega",
        "produto": "Buquê",
        "dia_entrega": date.today().isoformat(),
        "horario": "10:00",
    }
    res = client.post("/api/pedidos", json=payload, headers=_ADMIN_AUTH)
    assert res.status_code == 201
    body = res.get_json()
    assert "track_url" in body
    assert "/acompanhar/" in body["track_url"]
