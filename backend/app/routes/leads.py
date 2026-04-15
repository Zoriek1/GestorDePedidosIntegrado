# -*- coding: utf-8 -*-
"""
Rotas de Leads UTM — captura cliques da landing page e lista para o admin.
"""
import hashlib
import json
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db
from app.middleware import requires_any_role
from app.models.lead import Lead
from app.models.pedido import datetime_now_brazil
from app.repositories.meta_capi_lead_outbox_repository import MetaCapiLeadOutboxRepository
from app.utils.meta_capi_lead_helper import (
    extract_contact_event_id_from_payload,
    extract_lead_stage_event_id_from_payload,
    is_lead_funnel_enabled,
    is_truthy_meta_pixel_lead,
    try_flush_pending_meta_capi_lead_entries,
)
from app.utils.tracking_token import (
    extract_tracking_token_from_text,
    is_tracking_token_valid,
    normalize_tracking_token,
)

leads_bp = Blueprint("leads", __name__, url_prefix="/api/leads")

# Eventos considerados “principais” na listagem quando não há filtro explícito
DEFAULT_KEY_EVENTS = ("modal_open", "whatsapp_click", "site_click")
WHATSAPP_EVENT = "whatsapp_click"

ALLOWED_FIELDS = (
    "event",
    "url",
    "referrer",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "src",
    "sck",
    "token_rastreio",
    "destination_url",
    "phone",
    "fbclid",
    "fbp",
)


def _clip(value: object, max_len: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text[:max_len]


def _get_ip_address() -> str | None:
    # Preferir o primeiro IP do X-Forwarded-For (quando atrás de proxy)
    xff = (request.headers.get("X-Forwarded-For") or "").strip()
    if xff:
        return xff.split(",")[0].strip() or None
    return (request.remote_addr or "").strip() or None


def _build_dedup_key(payload: dict, ip_address: str | None) -> str:
    sck = (payload.get("sck") or "").strip()
    if sck:
        basis = f"sck:{sck}"
    else:
        ua = (request.headers.get("User-Agent") or "").strip()
        normalized = {k: (payload.get(k) or "") for k in ALLOWED_FIELDS}
        basis = (
            json.dumps(normalized, sort_keys=True, separators=(",", ":"))
            + f"|ip={ip_address or ''}|ua={ua}"
        )

    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _normalize_phone(value: object) -> str | None:
    raw = _clip(value, 50)
    if raw is None:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits[:30] if digits else None


def _extract_fbclid(data: dict) -> str | None:
    fbclid = _clip(data.get("fbclid"), 255)
    if fbclid:
        return fbclid

    # Compatibilidade: alguns fluxos enviam fbc no formato fb.1.<ts>.<fbclid>
    fbc = _clip(data.get("fbc"), 255)
    if not fbc:
        return None

    parts = fbc.split(".")
    if len(parts) >= 4:
        candidate = parts[-1].strip()
        return candidate[:255] if candidate else None
    return None


def _normalize_fbp(value: object) -> str | None:
    # _fbp costuma ter formato fb.1.<ts>.<random>; preservar valor bruto.
    return _clip(value, 255)


def _is_whatsapp_event(event: str | None) -> bool:
    return (event or "").strip().lower() == WHATSAPP_EVENT


def _resolve_lead_by_token_payload(data: dict) -> tuple[Lead | None, tuple | None]:
    """
    Busca lead mais recente com este token_rastreio.
    Retorna (lead, None) ou (None, (jsonify(...), status_code)).
    """
    token = normalize_tracking_token(data.get("token_rastreio"))
    if not token:
        return None, (
            jsonify({"ok": False, "error": "token_rastreio é obrigatório"}),
            400,
        )
    lead = (
        Lead.query.filter(Lead.token_rastreio == token)
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .first()
    )
    if not lead:
        return None, (
            jsonify({"ok": False, "error": "Nenhum lead encontrado com este token"}),
            404,
        )
    return lead, None


def _serialize_lead(lead: Lead, pedido_valores: dict | None = None) -> dict:
    payload = lead.to_dict()
    if not _is_whatsapp_event(payload.get("event")):
        payload["token_rastreio"] = None
        payload["token_valido"] = None
        if payload.get("status") == "pendente_whatsapp":
            payload["status"] = None
    payload["valor_pedido"] = (
        pedido_valores.get(lead.pedido_id)
        if (pedido_valores and lead.pedido_id)
        else None
    )
    return payload


def _parse_request_payload() -> dict:
    """
    Aceita JSON com Content-Type padrão e também text/plain (sendBeacon).
    """
    data = request.get_json(force=True, silent=True)
    if isinstance(data, dict):
        return data

    raw = request.get_data(as_text=True) or ""
    raw = raw.strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


@leads_bp.route("", methods=["POST"])
@leads_bp.route("/", methods=["POST"])
def criar_lead():
    """Recebe dados UTM da landing page (aceita application/json e text/plain via sendBeacon)."""
    data = _parse_request_payload()

    ip_address = _get_ip_address()
    dedup_key = _build_dedup_key(data, ip_address)
    event = _clip(data.get("event"), 50)
    is_whatsapp = _is_whatsapp_event(event)

    client_ua = None
    if is_whatsapp:
        ua_raw = (request.headers.get("User-Agent") or "").strip()
        client_ua = ua_raw[:512] if ua_raw else None

    meta_event_id_contact = None
    if is_whatsapp and is_lead_funnel_enabled():
        meta_event_id_contact = extract_contact_event_id_from_payload(data)
        if not meta_event_id_contact:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": (
                            "meta_event_id_contact (ou capi_event_id) é obrigatório "
                            "para whatsapp_click quando META_CAPI_LEAD_FUNNEL_ENABLED está ativo"
                        ),
                    }
                ),
                400,
            )

    token_rastreio = None
    token_valido = None
    if is_whatsapp:
        token_rastreio = normalize_tracking_token(data.get("token_rastreio"))
        if not token_rastreio:
            token_rastreio = extract_tracking_token_from_text(
                data.get("destination_url") or data.get("url")
            )
        token_valido = is_tracking_token_valid(token_rastreio)

    incoming_phone = _normalize_phone(data.get("phone") or data.get("telefone"))
    phone = None if token_rastreio else incoming_phone
    status = _clip(data.get("status"), 50)
    if is_whatsapp:
        status = status or "pendente_whatsapp"
    elif not status or status == "pendente_whatsapp":
        status = ""

    lead = Lead(
        dedup_key=dedup_key,
        ip_address=ip_address,
        event=event,
        url=_clip(data.get("url") or data.get("destination_url"), 10_000),
        referrer=_clip(data.get("referrer"), 10_000),
        utm_source=_clip(data.get("utm_source"), 100),
        utm_medium=_clip(data.get("utm_medium"), 100),
        utm_campaign=_clip(data.get("utm_campaign"), 100),
        utm_content=_clip(data.get("utm_content"), 100),
        utm_term=_clip(data.get("utm_term"), 100),
        src=_clip(data.get("src"), 100),
        sck=_clip(data.get("sck"), 200),
        phone=phone,
        token_rastreio=token_rastreio,
        token_valido=token_valido,
        status=status,
        fbclid=_extract_fbclid(data),
        fbp=_normalize_fbp(data.get("fbp")),
        meta_event_id_contact=meta_event_id_contact,
        client_user_agent=client_ua,
    )

    try:
        db.session.add(lead)
        db.session.commit()
        flush_ids: list[int] = []
        if is_lead_funnel_enabled() and is_whatsapp and meta_event_id_contact:
            repo = MetaCapiLeadOutboxRepository()
            row_c = repo.create_contact_from_lead(lead)
            if row_c:
                flush_ids.append(row_c.id)
            if lead.phone:
                if not lead.meta_event_id_lead:
                    lead.meta_event_id_lead = str(uuid.uuid4())
                    db.session.commit()
                row_l = repo.create_lead_stage_from_lead(
                    lead, event_time=datetime_now_brazil()
                )
                if row_l:
                    flush_ids.append(row_l.id)
        try_flush_pending_meta_capi_lead_entries(flush_ids)
        return (
            jsonify(
                {
                    "ok": True,
                    "id": lead.id,
                    "duplicated": False,
                    "token_valido": token_valido,
                }
            ),
            201,
        )
    except IntegrityError:
        db.session.rollback()
        existing = Lead.query.filter(Lead.dedup_key == dedup_key).first()
        return (
            jsonify(
                {
                    "ok": True,
                    "id": existing.id if existing else None,
                    "duplicated": True,
                    "token_valido": token_valido,
                }
            ),
            200,
        )


@leads_bp.route("/whatsapp-start", methods=["POST"])
def marcar_whatsapp_iniciado():
    """
    Marca lead como whatsapp_iniciado quando recebemos mensagem com código [Cod: XXXXXXX...].
    """
    data = _parse_request_payload()

    token = normalize_tracking_token(data.get("token_rastreio"))
    if not token:
        for key in ("message", "message_text", "text", "raw_message", "destination_url", "url"):
            token = extract_tracking_token_from_text(data.get(key))
            if token:
                break

    token_valido = is_tracking_token_valid(token)
    if not token:
        return jsonify({"ok": True, "found": False, "token": None, "token_valido": False}), 200
    if not token_valido:
        return jsonify({"ok": True, "found": False, "token": token, "token_valido": False}), 200

    lead = (
        Lead.query.filter(Lead.token_rastreio == token)
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .first()
    )
    if not lead:
        return jsonify({"ok": True, "found": False, "token": token, "token_valido": True}), 200

    if lead.status != "compra_realizada":
        lead.status = "whatsapp_iniciado"
        db.session.commit()

    return (
        jsonify(
            {
                "ok": True,
                "found": True,
                "token": token,
                "token_valido": True,
                "lead_id": lead.id,
                "status": lead.status,
            }
        ),
        200,
    )


def _apply_lead_status_update(lead: Lead, data: dict):
    """Mutação de status (nao_entrou_em_contato). Retorna (response, status_code)."""
    new_status = _clip(data.get("status"), 50)
    if not new_status:
        return jsonify({"ok": False, "error": "status é obrigatório"}), 400

    if new_status != "nao_entrou_em_contato":
        return jsonify({"ok": False, "error": "Status não suportado"}), 400

    if not _is_whatsapp_event(lead.event):
        return jsonify({"ok": False, "error": "Ação disponível apenas para leads WhatsApp"}), 400

    if lead.status != "pendente_whatsapp":
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Só é possível marcar a partir de Pendente WhatsApp",
                }
            ),
            400,
        )

    lead.status = new_status
    db.session.commit()
    return jsonify({"ok": True, "lead": _serialize_lead(lead)}), 200


@leads_bp.route("/by-token/status", methods=["PATCH"])
@requires_any_role("admin", "atendente", "vendedor")
def atualizar_status_lead_por_token():
    """Igual a PATCH /<id>/status, mas identifica o lead por token_rastreio no body."""
    data = _parse_request_payload()
    lead, err = _resolve_lead_by_token_payload(data)
    if err:
        return err
    return _apply_lead_status_update(lead, data)


@leads_bp.route("/<int:lead_id>/status", methods=["PATCH"])
@requires_any_role("admin", "atendente", "vendedor")
def atualizar_status_lead(lead_id: int):
    """
    Atualiza status operacional do lead (ex.: marcar como não entrou em contato).
    Transições válidas são explícitas para evitar estados inconsistentes.
    """
    data = _parse_request_payload()
    lead = db.session.get(Lead, lead_id)
    if not lead:
        return jsonify({"ok": False, "error": "Lead não encontrado"}), 404
    return _apply_lead_status_update(lead, data)


def _apply_lead_phone_update(lead: Lead, data: dict):
    """Atualiza telefone + CAPI Lead quando aplicável. Retorna (response, status_code)."""
    phone = _normalize_phone(
        data.get("phone") or data.get("telefone") or data.get("telefone_cliente")
    )
    if not phone:
        return jsonify({"ok": False, "error": "Telefone é obrigatório"}), 400

    phone_was_empty = not (lead.phone or "").strip()
    if (
        is_lead_funnel_enabled()
        and _is_whatsapp_event(lead.event)
        and phone_was_empty
    ):
        if is_truthy_meta_pixel_lead(data):
            new_lead_eid = extract_lead_stage_event_id_from_payload(data)
            if not new_lead_eid:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": (
                                "meta_event_id_lead é obrigatório quando "
                                "meta_pixel_lead é verdadeiro"
                            ),
                        }
                    ),
                    400,
                )
        else:
            new_lead_eid = str(uuid.uuid4())
        lead.meta_event_id_lead = new_lead_eid

    lead.phone = phone
    if _is_whatsapp_event(lead.event):
        if lead.status != "compra_realizada":
            lead.status = "whatsapp_iniciado"
    elif lead.status == "pendente_whatsapp":
        lead.status = None

    db.session.commit()

    flush_ids: list[int] = []
    if (
        is_lead_funnel_enabled()
        and _is_whatsapp_event(lead.event)
        and phone_was_empty
    ):
        repo = MetaCapiLeadOutboxRepository()
        row_l = repo.create_lead_stage_from_lead(lead, event_time=datetime_now_brazil())
        if row_l:
            flush_ids.append(row_l.id)
        try_flush_pending_meta_capi_lead_entries(flush_ids)

    return jsonify({"ok": True, "lead": _serialize_lead(lead)}), 200


@leads_bp.route("/by-token/phone", methods=["PATCH"])
@requires_any_role("admin", "atendente", "vendedor")
def atualizar_telefone_lead_por_token():
    """Igual a PATCH /<id>/phone, mas identifica o lead por token_rastreio no body."""
    data = _parse_request_payload()
    lead, err = _resolve_lead_by_token_payload(data)
    if err:
        return err
    return _apply_lead_phone_update(lead, data)


@leads_bp.route("/<int:lead_id>/phone", methods=["PATCH"])
@requires_any_role("admin", "atendente", "vendedor")
def atualizar_telefone_lead(lead_id: int):
    """Atualiza o telefone de um lead e destrava status pendente de WhatsApp."""
    data = _parse_request_payload()
    lead = db.session.get(Lead, lead_id)
    if not lead:
        return jsonify({"ok": False, "error": "Lead não encontrado"}), 404
    return _apply_lead_phone_update(lead, data)


@leads_bp.route("", methods=["GET"])
@requires_any_role("admin", "vendedor")
def listar_leads():
    """Lista leads com paginação e filtros opcionais."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)

    query = Lead.query.order_by(Lead.created_at.desc())

    events_param = (request.args.get("events") or "").strip()
    event_param = request.args.get("event")

    if events_param:
        parts = [e.strip() for e in events_param.split(",") if e.strip()]
        if parts:
            query = query.filter(Lead.event.in_(parts))
    elif event_param == "all":
        pass
    elif event_param:
        query = query.filter(Lead.event == event_param)
    else:
        query = query.filter(Lead.event.in_(DEFAULT_KEY_EVENTS))

    utm_source = request.args.get("utm_source")
    if utm_source:
        query = query.filter(Lead.utm_source == utm_source)

    utm_campaign = request.args.get("utm_campaign")
    if utm_campaign:
        query = query.filter(Lead.utm_campaign == utm_campaign)

    token_q = request.args.get("token_rastreio")
    if token_q:
        token_norm = normalize_tracking_token(token_q)
        if token_norm:
            query = query.filter(Lead.token_rastreio == token_norm)

    date_from = request.args.get("date_from")
    if date_from:
        try:
            query = query.filter(Lead.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass

    date_to = request.args.get("date_to")
    if date_to:
        try:
            query = query.filter(Lead.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Busca em lote os valores dos pedidos vinculados (evita N+1)
    pedido_valores: dict = {}
    pedido_ids = [lead.pedido_id for lead in pagination.items if lead.pedido_id]
    if pedido_ids:
        from app.models.pedido import Pedido

        pedidos = Pedido.query.filter(Pedido.id.in_(pedido_ids)).with_entities(
            Pedido.id, Pedido.valor
        ).all()
        pedido_valores = {p.id: p.valor for p in pedidos}

    return jsonify(
        {
            "leads": [_serialize_lead(lead, pedido_valores) for lead in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
        }
    )
