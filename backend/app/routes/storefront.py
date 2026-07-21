# -*- coding: utf-8 -*-
"""
Endpoints públicos para o storefront (scripts Nuvemshop no frontend da loja).

Rota base: /storefront/
CORS: Access-Control-Allow-Origin: * (dados públicos — preços visíveis na loja)
Cache: in-memory com TTL de 5 minutos (evita hammer na API Nuvemshop)
"""

import logging
import time
from pathlib import Path

from flask import Blueprint, jsonify, make_response, request, send_from_directory

from app.config import Config
from app.integrations.nuvemshop.client import NuvemshopClient
from app.models.nuvemshop_store import NuvemshopStore

logger = logging.getLogger(__name__)

storefront_bp = Blueprint("storefront", __name__, url_prefix="/storefront")

_ASSETS_DIR = Path(__file__).parent.parent.parent / "storefront_assets"

# ---------------------------------------------------------------------------
# Cache in-memory simples (por store_id)
# ---------------------------------------------------------------------------
_cache: dict = {}
_CACHE_TTL = 300  # 5 minutos


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data) -> None:
    _cache[key] = {"ts": time.time(), "data": data}


# ---------------------------------------------------------------------------
# Helpers de extração de preço
# ---------------------------------------------------------------------------


def _variant_price(variant: dict) -> float | None:
    """Retorna o preço efetivo de uma variante (promocional > normal)."""
    for field in ("promotional_price", "price"):
        raw = variant.get(field)
        if raw is None or raw == "" or raw == "0.00":
            continue
        try:
            val = float(str(raw).replace(",", "."))
            if val > 0:
                return val
        except (ValueError, TypeError):
            continue
    return None


def _build_summary(products: list) -> dict:
    """
    Transforma lista de produtos da API Nuvemshop em resumo leve para o script.

    Retorna: { "<product_id>": { "minPrice": float, "hasDifferentPrices": bool } }
    """
    summary = {}
    for product in products:
        raw_id = product.get("id")
        if raw_id is None:
            continue
        pid = str(raw_id)
        if not pid:
            continue

        variants = product.get("variants") or []
        prices = []
        for v in variants:
            p = _variant_price(v)
            if p is not None:
                prices.append(p)

        if not prices:
            continue

        unique_prices = list(set(prices))
        summary[pid] = {
            "minPrice": min(prices),
            "hasDifferentPrices": len(unique_prices) >= 2,
        }

    return summary


def _fetch_all_products(client: NuvemshopClient) -> list:
    """Busca todos os produtos com paginação automática (máx 200/página)."""
    all_products = []
    page = 1
    while True:
        batch = client.list_products(fields="id,variants", per_page=200, page=page)
        if not batch:
            break
        all_products.extend(batch)
        if len(batch) < 200:
            break
        page += 1
    return all_products


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _cors_response(response):
    """Adiciona headers CORS abertos (dados públicos de preço da loja)."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


@storefront_bp.route("/produtos-variantes", methods=["GET", "OPTIONS"])
def get_produtos_variantes():
    """
    Retorna resumo de variantes de todos os produtos da loja.

    Query params:
        store_id (opcional): filtra por store específico; usa loja ativa por padrão

    Response:
        { "<product_id>": { "minPrice": float, "hasDifferentPrices": bool } }
    """
    if request.method == "OPTIONS":
        return _cors_response(jsonify({}))

    store_id = request.args.get("store_id")
    if store_id:
        store = NuvemshopStore.query.filter_by(store_id=str(store_id), active=True).first()
    else:
        store = (
            NuvemshopStore.query.filter_by(active=True).order_by(NuvemshopStore.id.desc()).first()
        )

    if not store:
        return _cors_response(jsonify({"error": "store_not_found"})), 404

    if not Config.NUVEMSHOP_USER_AGENT:
        return _cors_response(jsonify({"error": "backend_not_configured"})), 503

    cache_key = f"catalog_{store.store_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug("[storefront] cache hit para store_id=%s", store.store_id)
        return _cors_response(jsonify(cached))

    try:
        client = NuvemshopClient(
            store_id=str(store.store_id),
            access_token=store.decrypted_token,
            user_agent=Config.NUVEMSHOP_USER_AGENT,
        )
        products = _fetch_all_products(client)
        summary = _build_summary(products)
        _cache_set(cache_key, summary)
        logger.info(
            "[storefront] catalog gerado: %d produtos para store_id=%s",
            len(summary),
            store.store_id,
        )
        return _cors_response(jsonify(summary))

    except Exception as exc:
        logger.exception("[storefront] erro ao buscar produtos")
        return _cors_response(jsonify({"error": str(exc)})), 502


def _serve_storefront_js():
    """Serve o bundle JS do storefront (Nuvemshop legado) com CORS aberto."""
    response = make_response(send_from_directory(_ASSETS_DIR, "nuvemshop-legado.js"))
    response.headers["Content-Type"] = "application/javascript; charset=utf-8"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


@storefront_bp.route("/nuvemshop-legado.js", methods=["GET"])
def get_nuvemshop_legado_script():
    """URL preferida para o script injetado na loja."""
    return _serve_storefront_js()


@storefront_bp.route("/storefront-script.js", methods=["GET"])
def get_storefront_script():
    """Alias legado; mesmo ficheiro que /nuvemshop-legado.js."""
    return _serve_storefront_js()
