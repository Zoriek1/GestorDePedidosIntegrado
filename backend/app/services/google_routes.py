# -*- coding: utf-8 -*-
"""
Serviço de Cálculo de Rotas usando Google Routes API v2.

Provider primário para distância/duração de rotas.
Fallback: GraphHopper → OpenRouteService → Haversine.
"""
import os
from typing import Dict, List, Optional, Tuple

import requests

# Tipo: (lat, lon)
Coord = Tuple[float, float]

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


def _parse_duration_seconds(duration_str: str) -> float:
    """Converte duração no formato '600s' para minutos."""
    try:
        return int(str(duration_str).rstrip("s")) / 60
    except (ValueError, TypeError):
        return 0.0


class GoogleRoutesService:
    """Cálculo de rotas via Google Routes API v2."""

    DEBUG = True

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")

    def _make_waypoint(self, coord: Coord) -> Dict:
        return {"location": {"latLng": {"latitude": coord[0], "longitude": coord[1]}}}

    # ------------------------------------------------------------------
    # Rota simples A → B
    # ------------------------------------------------------------------

    def calcular_rota(
        self,
        origem: Coord,
        destino: Coord,
    ) -> Optional[Dict]:
        """
        Calcula rota entre dois pontos.

        Args:
            origem: (lat, lon)
            destino: (lat, lon)

        Returns:
            Dict com distancia_km, duracao_min ou None
        """
        if not self.api_key:
            if self.DEBUG:
                print("[GoogleRoutes] GOOGLE_MAPS_API_KEY não configurada")
            return None

        try:
            payload = {
                "origin": self._make_waypoint(origem),
                "destination": self._make_waypoint(destino),
                "travelMode": "DRIVE",
                "languageCode": "pt-BR",
            }
            headers = {
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
            }

            if self.DEBUG:
                print(f"[GoogleRoutes] Rota: {origem} → {destino}")

            resp = requests.post(ROUTES_URL, json=payload, headers=headers, timeout=15)
            data = resp.json()

            routes = data.get("routes") or []
            if not routes:
                if self.DEBUG:
                    print(f"[GoogleRoutes] Sem rota retornada: {data.get('error', {})}")
                return None

            route = routes[0]
            distancia_km = round(route["distanceMeters"] / 1000, 2)
            duracao_min = round(_parse_duration_seconds(route["duration"]), 1)

            if self.DEBUG:
                print(f"[GoogleRoutes] ✓ {distancia_km} km, {duracao_min} min")

            return {
                "distancia_km": distancia_km,
                "duracao_min": duracao_min,
                "coords_origem": origem,
                "coords_destino": destino,
                "metodo": "google_routes",
            }

        except requests.exceptions.Timeout:
            if self.DEBUG:
                print("[GoogleRoutes] Timeout")
        except Exception as e:
            if self.DEBUG:
                print(f"[GoogleRoutes] Erro: {e}")

        return None

    # ------------------------------------------------------------------
    # Rota otimizada com waypoints
    # ------------------------------------------------------------------

    def calcular_rota_otimizada(
        self,
        origem: Coord,
        waypoints: List[Coord],
        retornar_origem: bool = True,
    ) -> Optional[Dict]:
        """
        Calcula rota otimizada com múltiplos waypoints via Google Routes API v2.

        Google otimiza a ordem automaticamente com optimizeWaypointOrder=true.

        Args:
            origem: (lat, lon) da floricultura
            waypoints: Lista de (lat, lon) das paradas
            retornar_origem: Se True, destino = origem (circuito)

        Returns:
            Dict com distancia_total_km, duracao_total_min,
            sequencia_otimizada, waypoint_order
        """
        if not self.api_key:
            if self.DEBUG:
                print("[GoogleRoutes] GOOGLE_MAPS_API_KEY não configurada")
            return None

        if not waypoints:
            return None

        try:
            destino = origem if retornar_origem else waypoints[-1]
            intermediates = waypoints if retornar_origem else waypoints[:-1]

            payload = {
                "origin": self._make_waypoint(origem),
                "destination": self._make_waypoint(destino),
                "intermediates": [self._make_waypoint(w) for w in intermediates],
                "travelMode": "DRIVE",
                "languageCode": "pt-BR",
                "optimizeWaypointOrder": True,
            }
            headers = {
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": (
                    "routes.duration,routes.distanceMeters,"
                    "routes.legs,routes.optimizedIntermediateWaypointIndex"
                ),
            }

            if self.DEBUG:
                print(f"[GoogleRoutes] Rota otimizada: {len(waypoints)} paradas")

            resp = requests.post(ROUTES_URL, json=payload, headers=headers, timeout=20)
            data = resp.json()

            routes = data.get("routes") or []
            if not routes:
                if self.DEBUG:
                    print(f"[GoogleRoutes] Sem rota retornada: {data.get('error', {})}")
                return None

            route = routes[0]
            waypoint_order = route.get(
                "optimizedIntermediateWaypointIndex", list(range(len(intermediates)))
            )

            distancia_km = round(route["distanceMeters"] / 1000, 2)
            duracao_min = round(_parse_duration_seconds(route["duration"]), 1)

            # Reordenar waypoints conforme Google otimizou
            sequencia_otimizada = [intermediates[i] for i in waypoint_order]

            if self.DEBUG:
                print(
                    f"[GoogleRoutes] ✓ Rota otimizada: {distancia_km} km, "
                    f"{duracao_min} min, ordem={waypoint_order}"
                )

            return {
                "distancia_total_km": distancia_km,
                "duracao_total_min": duracao_min,
                "sequencia_otimizada": sequencia_otimizada,
                "waypoint_order": waypoint_order,
                "num_waypoints": len(waypoints),
                "metodo": "google_routes",
            }

        except requests.exceptions.Timeout:
            if self.DEBUG:
                print("[GoogleRoutes] Timeout na rota otimizada")
        except Exception as e:
            if self.DEBUG:
                print(f"[GoogleRoutes] Erro na rota otimizada: {e}")

        return None


# Instância global
google_routes_service = GoogleRoutesService()
