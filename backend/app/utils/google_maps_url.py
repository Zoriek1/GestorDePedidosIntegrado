# -*- coding: utf-8 -*-
"""
Utilitário para construção de URLs do Google Maps (deep links).

Formato recomendado: https://www.google.com/maps/dir/?api=1&...
Ref: https://developers.google.com/maps/documentation/urls/get-started
"""
from typing import List, Optional, Tuple
from urllib.parse import quote

# Tipo: (lat, lon)
Coord = Tuple[float, float]

MAX_WAYPOINTS = 5  # Google Maps limita a ~9, mas 5 é mais confiável no app mobile


def build_google_maps_url(
    origin: Coord,
    stops: List[Coord],
    return_to_origin: bool = True,
    travel_mode: str = "driving",
) -> Optional[str]:
    """
    Constrói URL do Google Maps com formato ?api=1 (deep link confiável).

    Args:
        origin: (lat, lon) da origem (floricultura)
        stops: Lista de (lat, lon) das paradas
        return_to_origin: Se True, última parada retorna à origem
        travel_mode: driving, walking, bicycling, transit

    Returns:
        URL string ou None se não houver paradas
    """
    if not stops:
        return None

    origin_str = f"{origin[0]},{origin[1]}"

    if return_to_origin:
        destination_str = origin_str
        waypoints = stops
    else:
        destination_str = f"{stops[-1][0]},{stops[-1][1]}"
        waypoints = stops[:-1]

    # Construir waypoints pipe-separated
    waypoints_str = "|".join(f"{s[0]},{s[1]}" for s in waypoints)

    url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={quote(origin_str)}"
        f"&destination={quote(destination_str)}"
        f"&travelmode={travel_mode}"
    )

    if waypoints_str:
        url += f"&waypoints={quote(waypoints_str)}"

    return url


def build_step_by_step_urls(
    origin: Coord,
    stops: List[Coord],
    return_to_origin: bool = True,
    travel_mode: str = "driving",
) -> List[dict]:
    """
    Constrói URLs individuais segmento a segmento (fallback).
    Útil quando o app Google Maps tem problemas com muitos waypoints.

    Args:
        origin: (lat, lon) da origem
        stops: Lista de (lat, lon) das paradas
        return_to_origin: Se True, inclui segmento da última parada → origem
        travel_mode: driving, walking, bicycling, transit

    Returns:
        Lista de dicts com {step, label, url}
    """
    if not stops:
        return []

    segments = []
    all_points = [origin] + list(stops)
    if return_to_origin:
        all_points.append(origin)

    for i in range(len(all_points) - 1):
        from_coord = all_points[i]
        to_coord = all_points[i + 1]

        from_str = f"{from_coord[0]},{from_coord[1]}"
        to_str = f"{to_coord[0]},{to_coord[1]}"

        url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={quote(from_str)}"
            f"&destination={quote(to_str)}"
            f"&travelmode={travel_mode}"
        )

        # Labels
        if i == 0:
            label = f"Floricultura → Entrega {i + 1}"
        elif i == len(all_points) - 2 and return_to_origin:
            label = f"Entrega {i} → Floricultura"
        else:
            label = f"Entrega {i} → Entrega {i + 1}"

        segments.append(
            {
                "step": i + 1,
                "label": label,
                "url": url,
            }
        )

    return segments
