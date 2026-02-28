# -*- coding: utf-8 -*-
"""
Testes para app.utils.google_maps_url
Validação de URLs do Google Maps (formato ?api=1) e fallback step-by-step.
"""
from urllib.parse import parse_qs, urlparse

from app.utils.google_maps_url import (
    build_google_maps_url,
    build_step_by_step_urls,
)

# Coordenadas de teste (Goiânia)
FLORICULTURA = (-16.6869, -49.2648)
STOP_A = (-16.7000, -49.2500)
STOP_B = (-16.7200, -49.2300)
STOP_C = (-16.6500, -49.2800)


# ── build_google_maps_url ─────────────────────────────────────────────


def test_build_url_returns_none_when_no_stops():
    assert build_google_maps_url(FLORICULTURA, []) is None


def test_build_url_single_stop_return_to_origin():
    url = build_google_maps_url(FLORICULTURA, [STOP_A])
    assert url is not None

    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.hostname == "www.google.com"
    assert parsed.path == "/maps/dir/"

    params = parse_qs(parsed.query)
    assert params["api"] == ["1"]
    assert params["travelmode"] == ["driving"]
    # Destino é a origem (retorno)
    assert params["destination"] == [f"{FLORICULTURA[0]},{FLORICULTURA[1]}"]
    # Waypoint é o stop
    assert f"{STOP_A[0]},{STOP_A[1]}" in params["waypoints"][0]


def test_build_url_multiple_stops_return_to_origin():
    url = build_google_maps_url(FLORICULTURA, [STOP_A, STOP_B])
    assert url is not None

    params = parse_qs(urlparse(url).query)
    waypoints_str = params["waypoints"][0]
    # Pipe-separated
    assert "|" in waypoints_str
    assert f"{STOP_A[0]},{STOP_A[1]}" in waypoints_str
    assert f"{STOP_B[0]},{STOP_B[1]}" in waypoints_str
    # Destino = origem
    assert params["destination"] == [f"{FLORICULTURA[0]},{FLORICULTURA[1]}"]


def test_build_url_no_return_to_origin():
    url = build_google_maps_url(FLORICULTURA, [STOP_A, STOP_B], return_to_origin=False)
    params = parse_qs(urlparse(url).query)
    # Destino = último stop
    assert params["destination"] == [f"{STOP_B[0]},{STOP_B[1]}"]
    # Waypoints = todos menos o último
    waypoints_str = params["waypoints"][0]
    assert f"{STOP_A[0]},{STOP_A[1]}" in waypoints_str
    assert f"{STOP_B[0]},{STOP_B[1]}" not in waypoints_str


def test_build_url_custom_travel_mode():
    url = build_google_maps_url(FLORICULTURA, [STOP_A], travel_mode="walking")
    params = parse_qs(urlparse(url).query)
    assert params["travelmode"] == ["walking"]


# ── build_step_by_step_urls ───────────────────────────────────────────


def test_step_by_step_empty_stops():
    assert build_step_by_step_urls(FLORICULTURA, []) == []


def test_step_by_step_single_stop_with_return():
    segments = build_step_by_step_urls(FLORICULTURA, [STOP_A])
    # Floricultura → Stop A (step 1) + Stop A → Floricultura (step 2)
    assert len(segments) == 2

    assert segments[0]["step"] == 1
    assert "Floricultura" in segments[0]["label"]
    assert "Entrega 1" in segments[0]["label"]
    assert "api=1" in segments[0]["url"]

    assert segments[1]["step"] == 2
    assert "Floricultura" in segments[1]["label"]


def test_step_by_step_multiple_stops_with_return():
    segments = build_step_by_step_urls(FLORICULTURA, [STOP_A, STOP_B, STOP_C])
    # 3 stops + return = 4 segments
    assert len(segments) == 4
    # Steps sequenciais
    assert [s["step"] for s in segments] == [1, 2, 3, 4]
    # Último segmento volta à floricultura
    assert "Floricultura" in segments[-1]["label"]


def test_step_by_step_no_return():
    segments = build_step_by_step_urls(FLORICULTURA, [STOP_A, STOP_B], return_to_origin=False)
    # 2 stops, sem retorno = 2 segments
    assert len(segments) == 2
    # Não deve ter segmento de volta à floricultura
    assert "Floricultura" not in segments[-1]["label"]


def test_step_by_step_urls_are_valid():
    """Cada URL step-by-step deve ter formato ?api=1 válido."""
    segments = build_step_by_step_urls(FLORICULTURA, [STOP_A, STOP_B])
    for seg in segments:
        parsed = urlparse(seg["url"])
        params = parse_qs(parsed.query)
        assert params["api"] == ["1"]
        assert "origin" in params
        assert "destination" in params
        assert params["travelmode"] == ["driving"]
