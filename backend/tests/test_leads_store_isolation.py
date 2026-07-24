"""Módulo de Leads restrito à loja 1 — verificação de isolamento por loja.

O módulo de Leads é opt-in por loja (`stores.leads_enabled`). A captação pública
ainda resolve sempre a loja default (`resolve_public_store_id`), então liberar
Leads para um segundo tenant misturaria dados. Enquanto o mapeamento dominio→loja
não existir, somente a loja 1 opera Leads.

Testes:
- Admin da loja 1 (leads_enabled=True) acessa GET /api/leads → 200
- Admin da loja 2 (leads_enabled=False) acessa GET /api/leads → 403
- POST /api/leads público (sem auth) continua funcionando
- POST /api/leads/whatsapp-start público continua funcionando
"""

from app.models.store import Store
from app.models.user import User
from app.services.auth_service import generate_token, hash_password


def _store(session, slug: str, leads_enabled: bool = False) -> Store:
    store = Store(name=slug, slug=slug, active=True, leads_enabled=leads_enabled)
    session.add(store)
    session.commit()
    return store


def _admin(session, store: Store, email: str) -> User:
    user = User(
        name=email,
        email=email,
        password_hash=hash_password("secret123"),
        role="admin",
        is_active=True,
        store_ref_id=store.id,
    )
    session.add(user)
    session.commit()
    return user


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /api/leads — isolamento por loja
# ---------------------------------------------------------------------------
def test_store_with_leads_enabled_can_list(client, session):
    """Loja 1 (leads_enabled=True) pode listar leads."""
    store_a = _store(session, "default", leads_enabled=True)
    _admin(session, store_a, "admin@loja1.test")

    token = generate_token(
        User.query.filter_by(email="admin@loja1.test").first(), store_a
    )
    resp = client.get("/api/leads", headers=_bearer(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert "leads" in body


def test_store_without_leads_enabled_gets_403(client, session):
    """Loja 2 (leads_enabled=False) recebe 403 ao acessar leads."""
    store_b = _store(session, "loja-b", leads_enabled=False)
    _admin(session, store_b, "admin@loja2.test")

    token = generate_token(
        User.query.filter_by(email="admin@loja2.test").first(), store_b
    )
    resp = client.get("/api/leads", headers=_bearer(token))
    assert resp.status_code == 403
    body = resp.get_json()
    assert "indisponível" in body["error"].lower()


# ---------------------------------------------------------------------------
# POST /api/leads público — sempre funciona (captação da landing page)
# ---------------------------------------------------------------------------
def test_public_lead_creation_works_without_auth(client, session):
    """POST /api/leads público não requer auth — alimenta a landing page."""
    resp = client.post(
        "/api/leads",
        json={"utm_source": "facebook", "utm_medium": "cpc"},
    )
    # Pode ser 200 ou 201 — o importante é que NÃO é 403 ou 401
    assert resp.status_code in (200, 201)
    body = resp.get_json()
    assert body.get("ok") is True or body.get("success") is True


def test_public_whatsapp_start_works_without_auth(client, session):
    """POST /api/leads/whatsapp-start público não requer auth."""
    # Primeiro cria um lead para poder marcar
    resp_create = client.post(
        "/api/leads",
        json={"utm_source": "google", "event": "whatsapp_click"},
    )
    assert resp_create.status_code in (200, 201)
    lead_data = resp_create.get_json()
    token = lead_data.get("token_rastreio") or lead_data.get("lead", {}).get(
        "token_rastreio"
    )

    if token:
        resp = client.post(
            "/api/leads/whatsapp-start",
            json={"token_rastreio": token},
        )
        # Deve funcionar (200) — endpoint público
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# leads_enabled exposto no payload de login
# ---------------------------------------------------------------------------
def test_login_payload_includes_leads_enabled(client, session):
    """O payload de login inclui a flag leads_enabled."""
    store = _store(session, "default", leads_enabled=True)
    _admin(session, store, "admin@login.test")

    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@login.test", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    user = body.get("user", {})
    assert user.get("leads_enabled") is True


def test_login_payload_leads_enabled_false_when_disabled(client, session):
    """Login em loja sem leads_enabled retorna leads_enabled=false."""
    store = _store(session, "loja-b", leads_enabled=False)
    _admin(session, store, "admin2@login.test")

    resp = client.post(
        "/api/auth/login",
        json={"email": "admin2@login.test", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    user = body.get("user", {})
    assert user.get("leads_enabled") is False
