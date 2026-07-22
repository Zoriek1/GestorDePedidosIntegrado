# -*- coding: utf-8 -*-
"""Isolamento entre tenants com DUAS lojas ativas.

Estes testes existem porque as lacunas que eles cobrem só aparecem a partir do
segundo cliente — com uma loja só, tudo passa mesmo quebrado:

- nome de usuário era único GLOBALMENTE: a segunda loja não conseguia cadastrar
  uma "Maria" (índice `ux_users_name_active_ci`);
- o login buscava o usuário sem filtrar loja, então e-mails iguais em lojas
  diferentes entrariam na conta errada em silêncio.
"""

from app.models.store import Store
from app.models.store_setting import StoreSetting
from app.models.user import User
from app.services.auth_service import hash_password


def _store(
    session, *, slug: str, domain: str, name: str = "Loja", leads_enabled: bool = False
) -> Store:
    store = Store(
        name=name,
        slug=slug,
        email_domain=domain,
        active=True,
        leads_enabled=leads_enabled,
    )
    session.add(store)
    session.commit()
    return store


def _user(session, store: Store, *, name: str, email: str, role: str = "admin") -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password("senha-forte-123"),
        role=role,
        is_active=True,
        store_ref_id=store.id,
    )
    session.add(user)
    session.commit()
    return user


def _login(client, email: str, password: str = "senha-forte-123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_mesmo_nome_de_usuario_em_lojas_diferentes(client, session):
    """Duas lojas podem ter uma 'Maria' ativa cada uma.

    O conftest usa `db.create_all()` puro, que não passa por `init_database` e
    portanto não cria o índice. Chamamos o criador explicitamente para o teste
    exercitar o DDL de verdade — sem isso ele passaria mesmo com o índice global
    antigo, que é exatamente a regressão a proteger.
    """
    from app.extensions import _ensure_user_name_unique_index

    loja_a = _store(session, slug="loja-a", domain="lojaa.com", name="Loja A")
    loja_b = _store(session, slug="loja-b", domain="lojab.com", name="Loja B")

    _ensure_user_name_unique_index()

    from sqlalchemy import inspect

    indexes = {ix["name"] for ix in inspect(session.get_bind()).get_indexes("users")}
    assert "ux_users_store_name_active_ci" in indexes, "índice por loja não foi criado"

    _user(session, loja_a, name="Maria", email="maria@lojaa.com")
    _user(session, loja_b, name="Maria", email="maria@lojab.com")

    marias = User.query.filter_by(name="Maria", is_active=True).all()
    assert len(marias) == 2
    assert {u.store_ref_id for u in marias} == {loja_a.id, loja_b.id}


def test_nome_duplicado_na_mesma_loja_continua_bloqueado(client, session):
    """O escopo virou por loja, mas dentro da loja a unicidade permanece."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    from app.extensions import _ensure_user_name_unique_index

    loja = _store(session, slug="loja-a", domain="lojaa.com", name="Loja A")
    _ensure_user_name_unique_index()

    _user(session, loja, name="Maria", email="maria@lojaa.com")

    with pytest.raises(IntegrityError):
        _user(session, loja, name="maria", email="maria2@lojaa.com")
    session.rollback()


def test_login_resolve_a_loja_pelo_dominio_do_email(client, session):
    """O domínio decide o tenant; o JWT precisa sair com a loja certa."""
    loja_a = _store(session, slug="loja-a", domain="lojaa.com", name="Loja A")
    loja_b = _store(session, slug="loja-b", domain="lojab.com", name="Loja B")
    _user(session, loja_a, name="Maria", email="maria@lojaa.com")
    _user(session, loja_b, name="Maria", email="maria@lojab.com")

    resp_a = _login(client, "maria@lojaa.com")
    resp_b = _login(client, "maria@lojab.com")

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.get_json()["user"]["store_slug"] == loja_a.slug
    assert resp_b.get_json()["user"]["store_slug"] == loja_b.slug


def test_login_em_loja_inativa_e_bloqueado(client, session):
    loja = _store(session, slug="loja-a", domain="lojaa.com", name="Loja A")
    _user(session, loja, name="Maria", email="maria@lojaa.com")
    loja.active = False
    session.commit()

    response = _login(client, "maria@lojaa.com")

    assert response.status_code == 403


def test_login_por_nome_ambiguo_entre_lojas_recusa(client, session):
    """Sem domínio não dá para saber a loja — pedir o e-mail, nunca adivinhar."""
    loja_a = _store(session, slug="loja-a", domain="lojaa.com", name="Loja A")
    loja_b = _store(session, slug="loja-b", domain="lojab.com", name="Loja B")
    _user(session, loja_a, name="Maria", email="maria@lojaa.com")
    _user(session, loja_b, name="Maria", email="maria@lojab.com")

    response = _login(client, "Maria")

    assert response.status_code == 401
    assert "e-mail" in response.get_json()["error"].lower()


def test_config_de_uma_loja_nunca_devolve_dado_da_outra(client, session):
    """GET /api/config/integrations é escopado pelo tenant do JWT."""
    loja_a = _store(session, slug="loja-a", domain="lojaa.com", name="Loja A")
    loja_b = _store(session, slug="loja-b", domain="lojab.com", name="Loja B")
    _user(session, loja_a, name="Admin A", email="admin@lojaa.com")
    _user(session, loja_b, name="Admin B", email="admin@lojab.com")

    settings_b = StoreSetting(store_ref_id=loja_b.id)
    settings_b.meta_pixel_id = "pixel-da-loja-b"
    session.add(settings_b)
    session.commit()

    token_a = _login(client, "admin@lojaa.com").get_json()["access_token"]
    response = client.get(
        "/api/config/integrations", headers={"Authorization": f"Bearer {token_a}"}
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["config"]["store"]["slug"] == loja_a.slug
    assert body["config"]["meta_pixel_id"] != "pixel-da-loja-b"
    assert "pixel-da-loja-b" not in response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Módulo de Leads restrito por loja
# ---------------------------------------------------------------------------
# Leads é opt-in (`stores.leads_enabled`) porque a captação pública resolve
# sempre a loja default: liberar o módulo a um segundo tenant misturaria dados.


def test_loja_com_leads_habilitado_acessa_o_modulo(client, session):
    loja = _store(session, slug="loja-a", domain="lojaa.com", leads_enabled=True)
    _user(session, loja, name="Admin A", email="admin@lojaa.com")

    token = _login(client, "admin@lojaa.com").get_json()["access_token"]
    response = client.get("/api/leads", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_loja_sem_leads_habilitado_recebe_403(client, session):
    loja = _store(session, slug="loja-b", domain="lojab.com", leads_enabled=False)
    _user(session, loja, name="Admin B", email="admin@lojab.com")

    token = _login(client, "admin@lojab.com").get_json()["access_token"]
    response = client.get("/api/leads", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert "Leads" in response.get_json()["error"]


def test_login_expoe_leads_enabled_para_a_navegacao(client, session):
    """O frontend esconde o menu com base nesta flag."""
    loja_a = _store(session, slug="loja-a", domain="lojaa.com", leads_enabled=True)
    loja_b = _store(session, slug="loja-b", domain="lojab.com", leads_enabled=False)
    _user(session, loja_a, name="Admin A", email="admin@lojaa.com")
    _user(session, loja_b, name="Admin B", email="admin@lojab.com")

    assert _login(client, "admin@lojaa.com").get_json()["user"]["leads_enabled"] is True
    assert _login(client, "admin@lojab.com").get_json()["user"]["leads_enabled"] is False


def test_captacao_publica_de_lead_nao_e_bloqueada(client, session):
    """A landing page da loja 1 não pode morrer junto com o guard.

    O POST público não tem sessão nem tenant resolvido — se o guard não isentasse
    esses endpoints, toda a captação pararia.
    """
    _store(session, slug="default", domain="lojaa.com", leads_enabled=True)

    response = client.post(
        "/api/leads",
        json={"event": "whatsapp_click", "utm_source": "google"},
    )

    assert response.status_code != 403
