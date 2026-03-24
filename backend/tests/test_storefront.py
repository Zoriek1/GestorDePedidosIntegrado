# -*- coding: utf-8 -*-
"""
Testes do endpoint storefront e do método list_products do NuvemshopClient.

Cobre:
- _variant_price: extração de preço de variante (promocional > normal, formatos)
- _build_summary: construção do resumo de variantes por produto
- NuvemshopClient.list_products: HTTP GET com paginação
- GET /storefront/produtos-variantes: endpoint completo (cache, CORS, erros)
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.integrations.nuvemshop.client import NuvemshopClient
from app.models.nuvemshop_store import NuvemshopStore
from app.routes.storefront import _build_summary, _variant_price  # noqa: I001

# ---------------------------------------------------------------------------
# Helpers: _variant_price
# ---------------------------------------------------------------------------


class TestVariantPrice:
    def test_usa_preco_promocional_quando_disponivel(self):
        variant = {"price": "100.00", "promotional_price": "79.90"}
        assert _variant_price(variant) == pytest.approx(79.90)

    def test_usa_preco_normal_quando_sem_promocional(self):
        variant = {"price": "99.99", "promotional_price": None}
        assert _variant_price(variant) == pytest.approx(99.99)

    def test_ignora_preco_promocional_zero(self):
        variant = {"price": "50.00", "promotional_price": "0.00"}
        assert _variant_price(variant) == pytest.approx(50.00)

    def test_ignora_preco_promocional_vazio(self):
        variant = {"price": "45.00", "promotional_price": ""}
        assert _variant_price(variant) == pytest.approx(45.00)

    def test_retorna_none_quando_sem_preco(self):
        assert _variant_price({}) is None
        assert _variant_price({"price": None}) is None
        assert _variant_price({"price": ""}) is None

    def test_preco_com_virgula(self):
        # "49,90" → float("49.90") deve funcionar
        assert _variant_price({"price": "49,90", "promotional_price": None}) == pytest.approx(49.90)

    def test_preco_string_inteiro(self):
        variant = {"price": "120", "promotional_price": None}
        assert _variant_price(variant) == pytest.approx(120.0)


# ---------------------------------------------------------------------------
# Helpers: _build_summary
# ---------------------------------------------------------------------------


class TestBuildSummary:
    def _product(self, pid, variants):
        return {"id": pid, "variants": variants}

    def _variant(self, price, promo=None):
        return {"price": str(price), "promotional_price": str(promo) if promo else None}

    def test_produto_com_preco_unico(self):
        products = [self._product(10, [self._variant(50), self._variant(50)])]
        summary = _build_summary(products)
        assert "10" in summary
        assert summary["10"]["minPrice"] == pytest.approx(50.0)
        assert summary["10"]["hasDifferentPrices"] is False

    def test_produto_com_precos_diferentes(self):
        products = [self._product(20, [self._variant(30), self._variant(50), self._variant(80)])]
        summary = _build_summary(products)
        assert summary["20"]["minPrice"] == pytest.approx(30.0)
        assert summary["20"]["hasDifferentPrices"] is True

    def test_produto_com_preco_promocional(self):
        # Uma variante com promo 40, outra sem promo em 70
        products = [self._product(30, [self._variant(70, promo=40), self._variant(70)])]
        summary = _build_summary(products)
        # preços efetivos: [40, 70] → diferentes, min=40
        assert summary["30"]["minPrice"] == pytest.approx(40.0)
        assert summary["30"]["hasDifferentPrices"] is True

    def test_produto_sem_variantes_excluido(self):
        products = [self._product(40, [])]
        summary = _build_summary(products)
        assert "40" not in summary

    def test_produto_sem_id_ignorado(self):
        products = [{"id": None, "variants": [self._variant(10)]}]
        summary = _build_summary(products)
        assert summary == {}

    def test_multiplos_produtos(self):
        products = [
            self._product(1, [self._variant(10)]),
            self._product(2, [self._variant(20), self._variant(30)]),
            self._product(3, []),
        ]
        summary = _build_summary(products)
        assert set(summary.keys()) == {"1", "2"}
        assert summary["1"]["hasDifferentPrices"] is False
        assert summary["2"]["hasDifferentPrices"] is True

    def test_produto_com_variante_sem_preco_ignorado(self):
        products = [self._product(50, [{"price": None, "promotional_price": None}])]
        summary = _build_summary(products)
        assert "50" not in summary


# ---------------------------------------------------------------------------
# NuvemshopClient.list_products
# ---------------------------------------------------------------------------


class TestListProducts:
    def _client(self):
        return NuvemshopClient(
            store_id="999",
            access_token="token-abc",
            user_agent="TestApp (test@test.com)",
        )

    @patch("app.integrations.nuvemshop.client.requests.get")
    def test_retorna_lista_de_produtos(self, mock_get):
        payload = [{"id": 1, "variants": []}, {"id": 2, "variants": []}]
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = payload
        mock_get.return_value = mock_resp

        result = self._client().list_products()
        assert result == payload
        mock_get.assert_called_once()

    @patch("app.integrations.nuvemshop.client.requests.get")
    def test_envia_fields_e_per_page(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_get.return_value = mock_resp

        self._client().list_products(fields="id,variants", per_page=50, page=2)
        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["fields"] == "id,variants"
        assert params["per_page"] == 50
        assert params["page"] == 2

    @patch("app.integrations.nuvemshop.client.requests.get")
    def test_retorna_lista_vazia_se_api_retornar_dict(self, mock_get):
        # Garante que resposta inesperada (dict em vez de list) não quebra
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": "something"}
        mock_get.return_value = mock_resp

        result = self._client().list_products()
        assert result == []

    @patch("app.integrations.nuvemshop.client.requests.get")
    def test_propaga_erro_http(self, mock_get):
        import requests as req

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("404")
        mock_get.return_value = mock_resp

        with pytest.raises(req.HTTPError):
            self._client().list_products()


# ---------------------------------------------------------------------------
# Endpoint GET /storefront/produtos-variantes
# ---------------------------------------------------------------------------


class TestStorefrontEndpoint:
    def _create_store(self, db, store_id="12345"):
        store = NuvemshopStore(
            store_id=store_id,
            access_token="fake-token",
            active=True,
        )
        db.session.add(store)
        db.session.commit()
        return store

    def _nuvemshop_products(self):
        return [
            {
                "id": 101,
                "variants": [
                    {"price": "50.00", "promotional_price": None},
                    {"price": "80.00", "promotional_price": None},
                ],
            },
            {
                "id": 202,
                "variants": [
                    {"price": "30.00", "promotional_price": "25.00"},
                    {"price": "30.00", "promotional_price": "25.00"},
                ],
            },
        ]

    @patch("app.routes.storefront._fetch_all_products")
    @patch("app.routes.storefront.Config")
    def test_retorna_resumo_correto(self, mock_config, mock_fetch, client, app):
        mock_config.NUVEMSHOP_USER_AGENT = "TestApp (test@test.com)"
        from app import db

        with app.app_context():
            self._create_store(db)

        mock_fetch.return_value = self._nuvemshop_products()

        resp = client.get("/storefront/produtos-variantes")
        assert resp.status_code == 200
        data = json.loads(resp.data)

        assert "101" in data
        assert data["101"]["minPrice"] == pytest.approx(50.0)
        assert data["101"]["hasDifferentPrices"] is True

        assert "202" in data
        assert data["202"]["minPrice"] == pytest.approx(25.0)
        assert data["202"]["hasDifferentPrices"] is False

    @patch("app.routes.storefront._fetch_all_products")
    @patch("app.routes.storefront.Config")
    def test_cors_header_presente(self, mock_config, mock_fetch, client, app):
        mock_config.NUVEMSHOP_USER_AGENT = "TestApp (test@test.com)"
        from app import db

        with app.app_context():
            self._create_store(db)

        mock_fetch.return_value = self._nuvemshop_products()

        resp = client.get("/storefront/produtos-variantes")
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    def test_options_retorna_cors(self, client):
        resp = client.options("/storefront/produtos-variantes")
        assert resp.status_code == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    def test_sem_loja_retorna_404(self, client):
        resp = client.get("/storefront/produtos-variantes")
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data.get("error") == "store_not_found"

    @patch("app.routes.storefront._fetch_all_products")
    @patch("app.routes.storefront.Config")
    def test_usa_cache_na_segunda_chamada(self, mock_config, mock_fetch, client, app):
        mock_config.NUVEMSHOP_USER_AGENT = "TestApp (test@test.com)"
        from app import db
        from app.routes import storefront as sf_module

        # Limpar cache antes do teste
        sf_module._cache.clear()

        with app.app_context():
            self._create_store(db)

        mock_fetch.return_value = self._nuvemshop_products()

        client.get("/storefront/produtos-variantes")
        client.get("/storefront/produtos-variantes")

        # fetch chamado apenas 1x (segunda chamada usa cache)
        assert mock_fetch.call_count == 1

    @patch("app.routes.storefront._fetch_all_products")
    def test_sem_nuvemshop_user_agent_retorna_503(self, mock_fetch, client, app):
        from app import db
        from app.config import Config

        with app.app_context():
            self._create_store(db)

        original = Config.NUVEMSHOP_USER_AGENT
        Config.NUVEMSHOP_USER_AGENT = ""
        try:
            resp = client.get("/storefront/produtos-variantes")
            assert resp.status_code == 503
        finally:
            Config.NUVEMSHOP_USER_AGENT = original
        mock_fetch.assert_not_called()

    @patch("app.routes.storefront._fetch_all_products")
    @patch("app.routes.storefront.Config")
    def test_erro_na_api_retorna_502(self, mock_config, mock_fetch, client, app):
        mock_config.NUVEMSHOP_USER_AGENT = "TestApp (test@test.com)"
        from app import db
        from app.routes import storefront as sf_module

        sf_module._cache.clear()

        with app.app_context():
            self._create_store(db)

        mock_fetch.side_effect = Exception("timeout")

        resp = client.get("/storefront/produtos-variantes")
        assert resp.status_code == 502

    def test_serve_nuvemshop_legado_js(self, client):
        resp = client.get("/storefront/nuvemshop-legado.js")
        assert resp.status_code == 200
        assert "application/javascript" in (resp.headers.get("Content-Type") or "")
        assert b"nuvemshop-legado-v1" in resp.data

    def test_alias_storefront_script_js(self, client):
        r1 = client.get("/storefront/nuvemshop-legado.js")
        r2 = client.get("/storefront/storefront-script.js")
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.data == r2.data
