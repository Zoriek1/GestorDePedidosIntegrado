# -*- coding: utf-8 -*-
import base64
import json

from app.models.lead import Lead

_ADMIN_AUTH = {"Authorization": f"Basic {base64.b64encode(b'admin:testpass').decode()}"}


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


def test_cria_lead_text_plain_sendbeacon(client, session):
    payload = {"event": "whatsapp_click", "utm_source": "facebook"}
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
    }
    p2 = {
        "event": "whatsapp_click",
        "utm_source": "google",
        "utm_campaign": "c2",
        "sck": "hash-interno-utmify",
    }

    r1 = client.post("/api/leads", json=p1, headers={"User-Agent": "pytest"})
    assert r1.status_code == 201

    r2 = client.post("/api/leads", json=p2, headers={"User-Agent": "pytest"})
    assert r2.status_code == 200
    assert r2.get_json()["duplicated"] is True

    assert session.query(Lead).count() == 1


def test_cria_lead_trailing_slash(client, session):
    payload = {"event": "whatsapp_click", "utm_source": "facebook"}
    r = client.post("/api/leads/", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201
    assert session.query(Lead).count() == 1


def test_cria_lead_lendo_fbclid_de_fbc(client, session):
    payload = {"event": "whatsapp_click", "fbc": "fb.1.1700000000.fbclid-extraido"}
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
    }
    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201

    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.phone == "5562999990000"
    assert lead.fbclid == "IwARreal123"
    assert lead.fbp == "fb.1.1711111111111.555666777888"


def test_listar_leads_default_filtra_whatsapp_click(client, session):
    """GET /api/leads sem param event retorna apenas whatsapp_click."""
    client.post("/api/leads", json={"event": "whatsapp_click", "utm_source": "fb"}, headers={"User-Agent": "pytest"})
    client.post("/api/leads", json={"event": "page_view", "utm_source": "fb"}, headers={"User-Agent": "pytest"})
    client.post("/api/leads", json={"event": "scroll", "utm_source": "fb"}, headers={"User-Agent": "pytest"})

    r = client.get("/api/leads", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1
    assert data["leads"][0]["event"] == "whatsapp_click"


def test_listar_leads_event_all_retorna_tudo(client, session):
    """GET /api/leads?event=all retorna todos os eventos."""
    client.post("/api/leads", json={"event": "whatsapp_click"}, headers={"User-Agent": "pytest"})
    client.post("/api/leads", json={"event": "page_view"}, headers={"User-Agent": "pytest"})

    r = client.get("/api/leads?event=all", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 2


def test_listar_leads_event_especifico(client, session):
    """GET /api/leads?event=page_view filtra somente page_view."""
    client.post("/api/leads", json={"event": "whatsapp_click"}, headers={"User-Agent": "pytest"})
    client.post("/api/leads", json={"event": "page_view"}, headers={"User-Agent": "pytest"})

    r = client.get("/api/leads?event=page_view", headers=_ADMIN_AUTH)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1
    assert data["leads"][0]["event"] == "page_view"


def test_realcase_fbc_sem_fbclid_extrai_clickid(client, session):
    payload = {
        "event": "whatsapp_click",
        "url": "https://lpb.planteumaflor.com/",
        "fbc": "fb.1.1711111111111.IwARfbcOnly987",
        "fbp": "fb.1.1711111111111.999000111222",
    }
    r = client.post("/api/leads", json=payload, headers={"User-Agent": "pytest"})
    assert r.status_code == 201

    lead = session.query(Lead).first()
    assert lead is not None
    assert lead.fbclid == "IwARfbcOnly987"
    assert lead.fbp == "fb.1.1711111111111.999000111222"
