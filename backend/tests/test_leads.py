# -*- coding: utf-8 -*-
import json

from app.models.lead import Lead


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
