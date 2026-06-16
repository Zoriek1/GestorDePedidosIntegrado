# -*- coding: utf-8 -*-
import base64
import json

from app.models.lead import Lead
from app.models.user import User
from app.services.auth_service import generate_token, hash_password

_ADMIN_AUTH = {"Authorization": f"Basic {base64.b64encode(b'admin:testpass').decode()}"}
_VALID_TOKEN = "A3F9B7K20K"
_SECOND_VALID_TOKEN = "B7K2L9M1S0"
_INVALID_TOKEN = "A3F9B7K2ZZ"
# Quando META_CAPI_LEAD_FUNNEL_ENABLED está ligado em prod, todo POST whatsapp_click
# precisa de meta_event_id_contact. Os testes refletem isso enviando o campo abaixo.
_META_EVT_CONTACT = "evt_test_contact"


def _bearer_for_role(session, role: str) -> dict:
    user = User(
        name=f"{role}-leads",
        email=f"{role}-leads@test.com",
        password_hash=hash_password("pass1234"),
        role=role,
    )
    session.add(user)
    session.commit()
    return {"Authorization": f"Bearer {generate_token(user)}"}


def test_atendente_pode_listar_e_ver_stats_de_leads(client, session):
    """Regressão (Bug 1): o atendente opera leads (pode mutar status/telefone),
    mas a listagem e as stats exigiam só admin/vendedor → a página de leads
    falhava com 403 para o atendente. Agora os GET aceitam atendente também."""
    headers = _bearer_for_role(session, "atendente")

    resp = client.get("/api/leads", headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert "leads" in body and "total" in body

    resp_stats = client.get("/api/leads/stats", headers=headers)
    assert resp_stats.status_code == 200
    assert resp_stats.get_json().get("ok") is True


def test_entregador_continua_sem_acesso_a_leads(client, session):
    """O entregador não opera leads — deve continuar barrado (403) na listagem."""
    headers = _bearer_for_role(session, "entregador")
    resp = client.get("/api/leads", headers=headers)
    assert resp.status_code == 403


def test_cria_lead_json_e_nao_duplica_por_hash(client, session):
    payload = {
        "event": "whatsapp_click",
        "url": "https://lpb.planteumaflor.com/?utm_source=facebook&utm_medium=cpc&utm_campaign=buques-maio",
        "referrer": "https://www.facebook.com/",
        "utm_source": "facebook",
        "utm_medium": "cpc",
        "utm_campaign": "buques-maio",
        "utm_content": "video-arranjo-rosa",
        "utm_term": "flores-presente",
        "phone": "(31) 98888-7777",
        "fbclid": "fbclid-from-url",
        "fbp": "fb.1.1700000000.abc123xyz987",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }

    r1 = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r1.status_code == 201
    data1 = r1.get_json()
    assert data1["ok"] is True
    assert data1["duplicated"] is False

    r2 = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert data2["ok"] is True
    assert data2["duplicated"] is True

    assert session.query(Lead).count() == 1
    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.phone == "31988887777"
    assert lead.fbclid == "fbclid-from-url"
    assert lead.fbp == "fb.1.1700000000.abc123xyz987"


def test_persiste_campos_de_sessao_no_touchpoint(client, session):
    """first_landing_url/session_referrer chegam no POST e devem ser persistidos
    no touchpoint (antes eram descartados). Diagnóstico de perda de UTM."""
    from app.models.lead_touchpoint import LeadTouchpoint

    payload = {
        "event": "PageView",
        "url": "https://lpb.planteumaflor.com/?utm_campaign=buques",
        "utm_campaign": "buques",
        "first_landing_url": "https://lpb.planteumaflor.com/?utm_source=ig&utm_campaign=buques",
        "session_referrer": "https://l.instagram.com/",
    }
    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest (iPhone)"})
    assert r.status_code == 201

    tp = session.query(LeadTouchpoint).order_by(LeadTouchpoint.id.desc()).first()
    assert tp is not None
    assert tp.first_landing_url == "https://lpb.planteumaflor.com/?utm_source=ig&utm_campaign=buques"
    assert tp.session_referrer == "https://l.instagram.com/"
    # Capturado server-side a partir do header (a query de diagnóstico usa este campo).
    assert "iPhone" in (tp.client_user_agent or "")
    # E aparecem no serializer dos touchpoints.
    d = tp.to_dict()
    assert d["first_landing_url"] == payload["first_landing_url"]
    assert d["session_referrer"] == payload["session_referrer"]


def test_campos_de_sessao_nao_entram_no_dedup_key(client, session):
    """Campos de sessão variam por sessão; não podem entrar no dedup_key (ALLOWED_FIELDS),
    senão fragmentariam a deduplicação. Dois POSTs iguais a menos da sessão = 1 lead."""
    base = {
        "event": "whatsapp_click",
        "utm_campaign": "buques",
        "token_rastreio": _VALID_TOKEN,
        "meta_event_id_contact": _META_EVT_CONTACT,
    }
    r1 = client.post(
        "/api/leads",
        json={**base, "first_landing_url": "https://lpb.planteumaflor.com/a", "session_referrer": "https://x/"},
        headers={"User-Agent": "pytest"},
    )
    r2 = client.post(
        "/api/leads",
        json={**base, "first_landing_url": "https://lpb.planteumaflor.com/b", "session_referrer": "https://y/"},
        headers={"User-Agent": "pytest"},
    )
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r2.get_json()["duplicated"] is True
    assert session.query(Lead).count() == 1


def test_cria_lead_text_plain_sendbeacon(client, session):
    payload = {
        "event": "whatsapp_click",
        "utm_source": "facebook",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }
    body = json.dumps(payload)

    r = client.post(
        "/api/leads",
        data=body,
        content_type="text/plain",
        headers={"User-Agent": "pytest"},
    )
    assert r.status_code == 201
    assert session.query(Lead).count() == 1


def test_dedup_por_sck_prioriza_mesmo_com_payload_diferente(client, session):
    p1 = {
        "event": "whatsapp_click",
        "utm_source": "facebook",
        "utm_campaign": "c1",
        "sck": "hash-interno-utmify",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }
    p2 = {
        "event": "whatsapp_click",
        "utm_source": "google",
        "utm_campaign": "c2",
        "sck": "hash-interno-utmify",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }

    r1 = client.post("/api/leads", json=p1, headers={"User-Agent": "pytest"})
    assert r1.status_code == 201

    r2 = client.post("/api/leads", json=p2, headers={"User-Agent": "pytest"})
    assert r2.status_code == 200
    assert r2.get_json()["duplicated"] is True

    assert session.query(Lead).count() == 1


def test_cria_lead_trailing_slash(client, session):
    payload = {
        "event": "whatsapp_click",
        "utm_source": "facebook",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }
    r = client.post("/api/leads/", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201
    assert session.query(Lead).count() == 1


def test_cria_lead_lendo_fbclid_de_fbc(client, session):
    payload = {
        "event": "whatsapp_click",
        "fbc": "fb.1.1700000000.fbclid-extraido",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }
    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201
    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.fbclid == "fbclid-extraido"


def test_realcase_landing_fbclid_fbp_preserva_campos(client, session):
    payload = {
        "event": "whatsapp_click",
        "url": "https://lpb.planteumaflor.com/?utm_source=facebook&utm_medium=cpc&utm_campaign=mae&fbclid=IwARreal123",
        "utm_source": "facebook",
        "utm_medium": "cpc",
        "utm_campaign": "mae",
        "phone": "+55 (62) 99999-0000",
        "fbclid": "IwARreal123",
        "fbp": "fb.1.1711111111111.555666777888",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }
    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201

    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.phone == "5562999990000"
    assert lead.fbclid == "IwARreal123"
    assert lead.fbp == "fb.1.1711111111111.555666777888"


def test_listar_leads_default_filtra_eventos_principais(client, session):
    """GET /api/leads sem params retorna só eventos principais (exclui page_view, scroll)."""
    client.post(
        "/api/leads",
        json={
            "event": "whatsapp_click",
            "utm_source": "fb",
            "meta_event_id_contact": _META_EVT_CONTACT,
        },
        headers={"User-Agent": "pytest"},
    )
    client.post(
        "/api/leads",
        json={"event": "page_view", "utm_source": "fb"},
        headers={"User-Agent": "pytest"},
    )
    client.post(
        "/api/leads", json={"event": "scroll", "utm_source": "fb"}, headers={"User-Agent": "pytest"}
    )

    r = client.get("/api/leads", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1
    assert data["leads"][0]["event"] == "whatsapp_click"


def test_listar_leads_event_all_retorna_tudo(client, session):
    """GET /api/leads?event=all retorna todos os eventos."""
    client.post(
        "/api/leads",
        json={"event": "whatsapp_click", "meta_event_id_contact": _META_EVT_CONTACT},
        headers={"User-Agent": "pytest"},
    )
    client.post("/api/leads", json={"event": "page_view"}, headers={"User-Agent": "pytest"})

    r = client.get("/api/leads?event=all", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 2


def test_listar_leads_event_especifico(client, session):
    """GET /api/leads?event=page_view filtra somente page_view."""
    client.post(
        "/api/leads",
        json={"event": "whatsapp_click", "meta_event_id_contact": _META_EVT_CONTACT},
        headers={"User-Agent": "pytest"},
    )
    client.post("/api/leads", json={"event": "page_view"}, headers={"User-Agent": "pytest"})

    r = client.get("/api/leads?event=page_view", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1
    assert data["leads"][0]["event"] == "page_view"


def test_listar_leads_events_param_lista(client, session):
    """GET /api/leads?events=a,b filtra por vários eventos."""
    client.post("/api/leads", json={"event": "modal_open"}, headers={"User-Agent": "pytest"})
    client.post(
        "/api/leads",
        json={"event": "whatsapp_click", "meta_event_id_contact": _META_EVT_CONTACT},
        headers={"User-Agent": "pytest"},
    )
    client.post("/api/leads", json={"event": "page_view"}, headers={"User-Agent": "pytest"})

    r = client.get("/api/leads?events=modal_open,whatsapp_click", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 2


def test_realcase_fbc_sem_fbclid_extrai_clickid(client, session):
    payload = {
        "event": "whatsapp_click",
        "url": "https://lpb.planteumaflor.com/",
        "fbc": "fb.1.1711111111111.IwARfbcOnly987",
        "fbp": "fb.1.1711111111111.999000111222",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }
    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201

    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.fbclid == "IwARfbcOnly987"
    assert lead.fbp == "fb.1.1711111111111.999000111222"


def test_cria_lead_anonimo_com_token_rastreio(client, session):
    payload = {
        "event": "whatsapp_click",
        "token_rastreio": _VALID_TOKEN.lower(),
        "phone": "+55 (62) 99999-0000",
        "fbclid": "IwARtoken123",
        "fbp": "fb.1.1711111111111.555666777888",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }

    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201

    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.token_rastreio == _VALID_TOKEN
    assert lead.phone is None
    assert lead.token_valido is True
    assert lead.status == "pendente_whatsapp"


def test_token_rastreio_repetido_retorna_duplicado(client, session):
    payload = {
        "event": "whatsapp_click",
        "token_rastreio": _VALID_TOKEN,
        "fbclid": "IwARtoken123",
        "fbp": "fb.1.1711111111111.555666777888",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }

    r1 = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r1.status_code == 201
    first_id = r1.get_json()["id"]

    r2 = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert data2["duplicated"] is True
    assert data2["id"] == first_id
    assert session.query(Lead).count() == 1


def test_token_invalido_persiste_token_valido_false(client, session):
    payload = {
        "event": "whatsapp_click",
        "token_rastreio": _INVALID_TOKEN,
        "status": "pendente_whatsapp",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }

    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["token_valido"] is False

    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.token_rastreio == _INVALID_TOKEN
    assert lead.token_valido is False


def test_evento_nao_whatsapp_nao_persiste_token_invalido(client, session):
    payload = {
        "event": "site_click",
        "token_rastreio": _INVALID_TOKEN,
        "destination_url": f"https://site.exemplo.com/?text=[Cod:%20{_VALID_TOKEN}]",
        "status": "pendente_whatsapp",
    }

    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["token_valido"] is None

    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.event == "site_click"
    assert lead.token_rastreio is None
    assert lead.token_valido is None
    assert lead.status in (None, "")


def test_extrai_token_de_destination_url(client, session):
    payload = {
        "event": "whatsapp_click",
        "destination_url": f"https://wa.me/5562999990000?text=Ol%C3%A1%20[Cod:%20{_VALID_TOKEN}]",
        "status": "pendente_whatsapp",
        "meta_event_id_contact": _META_EVT_CONTACT,
    }

    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["token_valido"] is True

    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.token_rastreio == _VALID_TOKEN
    assert lead.token_valido is True
    assert lead.status == "pendente_whatsapp"


def test_whatsapp_start_atualiza_status_sem_sobrescrever_compra_realizada(client, session):
    lead = Lead(
        dedup_key="lead-whatsapp-start",
        token_rastreio=_SECOND_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
    )
    lead_compra = Lead(
        dedup_key="lead-whatsapp-start-compra",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="compra_realizada",
    )
    session.add_all([lead, lead_compra])
    session.commit()

    r1 = client.post("/api/leads/whatsapp-start", json={"message": f"Olá [Cod: {_SECOND_VALID_TOKEN}]"})
    assert r1.status_code == 200
    data1 = r1.get_json()
    assert data1["ok"] is True
    assert data1["found"] is True
    assert data1["token_valido"] is True
    # Webhook nunca confirma direto — sempre promove pra lead_pendente; operador
    # confirma manualmente com 1-clique (que dispara CAPI Lead on-event).
    assert data1["status"] == "lead_pendente"

    session.refresh(lead)
    assert lead.status == "lead_pendente"

    r2 = client.post("/api/leads/whatsapp-start", json={"token_rastreio": _VALID_TOKEN})
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert data2["ok"] is True
    assert data2["found"] is True
    assert data2["status"] == "compra_realizada"

    session.refresh(lead_compra)
    assert lead_compra.status == "compra_realizada"


def test_patch_phone_atualiza_lead_pendente_whatsapp(client, session):
    lead = Lead(
        dedup_key="lead-phone-manual",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone=None,
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/phone",
        json={"phone": "(62) 98888-7777"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True

    session.refresh(lead)
    assert lead.phone == "62988887777"
    # Captura de telefone promove pra lead_pendente; operador confirma depois.
    assert lead.status == "lead_pendente"


def test_patch_phone_atualiza_lead_nao_entrou_em_contato(client, session):
    lead = Lead(
        dedup_key="lead-phone-no-contact",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="nao_entrou_em_contato",
        phone=None,
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/phone",
        json={"phone": "(62) 97777-6666"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True

    session.refresh(lead)
    assert lead.phone == "62977776666"
    # nao_entrou_em_contato + telefone → lead_pendente (Trilha B reaberta).
    assert lead.status == "lead_pendente"


def test_patch_status_nao_entrou_em_contato(client, session):
    lead = Lead(
        dedup_key="lead-status-no-contact",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "nao_entrou_em_contato"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["lead"]["status"] == "nao_entrou_em_contato"

    session.refresh(lead)
    assert lead.status == "nao_entrou_em_contato"


def test_patch_status_rejeita_se_nao_pendente_whatsapp(client, session):
    lead = Lead(
        dedup_key="lead-status-wrong",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="whatsapp_iniciado",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "nao_entrou_em_contato"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 400
    session.refresh(lead)
    assert lead.status == "whatsapp_iniciado"


def test_listar_leads_filtra_token_rastreio(client, session):
    session.add(
        Lead(
            dedup_key="tok-a",
            event="whatsapp_click",
            token_rastreio=_VALID_TOKEN,
            token_valido=True,
        )
    )
    session.add(
        Lead(
            dedup_key="tok-b",
            event="whatsapp_click",
            token_rastreio=_SECOND_VALID_TOKEN,
            token_valido=True,
        )
    )
    session.commit()

    r = client.get(
        f"/api/leads?token_rastreio={_VALID_TOKEN}",
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1
    assert data["leads"][0]["token_rastreio"] == _VALID_TOKEN


def test_patch_phone_por_token_rastreio(client, session):
    lead = Lead(
        dedup_key="lead-phone-by-token",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone=None,
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        "/api/leads/by-token/phone",
        json={"token_rastreio": _VALID_TOKEN, "phone": "(62) 98888-7777"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    session.refresh(lead)
    assert lead.phone == "62988887777"
    assert lead.status == "lead_pendente"


def test_patch_status_por_token_rastreio(client, session):
    lead = Lead(
        dedup_key="lead-status-by-token",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        "/api/leads/by-token/status",
        json={"token_rastreio": _VALID_TOKEN, "status": "nao_entrou_em_contato"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    session.refresh(lead)
    assert lead.status == "nao_entrou_em_contato"


def test_patch_phone_por_token_sem_token_400(client, session):
    r = client.patch(
        "/api/leads/by-token/phone",
        json={"phone": "(62) 98888-7777"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 400


def test_patch_phone_por_token_desconhecido_404(client, session):
    r = client.patch(
        "/api/leads/by-token/phone",
        json={"token_rastreio": _INVALID_TOKEN, "phone": "(62) 98888-7777"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 404


def test_patch_phone_por_token_usa_lead_mais_recente(client, session):
    old = Lead(
        dedup_key="dup-old",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone=None,
    )
    new = Lead(
        dedup_key="dup-new",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone=None,
    )
    session.add_all([old, new])
    session.commit()

    r = client.patch(
        "/api/leads/by-token/phone",
        json={"token_rastreio": _VALID_TOKEN, "phone": "(62) 91111-2222"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    session.refresh(old)
    session.refresh(new)
    assert new.phone == "62911112222"
    assert old.phone is None


def test_post_whatsapp_exige_meta_event_id_quando_funnel_ativo(client, monkeypatch):
    monkeypatch.setenv("META_CAPI_LEAD_FUNNEL_ENABLED", "true")
    r = client.post(
        "/api/leads",
        json={"event": "whatsapp_click", "utm_source": "fb"},
        headers={"User-Agent": "pytest"},
    )
    assert r.status_code == 400
    assert "meta_event_id_contact" in r.get_json().get("error", "")


def test_post_whatsapp_com_meta_event_id_grava_outbox_contact(client, session, monkeypatch):
    monkeypatch.setenv("META_CAPI_LEAD_FUNNEL_ENABLED", "true")
    monkeypatch.setenv("META_PIXEL_ID", "1")
    monkeypatch.setenv("META_CAPI_ACCESS_TOKEN", "test_token")
    from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox

    r = client.post(
        "/api/leads",
        json={
            "event": "whatsapp_click",
            "utm_source": "fb",
            "meta_event_id_contact": "contact_evt_abc12",
            "fbp": "fb.1.1711111111111.555666777888",
        },
        headers={"User-Agent": "pytest-ua"},
    )
    assert r.status_code == 201
    lead = session.query(Lead).first()
    assert lead.meta_event_id_contact == "contact_evt_abc12"
    rows = session.query(MetaCapiLeadOutbox).all()
    assert len(rows) == 1
    assert rows[0].funnel_stage == "contact"
    assert rows[0].event_id == "contact_evt_abc12"


def test_patch_phone_com_pixel_exige_meta_event_id_lead(client, session, monkeypatch):
    monkeypatch.setenv("META_CAPI_LEAD_FUNNEL_ENABLED", "true")
    lead = Lead(
        dedup_key="px-req-lead-eid",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone=None,
        meta_event_id_contact="c1",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/phone",
        json={"phone": "(62) 98888-7777", "meta_pixel_lead": True},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 400


def test_patch_status_rejeita_evento_nao_whatsapp(client, session):
    lead = Lead(
        dedup_key="lead-status-site",
        event="site_click",
        status="",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "nao_entrou_em_contato"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 400


def test_patch_status_descarte_a_partir_de_pendente(client, session):
    # Descarte exige telefone (regra dura). Lead inicia com phone capturado.
    lead = Lead(
        dedup_key="lead-descarte-pend",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone="62988887777",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    session.refresh(lead)
    assert lead.status == "descarte"


def test_patch_status_descarte_sem_phone_retorna_422(client, session):
    """Invariante: whatsapp_iniciado e descarte exigem telefone (422 telefone_obrigatorio)."""
    lead = Lead(
        dedup_key="lead-descarte-sem-fone",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone=None,
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 422
    assert r.get_json()["error"] == "telefone_obrigatorio"
    session.refresh(lead)
    assert lead.status == "pendente_whatsapp"


def test_patch_status_whatsapp_iniciado_sem_phone_retorna_422(client, session):
    """Confirmação 1-clique sem telefone também retorna 422."""
    lead = Lead(
        dedup_key="lead-confirm-sem-fone",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="lead_pendente",
        phone=None,
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "whatsapp_iniciado"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 422
    assert r.get_json()["error"] == "telefone_obrigatorio"


def test_patch_status_descarte_a_partir_de_whatsapp_iniciado_eh_proibido(client, session):
    """Lead Confirmado (whatsapp_iniciado) é terminal — não pode virar descarte."""
    lead = Lead(
        dedup_key="lead-descarte-wpp",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="whatsapp_iniciado",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 400
    session.refresh(lead)
    assert lead.status == "whatsapp_iniciado"


def test_patch_status_nao_entrou_em_contato_para_descarte(client, session):
    """Lead já marcado como 'não contatou' deve poder virar descarte (caso reclassificação).

    Descarte exige telefone — adicionar phone garante que a regra dura é
    satisfeita (cenário onde reclassificamos um descarte antigo já com fone).
    """
    lead = Lead(
        dedup_key="lead-noctc-to-descarte",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="nao_entrou_em_contato",
        phone="62977776666",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    session.refresh(lead)
    assert lead.status == "descarte"


def test_patch_status_undo_nao_entrou_em_contato_para_pendente(client, session):
    lead = Lead(
        dedup_key="lead-undo-noctc",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="nao_entrou_em_contato",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "pendente_whatsapp"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    session.refresh(lead)
    assert lead.status == "pendente_whatsapp"


def test_patch_status_undo_descarte_para_pendente(client, session):
    lead = Lead(
        dedup_key="lead-undo-descarte",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="descarte",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "pendente_whatsapp"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    session.refresh(lead)
    assert lead.status == "pendente_whatsapp"


def test_patch_status_rejeita_transicao_invalida(client, session):
    lead = Lead(
        dedup_key="lead-trans-inv",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="compra_realizada",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 400
    session.refresh(lead)
    assert lead.status == "compra_realizada"


def test_bulk_status_atualiza_e_pula_invalidos(client, session):
    pendente = Lead(
        dedup_key="bulk-pend",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        # Descarte exige fone; lead já tem captura prévia.
        phone="62988887777",
    )
    compra = Lead(
        dedup_key="bulk-compra",
        event="whatsapp_click",
        token_rastreio=_SECOND_VALID_TOKEN,
        token_valido=True,
        status="compra_realizada",
    )
    site = Lead(
        dedup_key="bulk-site",
        event="site_click",
        status="",
    )
    session.add_all([pendente, compra, site])
    session.commit()

    inexistente = max(pendente.id, compra.id, site.id) + 999

    r = client.patch(
        "/api/leads/bulk/status",
        json={"ids": [pendente.id, compra.id, site.id, inexistente], "status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["updated"] == 1
    assert data["skipped"] == 3
    assert set(data["skipped_ids"]) == {compra.id, site.id, inexistente}

    session.refresh(pendente)
    session.refresh(compra)
    assert pendente.status == "descarte"
    assert compra.status == "compra_realizada"


def test_bulk_status_valida_payload(client, session):
    r1 = client.patch(
        "/api/leads/bulk/status",
        json={"ids": [], "status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r1.status_code == 400

    r2 = client.patch(
        "/api/leads/bulk/status",
        json={"ids": [1], "status": "compra_realizada"},
        headers=_ADMIN_AUTH,
    )
    assert r2.status_code == 400

    r3 = client.patch(
        "/api/leads/bulk/status",
        json={"ids": ["abc"], "status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r3.status_code == 400


def test_leads_stats_conta_pendentes_confirmados_e_compras(client, session):
    from datetime import timedelta

    from app.models.pedido import datetime_now_brazil

    now = datetime_now_brazil()

    leads = [
        Lead(
            dedup_key="stat-pend-phone",
            event="whatsapp_click",
            status="pendente_whatsapp",
            phone="11999990001",
            created_at=now,
        ),
        Lead(
            dedup_key="stat-pend-nophone",
            event="whatsapp_click",
            status="pendente_whatsapp",
            phone=None,
            created_at=now,
        ),
        # Confirmado com telefone — deve entrar em `confirmados`
        Lead(
            dedup_key="stat-confirmado",
            event="whatsapp_click",
            status="whatsapp_iniciado",
            phone="11999990004",
            created_at=now,
        ),
        # Confirmado sem telefone — não deve entrar em `confirmados` (defensivo)
        Lead(
            dedup_key="stat-confirmado-sem-phone",
            event="whatsapp_click",
            status="whatsapp_iniciado",
            phone=None,
            created_at=now,
        ),
        Lead(
            dedup_key="stat-compra",
            event="whatsapp_click",
            status="compra_realizada",
            phone="11999990002",
            created_at=now,
        ),
        Lead(
            dedup_key="stat-velho",
            event="whatsapp_click",
            status="pendente_whatsapp",
            phone="11999990003",
            created_at=now - timedelta(days=20),
        ),
        Lead(
            dedup_key="stat-site",
            event="site_click",
            status="",
            created_at=now,
        ),
    ]
    session.add_all(leads)
    session.commit()

    r = client.get("/api/leads/stats", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    # Hoje: 2 pendentes, 1 confirmado (whatsapp_iniciado + phone), 1 compra
    assert data["today"]["pendentes"] == 2
    assert data["today"]["confirmados"] == 1
    assert data["today"]["compras"] == 1
    assert data["today"]["total"] == 5
    # 14d: hoje + nada anterior (20d está fora)
    assert data["last_14d"]["pendentes"] == 2
    assert data["last_14d"]["confirmados"] == 1
    assert data["last_14d"]["compras"] == 1


def test_listar_leads_period_today(client, session):
    from datetime import timedelta

    from app.models.pedido import datetime_now_brazil

    now = datetime_now_brazil()
    today_lead = Lead(
        dedup_key="period-today",
        event="whatsapp_click",
        status="pendente_whatsapp",
        created_at=now,
    )
    old_lead = Lead(
        dedup_key="period-old",
        event="whatsapp_click",
        status="pendente_whatsapp",
        created_at=now - timedelta(days=5),
    )
    session.add_all([today_lead, old_lead])
    session.commit()

    r = client.get("/api/leads?period=today", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    ids = [lead["id"] for lead in data["leads"]]
    assert today_lead.id in ids
    assert old_lead.id not in ids


def test_listar_leads_period_14d(client, session):
    from datetime import timedelta

    from app.models.pedido import datetime_now_brazil

    now = datetime_now_brazil()
    recent = Lead(
        dedup_key="period-14d-recent",
        event="whatsapp_click",
        status="pendente_whatsapp",
        created_at=now - timedelta(days=5),
    )
    old = Lead(
        dedup_key="period-14d-old",
        event="whatsapp_click",
        status="pendente_whatsapp",
        created_at=now - timedelta(days=20),
    )
    session.add_all([recent, old])
    session.commit()

    r = client.get("/api/leads?period=14d", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    ids = [lead["id"] for lead in data["leads"]]
    assert recent.id in ids
    assert old.id not in ids


def test_descarte_dispara_outbox_lead_disqualified(client, session, monkeypatch):
    """Quando lead vira descarte com META funnel ligado, cria outbox LeadDisqualified."""
    monkeypatch.setenv("META_CAPI_LEAD_FUNNEL_ENABLED", "true")
    monkeypatch.setenv("META_PIXEL_ID", "1")
    monkeypatch.setenv("META_CAPI_ACCESS_TOKEN", "test_token")
    from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox

    lead = Lead(
        dedup_key="descarte-outbox",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone="62988887777",
        meta_event_id_contact="c_x",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200

    rows = (
        session.query(MetaCapiLeadOutbox)
        .filter_by(lead_id=lead.id, funnel_stage="disqualified")
        .all()
    )
    assert len(rows) == 1
    payload = json.loads(rows[0].payload_json)
    assert payload["event_name"] == "LeadDisqualified"
    assert payload["custom_data"]["lead_id"] == str(lead.id)
    # value/currency omitidos: evento custom não tem pricing aplicável e
    # value=0 era flagado como "preço inválido" pela Meta.
    assert "value" not in payload["custom_data"]
    assert "currency" not in payload["custom_data"]


def test_descarte_idempotente_nao_duplica_outbox(client, session, monkeypatch):
    """Reverter descarte e re-descartar não cria segundo outbox row disqualified."""
    monkeypatch.setenv("META_CAPI_LEAD_FUNNEL_ENABLED", "true")
    monkeypatch.setenv("META_PIXEL_ID", "1")
    monkeypatch.setenv("META_CAPI_ACCESS_TOKEN", "test_token")
    from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox

    lead = Lead(
        dedup_key="descarte-idemp",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone="62977776666",
        meta_event_id_contact="c_y",
    )
    session.add(lead)
    session.commit()

    # 1ª vez → cria outbox
    r1 = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r1.status_code == 200

    # Undo → volta pra pendente
    r2 = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "pendente_whatsapp"},
        headers=_ADMIN_AUTH,
    )
    assert r2.status_code == 200

    # 2ª vez descartando → NÃO cria outbox novo (já existe row)
    r3 = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r3.status_code == 200

    rows = (
        session.query(MetaCapiLeadOutbox)
        .filter_by(lead_id=lead.id, funnel_stage="disqualified")
        .all()
    )
    assert len(rows) == 1


def test_descarte_nao_dispara_outbox_com_funnel_desativado(client, session):
    """Sem META_CAPI_LEAD_FUNNEL_ENABLED, transição para descarte não cria outbox."""
    from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox

    lead = Lead(
        dedup_key="descarte-funnel-off",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone="62966665555",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200

    rows = (
        session.query(MetaCapiLeadOutbox)
        .filter_by(lead_id=lead.id, funnel_stage="disqualified")
        .all()
    )
    assert rows == []


def test_bulk_descarte_dispara_outbox_para_cada_lead(client, session, monkeypatch):
    """Bulk update para descarte cria 1 outbox row por lead que efetivamente mudou."""
    monkeypatch.setenv("META_CAPI_LEAD_FUNNEL_ENABLED", "true")
    monkeypatch.setenv("META_PIXEL_ID", "1")
    monkeypatch.setenv("META_CAPI_ACCESS_TOKEN", "test_token")
    from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox

    leads = [
        Lead(
            dedup_key=f"bulk-descarte-{i}",
            event="whatsapp_click",
            token_rastreio=_VALID_TOKEN if i == 0 else _SECOND_VALID_TOKEN if i == 1 else None,
            status="pendente_whatsapp",
            phone=f"6299988{i:04d}",
            meta_event_id_contact=f"c_b{i}",
        )
        for i in range(3)
    ]
    session.add_all(leads)
    session.commit()
    ids = [lead.id for lead in leads]

    r = client.patch(
        "/api/leads/bulk/status",
        json={"ids": ids, "status": "descarte"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    assert r.get_json()["updated"] == 3

    rows = (
        session.query(MetaCapiLeadOutbox)
        .filter_by(funnel_stage="disqualified")
        .all()
    )
    assert len(rows) == 3
    assert {row.lead_id for row in rows} == set(ids)


def test_bulk_disqualify_atualiza_phone_e_dispara_outbox(client, session, monkeypatch):
    """Endpoint /bulk/disqualify: phone fornecido vai pro user_data do LeadDisqualified."""
    monkeypatch.setenv("META_CAPI_LEAD_FUNNEL_ENABLED", "true")
    monkeypatch.setenv("META_PIXEL_ID", "1")
    monkeypatch.setenv("META_CAPI_ACCESS_TOKEN", "test_token")
    from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox

    lead = Lead(
        dedup_key="disq-with-phone",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone=None,
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        "/api/leads/bulk/disqualify",
        json={"updates": [{"id": lead.id, "phone": "(62) 99999-0000"}]},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["updated"] == 1
    assert data["skipped"] == 0

    session.refresh(lead)
    assert lead.status == "descarte"
    assert lead.phone == "62999990000"

    rows = (
        session.query(MetaCapiLeadOutbox)
        .filter_by(lead_id=lead.id, funnel_stage="disqualified")
        .all()
    )
    assert len(rows) == 1
    payload = json.loads(rows[0].payload_json)
    assert payload["event_name"] == "LeadDisqualified"
    assert "ph" in payload["user_data"]
    assert isinstance(payload["user_data"]["ph"], list)
    assert len(payload["user_data"]["ph"][0]) == 64  # sha256 hex


def test_bulk_disqualify_sem_phone_eh_pulado(client, session, monkeypatch):
    """Sem phone fornecido E sem phone prévio: lead é skipped (regra dura).

    Substitui o teste antigo `test_bulk_disqualify_sem_phone_dispara_outbox_sem_ph`,
    que era válido no modelo antigo (descarte sem fone era permitido). Agora a
    invariante "descarte exige telefone" se aplica também ao bulk: sem nenhum
    telefone (do update ou pré-existente), o lead é pulado e nenhum outbox sai.
    """
    monkeypatch.setenv("META_CAPI_LEAD_FUNNEL_ENABLED", "true")
    monkeypatch.setenv("META_PIXEL_ID", "1")
    monkeypatch.setenv("META_CAPI_ACCESS_TOKEN", "test_token")
    from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox

    lead = Lead(
        dedup_key="disq-no-phone",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone=None,
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        "/api/leads/bulk/disqualify",
        json={"updates": [{"id": lead.id}]},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["updated"] == 0
    assert data["skipped"] == 1
    assert data["skipped_ids"] == [lead.id]

    session.refresh(lead)
    assert lead.status == "pendente_whatsapp"
    assert lead.phone is None

    rows = (
        session.query(MetaCapiLeadOutbox)
        .filter_by(lead_id=lead.id, funnel_stage="disqualified")
        .all()
    )
    assert rows == []


def test_bulk_disqualify_phone_invalido_pula_lead(client, session):
    """Phone fornecido mas inválido: lead inteiro é pulado (não desqualifica sem o dado pedido)."""
    lead = Lead(
        dedup_key="disq-bad-phone",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        phone=None,
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        "/api/leads/bulk/disqualify",
        json={"updates": [{"id": lead.id, "phone": "abc"}]},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["updated"] == 0
    assert data["skipped"] == 1
    assert data["skipped_ids"] == [lead.id]

    session.refresh(lead)
    assert lead.status == "pendente_whatsapp"


def test_bulk_disqualify_pula_whatsapp_iniciado(client, session):
    """Leads em whatsapp_iniciado (Lead Confirmado) são pulados — transição não permitida."""
    confirmado = Lead(
        dedup_key="disq-skip-confirmado",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="whatsapp_iniciado",
        phone="62988887777",
    )
    pendente = Lead(
        dedup_key="disq-skip-pend",
        event="whatsapp_click",
        token_rastreio=_SECOND_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
        # Descarte exige fone; lead já tem captura prévia.
        phone="62977776666",
    )
    session.add_all([confirmado, pendente])
    session.commit()

    r = client.patch(
        "/api/leads/bulk/disqualify",
        json={"updates": [{"id": confirmado.id}, {"id": pendente.id}]},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["updated"] == 1
    assert data["skipped"] == 1
    assert data["skipped_ids"] == [confirmado.id]

    session.refresh(confirmado)
    session.refresh(pendente)
    assert confirmado.status == "whatsapp_iniciado"  # intocado
    assert pendente.status == "descarte"


def test_bulk_disqualify_valida_payload(client, session):
    r1 = client.patch(
        "/api/leads/bulk/disqualify",
        json={"updates": []},
        headers=_ADMIN_AUTH,
    )
    assert r1.status_code == 400

    r2 = client.patch(
        "/api/leads/bulk/disqualify",
        json={"updates": [{"id": "abc"}]},
        headers=_ADMIN_AUTH,
    )
    assert r2.status_code == 400


def test_listar_leads_period_all_ignora_janela(client, session):
    from datetime import timedelta

    from app.models.pedido import datetime_now_brazil

    now = datetime_now_brazil()
    old = Lead(
        dedup_key="period-all-old",
        event="whatsapp_click",
        status="pendente_whatsapp",
        created_at=now - timedelta(days=60),
    )
    session.add(old)
    session.commit()

    r = client.get("/api/leads?period=all", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    ids = [lead["id"] for lead in data["leads"]]
    assert old.id in ids


def test_marcar_followup_seta_timestamp(client, session):
    lead = Lead(
        dedup_key="followup-mark",
        event="whatsapp_click",
        status="whatsapp_iniciado",
        phone="11999990050",
    )
    session.add(lead)
    session.commit()
    assert lead.followup_feito_em is None

    r = client.patch(f"/api/leads/{lead.id}/followup", json={}, headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["lead"]["followup_feito_em"] is not None

    session.refresh(lead)
    assert lead.followup_feito_em is not None


def test_marcar_followup_undo_limpa_campos(client, session):
    from app.models.pedido import datetime_now_brazil

    lead = Lead(
        dedup_key="followup-undo",
        event="whatsapp_click",
        status="whatsapp_iniciado",
        phone="11999990051",
        followup_feito_em=datetime_now_brazil(),
        followup_por=1,
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/followup",
        json={"action": "undo"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["lead"]["followup_feito_em"] is None
    assert data["lead"]["followup_por"] is None

    session.refresh(lead)
    assert lead.followup_feito_em is None
    assert lead.followup_por is None


def test_marcar_followup_action_invalida(client, session):
    lead = Lead(
        dedup_key="followup-bad-action",
        event="whatsapp_click",
        status="whatsapp_iniciado",
        phone="11999990052",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/followup",
        json={"action": "destruir"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 400


def test_marcar_followup_lead_inexistente(client):
    r = client.patch("/api/leads/999999/followup", json={}, headers=_ADMIN_AUTH)
    assert r.status_code == 404


def test_filtro_pending_followup_days_lista_apenas_atrasados(client, session):
    from datetime import timedelta

    from app.models.pedido import datetime_now_brazil

    now = datetime_now_brazil()

    # Lead confirmado sem followup nenhum (NULL) — deve aparecer.
    lead_nunca = Lead(
        dedup_key="pending-null",
        event="whatsapp_click",
        status="whatsapp_iniciado",
        phone="11999990060",
        followup_feito_em=None,
    )
    # Lead confirmado com followup há 10 dias — deve aparecer no filtro de 7d.
    lead_atrasado = Lead(
        dedup_key="pending-atrasado",
        event="whatsapp_click",
        status="whatsapp_iniciado",
        phone="11999990061",
        followup_feito_em=now - timedelta(days=10),
    )
    # Lead confirmado com followup recente (2 dias) — NÃO deve aparecer no filtro 7d.
    lead_recente = Lead(
        dedup_key="pending-recente",
        event="whatsapp_click",
        status="whatsapp_iniciado",
        phone="11999990062",
        followup_feito_em=now - timedelta(days=2),
    )
    # Lead pendente_whatsapp sem followup — NÃO deve aparecer (só confirmados entram).
    lead_pendente = Lead(
        dedup_key="pending-status-pendente",
        event="whatsapp_click",
        status="pendente_whatsapp",
        phone="11999990063",
        followup_feito_em=None,
    )
    session.add_all([lead_nunca, lead_atrasado, lead_recente, lead_pendente])
    session.commit()

    r = client.get("/api/leads?pending_followup_days=7&period=all", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    ids = {lead["id"] for lead in r.get_json()["leads"]}
    assert lead_nunca.id in ids
    assert lead_atrasado.id in ids
    assert lead_recente.id not in ids
    assert lead_pendente.id not in ids


# ---------------------------------------------------------------------------
# Situação (subestado do lead confirmado) — funil por situação
# ---------------------------------------------------------------------------


def test_patch_situacao_em_lead_confirmado_grava_e_nao_dispara_outbox(
    client, session, monkeypatch
):
    """Marcar situação num lead confirmado grava o valor e NÃO enfileira no outbox."""
    monkeypatch.setenv("META_CAPI_LEAD_FUNNEL_ENABLED", "true")
    monkeypatch.setenv("META_PIXEL_ID", "1")
    monkeypatch.setenv("META_CAPI_ACCESS_TOKEN", "test_token")
    from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox

    # Lead já confirmado direto (sem transição) — não há outbox pré-existente.
    lead = Lead(
        dedup_key="situacao-confirmado",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="whatsapp_iniciado",
        phone="62988887777",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/situacao",
        json={"situacao": "orcamento_enviado"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    assert r.get_json()["lead"]["situacao"] == "orcamento_enviado"
    session.refresh(lead)
    assert lead.situacao == "orcamento_enviado"
    assert lead.status == "whatsapp_iniciado"  # status intocado

    # Etiqueta operacional não toca o outbox Meta CAPI.
    assert session.query(MetaCapiLeadOutbox).count() == 0


def test_patch_situacao_em_lead_nao_confirmado_retorna_422(client, session):
    """Situação só vale para lead confirmado; lead_pendente é rejeitado."""
    lead = Lead(
        dedup_key="situacao-nao-confirmado",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="lead_pendente",
        phone="62988887777",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/situacao",
        json={"situacao": "orcamento_enviado"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 422
    assert r.get_json()["error"] == "lead_nao_confirmado"
    session.refresh(lead)
    assert lead.situacao is None


def test_patch_situacao_valor_invalido_retorna_400(client, session):
    lead = Lead(
        dedup_key="situacao-invalida",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="whatsapp_iniciado",
        phone="62988887777",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/situacao",
        json={"situacao": "qualquer_coisa"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 400
    session.refresh(lead)
    assert lead.situacao is None


def test_patch_situacao_por_token_rastreio(client, session):
    lead = Lead(
        dedup_key="situacao-by-token",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="whatsapp_iniciado",
        phone="62988887777",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        "/api/leads/by-token/situacao",
        json={"token_rastreio": _VALID_TOKEN, "situacao": "sem_resposta"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    session.refresh(lead)
    assert lead.situacao == "sem_resposta"


def test_confirmar_lead_aplica_situacao_default(client, session):
    """Ao confirmar (whatsapp_iniciado), situacao recebe default 'aguardando_resposta'."""
    lead = Lead(
        dedup_key="situacao-default-on-confirm",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="lead_pendente",
        phone="62988887777",
    )
    session.add(lead)
    session.commit()

    r = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "whatsapp_iniciado"},
        headers=_ADMIN_AUTH,
    )
    assert r.status_code == 200
    session.refresh(lead)
    assert lead.status == "whatsapp_iniciado"
    assert lead.situacao == "aguardando_resposta"


def test_listar_leads_filtra_situacao(client, session):
    confirmado_orcamento = Lead(
        dedup_key="situacao-filtro-orcamento",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="whatsapp_iniciado",
        phone="62988887777",
        situacao="orcamento_enviado",
    )
    confirmado_conversa = Lead(
        dedup_key="situacao-filtro-conversa",
        event="whatsapp_click",
        token_rastreio=_SECOND_VALID_TOKEN,
        token_valido=True,
        status="whatsapp_iniciado",
        phone="62977776666",
        situacao="aguardando_resposta",
    )
    session.add_all([confirmado_orcamento, confirmado_conversa])
    session.commit()

    r = client.get("/api/leads?situacao=orcamento_enviado", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    ids = {lead["id"] for lead in data["leads"]}
    assert confirmado_orcamento.id in ids
    assert confirmado_conversa.id not in ids
