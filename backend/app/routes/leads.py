# -*- coding: utf-8 -*-
"""
Rotas de Leads UTM — captura cliques da landing page e lista para o admin.
"""
import hashlib
import json
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from app import db
from app.middleware import requires_any_role
from app.models.lead import Lead
from app.models.lead_touchpoint import LeadTouchpoint, derive_is_paid
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

# Evento padrão quando nenhum filtro de evento é enviado pelo frontend
DEFAULT_KEY_EVENTS = ("whatsapp_click",)
WHATSAPP_EVENT = "whatsapp_click"

# Transições de status permitidas para mutação operacional (PATCH individual e bulk).
# Chave = status atual; valor = conjunto de status finais permitidos.
ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pendente_whatsapp": {"nao_entrou_em_contato", "descarte"},
    "nao_entrou_em_contato": {"descarte", "pendente_whatsapp"},
    "descarte": {"pendente_whatsapp"},
    # whatsapp_iniciado é terminal para mutações manuais — uma vez que o evento Meta
    # `Lead` foi disparado, não permitimos voltar pra descarte/nao_entrou. Único caminho
    # adiante é `compra_realizada` (via fluxo automático de pedido). Isso evita o ciclo
    # "Meta otimiza pra perfil ruim → LeadDisqualified corrige tarde".
}
BULK_TARGET_STATUSES = {"descarte", "nao_entrou_em_contato", "pendente_whatsapp"}
BULK_MAX_IDS = 500

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


def _build_touchpoint_fields(data: dict, ip_address: str | None, user_agent: str | None) -> dict:
    """Extrai a UTM bag do payload + calcula is_paid pra inserção em lead_touchpoints."""
    fbclid = _extract_fbclid(data)
    utm_id = _clip(data.get("utm_id"), 100)
    utm_medium = _clip(data.get("utm_medium"), 100)
    return {
        "utm_source": _clip(data.get("utm_source"), 100),
        "utm_medium": utm_medium,
        "utm_campaign": _clip(data.get("utm_campaign"), 100),
        "utm_content": _clip(data.get("utm_content"), 100),
        "utm_term": _clip(data.get("utm_term"), 100),
        "utm_id": utm_id,
        "src": _clip(data.get("src"), 100),
        "placement": _clip(data.get("placement"), 100),
        "sck": _clip(data.get("sck"), 200),
        "fbclid": fbclid,
        "fbp": _normalize_fbp(data.get("fbp")),
        "referrer": _clip(data.get("referrer"), 10_000),
        "url": _clip(data.get("url") or data.get("destination_url"), 10_000),
        "ip_address": ip_address,
        "client_user_agent": user_agent,
        "is_paid": derive_is_paid(utm_medium=utm_medium, fbclid=fbclid, utm_id=utm_id),
    }


def _record_touchpoint(lead: Lead, tp_fields: dict) -> LeadTouchpoint:
    """
    Insere touchpoint vinculado ao lead. Se for pago (is_paid=True), promove o
    touchpoint para last_touch e copia utm_*/fbclid/fbp pro lead. Toques diretos
    apenas viram histórico (last non-direct).
    """
    tp = LeadTouchpoint(lead_id=lead.id, **tp_fields)
    db.session.add(tp)
    db.session.flush()
    if tp.is_paid:
        lead.utm_source = tp.utm_source
        lead.utm_medium = tp.utm_medium
        lead.utm_campaign = tp.utm_campaign
        lead.utm_content = tp.utm_content
        lead.utm_term = tp.utm_term
        if tp.fbclid:
            lead.fbclid = tp.fbclid
        if tp.fbp:
            lead.fbp = tp.fbp
        lead.last_touch_id = tp.id
    return tp


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
        pedido_valores.get(lead.pedido_id) if (pedido_valores and lead.pedido_id) else None
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

    ua_raw = (request.headers.get("User-Agent") or "").strip()
    full_ua = ua_raw[:512] if ua_raw else None
    client_ua = full_ua if is_whatsapp else None

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

    tp_fields = _build_touchpoint_fields(data, ip_address, full_ua)

    existing = Lead.query.filter(Lead.dedup_key == dedup_key).first()
    if existing is not None:
        _record_touchpoint(existing, tp_fields)
        db.session.commit()
        return (
            jsonify(
                {
                    "ok": True,
                    "id": existing.id,
                    "duplicated": True,
                    "token_valido": token_valido,
                }
            ),
            200,
        )

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
        db.session.flush()
        tp = LeadTouchpoint(lead_id=lead.id, **tp_fields)
        db.session.add(tp)
        db.session.flush()
        lead.first_touch_id = tp.id
        lead.last_touch_id = tp.id
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
                row_l = repo.create_lead_stage_from_lead(lead, event_time=datetime_now_brazil())
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
        # Race: outro request inseriu o mesmo dedup_key entre nosso SELECT e INSERT.
        db.session.rollback()
        existing = Lead.query.filter(Lead.dedup_key == dedup_key).first()
        if existing is not None:
            _record_touchpoint(existing, tp_fields)
            db.session.commit()
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
    """Mutação operacional de status. Aceita transições em ALLOWED_STATUS_TRANSITIONS."""
    new_status = _clip(data.get("status"), 50)
    if not new_status:
        return jsonify({"ok": False, "error": "status é obrigatório"}), 400

    if new_status not in BULK_TARGET_STATUSES:
        return jsonify({"ok": False, "error": "Status não suportado"}), 400

    if not _is_whatsapp_event(lead.event):
        return jsonify({"ok": False, "error": "Ação disponível apenas para leads WhatsApp"}), 400

    allowed = ALLOWED_STATUS_TRANSITIONS.get(lead.status or "", set())
    if new_status not in allowed:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": (
                        f"Transição não permitida: {lead.status or '(vazio)'} → {new_status}"
                    ),
                }
            ),
            400,
        )

    fire_disqualified = (
        new_status == "descarte"
        and is_lead_funnel_enabled()
        and lead.status != "descarte"
    )
    lead.status = new_status
    db.session.commit()

    if fire_disqualified:
        repo = MetaCapiLeadOutboxRepository()
        row = repo.create_disqualified_from_lead(lead, event_time=datetime_now_brazil())
        if row:
            try_flush_pending_meta_capi_lead_entries([row.id])

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
    if is_lead_funnel_enabled() and _is_whatsapp_event(lead.event) and phone_was_empty:
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
    if is_lead_funnel_enabled() and _is_whatsapp_event(lead.event) and phone_was_empty:
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


@leads_bp.route("/<int:lead_id>/touchpoints", methods=["GET"])
@requires_any_role("admin", "vendedor")
def listar_touchpoints(lead_id: int):
    """Histórico completo de toques de um lead, do mais antigo ao mais recente."""
    lead = db.session.get(Lead, lead_id)
    if not lead:
        return jsonify({"ok": False, "error": "Lead não encontrado"}), 404
    touchpoints = (
        LeadTouchpoint.query.filter(LeadTouchpoint.lead_id == lead_id)
        .order_by(LeadTouchpoint.created_at.asc(), LeadTouchpoint.id.asc())
        .all()
    )
    return (
        jsonify(
            {
                "ok": True,
                "lead_id": lead_id,
                "first_touch_id": lead.first_touch_id,
                "last_touch_id": lead.last_touch_id,
                "touchpoints": [tp.to_dict() for tp in touchpoints],
            }
        ),
        200,
    )


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

    status_q = request.args.get("status")
    if status_q:
        query = query.filter(Lead.status == status_q)

    token_q = request.args.get("token_rastreio")
    if token_q:
        token_norm = normalize_tracking_token(token_q)
        if token_norm:
            query = query.filter(Lead.token_rastreio == token_norm)

    period = (request.args.get("period") or "").strip().lower()
    if period in {"today", "14d"}:
        # Backend resolve a janela em BRT — única fonte de verdade de fuso.
        # Usar somente period; ignorar date_from/date_to nesse caso.
        now_brt = datetime_now_brazil()
        if period == "today":
            start = now_brt.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # "14d"
            start = now_brt - timedelta(days=14)
        query = query.filter(Lead.created_at >= start)
    elif period == "all":
        # Sem janela temporal.
        pass
    else:
        # period == "custom" (ou omitido): respeita date_from/date_to atuais.
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

    from sqlalchemy import func

    from app.models.pedido import Pedido

    # 1. Busca valores para leads que já têm pedido_id
    pedido_valores: dict = {}
    pedido_ids = [lead.pedido_id for lead in pagination.items if lead.pedido_id]
    if pedido_ids:
        pedidos = (
            Pedido.query.filter(Pedido.id.in_(pedido_ids))
            .with_entities(Pedido.id, Pedido.valor)
            .all()
        )
        pedido_valores = {p.id: p.valor for p in pedidos}

    # 2. Backfill preguiçoso: leads compra_realizada sem pedido_id → busca por telefone
    unlinked = [
        lead
        for lead in pagination.items
        if not lead.pedido_id and lead.status == "compra_realizada" and lead.phone
    ]
    if unlinked:
        phones = list({lead.phone for lead in unlinked})
        norm_expr = func.regexp_replace(Pedido.telefone_cliente, "[^0-9]", "", "g")
        matched = (
            Pedido.query.filter(
                norm_expr.in_(phones),
                Pedido.deleted_at.is_(None),
                Pedido.status != "cancelado",
            )
            .with_entities(Pedido.id, norm_expr.label("phone_norm"), Pedido.valor)
            .order_by(Pedido.id.desc())
            .all()
        )
        # phone → pedido mais recente
        phone_to_pedido: dict = {}
        for p in matched:
            if p.phone_norm not in phone_to_pedido:
                phone_to_pedido[p.phone_norm] = (p.id, p.valor)

        backfilled = False
        for lead in unlinked:
            entry = phone_to_pedido.get(lead.phone)
            if entry:
                pid, pval = entry
                lead.pedido_id = pid
                pedido_valores[pid] = pval
                backfilled = True
        if backfilled:
            db.session.commit()

    return jsonify(
        {
            "leads": [_serialize_lead(lead, pedido_valores) for lead in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
        }
    )


def _aggregate_lead_stats(start_dt: datetime) -> dict:
    """Conta pendentes/com_telefone/compras/total a partir de `start_dt`."""
    is_pendente = case((Lead.status == "pendente_whatsapp", 1), else_=0)
    is_pendente_com_phone = case(
        (
            (Lead.status == "pendente_whatsapp") & Lead.phone.isnot(None) & (Lead.phone != ""),
            1,
        ),
        else_=0,
    )
    is_compra = case((Lead.status == "compra_realizada", 1), else_=0)

    row = (
        db.session.query(
            func.coalesce(func.sum(is_pendente), 0),
            func.coalesce(func.sum(is_pendente_com_phone), 0),
            func.coalesce(func.sum(is_compra), 0),
            func.count(Lead.id),
        )
        .filter(Lead.event.in_(DEFAULT_KEY_EVENTS), Lead.created_at >= start_dt)
        .one()
    )
    pendentes, com_telefone, compras, total = row
    return {
        "pendentes": int(pendentes or 0),
        "com_telefone": int(com_telefone or 0),
        "compras": int(compras or 0),
        "total": int(total or 0),
    }


@leads_bp.route("/stats", methods=["GET"])
@requires_any_role("admin", "vendedor")
def leads_stats():
    """
    Contadores agregados por janela fixa (today + last_14d).
    Não acompanha o filtro de período da listagem — visão gerencial constante.
    """
    now_brt = datetime_now_brazil()
    today_start = now_brt.replace(hour=0, minute=0, second=0, microsecond=0)
    last_14d_start = now_brt - timedelta(days=14)

    return jsonify(
        {
            "ok": True,
            "today": _aggregate_lead_stats(today_start),
            "last_14d": _aggregate_lead_stats(last_14d_start),
        }
    )


@leads_bp.route("/bulk/status", methods=["PATCH"])
@requires_any_role("admin", "atendente", "vendedor")
def atualizar_status_leads_em_lote():
    """
    Atualiza status de múltiplos leads em uma transação.
    Body: {"ids": [...], "status": "<target>"}
    Pula silenciosamente leads sem transição válida e retorna skipped_ids.
    """
    data = _parse_request_payload()
    ids_raw = data.get("ids")
    if not isinstance(ids_raw, list) or not ids_raw:
        return jsonify({"ok": False, "error": "ids é obrigatório (lista não vazia)"}), 400
    if len(ids_raw) > BULK_MAX_IDS:
        return jsonify({"ok": False, "error": f"Máximo de {BULK_MAX_IDS} ids por chamada"}), 400

    ids: list[int] = []
    for v in ids_raw:
        try:
            ids.append(int(v))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "ids deve conter apenas inteiros"}), 400

    new_status = _clip(data.get("status"), 50)
    if not new_status or new_status not in BULK_TARGET_STATUSES:
        return jsonify({"ok": False, "error": "status inválido para bulk update"}), 400

    leads = Lead.query.filter(Lead.id.in_(ids)).all()
    found_ids = {lead.id for lead in leads}

    updated = 0
    skipped_ids: list[int] = [i for i in ids if i not in found_ids]
    transitioned_to_descarte: list[Lead] = []

    for lead in leads:
        if not _is_whatsapp_event(lead.event):
            skipped_ids.append(lead.id)
            continue
        allowed = ALLOWED_STATUS_TRANSITIONS.get(lead.status or "", set())
        if new_status not in allowed:
            skipped_ids.append(lead.id)
            continue
        if new_status == "descarte" and lead.status != "descarte":
            transitioned_to_descarte.append(lead)
        lead.status = new_status
        updated += 1

    db.session.commit()

    if transitioned_to_descarte and is_lead_funnel_enabled():
        repo = MetaCapiLeadOutboxRepository()
        flush_ids: list[int] = []
        now_brt = datetime_now_brazil()
        for lead in transitioned_to_descarte:
            row = repo.create_disqualified_from_lead(lead, event_time=now_brt)
            if row:
                flush_ids.append(row.id)
        if flush_ids:
            try_flush_pending_meta_capi_lead_entries(flush_ids)

    return jsonify(
        {
            "ok": True,
            "updated": updated,
            "skipped": len(skipped_ids),
            "skipped_ids": skipped_ids,
        }
    )


@leads_bp.route("/bulk/disqualify", methods=["PATCH"])
@requires_any_role("admin", "atendente", "vendedor")
def desqualificar_leads_em_lote():
    """
    Marca leads como `descarte` em lote, opcionalmente atualizando o telefone
    antes para enriquecer o `user_data.ph` do evento Meta `LeadDisqualified`.

    Body:
      {
        "updates": [
          {"id": 1, "phone": "62999990000"},  # phone opcional
          {"id": 2},
          {"id": 3, "phone": ""}               # vazio = não atualiza
        ]
      }

    Diferente de PATCH /<id>/phone: aqui o telefone é setado de forma silenciosa
    (não dispara evento `Lead` e não muda status para `whatsapp_iniciado`). O lead
    vai direto para `descarte` e o `LeadDisqualified` carrega o phone hash novo.
    """
    data = _parse_request_payload()
    updates_raw = data.get("updates")
    if not isinstance(updates_raw, list) or not updates_raw:
        return jsonify({"ok": False, "error": "updates é obrigatório (lista não vazia)"}), 400
    if len(updates_raw) > BULK_MAX_IDS:
        return jsonify({"ok": False, "error": f"Máximo de {BULK_MAX_IDS} updates por chamada"}), 400

    updates_by_id: dict[int, dict] = {}
    for u in updates_raw:
        if not isinstance(u, dict):
            return jsonify({"ok": False, "error": "updates deve conter objetos"}), 400
        try:
            uid = int(u.get("id"))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "cada update precisa de id inteiro"}), 400
        updates_by_id[uid] = u

    ids = list(updates_by_id.keys())
    leads = Lead.query.filter(Lead.id.in_(ids)).all()
    found_ids = {lead.id for lead in leads}

    updated = 0
    skipped_ids: list[int] = [i for i in ids if i not in found_ids]
    transitioned: list[Lead] = []

    for lead in leads:
        if not _is_whatsapp_event(lead.event):
            skipped_ids.append(lead.id)
            continue
        allowed = ALLOWED_STATUS_TRANSITIONS.get(lead.status or "", set())
        if "descarte" not in allowed:
            skipped_ids.append(lead.id)
            continue

        phone_raw = updates_by_id[lead.id].get("phone")
        if phone_raw is not None and str(phone_raw).strip():
            phone_norm = _normalize_phone(phone_raw)
            if not phone_norm:
                # phone fornecido mas inválido: pula o lead inteiro pra não desqualificar
                # com phone errado e nem desqualificar sem o dado que o operador quis dar
                skipped_ids.append(lead.id)
                continue
            lead.phone = phone_norm

        lead.status = "descarte"
        transitioned.append(lead)
        updated += 1

    db.session.commit()

    if transitioned and is_lead_funnel_enabled():
        repo = MetaCapiLeadOutboxRepository()
        flush_ids: list[int] = []
        now_brt = datetime_now_brazil()
        for lead in transitioned:
            row = repo.create_disqualified_from_lead(lead, event_time=now_brt)
            if row:
                flush_ids.append(row.id)
        if flush_ids:
            try_flush_pending_meta_capi_lead_entries(flush_ids)

    return jsonify(
        {
            "ok": True,
            "updated": updated,
            "skipped": len(skipped_ids),
            "skipped_ids": skipped_ids,
        }
    )
