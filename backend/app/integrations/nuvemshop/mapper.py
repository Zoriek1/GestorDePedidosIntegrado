"""
Mapeamento de Order (Nuvemshop) -> Pedido (sistema interno).
"""

import json
import re
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.models.pedido import datetime_now_brazil

# Mapeamento de períodos textuais para intervalos de horário
HUAAPPS_KEYWORD_MAP = {
    "dia inteiro": "08:00 - 18:00",
    "horario comercial": "08:00 - 18:00",
    "horário comercial": "08:00 - 18:00",
    "comercial": "08:00 - 18:00",
    "manhã": "08:00 - 12:00",
    "manha": "08:00 - 12:00",
    "tarde": "13:00 - 18:00",
    "noite": "18:00 - 22:00",
}

# Keywords que identificam frete expresso (entrega em ~1h)
_EXPRESS_KEYWORDS = frozenset({"expresso", "expressa", "express"})
_PICKUP_KEYWORDS = frozenset(
    {"retirada", "retirar", "pickup", "pick up", "retire na loja", "retirada em loja"}
)

# Mapeamento de storefront da Nuvemshop para canal interno
STOREFRONT_TO_CANAL_MAP = {
    "store": "Site",
    "meli": "Mercado Livre",
    "pos": "PDV",
    "form": "Pedido Manual",
    "api": "API/Integração",
}


def _map_storefront_to_canal(storefront: str) -> str:
    """Mapeia storefront da Nuvemshop para canal interno"""
    if not storefront:
        return "Site"
    return STOREFRONT_TO_CANAL_MAP.get(storefront.lower(), "Site")


_COMPLEMENT_FIELD_KEYS = (
    "floor",
    "complement",
    "complement_2",
    "apartment",
    "suite",
    "floor_number",
    "address_2",
    "additional_info",
    "unit",
    "block",
)

# Padrões para extrair complemento embutido em texto livre (nota, address, etc).
# Captura "Apto 502", "Ap. 3", "Apartamento 502 Bl B", "andar 3", "sala 12",
# "casa 5", "bloco B", "torre 2", "fundos".
_COMPLEMENT_TEXT_PATTERNS = (
    re.compile(r"\b(?:apto|apt|ap)\s*\.?\s*([A-Z0-9\-]+)\b", re.I),
    re.compile(r"\bapartamento\s*([A-Z0-9\-]+)\b", re.I),
    re.compile(r"\b(\d{1,3})[ºo]?\s*andar\b", re.I),
    re.compile(r"\bandar\s*([A-Z0-9\-]+)\b", re.I),
    re.compile(r"\bsala\s*([A-Z0-9\-]+)\b", re.I),
    re.compile(r"\b(?:bl|bloco)\s*\.?\s*([A-Z0-9\-]+)\b", re.I),
    re.compile(r"\btorre\s*([A-Z0-9\-]+)\b", re.I),
    re.compile(r"\bcasa\s*([A-Z0-9\-]+)\b", re.I),
    re.compile(r"\b(fundos)\b", re.I),
)


def _extract_complement_from_text(text: str, already: set) -> list:
    """Procura padrões de andar/sala/apto/bloco em texto livre.

    `already` é o conjunto (uppercase) dos fragmentos já coletados, usado para
    evitar duplicatas como "Apt 502" + "Apartamento 502".
    """
    if not text:
        return []
    found = []
    for pattern in _COMPLEMENT_TEXT_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        # Reconstrói um fragmento canônico legível mantendo o rótulo do padrão.
        whole = match.group(0).strip()
        whole_norm = whole.upper()
        # Heurística simples para evitar duplicar com fragmento já coletado.
        if any(whole_norm in existing or existing in whole_norm for existing in already):
            continue
        already.add(whole_norm)
        found.append(whole)
    return found


def _extract_address_complement(
    shipping_address: Dict[str, Any], order: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Extrai complemento/andar do endereço de entrega.

    Fontes consultadas (em ordem):
      1. Campos dedicados no shipping_address (floor, complement, etc).
      2. Padrões textuais (apto/andar/sala/bloco) embutidos no campo
         `address`, em campos extras do shipping_address e na `note` do
         pedido — onde o cliente costuma escrever "Apto 502, andar 3".
      3. Padrão QD/LT (loteamentos), já tratado por
         _extract_qd_lt_from_address_payload.
    """
    complement_parts: list = []
    seen: set = set()

    # 1) Campos dedicados
    for key in _COMPLEMENT_FIELD_KEYS:
        value = _safe_str(shipping_address.get(key))
        if value:
            normalized = value.upper()
            if normalized not in seen:
                complement_parts.append(value)
                seen.add(normalized)

    # 2) Padrões textuais em campos textuais do endereço e na nota do pedido
    free_text_sources = [
        _safe_str(shipping_address.get("address")),
        _safe_str(shipping_address.get("between_streets")),
        _safe_str(shipping_address.get("reference")),
    ]
    if order:
        free_text_sources.append(_safe_str(order.get("note")))
        free_text_sources.append(_safe_str(order.get("owner_note")))

    for source_text in free_text_sources:
        complement_parts.extend(_extract_complement_from_text(source_text, seen))

    # 3) QD/LT (mantido por compatibilidade — loteamentos)
    qd_lt = _extract_qd_lt_from_address_payload(shipping_address, order)
    if qd_lt:
        normalized_existing = " | ".join(complement_parts).upper()
        if qd_lt not in normalized_existing:
            complement_parts.append(qd_lt)

    return "; ".join(complement_parts) if complement_parts else None


def _extract_qd_lt_from_address_payload(
    shipping_address: Dict[str, Any], order: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Extrai padrao QD/LT de campos textuais do payload de endereco."""
    if not isinstance(shipping_address, dict):
        return None

    candidates = []
    for key in (
        "address",
        "number",
        "locality",
        "reference",
        "between_streets",
        "floor",
        "complement",
        "apartment",
        "suite",
    ):
        value = shipping_address.get(key)
        if value is not None:
            candidates.append(_safe_str(value))

    candidates_text = " | ".join([c for c in candidates if c])
    if order:
        candidates_text = " | ".join(
            [
                candidates_text,
                _safe_str(order.get("note")),
                _safe_str(order.get("owner_note")),
            ]
        )
    if not candidates_text:
        return None

    quadra_match = re.search(r"\b(?:QD|QUADRA)\s*[:\-]?\s*([A-Z0-9\-\/]+)\b", candidates_text, re.I)
    lote_match = re.search(r"\b(?:LT|LOTE)\s*[:\-]?\s*([A-Z0-9\-\/]+)\b", candidates_text, re.I)
    if not (quadra_match and lote_match):
        return None

    quadra = quadra_match.group(1).upper()
    lote = lote_match.group(1).upper()
    return f"QD {quadra} LT {lote}"


def _clean_bairro_from_qd_lt(value: str) -> Optional[str]:
    """Remove trechos de QD/LT do bairro quando vierem misturados no mesmo campo."""
    bairro = _safe_str(value)
    if not bairro:
        return None

    bairro = re.sub(r"\b(?:QD|QUADRA)\s*[:\-]?\s*[A-Z0-9\-\/]+\b", "", bairro, flags=re.I)
    bairro = re.sub(r"\b(?:LT|LOTE)\s*[:\-]?\s*[A-Z0-9\-\/]+\b", "", bairro, flags=re.I)
    bairro = re.sub(r"\s*[,;\-]\s*", " ", bairro)
    bairro = re.sub(r"\s+", " ", bairro).strip()
    return bairro or None


def _format_produtos_detalhado(produtos: list) -> Tuple[str, str]:
    """
    Formata lista de produtos com detalhes.
    Produtos separados por " + " para clareza visual.

    Returns:
        Tuple[produto_resumo, produto_detalhado_obs]
        - produto_resumo: "Ferrero Rocher + Buquezinho de flor"
        - produto_detalhado_obs: "1x Ferrero (SKU: X) - R$ 58.00 | 1x Buquezinho (SKU: Y) - R$ 99.90"
    """
    if not produtos:
        return "Produto Nuvemshop", ""

    resumo = []
    detalhes = []

    for item in produtos:
        nome = _safe_str(item.get("name")) or "Produto"
        sku = _safe_str(item.get("sku"))
        quantidade = item.get("quantity") or 1
        preco = item.get("price") or 0

        try:
            quantidade_int = int(float(quantidade))
        except (ValueError, TypeError):
            quantidade_int = 1

        # Resumo simples: nome sem quantidade se for 1 unidade
        if quantidade_int == 1:
            resumo.append(nome)
        else:
            resumo.append(f"{quantidade_int}x {nome}")

        # Detalhes completos para observações
        detalhe = f"{quantidade_int}x {nome}"
        if sku:
            detalhe += f" (SKU: {sku})"
        if preco:
            try:
                preco_float = float(preco)
                detalhe += f" - R$ {preco_float:.2f}"
            except (ValueError, TypeError):
                pass
        detalhes.append(detalhe)

    # IMPORTANTE: usar " + " ao invés de ";"
    produto_resumo = " + ".join(resumo)
    produto_detalhado = " | ".join(detalhes)

    return produto_resumo, produto_detalhado


def _extract_financial_details(order: Dict[str, Any]) -> str:
    """Extrai detalhes financeiros do pedido para as observações."""
    parts = []

    # Subtotal
    subtotal = order.get("subtotal")
    if subtotal:
        try:
            parts.append(f"subtotal=R${float(subtotal):.2f}")
        except (ValueError, TypeError):
            pass

    # Descontos específicos
    for discount in order.get("discounts", []):
        if isinstance(discount, dict):
            code = discount.get("code") or discount.get("name")
            value = discount.get("value") or discount.get("amount")
            if code and value:
                try:
                    parts.append(f"desconto_{code}=R${float(value):.2f}")
                except (ValueError, TypeError):
                    parts.append(f"desconto_{code}={value}")

    # Taxas
    gateway_cost = order.get("gateway_cost_customer") or order.get("gateway_cost")
    if gateway_cost:
        try:
            parts.append(f"taxas=R${float(gateway_cost):.2f}")
        except (ValueError, TypeError):
            pass

    return " | ".join(parts) if parts else ""


def _extract_customer_extras(
    order: Dict[str, Any], customer: Dict[str, Any], shipping_address: Dict[str, Any]
) -> str:
    """Extrai informações extras do cliente: CPF, email, estado, país."""
    billing_address = order.get("billing_address") or {}
    info_extras = []

    # CPF (pode estar em customer, billing ou order)
    cpf = (
        _safe_str(customer.get("identification"))
        or _safe_str(billing_address.get("identification"))
        or _safe_str(order.get("billing_identification"))
    )
    if cpf:
        info_extras.append(f"CPF={cpf}")

    # Email
    email = _safe_str(customer.get("email") or order.get("contact_email"))
    if email:
        info_extras.append(f"email={email}")

    # Estado e País do endereço de entrega
    estado = _safe_str(shipping_address.get("province"))
    pais = _safe_str(shipping_address.get("country"))
    if estado:
        info_extras.append(f"estado={estado}")
    if pais and pais.upper() != "BR":
        info_extras.append(f"pais={pais}")

    return " | ".join(info_extras) if info_extras else ""


def _extract_shipping_costs(order: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Extrai custos de frete do pedido.

    Returns:
        Tuple[frete_cobrado_cliente, desconto_frete, frete_liquido_cliente]
    """
    # Diferentes campos onde o frete pode estar
    shipping_cost_raw = (
        order.get("shipping_cost_customer")
        or order.get("shipping_cost_owner")
        or order.get("shipping")
        or 0
    )

    # Desconto de frete (pode estar em diferentes lugares)
    discount_shipping_raw = order.get("discount_shipping") or order.get("shipping_discount") or 0

    try:
        frete_cobrado = float(shipping_cost_raw) if shipping_cost_raw else 0.0
    except (ValueError, TypeError):
        frete_cobrado = 0.0

    try:
        desconto_frete = float(discount_shipping_raw) if discount_shipping_raw else 0.0
    except (ValueError, TypeError):
        desconto_frete = 0.0

    # Frete líquido = cobrado - desconto (cliente pagou efetivamente)
    frete_liquido = max(0.0, frete_cobrado - desconto_frete)

    return frete_cobrado, desconto_frete, frete_liquido


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_phone(value: str) -> str:
    """Normaliza telefone removendo caracteres especiais e prefixo +55 do Brasil."""
    digits = re.sub(r"[^\d]", "", value or "")

    # Remover prefixo 55 do Brasil se presente
    # Telefone brasileiro tem 10 ou 11 dígitos (com DDD)
    # Se tem mais de 11 e começa com 55, remover o prefixo
    if digits.startswith("55") and len(digits) > 11:
        digits = digits[2:]

    return digits


def _format_brl(value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        return ""
    if "." in normalized:
        normalized = normalized.replace(".", ",")
    return f"R$ {normalized}"


def _normalize_valor_canonical(value: str) -> str:
    """
    Normaliza valor bruto da API para string canônica "xxx.xx" (ponto decimal, sem R$).
    Usado para persistir no DB e evitar quebra de lógica (somas, comparações).
    """
    if not value:
        return ""
    raw = str(value).strip().replace("R$", "").strip()
    if not raw:
        return ""
    # Formato BR: vírgula decimal, ponto milhar
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "." in raw:
        dot_count = raw.count(".")
        if dot_count > 1:
            raw = raw.replace(".", "")
    try:
        f = float(raw)
        return f"{f:.2f}"
    except (ValueError, TypeError):
        return ""


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    raw = str(value).strip()
    if not raw:
        return None

    # Normalize timezone formats like +0000 -> +00:00
    if re.match(r".*[\+\-]\d{4}$", raw):
        raw = raw[:-5] + raw[-5:-2] + ":" + raw[-2:]

    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _extract_date_from_text(text: str) -> Optional[date]:
    if not text:
        return None

    match = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
    if match:
        day, month, year = match.groups()
        try:
            return datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y").date()
        except ValueError:
            pass

    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        year, month, day = match.groups()
        try:
            return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date()
        except ValueError:
            pass

    return None


def _extract_time_interval(text: str) -> Optional[str]:
    """
    Extrai intervalo de horário do texto.

    Suporta formatos:
    - "13:00 18:00" (com espaço)
    - "13:00-18:00" (com hífen)
    - "13:00 - 18:00" (com hífen e espaços)
    - "Tarde" -> "13:00 - 18:00"
    - "Manhã" -> "08:00 - 12:00"
    - etc.
    """
    if not text:
        return None

    # Normalizar espaços múltiplos
    text_normalized = re.sub(r"\s+", " ", text.strip())
    lowered = text_normalized.lower()

    # Expressa com marcador de duração (ex: "(01:00)") deve cair na regra dinâmica de 1h.
    if _is_express_shipping(lowered) and re.search(r"\(\s*0?1:00\s*\)", lowered):
        return None

    # Padrão 1: "13:00 18:00" ou "13:00-18:00" ou "13:00 - 18:00"
    times = re.findall(r"\b(\d{1,2}):(\d{2})\b", text_normalized)
    if len(times) >= 2:
        h1, m1 = times[0]
        h2, m2 = times[1]
        return f"{int(h1):02d}:{m1} - {int(h2):02d}:{m2}"

    # Padrão 2: Períodos textuais (manhã, tarde, noite, dia inteiro)
    for key, value in HUAAPPS_KEYWORD_MAP.items():
        if key in lowered:
            return value

    # Padrão 3: Horário único (ex: "15:00")
    if len(times) == 1:
        h, m = times[0]
        return f"{int(h):02d}:{m}"

    return None


def _is_express_shipping(text: str) -> bool:
    """Verifica se o texto da opção de frete indica entrega expressa (~1h)."""
    lowered = text.lower()
    return any(kw in lowered for kw in _EXPRESS_KEYWORDS)


def _compute_express_time_window(created_at: Optional[datetime]) -> str:
    """
    Calcula janela de 1h para frete expresso a partir do horário de criação do pedido.
    Arredonda para baixo no múltiplo de 15 minutos mais próximo.
    Ex: criado às 14:23 → "14:15 - 15:15"
    """
    from app.models.pedido import datetime_now_brazil

    base = created_at or datetime_now_brazil()
    rounded_min = (base.minute // 15) * 15
    start = base.replace(minute=rounded_min, second=0, microsecond=0)
    end_hour = start.hour + 1 if start.hour < 23 else 23
    end_min = start.minute if start.hour < 23 else 59
    return f"{start.hour:02d}:{start.minute:02d} - {end_hour:02d}:{end_min:02d}"


def _is_pickup_shipping_text(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _PICKUP_KEYWORDS)


def _extract_shipping_lines_text(order: Dict[str, Any]) -> str:
    shipping_lines = order.get("shipping_lines")
    if not isinstance(shipping_lines, list):
        return ""

    candidates = []
    for line in shipping_lines:
        if not isinstance(line, dict):
            continue
        for key in (
            "name",
            "title",
            "method",
            "shipping_method",
            "delivery_type",
            "type",
            "service_name",
            "code",
        ):
            value = line.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())
    return " | ".join(candidates)


def _is_pickup_order(order: Dict[str, Any], shipping_option_text: str) -> bool:
    """
    Detecta retirada usando múltiplos sinais. A Nuvemshop nem sempre preenche
    `shipping_pickup_type`; muitos checkouts deixam apenas o billing_address e
    nenhum endereço de entrega real, e nesse caso o pedido vinha sendo
    classificado erradamente como Entrega.
    """
    # 1) Sinal explícito da Nuvemshop
    if _safe_str(order.get("shipping_pickup_type")).lower() == "pickup":
        return True

    # 2) shipping_pickup_details preenchido = pedido marcado para retirada
    pickup_details = order.get("shipping_pickup_details")
    if pickup_details and (
        (isinstance(pickup_details, dict) and any(pickup_details.values()))
        or (isinstance(pickup_details, str) and pickup_details.strip())
    ):
        return True

    # 3) Texto da opção de envio menciona retirada
    if _is_pickup_shipping_text(shipping_option_text):
        return True

    # 4) Heurística: ausência total de sinais de entrega.
    # Quando o pedido não tem endereço de envio real (CEP/rua), não tem
    # shipping_lines, custo de envio é zero e nenhuma opção de envio foi
    # selecionada, é praticamente certo que é retirada — o cliente só tem
    # billing_address por estar cadastrado, mas o pedido em si não envia
    # nada.
    shipping_address = order.get("shipping_address") or {}
    has_real_shipping_address = bool(
        _safe_str(shipping_address.get("zipcode"))
        or _safe_str(shipping_address.get("address"))
    )
    shipping_lines = order.get("shipping_lines")
    has_shipping_lines = bool(shipping_lines) if isinstance(shipping_lines, list) else False
    shipping_cost_raw = (
        order.get("shipping_cost_customer")
        or order.get("shipping_cost_owner")
        or order.get("shipping")
        or 0
    )
    try:
        shipping_cost = float(shipping_cost_raw) if shipping_cost_raw else 0.0
    except (ValueError, TypeError):
        shipping_cost = 0.0

    if (
        not has_real_shipping_address
        and not has_shipping_lines
        and shipping_cost == 0.0
        and not shipping_option_text.strip()
    ):
        return True

    return False


def _resolve_brazil_delivery_date(created_at: Optional[datetime]) -> date:
    if not created_at:
        return datetime_now_brazil().date()

    brazil_tz = datetime_now_brazil().tzinfo
    normalized_dt = created_at
    if normalized_dt.tzinfo is None:
        normalized_dt = normalized_dt.replace(tzinfo=timezone.utc)
    if brazil_tz:
        normalized_dt = normalized_dt.astimezone(brazil_tz)
    return normalized_dt.date()


def _get_shipping_option_text(order: Dict[str, Any]) -> str:
    candidates = []
    for key in ("shipping_option", "shipping_option_name", "shipping_method", "shipping"):
        value = order.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())
        elif isinstance(value, dict):
            for nested_key in ("name", "title", "option", "method", "code"):
                nested_val = value.get(nested_key)
                if isinstance(nested_val, str) and nested_val.strip():
                    candidates.append(nested_val.strip())
    shipping_lines_text = _extract_shipping_lines_text(order)
    if shipping_lines_text:
        candidates.append(shipping_lines_text)
    return " | ".join([c for c in candidates if c])


def _collect_text_for_date_search(order: Dict[str, Any], shipping_option_text: str) -> str:
    parts = [
        shipping_option_text,
        _safe_str(order.get("note")),
        _safe_str(order.get("owner_note")),
    ]

    for key in ("attributes", "extra", "shipping_address"):
        value = order.get(key)
        if value:
            try:
                parts.append(json.dumps(value, ensure_ascii=True))
            except TypeError:
                parts.append(_safe_str(value))

    return " | ".join([p for p in parts if p])


# Nomes de campos personalizados que indicam data de entrega (Huapps/Nuvemshop)
_DATE_FIELD_NAMES = frozenset(
    {"data da entrega", "data", "agendamento", "data agendada", "data entrega"}
)
# Nomes que indicam período/horário
_TIME_FIELD_NAMES = frozenset(
    {"período da entrega", "período", "periodo", "horário", "horario", "agendamento"}
)
# Nome do campo de destinatário
_DESTINATARIO_FIELD_NAMES = frozenset(
    {"nome do destinatário", "nome destinatario", "destinatário", "destinatario"}
)


def _extract_schedule_from_custom_fields(
    order: Dict[str, Any],
) -> Tuple[Optional[date], Optional[str], Optional[str]]:
    """
    Extrai data/horário de entrega de Order Custom Fields.

    Na API Nuvemshop, custom fields vêm do endpoint GET /orders/{id}/custom-fields
    (precisam ser buscados separadamente e mesclados no order).

    Campos Huapps comuns:
    - "Data da Entrega" = "03/03/2026"
    - "Período da Entrega" = "Manhã (09:00 - 12:00)"
    - Ou em um único campo "Agendamento" = "03/03/2026 09:00 - 12:00"

    Percorre TODOS os campos para obter data e horário (podem estar separados).
    """
    candidates = []
    for key in ("custom_fields", "order_custom_fields"):
        value = order.get(key)
        if isinstance(value, list):
            candidates.extend([v for v in value if isinstance(v, dict)])

    best_date: Optional[date] = None
    best_time: Optional[str] = None
    source_names: list = []

    for entry in candidates:
        name = _safe_str(
            entry.get("name") or entry.get("key") or entry.get("label") or entry.get("title")
        )
        raw_value = _safe_str(
            entry.get("value") or entry.get("text") or entry.get("data") or entry.get("string")
        )
        if not raw_value:
            continue

        name_lower = name.lower()
        combined = f"{name} {raw_value}".strip()

        # Extrair data (de valor ou nome+valor)
        extracted_date = _extract_date_from_text(raw_value) or _extract_date_from_text(combined)
        if extracted_date and (name_lower in _DATE_FIELD_NAMES or not best_date):
            best_date = extracted_date
            if name and name not in source_names:
                source_names.append(name)

        # Extrair horário (de valor ou nome+valor)
        extracted_time = _extract_time_interval(raw_value) or _extract_time_interval(combined)
        if extracted_time and (name_lower in _TIME_FIELD_NAMES or not best_time):
            best_time = extracted_time
            if name and name not in source_names:
                source_names.append(name)

    source = (
        " | ".join(source_names)
        if source_names
        else ("custom_field" if (best_date or best_time) else None)
    )
    return best_date, best_time, source


def _extract_destinatario_from_custom_fields(order: Dict[str, Any]) -> Optional[str]:
    """Extrai Nome do Destinatário de custom fields (Huapps)."""
    candidates = []
    for key in ("custom_fields", "order_custom_fields"):
        value = order.get(key)
        if isinstance(value, list):
            candidates.extend([v for v in value if isinstance(v, dict)])

    for entry in candidates:
        name = _safe_str(
            entry.get("name") or entry.get("key") or entry.get("label") or entry.get("title")
        )
        raw_value = _safe_str(
            entry.get("value") or entry.get("text") or entry.get("data") or entry.get("string")
        )
        if not raw_value or not raw_value.strip():
            continue
        if name.lower() in _DESTINATARIO_FIELD_NAMES:
            return raw_value.strip()
    return None


def map_nuvemshop_order_to_pedido_data(
    order: Dict[str, Any],
) -> Tuple[Dict[str, Any], bool, str, str]:
    """
    Mapeia Order da Nuvemshop para dados de Pedido interno.

    Returns:
        Tuple[pedido_data, schedule_pending, shipping_option_text, agendamento_source]
    """
    shipping_address = order.get("shipping_address") or {}
    customer = order.get("customer") or {}

    cliente = _safe_str(order.get("contact_name") or customer.get("name")) or "Nao informado"
    destinatario = _safe_str(shipping_address.get("name")) or cliente
    # Huapps: Nome do Destinatário pode vir em custom field (diferente do comprador)
    cf_destinatario = _extract_destinatario_from_custom_fields(order)
    if cf_destinatario:
        destinatario = cf_destinatario

    telefone = _normalize_phone(
        _safe_str(
            order.get("contact_phone")
            or customer.get("phone")
            or order.get("billing_phone")
            or shipping_address.get("phone")
        )
    )
    telefone_missing = False
    if not telefone:
        telefone = "0000000000"
        telefone_missing = True

    # Formatar produtos com " + " entre eles
    produtos = order.get("products") or []
    produto, _ = _format_produtos_detalhado(produtos)

    _currency = _safe_str(order.get("currency")) or "BRL"
    # Para pedidos pendentes, total_paid_by_customer é "0" ou "0.00".
    # Usar total (valor real do pedido) como base e só preferir
    # total_paid_by_customer quando ele for > 0 (pedido já pago).
    paid_raw = _safe_str(order.get("total_paid_by_customer"))
    paid_is_zero = paid_raw in ("", "0", "0.0", "0.00")
    if paid_raw and not paid_is_zero:
        valor_raw = paid_raw
    else:
        valor_raw = (
            _safe_str(order.get("total"))
            or _safe_str(order.get("total_paid_by_customer_including_fees"))
            or ""
        )
    # Persistir valor no formato canônico "xxx.xx" (evita "R$ xxx,xx" que quebra somas no backend)
    valor = _normalize_valor_canonical(valor_raw) if valor_raw else None
    if valor == "":
        valor = None

    # Extrair forma de pagamento de múltiplos campos possíveis
    payment_details = order.get("payment_details") or {}
    pagamento = (
        _safe_str(order.get("gateway_name"))
        or _safe_str(order.get("gateway"))
        or _safe_str(order.get("payment_provider"))
        or _safe_str(payment_details.get("method"))
        or _safe_str(payment_details.get("type"))
        or _safe_str(payment_details.get("credit_card_company"))  # Ex: "Elo", "Visa"
        or None
    )

    # Se ainda não tiver, tentar inferir do status/gateway
    if not pagamento:
        # Nuvem Pago é comum
        if "nuvempago" in _safe_str(order.get("gateway_id")).lower():
            pagamento = "Nuvem Pago"

    payment_status = _safe_str(order.get("payment_status")).lower()
    # IMPORTANTE: Valores são case-sensitive e devem corresponder ao dropdown do sistema
    # Valores válidos: "Pendente", "Pago", "Parcial"
    status_pagamento_map = {
        "paid": "Pago",
        "partially_paid": "Parcial",
        "pending": "Pendente",
        "authorized": "Pendente",
        "voided": "Pendente",  # Cancelado não existe no dropdown
        "refunded": "Pendente",  # Estornado não existe no dropdown
        "abandoned": "Pendente",
    }
    status_pagamento = status_pagamento_map.get(payment_status, "Pendente")

    status = "agendado"
    if _safe_str(order.get("status")).lower() == "cancelled":
        status = "cancelado"

    shipping_option_text = _get_shipping_option_text(order)
    tipo_pedido = "Retirada" if _is_pickup_order(order, shipping_option_text) else "Entrega"
    horario_from_shipping = _extract_time_interval(shipping_option_text)

    # Frete expresso: calcular janela dinâmica de 1h a partir do horário do pedido
    if not horario_from_shipping and _is_express_shipping(shipping_option_text):
        created_at_express = _parse_datetime(order.get("created_at"))
        horario_from_shipping = _compute_express_time_window(created_at_express)

    date_search_text = _collect_text_for_date_search(order, shipping_option_text)
    shipping_date = _extract_date_from_text(date_search_text)
    custom_field_date, custom_field_time, custom_field_name = _extract_schedule_from_custom_fields(
        order
    )

    dia_entrega = custom_field_date or shipping_date
    horario = custom_field_time or horario_from_shipping or "08:00 - 18:00"
    if custom_field_date or custom_field_time:
        agendamento_source = (
            f"custom_field:{custom_field_name}" if custom_field_name else "custom_field"
        )
    elif shipping_date or horario_from_shipping:
        agendamento_source = "shipping_option"
    else:
        agendamento_source = None

    created_at = _parse_datetime(order.get("created_at"))
    if not dia_entrega:
        dia_entrega = _resolve_brazil_delivery_date(created_at)
        schedule_pending = True
        agendamento_source = "fallback"
    else:
        schedule_pending = False

    # Extrair storefront para mapear canal
    storefront = _safe_str(order.get("storefront")) or "store"
    canal = _map_storefront_to_canal(storefront)

    # Extrair custos de frete
    frete_cobrado, desconto_frete, frete_liquido = _extract_shipping_costs(order)

    # Extrair complemento do endereço (floor, apartment, etc)
    complemento = _extract_address_complement(shipping_address, order=order)

    # Mensagem do cartão: note (mensagem do cliente) tem prioridade sobre owner_note (nota interna)
    nota_cliente = _safe_str(order.get("note")) or None
    nota_interna = _safe_str(order.get("owner_note")) or None
    mensagem_cartao = nota_cliente or nota_interna or None

    # Observações: apenas avisos operacionais relevantes (sem metadados técnicos)
    observacoes_parts = []

    if telefone_missing:
        observacoes_parts.append("Telefone ausente no pedido")
    if schedule_pending:
        observacoes_parts.append("Data de entrega não disponível; revisar dia_entrega")

    observacoes = " | ".join([p for p in observacoes_parts if p]) or None

    # Montar obs_entrega incluindo complemento (floor/apt) + shipping option.
    # O complemento contem dados cruciais para o entregador:
    #   quadra/lote, edificio/sala, ponto de referencia, etc.
    obs_entrega_parts = []
    if complemento:
        obs_entrega_parts.append(complemento)
    if shipping_option_text:
        obs_entrega_parts.append(shipping_option_text)
    obs_entrega = " | ".join(obs_entrega_parts) if obs_entrega_parts else None

    pedido_data = {
        "cliente": cliente,
        "telefone_cliente": telefone,
        "destinatario": destinatario,
        "tipo_pedido": tipo_pedido,
        "produto": produto,
        "valor": valor or None,
        "horario": horario,
        "dia_entrega": dia_entrega,
        "cep": _safe_str(shipping_address.get("zipcode")) or None,
        "rua": _safe_str(shipping_address.get("address")) or None,
        "numero": _safe_str(shipping_address.get("number")) or None,
        "complemento": complemento or None,
        "bairro": _clean_bairro_from_qd_lt(_safe_str(shipping_address.get("locality"))),
        "cidade": _safe_str(shipping_address.get("city")) or None,
        "endereco": None,
        "obs_entrega": obs_entrega,
        "mensagem": mensagem_cartao,
        "pagamento": pagamento or None,
        "observacoes": observacoes,
        "status_pagamento": status_pagamento,
        "status": status,
        # Novos campos - Plataforma e Canal
        "plataforma": "Nuvemshop",
        "canal": canal,
        # Novos campos - Frete
        "frete_cobrado_cliente": frete_cobrado if frete_cobrado > 0 else None,
        "desconto_frete": desconto_frete if desconto_frete > 0 else None,
        "frete_liquido_cliente": frete_liquido if frete_liquido > 0 else None,
    }

    return pedido_data, schedule_pending, shipping_option_text, agendamento_source
