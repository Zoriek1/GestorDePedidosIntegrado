# -*- coding: utf-8 -*-
"""
Testes para app.services.google_geocoding
Foca na lógica pura (classify_confidence, _build_address_line, _is_within_goias).
Chamadas HTTP são mockadas para não depender de API key real.
"""
from unittest.mock import MagicMock, patch

from app.services.google_geocoding import GoogleGeocodingService

# ── classify_confidence (quality gate) ────────────────────────────────


def test_classify_rooftop_is_auto_ok():
    assert GoogleGeocodingService.classify_confidence("ROOFTOP") == "AUTO_OK"


def test_classify_range_interpolated_with_numero_and_cep():
    result = GoogleGeocodingService.classify_confidence(
        "RANGE_INTERPOLATED", has_numero=True, has_cep=True
    )
    assert result == "OK_WITH_CAUTION"


def test_classify_range_interpolated_with_inferred():
    result = GoogleGeocodingService.classify_confidence(
        "RANGE_INTERPOLATED", has_numero=True, has_cep=True, has_inferred=True
    )
    assert result == "NEEDS_REVIEW"


def test_classify_range_interpolated_without_numero():
    result = GoogleGeocodingService.classify_confidence(
        "RANGE_INTERPOLATED", has_numero=False, has_cep=True
    )
    assert result == "NEEDS_REVIEW"


def test_classify_geometric_center():
    assert GoogleGeocodingService.classify_confidence("GEOMETRIC_CENTER") == "NEEDS_REVIEW"


def test_classify_approximate():
    assert GoogleGeocodingService.classify_confidence("APPROXIMATE") == "NEEDS_REVIEW"


# ── _is_within_goias ─────────────────────────────────────────────────


def test_within_goias_valid():
    assert GoogleGeocodingService._is_within_goias(-16.6869, -49.2648) is True


def test_within_goias_aparecida():
    assert GoogleGeocodingService._is_within_goias(-16.8200, -49.2400) is True


def test_outside_goias_sao_paulo():
    assert GoogleGeocodingService._is_within_goias(-23.5505, -46.6333) is False


def test_outside_goias_north():
    assert GoogleGeocodingService._is_within_goias(-10.0, -49.0) is False


# ── _build_address_line ──────────────────────────────────────────────


def test_build_address_line_full():
    line = GoogleGeocodingService._build_address_line(
        rua="Rua 132",
        numero="289",
        bairro="Setor Sul",
        cidade="Goiânia",
        estado="GO",
        cep="74093-210",
    )
    assert "Rua 132" in line
    assert "289" in line
    assert "Setor Sul" in line
    assert "Goiânia - GO" in line
    assert "74093-210" in line
    assert "Brasil" in line


def test_build_address_line_minimal():
    line = GoogleGeocodingService._build_address_line(
        rua="Rua X", numero="", bairro="", cidade="", estado="", cep=""
    )
    assert "Rua X" in line
    assert "Goiânia" in line  # default
    assert "Brasil" in line


def test_build_address_line_cep_digits_only():
    line = GoogleGeocodingService._build_address_line(
        rua="Rua Y",
        numero="10",
        bairro="Centro",
        cidade="Goiânia",
        estado="GO",
        cep="74000100",
    )
    assert "74000-100" in line


# ── geocode (mock HTTP) ──────────────────────────────────────────────


def test_geocode_returns_none_without_api_key():
    svc = GoogleGeocodingService()
    svc.api_key = ""
    assert svc.geocode("Rua 132, 289, Goiânia") is None


def test_geocode_returns_none_for_empty_address():
    svc = GoogleGeocodingService()
    svc.api_key = "fake-key"
    assert svc.geocode("") is None
    assert svc.geocode("   ") is None


@patch("app.services.google_geocoding.requests.get")
def test_geocode_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "status": "OK",
        "results": [
            {
                "geometry": {
                    "location": {"lat": -16.6869, "lng": -49.2648},
                    "location_type": "ROOFTOP",
                },
                "place_id": "ChIJxyz123",
                "formatted_address": "Rua 132, 289 - Setor Sul, Goiânia - GO, Brasil",
            }
        ],
    }
    mock_get.return_value = mock_resp

    svc = GoogleGeocodingService()
    svc.api_key = "fake-key"
    svc.DEBUG = False

    result = svc.geocode("Rua 132, 289, Setor Sul, Goiânia")
    assert result is not None
    assert result["lat"] == -16.6869
    assert result["lng"] == -49.2648
    assert result["location_type"] == "ROOFTOP"
    assert result["place_id"] == "ChIJxyz123"


@patch("app.services.google_geocoding.requests.get")
def test_geocode_outside_goias_returns_none(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "status": "OK",
        "results": [
            {
                "geometry": {
                    "location": {"lat": -23.55, "lng": -46.63},  # São Paulo
                    "location_type": "ROOFTOP",
                },
                "place_id": "ChIJabc",
                "formatted_address": "SP",
            }
        ],
    }
    mock_get.return_value = mock_resp

    svc = GoogleGeocodingService()
    svc.api_key = "fake-key"
    svc.DEBUG = False

    assert svc.geocode("algum endereço errado") is None


@patch("app.services.google_geocoding.requests.get")
def test_geocode_zero_results(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "ZERO_RESULTS", "results": []}
    mock_get.return_value = mock_resp

    svc = GoogleGeocodingService()
    svc.api_key = "fake-key"
    svc.DEBUG = False

    assert svc.geocode("endereço inexistente xyz") is None


# ── validate_address (mock HTTP) ─────────────────────────────────────


def test_validate_address_returns_none_without_api_key():
    svc = GoogleGeocodingService()
    svc.api_key = ""
    assert svc.validate_address(rua="Rua 1") is None


@patch("app.services.google_geocoding.requests.post")
def test_validate_address_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": {
            "verdict": {
                "validationGranularity": "PREMISE",
                "hasInferredComponents": False,
                "hasReplacedComponents": False,
            },
            "geocode": {
                "location": {"latitude": -16.68, "longitude": -49.26},
                "placeId": "ChIJ_place",
            },
            "address": {
                "formattedAddress": "Rua 132, 289 - Setor Sul, Goiânia - GO",
            },
        }
    }
    mock_post.return_value = mock_resp

    svc = GoogleGeocodingService()
    svc.api_key = "fake-key"
    svc.DEBUG = False

    result = svc.validate_address(rua="Rua 132", numero="289", bairro="Setor Sul")
    assert result is not None
    assert result["verdict"] == "PREMISE"
    assert result["has_inferred_components"] is False
    assert result["geocode"]["lat"] == -16.68
    assert result["geocode"]["place_id"] == "ChIJ_place"
