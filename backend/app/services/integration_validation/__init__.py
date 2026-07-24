# -*- coding: utf-8 -*-
"""Dispatcher de validacao isolada por canal/campo.

Recebe `(channel, field, value)` e devolve `(ok, error)`. Erros nao devem
ecoar segredos.

Canais OAuth (nuvemshop/bling) nao passam por aqui: a UI consulta
`/api/integrations/{provider}/status`.
"""

from __future__ import annotations

from typing import Callable, Optional

from . import dados_operacionais, ga4, mercado_pago, meta_capi, utmify

HttpGet = Callable[[str, float], tuple[int, dict | str]]


def validate(
    channel: str,
    field: str,
    value: str | None,
    *,
    http_get: Optional[HttpGet] = None,
) -> tuple[bool, str | None]:
    """Roteia (channel, field) para a funcao de validacao especifica.

    Para `meta_capi_access_token` e `ga4_api_secret` faz chamada de rede
    opcional (mockavel via `http_get`). Outros canais sao apenas formato.
    """
    if channel == "meta_capi":
        if field == "meta_pixel_id":
            return meta_capi.validate_meta_pixel_id(value)
        if field == "meta_capi_access_token":
            return meta_capi.validate_meta_capi_access_token(value, http_get=http_get)
    elif channel == "ga4":
        if field == "ga4_measurement_id":
            return ga4.validate_ga4_measurement_id(value)
        if field == "ga4_api_secret":
            return ga4.validate_ga4_api_secret(value, http_get=http_get)
    elif channel == "utmify":
        if field == "utmify_api_token":
            return utmify.validate_utmify_api_token(value)
        if field == "utmify_platform":
            return utmify.validate_utmify_platform(value)
    elif channel == "dados_operacionais":
        if field == "loja_cep":
            return dados_operacionais.validate_loja_cep(value, http_get=http_get)
        if field == "endereco_floricultura":
            return dados_operacionais.validate_endereco_floricultura(value)
    elif channel == "mercado_pago":
        if field == "mercado_pago_access_token":
            return mercado_pago.validate_mercado_pago_access_token(value, http_get=http_get)
        if field == "mercado_pago_public_key":
            return mercado_pago.validate_mercado_pago_public_key(value, http_get=http_get)
        if field == "mercado_pago_client_id":
            return mercado_pago.validate_mercado_pago_client_id(value, http_get=http_get)
        if field == "mercado_pago_client_secret":
            return mercado_pago.validate_mercado_pago_client_secret(value, http_get=http_get)

    return False, f"Campo nao validavel: {channel}.{field}"


__all__ = ["validate", "HttpGet"]
