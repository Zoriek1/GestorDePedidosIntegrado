# -*- coding: utf-8 -*-
"""
Rotas de Leads UTM — captura cliques da landing page e lista para o admin.
"""
import hashlib
import json
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db
from app.middleware import requires_any_role
from app.models.lead import Lead
from app.utils.tracking_token import (
    extract_tracking_token_from_text,
    is_tracking_token_valid,
    normalize_tracking_token,
)

leads_bp = Blueprint("leads", __name__, url_prefix="/api/leads")

# Eventos considerados “principais” na listagem quando não há filtro explícito
DEFAULT_KEY_EVENTS = ("modal_open", "whatsapp_click", "site_click")

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
    token_rastreio = normalize_tracking_token(data.get("token_rastreio"))
    if not token_rastreio:
        token_rastreio = extract_tracking_token_from_text(data.get("destination_url") or data.get("url"))
    token_valido = is_tracking_token_valid(token_rastreio)
    incoming_phone = _normalize_phone(data.get("phone") or data.get("telefone"))
    phone = None if token_rastreio else incoming_phone
    status = _clip(data.get("status"), 50) or "pendente_whatsapp"

    lead = Lead(
        dedup_key=dedup_key,
        ip_address=ip_address,
        event=_clip(data.get("event"), 50),
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
    )

    try:
        db.session.add(lead)
        db.session.commit()
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

    lead = Lead.query.filter(Lead.token_rastreio == token).order_by(Lead.created_at.desc()).first()
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


@leads_bp.route("", methods=["GET"])
@requires_any_role("admin")
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

    return jsonify(
        {
            "leads": [lead.to_dict() for lead in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
        }
    )
