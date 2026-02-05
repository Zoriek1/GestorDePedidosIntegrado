"""
Mapeamento de Order (Nuvemshop) -> Pedido (sistema interno).
"""

import json
import re
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple

from app.models.pedido import datetime_now_brazil

# Mapeamento de períodos textuais para intervalos de horário
HUAAPPS_KEYWORD_MAP = {
    "dia inteiro": "08:00 - 18:00",
    "manhã": "08:00 - 12:00",
    "manha": "08:00 - 12:00",
    "tarde": "13:00 - 18:00",
    "noite": "18:00 - 22:00",
}

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


def _extract_address_complement(shipping_address: Dict[str, Any]) -> Optional[str]:
    """Extrai complemento/andar do endereço de entrega."""
    complement_parts = []

    # Campos comuns para complemento na API Nuvemshop
    for key in ("floor", "complement", "apartment", "suite", "floor_number"):
        value = _safe_str(shipping_address.get(key))
        if value:
            complement_parts.append(value)

    return "; ".join(complement_parts) if complement_parts else None


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

    # Padrão 1: "13:00 18:00" ou "13:00-18:00" ou "13:00 - 18:00"
    times = re.findall(r"\b(\d{1,2}):(\d{2})\b", text_normalized)
    if len(times) >= 2:
        h1, m1 = times[0]
        h2, m2 = times[1]
        return f"{int(h1):02d}:{m1} - {int(h2):02d}:{m2}"

    # Padrão 2: Períodos textuais (manhã, tarde, noite, dia inteiro)
    lowered = text_normalized.lower()
    for key, value in HUAAPPS_KEYWORD_MAP.items():
        if key in lowered:
            return value

    # Padrão 3: Horário único (ex: "15:00")
    if len(times) == 1:
        h, m = times[0]
        return f"{int(h):02d}:{m}"

    return None


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


def _extract_schedule_from_custom_fields(
    order: Dict[str, Any],
) -> Tuple[Optional[date], Optional[str], Optional[str]]:
    """
    Extrai data/horário de entrega de Order Custom Fields.

    Alguns apps (ex.: agendadores) salvam a data escolhida em um custom field do pedido.
    Estruturas encontradas:
    - order["custom_fields"] = [{"name": "...", "value": "02/01/2026"}, ...]
    - ou chaves semelhantes (key/label/text/value).
    """
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
        if not raw_value:
            continue

        extracted_date = _extract_date_from_text(raw_value)
        extracted_time = _extract_time_interval(raw_value)
        if extracted_date or extracted_time:
            return extracted_date, extracted_time, (name or "custom_field")

        # fallback: alguns campos podem embutir texto maior; tentar extrair no conjunto
        combined = f"{name} {raw_value}".strip()
        extracted_date = _extract_date_from_text(combined)
        extracted_time = _extract_time_interval(combined)
        if extracted_date or extracted_time:
            return extracted_date, extracted_time, (name or "custom_field")

    return None, None, None


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

    # Formatar produtos com " + " entre eles e detalhes para observações
    produtos = order.get("products") or []
    produto, produto_detalhado = _format_produtos_detalhado(produtos)

    currency = _safe_str(order.get("currency")) or "BRL"
    valor_raw = (
        order.get("total_paid_by_customer")
        or order.get("total_paid_by_customer_including_fees")
        or order.get("total")
        or ""
    )
    valor = _safe_str(valor_raw)
    if currency.upper() == "BRL" and valor:
        valor = _format_brl(valor)
    elif valor:
        valor = f"{currency} {valor}"

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

    tipo_pedido = "Entrega"
    if _safe_str(order.get("shipping_pickup_type")).lower() == "pickup":
        tipo_pedido = "Retirada"

    status = "agendado"
    if _safe_str(order.get("status")).lower() == "cancelled":
        status = "cancelado"

    shipping_option_text = _get_shipping_option_text(order)
    horario_from_shipping = _extract_time_interval(shipping_option_text)
    horario = horario_from_shipping
    if not horario:
        horario = "08:00 - 18:00"

    date_search_text = _collect_text_for_date_search(order, shipping_option_text)
    dia_entrega = _extract_date_from_text(date_search_text)
    custom_field_date, custom_field_time, custom_field_name = _extract_schedule_from_custom_fields(
        order
    )

    # Rastrear origem do agendamento
    agendamento_source = "shipping_option" if horario_from_shipping else None

    if custom_field_date:
        dia_entrega = custom_field_date
        agendamento_source = (
            f"custom_field:{custom_field_name}" if custom_field_name else "custom_field"
        )
    # Só sobrescrever horário se ele não veio do método de entrega (frete).
    if custom_field_time and not horario_from_shipping:
        horario = custom_field_time
        if not agendamento_source or agendamento_source == "shipping_option":
            agendamento_source = (
                f"custom_field:{custom_field_name}" if custom_field_name else "custom_field"
            )

    created_at = _parse_datetime(order.get("created_at"))
    if not dia_entrega:
        if created_at:
            dia_entrega = created_at.date()
        else:
            dia_entrega = datetime_now_brazil().date()
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
    complemento = _extract_address_complement(shipping_address)

    # Extrair detalhes financeiros
    financial_details = _extract_financial_details(order)

    # Extrair informações extras do cliente
    customer_extras = _extract_customer_extras(order, customer, shipping_address)

    # IMPORTANTE: owner_note vai para mensagem (cartão), não para observações
    # note (observações do cliente) continua nas observações
    mensagem_cartao = _safe_str(order.get("owner_note")) or None

    observacoes_parts = [
        f"NUVEMSHOP order_id={_safe_str(order.get('id'))}",
        f"order_number={_safe_str(order.get('number'))}",
        f"order_token={_safe_str(order.get('token'))}",
    ]

    if shipping_option_text:
        observacoes_parts.append(f"shipping_option={shipping_option_text}")

    # Note (observações do cliente) - vai para observações
    if order.get("note"):
        observacoes_parts.append(f"note={_safe_str(order.get('note'))}")

    # Complemento do endereço
    if complemento:
        observacoes_parts.append(f"complemento={complemento}")

    # Detalhes dos produtos (SKU, preços individuais)
    if produto_detalhado:
        observacoes_parts.append(f"produtos_detalhados={produto_detalhado}")

    # Detalhes financeiros (descontos, taxas)
    if financial_details:
        observacoes_parts.append(financial_details)

    # Informações extras do cliente (CPF, email, estado)
    if customer_extras:
        observacoes_parts.append(customer_extras)

    if telefone_missing:
        observacoes_parts.append("telefone ausente no pedido (fallback usado)")
    if schedule_pending:
        observacoes_parts.append(
            "IMPORTADO NUVEMSHOP/HUAAPPS: data de entrega nao disponivel na API; revisar dia_entrega"
        )
    elif custom_field_date or custom_field_time:
        info = []
        if custom_field_date:
            info.append("dia_entrega")
        if custom_field_time:
            info.append("horario")
        observacoes_parts.append(
            f"{'/'.join(info)} via custom_field={_safe_str(custom_field_name)}"
        )

    observacoes = " | ".join([p for p in observacoes_parts if p])

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
        "bairro": _safe_str(shipping_address.get("locality")) or None,
        "cidade": _safe_str(shipping_address.get("city")) or None,
        "endereco": None,
        "obs_entrega": shipping_option_text or None,
        "mensagem": mensagem_cartao,  # owner_note vai para mensagem (cartão)
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
