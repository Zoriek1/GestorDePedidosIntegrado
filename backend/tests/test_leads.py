# -*- coding: utf-8 -*-
import base64
import json

from app.models.lead import Lead

_ADMIN_AUTH = {"Authorization": f"Basic {base64.b64encode(b'admin:testpass').decode()}"}
_VALID_TOKEN = "A3F9B7K20K"
_SECOND_VALID_TOKEN = "B7K2L9M1S0"
_INVALID_TOKEN = "A3F9B7K2ZZ"


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


def test_listar_leads_default_filtra_eventos_principais(client, session):
    """GET /api/leads sem params retorna só eventos principais (exclui page_view, scroll)."""
    client.post(
        "/api/leads",
        json={"event": "whatsapp_click", "utm_source": "fb"},
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


def test_listar_leads_events_param_lista(client, session):
    """GET /api/leads?events=a,b filtra por vários eventos."""
    client.post("/api/leads", json={"event": "modal_open"}, headers={"User-Agent": "pytest"})
    client.post("/api/leads", json={"event": "whatsapp_click"}, headers={"User-Agent": "pytest"})
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
    assert data1["status"] == "whatsapp_iniciado"

    session.refresh(lead)
    assert lead.status == "whatsapp_iniciado"

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
    assert lead.status == "whatsapp_iniciado"


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
    assert lead.status == "whatsapp_iniciado"


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
    assert lead.status == "whatsapp_iniciado"


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
    lead = Lead(
        dedup_key="lead-descarte-pend",
        event="whatsapp_click",
        token_rastreio=_VALID_TOKEN,
        token_valido=True,
        status="pendente_whatsapp",
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


def test_patch_status_descarte_a_partir_de_whatsapp_iniciado(client, session):
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
    assert r.status_code == 200
    session.refresh(lead)
    assert lead.status == "descarte"


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


def test_leads_stats_conta_pendentes_e_compras(client, session):
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
    # Hoje: 2 pendentes (1 com phone), 1 compra; site_click é excluído
    assert data["today"]["pendentes"] == 2
    assert data["today"]["com_telefone"] == 1
    assert data["today"]["compras"] == 1
    assert data["today"]["total"] == 3
    # 14d: hoje + nada anterior (20d está fora)
    assert data["last_14d"]["pendentes"] == 2
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
