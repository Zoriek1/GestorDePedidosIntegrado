# -*- coding: utf-8 -*-
"""Integrações com APIs de geocodificação (ViaCEP, Nominatim, OpenRouteService)."""
from __future__ import annotations

from typing import Optional, Tuple

import requests

from app.utils.http_client import HttpClient
from app.utils.logger import get_logger


VIACEP_URL = "https://viacep.com.br/ws"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPENROUTE_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
OPENROUTE_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"


def buscar_endereco_por_cep(cep: str, http_client: HttpClient, logger=None) -> Optional[str]:
    logger = logger or get_logger(__name__)

    if not cep:
        return None

    try:
        response = http_client.get(f"{VIACEP_URL}/{cep}/json/", timeout=10)
    except requests.exceptions.Timeout:
        logger.error("ViaCEP timeout para CEP: %s", cep)
        return None
    except Exception as exc:
        logger.error("Erro ao consultar ViaCEP: %s", exc)
        return None

    if response.status_code != 200:
        logger.debug("ViaCEP erro HTTP: %s", response.status_code)
        return None

    data = response.json()

    if data.get("erro"):
        logger.debug("ViaCEP: CEP %s não encontrado", cep)
        return None

    logradouro = data.get("logradouro", "")
    bairro = data.get("bairro", "")
    localidade = data.get("localidade", "")
    uf = data.get("uf", "")

    logger.debug("ViaCEP encontrou: logradouro=%s bairro=%s cidade=%s/%s", logradouro, bairro, localidade, uf)

    partes = []
    if logradouro:
        partes.append(logradouro)
    if bairro:
        partes.append(bairro)
    if localidade:
        partes.append(localidade)
    if uf:
        partes.append(uf)
    partes.append("Brasil")

    endereco_formatado = ", ".join(partes)
    logger.debug("Endereço do CEP: %s", endereco_formatado)
    return endereco_formatado


def geocodificar_nominatim(
    endereco: str,
    http_client: HttpClient,
    logger=None,
) -> Optional[Tuple[float, float]]:
    logger = logger or get_logger(__name__)

    if not endereco:
        return None

    headers = {
        "User-Agent": "PlanteumaFlor-GestorPedidos/1.0 (contato@planteumaflor.com.br)",
        "Accept": "application/json",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    params = {
        "q": endereco,
        "format": "json",
        "limit": 1,
        "countrycodes": "br",
        "addressdetails": 1,
    }

    logger.debug("Nominatim request: %s params=%s", NOMINATIM_URL, params)

    try:
        response = http_client.get(
            NOMINATIM_URL,
            headers=headers,
            params=params,
            timeout=15,
        )
    except requests.exceptions.Timeout:
        logger.error("Nominatim timeout para: %s", endereco)
        return None
    except requests.exceptions.ConnectionError as exc:
        logger.error("Nominatim conexão falhou: %s", exc)
        return None
    except Exception as exc:
        logger.error("Nominatim erro: %s", exc)
        return None

    logger.debug("Nominatim status: %s", response.status_code)

    if response.status_code != 200:
        logger.debug("Nominatim erro HTTP: %s - %s", response.status_code, response.text[:200])
        return None

    results = response.json()
    logger.debug("Nominatim resultados: %s", len(results))

    if not results:
        logger.debug("Nominatim: nenhum resultado para '%s'", endereco)
        return None

    result = results[0]
    lat = float(result["lat"])
    lon = float(result["lon"])
    display_name = result.get("display_name", "N/A")

    logger.debug("Nominatim encontrou: display=%s coordenadas=lon=%s lat=%s", display_name[:100], lon, lat)

    return lon, lat


def geocodificar_openroute(
    endereco: str,
    api_key: str,
    focus_lat: float,
    focus_lon: float,
    http_client: HttpClient,
    logger=None,
) -> Optional[dict]:
    logger = logger or get_logger(__name__)

    if not api_key:
        return None

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    params = {
        "api_key": api_key,
        "text": endereco,
        "boundary.country": "BR",
        "size": 1,
        "focus.point.lat": focus_lat,
        "focus.point.lon": focus_lon,
    }

    try:
        response = http_client.get(
            OPENROUTE_GEOCODE_URL,
            headers=headers,
            params=params,
            timeout=10,
        )
    except requests.exceptions.Timeout:
        logger.error("Timeout ao geocodificar: %s", endereco)
        return None
    except Exception as exc:
        logger.error("Erro ao geocodificar: %s", exc)
        return None

    if response.status_code != 200:
        logger.error("Geocodificação falhou: %s", response.status_code)
        return None

    data = response.json()
    features = data.get("features", [])

    if not features:
        logger.debug("Nenhum resultado encontrado")
        return None

    feature = features[0]
    coords = feature["geometry"]["coordinates"]
    properties = feature.get("properties", {})

    return {
        "coords": (coords[0], coords[1]),
        "properties": properties,
    }


def calcular_rota_openroute(
    coords_origem: Tuple[float, float],
    coords_destino: Tuple[float, float],
    api_key: str,
    http_client: HttpClient,
    logger=None,
):
    logger = logger or get_logger(__name__)

    if not api_key:
        return None

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    body = {
        "coordinates": [
            list(coords_origem),
            list(coords_destino),
        ]
    }

    try:
        response = http_client.post(
            OPENROUTE_DIRECTIONS_URL,
            headers=headers,
            json=body,
            timeout=10,
        )
    except requests.exceptions.Timeout:
        logger.error("Timeout ao calcular rota com OpenRouteService")
        return None
    except Exception as exc:
        logger.error("Erro ao calcular rota com OpenRouteService: %s", exc)
        return None

    if response.status_code != 200:
        logger.error("OpenRouteService retornou status %s: %s", response.status_code, response.text[:200])
        return None

    data = response.json()
    routes = data.get("routes", [])
    if not routes:
        logger.debug("OpenRouteService não retornou rotas")
        return None

    return routes[0]
