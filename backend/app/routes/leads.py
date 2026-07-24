# -*- coding: utf-8 -*-
"""
Rotas de Leads UTM — captura cliques da landing page e lista para o admin.
"""
import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta
from urllib.parse import unquote

from flask import Blueprint, g, jsonify, request
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from app import db
from app.middleware import requires_any_role
from app.models.lead import Lead
from app.models.lead_touchpoint import LeadTouchpoint, derive_is_paid
from app.models.pedido import TIMEZONE_BRASIL, datetime_now_brazil
from app.repositories.meta_capi_lead_outbox_repository import MetaCapiLeadOutboxRepository
from app.utils.meta_capi_lead_helper import (
    extract_contact_event_id_from_payload,
    extract_lead_stage_event_id_from_payload,
    is_lead_funnel_enabled,
    is_truthy_meta_pixel_lead,
)
from app.utils.tracking_token import (
    extract_tracking_token_from_text,
    is_tracking_token_valid,
    normalize_tracking_token,
)

leads_bp = Blueprint("leads", __name__, url_prefix="/api/leads")
logger = logging.getLogger(__name__)

# Endpoints da landing page: não têm sessão nem tenant resolvido e alimentam a
# captação da loja 1 (`resolve_public_store_id` devolve sempre a default).
# Ficam de fora do guard, senão a captação pública morreria junto.
PUBLIC_ENDPOINTS = frozenset({"leads.criar_lead", "leads.marcar_whatsapp_iniciado"})


@leads_bp.before_request
def _require_leads_enabled():
    """Bloqueia o módulo de Leads em lojas que não o têm habilitado.

    O módulo é opt-in por loja (`stores.leads_enabled`) enquanto a captação
    pública não souber mapear domínio→loja: hoje todo lead público cai na loja
    default, então liberar Leads para um segundo tenant misturaria dados.

    Preflight de CORS passa direto; o browser não manda credenciais no OPTIONS.
    """
    if request.method == "OPTIONS" or request.endpoint in PUBLIC_ENDPOINTS:
        return None

    store = getattr(g, "current_store", None)

    # Fallback: se prime_request_tenant não resolveu a loja (ex: exceção
    # silenciada no try/except), resolve aqui a partir do JWT para que o
    # guard funcione mesmo quando o middleware de tenant falha.
    if store is None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            try:
                from app.services.auth_context import load_request_identity
                from app.services.auth_service import decode_token, extract_bearer_token

                token = extract_bearer_token(auth_header)
                payload = decode_token(token) if token else None
                if payload:
                    current_user, error = load_request_identity(payload)
                    if not error:
                        store = getattr(g, "current_store", None)
            except Exception:
                pass

    if store is None:
        # Sem loja resolvida o decorator de papel da rota produz o erro correto
        # (401/403); não é papel deste guard autenticar.
        return None

    if not getattr(store, "leads_enabled", False):
        return jsonify({"success": False, "error": "Módulo de Leads indisponível"}), 403
    return None

# Evento padrão quando nenhum filtro de evento é enviado pelo frontend
DEFAULT_KEY_EVENTS = ("whatsapp_click",)
WHATSAPP_EVENT = "whatsapp_click"

# Transições de status permitidas para mutação operacional (PATCH individual e bulk).
# Chave = status atual; valor = conjunto de status finais permitidos.
#
# Modelo: `pendente_whatsapp` (sem telefone, vem do anúncio) → captura do telefone
# transiciona para `lead_pendente` (tem telefone, aguardando triagem) → confirma
# (whatsapp_iniciado) ou descarta (descarte). Confirmar/desqualificar EXIGE telefone
# — validado em `_apply_lead_status_update`.
#
# `pendente_whatsapp → descarte` continua permitido apenas pelo bulk dialog (que
# enriquece telefone no mesmo request). Sem telefone na linha, o backend rejeita.
ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pendente_whatsapp": {"nao_entrou_em_contato", "lead_pendente", "descarte"},
    "lead_pendente": {"whatsapp_iniciado", "descarte", "pendente_whatsapp"},
    "nao_entrou_em_contato": {"descarte", "pendente_whatsapp"},
    "descarte": {"lead_pendente", "pendente_whatsapp"},
    # whatsapp_iniciado é terminal para mutações manuais — uma vez que o evento Meta
    # `Lead` foi disparado, não permitimos voltar pra descarte/nao_entrou. Único caminho
    # adiante é `compra_realizada` (via fluxo automático de pedido).
}
BULK_TARGET_STATUSES = {
    "descarte",
    "nao_entrou_em_contato",
    "pendente_whatsapp",
    "lead_pendente",
    "whatsapp_iniciado",
}
# Targets que exigem telefone preenchido no lead (regra dura).
STATUSES_REQUIRING_PHONE = {"whatsapp_iniciado", "descarte"}
BULK_MAX_IDS = 500

# Subestados operacionais do lead confirmado (`status='whatsapp_iniciado'`).
# Etiqueta marcada pelo operador — NÃO dispara evento Meta nem mexe nas stats.
SITUACAO_VALUES = {"aguardando_resposta", "orcamento_enviado", "sem_resposta"}
DEFAULT_SITUACAO = "aguardando_resposta"

# Status considerados "ocultos" para o operador: leads que pararam de gerar valor
# (descarte explícito ou ausência de retorno do cliente). Filtrados por padrão na
# listagem (`hidden=exclude`) para não inflar a paginação. Ver Change 1 do plano.
HIDDEN_STATUSES = ("descarte", "nao_entrou_em_contato")
RECENT_WHATSAPP_TOKEN_MATCH_LIMIT = 5

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
    "gclid",
    "gbraid",
    "wbraid",
    "ga_client_id",
    "ga_session_id",
    "cta_location",
    "product_id",
    "product_name",
)


def _parse_brt_day_start(value: str) -> datetime | None:
    """Converte 'YYYY-MM-DD' (ou ISO completo) em datetime tz-aware no início do dia BRT."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # Date-only ou ISO sem fuso: tratar como BRT na meia-noite.
        parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=TIMEZONE_BRASIL)
    return parsed


def _parse_brt_day_end(value: str) -> datetime | None:
    """Converte 'YYYY-MM-DD' (ou ISO completo) em datetime tz-aware no fim do dia BRT."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # Date-only: estender para 23:59:59.999999 BRT para incluir o dia inteiro.
        parsed = parsed.replace(
            hour=23, minute=59, second=59, microsecond=999999, tzinfo=TIMEZONE_BRASIL
        )
    return parsed


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


def _parse_tracking_datetime(value: object) -> datetime | None:
    """Aceita epoch (segundos/milisegundos) ou ISO-8601 enviado pelo navegador."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)) or str(value).strip().isdigit():
            raw = float(value)
            if raw > 10_000_000_000:
                raw /= 1000
            return datetime.fromtimestamp(raw, tz=TIMEZONE_BRASIL)
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=TIMEZONE_BRASIL)
        return parsed.astimezone(TIMEZONE_BRASIL)
    except (TypeError, ValueError, OSError):
        return None


def _is_whatsapp_event(event: str | None) -> bool:
    return (event or "").strip().lower() == WHATSAPP_EVENT


def _build_touchpoint_fields(data: dict, ip_address: str | None, user_agent: str | None) -> dict:
    """Extrai a UTM bag do payload + calcula is_paid pra inserção em lead_touchpoints."""
    fbclid = _extract_fbclid(data)
    utm_id = _clip(data.get("utm_id"), 100)
    utm_medium = _clip(data.get("utm_medium"), 100)
    gclid = _clip(data.get("gclid"), 255)
    gbraid = _clip(data.get("gbraid"), 255)
    wbraid = _clip(data.get("wbraid"), 255)
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
        "gclid": gclid,
        "gbraid": gbraid,
        "wbraid": wbraid,
        "ga_client_id": _clip(data.get("ga_client_id") or data.get("client_id"), 255),
        "ga_session_id": _clip(data.get("ga_session_id") or data.get("session_id"), 100),
        "ga_session_started_at": _parse_tracking_datetime(data.get("ga_session_started_at")),
        "referrer": _clip(data.get("referrer"), 10_000),
        "url": _clip(data.get("url") or data.get("destination_url"), 10_000),
        # Camada de sessão da LP (diagnóstico de perda de UTM). NÃO entram em
        # ALLOWED_FIELDS de propósito: aquilo alimenta o dedup_key e estes campos
        # variam por sessão, fragmentariam a deduplicação.
        "first_landing_url": _clip(data.get("first_landing_url"), 10_000),
        "session_referrer": _clip(data.get("session_referrer"), 10_000),
        "cta_location": _clip(data.get("cta_location") or data.get("placement"), 100),
        "product_id": _clip(data.get("product_id"), 100),
        "product_name": _clip(data.get("product_name"), 255),
        "ip_address": ip_address,
        "client_user_agent": user_agent,
        "is_paid": derive_is_paid(
            utm_medium=utm_medium,
            fbclid=fbclid,
            utm_id=utm_id,
            gclid=gclid,
            gbraid=gbraid,
            wbraid=wbraid,
        ),
    }


def _record_touchpoint(lead: Lead, tp_fields: dict) -> LeadTouchpoint:
    """
    Insere touchpoint vinculado ao lead. Se for pago (is_paid=True), promove o
    touchpoint para last_touch e copia utm_*/fbclid/fbp pro lead. Toques diretos
    apenas viram histórico (last non-direct).
    """
    tp = LeadTouchpoint(
        lead_id=lead.id,
        store_ref_id=lead.store_ref_id,
        **tp_fields,
    )
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
        lead.gclid = tp.gclid
        lead.gbraid = tp.gbraid
        lead.wbraid = tp.wbraid
        if tp.ga_client_id:
            lead.ga_client_id = tp.ga_client_id
        if tp.ga_session_id:
            lead.ga_session_id = tp.ga_session_id
        if tp.ga_session_started_at:
            lead.ga_session_started_at = tp.ga_session_started_at
        if tp.first_landing_url:
            lead.first_landing_url = tp.first_landing_url
        if tp.session_referrer:
            lead.session_referrer = tp.session_referrer
        if tp.cta_location:
            lead.cta_location = tp.cta_location
        if tp.product_id:
            lead.product_id = tp.product_id
        if tp.product_name:
            lead.product_name = tp.product_name
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


def _iter_payload_pairs(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key), child
            yield from _iter_payload_pairs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_payload_pairs(child)


def _extract_whatsapp_message_text(data: dict) -> str:
    text_keys = {
        "message",
        "message_text",
        "text",
        "raw_message",
        "body",
        "content",
        "conversation",
        "caption",
    }
    parts: list[str] = []
    for key, value in _iter_payload_pairs(data):
        if key.lower() in text_keys and isinstance(value, (str, int, float)):
            text = str(value).strip()
            if text:
                parts.append(text)
    return "\n".join(parts)


def _phone_from_whatsapp_jid(value: object) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if raw.lower().endswith("@lid"):
        return None
    phone = _normalize_phone(raw)
    return phone if phone and len(phone) >= 10 else None


def _extract_whatsapp_phone(data: dict) -> str | None:
    key_data = data.get("data", {}).get("key", {}) if isinstance(data.get("data"), dict) else {}
    remote_jid = key_data.get("remoteJid") if isinstance(key_data, dict) else None
    alternate_jids = []
    if isinstance(key_data, dict):
        alternate_jids = [key_data.get("remoteJidAlt"), key_data.get("senderPn")]
    jid_candidates = (
        alternate_jids
        if str(remote_jid or "").lower().endswith("@lid")
        else [remote_jid, *alternate_jids]
    )
    for candidate in jid_candidates:
        phone = _phone_from_whatsapp_jid(candidate)
        if phone:
            return phone

    phone_keys = {
        "phone",
        "telefone",
        "telefone_cliente",
        "number",
        "remotejid",
        "remotejidalt",
        "senderpn",
        "participant",
        "sender",
        "from",
    }
    for key, value in _iter_payload_pairs(data):
        if key.lower() not in phone_keys:
            continue
        phone = _phone_from_whatsapp_jid(value)
        if phone:
            return phone
    return None


def _find_recent_valid_token_in_text(text: str) -> str | None:
    normalized_text = unquote(text or "").upper()
    if not normalized_text:
        return None

    from app.services.auth_context import resolve_public_store_id
    from app.services.tenancy import is_multi_store

    store_ref_id = resolve_public_store_id()
    query = Lead.query.execution_options(include_all_tenants=True).filter(
        Lead.token_valido.is_(True),
        Lead.token_rastreio.isnot(None),
    )
    if store_ref_id is not None:
        # Loja pública resolvida (loja default): restringe a busca ao tenant.
        query = query.filter(Lead.store_ref_id == store_ref_id)
    elif is_multi_store():
        # Multiempresa sem loja resolvida: fail-closed, não cruza tenants
        # (consistente com criar_lead/marcar_whatsapp_iniciado).
        return None
    # Single-store sem loja default (legado): comportamento global preservado.
    recent_tokens = (
        query.order_by(Lead.created_at.desc(), Lead.id.desc())
        .limit(RECENT_WHATSAPP_TOKEN_MATCH_LIMIT)
        .all()
    )
    for lead in recent_tokens:
        token = normalize_tracking_token(lead.token_rastreio)
        if token and token in normalized_text:
            return token
    return None


@leads_bp.route("", methods=["POST"])
@leads_bp.route("/", methods=["POST"])
def criar_lead():
    """Recebe dados UTM da landing page (aceita application/json e text/plain via sendBeacon)."""
    from app.services.auth_context import resolve_public_store_id

    data = _parse_request_payload()
    store_ref_id = resolve_public_store_id()
    if store_ref_id is None:
        from app.services.tenancy import is_multi_store

        if is_multi_store():
            logger.error("lead.public_store_unresolved route=create")
            return jsonify({"ok": False, "error": "Entrada publica indisponivel"}), 503

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

    # O token e a chave idempotente do funil. Repeticoes do mesmo clique/sessao
    # enriquecem o lead existente e sempre acrescentam um touchpoint.
    existing = None
    if is_whatsapp and token_valido:
        existing = (
            Lead.query.execution_options(include_all_tenants=True)
            .filter(
                Lead.store_ref_id == store_ref_id,
                Lead.token_rastreio == token_rastreio,
                Lead.status != "compra_realizada",
            )
            .order_by(Lead.created_at.desc(), Lead.id.desc())
            .first()
        )
    if existing is None:
        existing = (
            Lead.query.execution_options(include_all_tenants=True)
            .filter(
                Lead.store_ref_id == store_ref_id,
                Lead.dedup_key == dedup_key,
            )
            .first()
        )
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
        store_ref_id=store_ref_id,
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
        gclid=tp_fields["gclid"],
        gbraid=tp_fields["gbraid"],
        wbraid=tp_fields["wbraid"],
        ga_client_id=tp_fields["ga_client_id"],
        ga_session_id=tp_fields["ga_session_id"],
        ga_session_started_at=tp_fields["ga_session_started_at"],
        first_landing_url=tp_fields["first_landing_url"],
        session_referrer=tp_fields["session_referrer"],
        cta_location=tp_fields["cta_location"],
        product_id=tp_fields["product_id"],
        product_name=tp_fields["product_name"],
        meta_event_id_contact=meta_event_id_contact,
        client_user_agent=client_ua,
    )

    try:
        db.session.add(lead)
        db.session.flush()
        tp = LeadTouchpoint(
            lead_id=lead.id,
            store_ref_id=store_ref_id,
            **tp_fields,
        )
        db.session.add(tp)
        db.session.flush()
        lead.first_touch_id = tp.id
        lead.last_touch_id = tp.id
        db.session.commit()
        # Enfileira no outbox; o capi-worker envia de forma assíncrona.
        if is_lead_funnel_enabled() and is_whatsapp and meta_event_id_contact:
            # Dual-write: old Meta CAPI outbox (draining)
            repo = MetaCapiLeadOutboxRepository()
            repo.create_contact_from_lead(lead)
            if lead.phone:
                if not lead.meta_event_id_lead:
                    lead.meta_event_id_lead = str(uuid.uuid4())
                    db.session.commit()
                repo.create_lead_stage_from_lead(lead, event_time=datetime_now_brazil())
            # New unified outbox
            from app.services.events_service import EventsService
            events_svc = EventsService()
            if lead.phone:
                events_svc.enqueue_lead(lead, event_time=datetime_now_brazil())
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
        existing = (
            Lead.query.execution_options(include_all_tenants=True)
            .filter(
                Lead.store_ref_id == store_ref_id,
                Lead.dedup_key == dedup_key,
            )
            .first()
        )
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
    Promove lead para lead_pendente quando uma nova conversa do WhatsApp contém
    um dos tokens válidos recentes. O webhook nunca confirma o Lead sozinho.
    """
    from app.services.auth_context import resolve_public_store_id

    data = _parse_request_payload()
    store_ref_id = resolve_public_store_id()
    if store_ref_id is None:
        from app.services.tenancy import is_multi_store

        if is_multi_store():
            logger.error("lead.public_store_unresolved route=whatsapp-start")
            return jsonify({"ok": False, "error": "Entrada publica indisponivel"}), 503

    phone = _extract_whatsapp_phone(data)
    token = normalize_tracking_token(data.get("token_rastreio"))
    if not token:
        for key in ("message", "message_text", "text", "raw_message", "destination_url", "url"):
            token = extract_tracking_token_from_text(data.get(key))
            if token:
                break
    if not token:
        token = _find_recent_valid_token_in_text(_extract_whatsapp_message_text(data))

    token_valido = is_tracking_token_valid(token)
    if not token:
        return jsonify({"ok": True, "found": False, "token": None, "token_valido": False}), 200
    if not token_valido:
        return jsonify({"ok": True, "found": False, "token": token, "token_valido": False}), 200

    lead = (
        Lead.query.execution_options(include_all_tenants=True)
        .filter(Lead.store_ref_id == store_ref_id, Lead.token_rastreio == token)
        .order_by(Lead.created_at.desc(), Lead.id.desc())
        .first()
    )
    if not lead:
        return jsonify({"ok": True, "found": False, "token": token, "token_valido": True}), 200

    # Tabela = lei: whatsapp_iniciado só é alcançável via 1-clique do operador
    # (que dispara CAPI Lead on-event). O webhook nunca confirma sozinho —
    # promove no máximo pra `lead_pendente` (a fila de decisão) e só com telefone.
    if lead.status not in {"compra_realizada", "whatsapp_iniciado", "descarte"}:
        if not phone and not lead.phone:
            return (
                jsonify(
                    {
                        "ok": True,
                        "found": True,
                        "token": token,
                        "token_valido": True,
                        "lead_id": lead.id,
                        "status": lead.status,
                        "phone": lead.phone,
                        "missing_phone": True,
                    }
                ),
                200,
            )
        if phone:
            lead.phone = phone
        lead.status = "lead_pendente"
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
                "phone": lead.phone,
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

    # Regra dura: confirmar/desqualificar exigem telefone capturado.
    if new_status in STATUSES_REQUIRING_PHONE and not (lead.phone or "").strip():
        return jsonify({"ok": False, "error": "telefone_obrigatorio"}), 422

    old_status = lead.status
    fire_disqualified = (
        new_status == "descarte" and is_lead_funnel_enabled() and old_status != "descarte"
    )
    fire_lead_confirmed = (
        new_status == "whatsapp_iniciado"
        and is_lead_funnel_enabled()
        and old_status != "whatsapp_iniciado"
    )

    if fire_lead_confirmed and not lead.meta_event_id_lead:
        lead.meta_event_id_lead = str(uuid.uuid4())

    lead.status = new_status
    # Lead confirmado entra no funil por situação já em "aguardando_resposta"
    # (grupo "Em conversa"). Sem efeito no CAPI — situacao é etiqueta separada.
    if new_status == "whatsapp_iniciado" and not lead.situacao:
        lead.situacao = DEFAULT_SITUACAO
    db.session.commit()

    # Enfileira no outbox; o capi-worker envia de forma assíncrona.
    if fire_disqualified or fire_lead_confirmed:
        repo = MetaCapiLeadOutboxRepository()
        now_brt = datetime_now_brazil()
        if fire_lead_confirmed:
            repo.create_lead_stage_from_lead(lead, event_time=now_brt)
        if fire_disqualified:
            repo.create_disqualified_from_lead(lead, event_time=now_brt)
        from app.services.events_service import EventsService
        events_svc = EventsService()
        if fire_lead_confirmed:
            events_svc.enqueue_lead(lead, event_time=now_brt)
        if fire_disqualified:
            events_svc.enqueue_disqualified(lead, event_time=now_brt)

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
    lead = Lead.query.filter(Lead.id == lead_id).first()
    if not lead:
        return jsonify({"ok": False, "error": "Lead não encontrado"}), 404
    return _apply_lead_status_update(lead, data)


def _apply_lead_phone_update(lead: Lead, data: dict):
    """Captura/atualiza telefone do lead.

    Captura no 1º contato: lead em `pendente_whatsapp` (vindo do anúncio sem
    telefone) ganha o número e transiciona para `lead_pendente`. Nada de evento
    Meta nesta rota — telefone é dado de match, não gatilho. O evento `Lead`
    (positivo) só dispara quando o operador confirma (whatsapp_iniciado).
    """
    phone = _normalize_phone(
        data.get("phone") or data.get("telefone") or data.get("telefone_cliente")
    )
    if not phone:
        return jsonify({"ok": False, "error": "Telefone é obrigatório"}), 400

    # Compat: payloads antigos com meta_pixel_lead truthy ainda precisam de
    # event_id (garantia de dedup browser↔servidor caso o pixel tenha sido
    # disparado no front pra este lead).
    if is_lead_funnel_enabled() and _is_whatsapp_event(lead.event):
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
            lead.meta_event_id_lead = new_lead_eid

    lead.phone = phone
    if _is_whatsapp_event(lead.event):
        # Captura de telefone promove o lead pra fila de decisão (`lead_pendente`)
        # a partir de qualquer estágio "sem decisão tomada":
        #   - pendente_whatsapp (triagem)
        #   - nao_entrou_em_contato (Trilha A reabriu — agora temos número)
        #   - descarte (reabertura explícita; ver item 4 do checklist do owner)
        # whatsapp_iniciado e compra_realizada mantêm status (telefone corrigido).
        if lead.status in {"pendente_whatsapp", "nao_entrou_em_contato", "descarte"}:
            lead.status = "lead_pendente"
    elif lead.status == "pendente_whatsapp":
        lead.status = None

    db.session.commit()
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
    lead = Lead.query.filter(Lead.id == lead_id).first()
    if not lead:
        return jsonify({"ok": False, "error": "Lead não encontrado"}), 404
    return _apply_lead_phone_update(lead, data)


def _apply_lead_situacao_update(lead: Lead, data: dict):
    """Marca o subestado operacional (`situacao`) de um lead confirmado.

    `situacao` refina o lead confirmado (`status='whatsapp_iniciado'`) em
    `aguardando_resposta | orcamento_enviado | sem_resposta`. É etiqueta pura:
    não muda `status`, não dispara evento Meta, não enfileira no outbox.
    """
    if lead.status != "whatsapp_iniciado":
        return jsonify({"ok": False, "error": "lead_nao_confirmado"}), 422

    new_situacao = _clip(data.get("situacao"), 30)
    if new_situacao not in SITUACAO_VALUES:
        return jsonify({"ok": False, "error": "situacao inválida"}), 400

    lead.situacao = new_situacao
    db.session.commit()
    return jsonify({"ok": True, "lead": _serialize_lead(lead)}), 200


@leads_bp.route("/by-token/situacao", methods=["PATCH"])
@requires_any_role("admin", "atendente", "vendedor")
def atualizar_situacao_lead_por_token():
    """Igual a PATCH /<id>/situacao, mas identifica o lead por token_rastreio no body."""
    data = _parse_request_payload()
    lead, err = _resolve_lead_by_token_payload(data)
    if err:
        return err
    return _apply_lead_situacao_update(lead, data)


@leads_bp.route("/<int:lead_id>/situacao", methods=["PATCH"])
@requires_any_role("admin", "atendente", "vendedor")
def atualizar_situacao_lead(lead_id: int):
    """Marca a situação operacional de um lead confirmado (etiqueta de funil)."""
    data = _parse_request_payload()
    lead = Lead.query.filter(Lead.id == lead_id).first()
    if not lead:
        return jsonify({"ok": False, "error": "Lead não encontrado"}), 404
    return _apply_lead_situacao_update(lead, data)


@leads_bp.route("/<int:lead_id>/followup", methods=["PATCH"])
@requires_any_role("admin", "atendente", "vendedor")
def marcar_followup_lead(lead_id: int):
    """
    Marca/desmarca followup feito em um lead.

    Body: {"action": "mark" | "undo"}  (default: "mark")

    - mark: registra followup_feito_em=now, followup_por=current_user.id
    - undo: limpa ambos os campos (NULL)

    Sem validação de status: o operador é livre pra rastrear followup em
    qualquer lead — o filtro de "pending followup" é quem decide quais
    contar como atrasados.
    """
    data = _parse_request_payload()
    action = _clip(data.get("action"), 10) or "mark"
    if action not in {"mark", "undo"}:
        return jsonify({"ok": False, "error": "action deve ser 'mark' ou 'undo'"}), 400

    lead = Lead.query.filter(Lead.id == lead_id).first()
    if not lead:
        return jsonify({"ok": False, "error": "Lead não encontrado"}), 404

    if action == "mark":
        lead.followup_feito_em = datetime_now_brazil()
        current_user = getattr(request, "current_user", None) or {}
        lead.followup_por = current_user.get("user_id")
    else:
        lead.followup_feito_em = None
        lead.followup_por = None

    db.session.commit()
    return jsonify({"ok": True, "lead": _serialize_lead(lead)}), 200


@leads_bp.route("/<int:lead_id>/touchpoints", methods=["GET"])
@requires_any_role("admin", "atendente", "vendedor")
def listar_touchpoints(lead_id: int):
    """Histórico completo de toques de um lead, do mais antigo ao mais recente."""
    lead = Lead.query.filter(Lead.id == lead_id).first()
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
@requires_any_role("admin", "atendente", "vendedor")
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

    # Filtro: confirmados sem followup há X dias.
    # status=whatsapp_iniciado AND (followup_feito_em IS NULL OR < now - X dias)
    pending_followup_days_raw = request.args.get("pending_followup_days")
    if pending_followup_days_raw:
        try:
            days = int(pending_followup_days_raw)
        except (TypeError, ValueError):
            days = 0
        if days > 0:
            cutoff = datetime_now_brazil() - timedelta(days=days)
            query = query.filter(
                Lead.status == "whatsapp_iniciado",
                db.or_(
                    Lead.followup_feito_em.is_(None),
                    Lead.followup_feito_em < cutoff,
                ),
            )

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
        # Datas no formato YYYY-MM-DD são interpretadas em BRT: date_from vira
        # início do dia (00:00:00-03) e date_to vira fim do dia (23:59:59.999999-03).
        # Sem isso, "20/05/2026" → "20/05/2026" matava o range (>= meia-noite AND <= meia-noite).
        date_from = request.args.get("date_from")
        if date_from:
            parsed_from = _parse_brt_day_start(date_from)
            if parsed_from is not None:
                query = query.filter(Lead.created_at >= parsed_from)

        date_to = request.args.get("date_to")
        if date_to:
            parsed_to = _parse_brt_day_end(date_to)
            if parsed_to is not None:
                query = query.filter(Lead.created_at <= parsed_to)

    # Filtros de status: `status` (exato) e `hidden` (categorias agrupadas).
    # Aplicados POR ÚLTIMO para que `hidden_count` reflita os demais filtros
    # (período, evento, utm, followup) na janela atual.
    status_q = request.args.get("status")
    hidden_mode = (request.args.get("hidden") or "exclude").strip().lower()
    if hidden_mode not in {"exclude", "only", "include"}:
        hidden_mode = "exclude"

    # `hidden_count` = quantos leads ocultos existem na janela atual (independente
    # do que será paginado). Snapshot ANTES de aplicar status/hidden no `query`.
    hidden_count = query.filter(Lead.status.in_(HIDDEN_STATUSES)).count()

    if status_q:
        query = query.filter(Lead.status == status_q)
    elif hidden_mode == "exclude":
        query = query.filter(db.or_(Lead.status.is_(None), ~Lead.status.in_(HIDDEN_STATUSES)))
    elif hidden_mode == "only":
        query = query.filter(Lead.status.in_(HIDDEN_STATUSES))

    # Filtro opcional por situação (subestado do lead confirmado).
    situacao_q = request.args.get("situacao")
    if situacao_q:
        query = query.filter(Lead.situacao == situacao_q)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

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
            "hidden_count": int(hidden_count or 0),
        }
    )


def _aggregate_lead_stats(start_dt: datetime) -> dict:
    """Conta pendentes/lead_pendentes/confirmados/compras/total a partir de `start_dt`.

    Buckets:
      - `pendentes`: leads em `pendente_whatsapp` — triagem (vieram do anúncio
        sem telefone). Volume desta fila reflete falha de captura.
      - `lead_pendentes`: leads em `lead_pendente` — fila de decisão (têm
        telefone, aguardando confirmar ou desqualificar). Volume aqui reflete
        backlog operacional do vendedor.
      - `confirmados`: leads `whatsapp_iniciado` com telefone — Lead Confirmado.
      - `compras`: leads `compra_realizada`.

    Buckets `pendentes` e `lead_pendentes` ficam separados porque medem fenômenos
    distintos — não juntar no header.
    """
    is_pendente = case((Lead.status == "pendente_whatsapp", 1), else_=0)
    is_lead_pendente = case((Lead.status == "lead_pendente", 1), else_=0)
    is_confirmado = case(
        (
            (Lead.status == "whatsapp_iniciado") & Lead.phone.isnot(None) & (Lead.phone != ""),
            1,
        ),
        else_=0,
    )
    is_compra = case((Lead.status == "compra_realizada", 1), else_=0)

    row = (
        db.session.query(
            func.coalesce(func.sum(is_pendente), 0),
            func.coalesce(func.sum(is_lead_pendente), 0),
            func.coalesce(func.sum(is_confirmado), 0),
            func.coalesce(func.sum(is_compra), 0),
            func.count(Lead.id),
        )
        .filter(Lead.event.in_(DEFAULT_KEY_EVENTS), Lead.created_at >= start_dt)
        .one()
    )
    pendentes, lead_pendentes, confirmados, compras, total = row
    return {
        "pendentes": int(pendentes or 0),
        "lead_pendentes": int(lead_pendentes or 0),
        "confirmados": int(confirmados or 0),
        "compras": int(compras or 0),
        "total": int(total or 0),
    }


@leads_bp.route("/stats", methods=["GET"])
@requires_any_role("admin", "atendente", "vendedor")
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
    transitioned_to_confirmed: list[Lead] = []

    for lead in leads:
        if not _is_whatsapp_event(lead.event):
            skipped_ids.append(lead.id)
            continue
        allowed = ALLOWED_STATUS_TRANSITIONS.get(lead.status or "", set())
        if new_status not in allowed:
            skipped_ids.append(lead.id)
            continue
        # Regra dura: confirmar/desqualificar exigem telefone.
        if new_status in STATUSES_REQUIRING_PHONE and not (lead.phone or "").strip():
            skipped_ids.append(lead.id)
            continue
        if new_status == "descarte" and lead.status != "descarte":
            transitioned_to_descarte.append(lead)
        if new_status == "whatsapp_iniciado" and lead.status != "whatsapp_iniciado":
            if not lead.meta_event_id_lead:
                lead.meta_event_id_lead = str(uuid.uuid4())
            if not lead.situacao:
                lead.situacao = DEFAULT_SITUACAO
            transitioned_to_confirmed.append(lead)
        lead.status = new_status
        updated += 1

    db.session.commit()

    # Enfileira no outbox; o capi-worker envia de forma assíncrona.
    if (transitioned_to_descarte or transitioned_to_confirmed) and is_lead_funnel_enabled():
        repo = MetaCapiLeadOutboxRepository()
        now_brt = datetime_now_brazil()
        for lead in transitioned_to_confirmed:
            repo.create_lead_stage_from_lead(lead, event_time=now_brt)
        for lead in transitioned_to_descarte:
            repo.create_disqualified_from_lead(lead, event_time=now_brt)
        from app.services.events_service import EventsService
        events_svc = EventsService()
        for lead in transitioned_to_confirmed:
            events_svc.enqueue_lead(lead, event_time=now_brt)
        for lead in transitioned_to_descarte:
            events_svc.enqueue_disqualified(lead, event_time=now_brt)

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

        # Regra dura: descarte exige telefone (do update OU pré-existente).
        if not (lead.phone or "").strip():
            skipped_ids.append(lead.id)
            continue

        lead.status = "descarte"
        transitioned.append(lead)
        updated += 1

    db.session.commit()

    # Enfileira no outbox; o capi-worker envia de forma assíncrona.
    if transitioned and is_lead_funnel_enabled():
        repo = MetaCapiLeadOutboxRepository()
        now_brt = datetime_now_brazil()
        for lead in transitioned:
            repo.create_disqualified_from_lead(lead, event_time=now_brt)
        from app.services.events_service import EventsService
        events_svc = EventsService()
        for lead in transitioned:
            events_svc.enqueue_disqualified(lead, event_time=now_brt)

    return jsonify(
        {
            "ok": True,
            "updated": updated,
            "skipped": len(skipped_ids),
            "skipped_ids": skipped_ids,
        }
    )
