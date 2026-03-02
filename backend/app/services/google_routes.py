# -*- coding: utf-8 -*-
"""
Serviço de Cálculo de Rotas usando Google Directions API.

Provider primário para distância/duração de rotas.
Fallback: GraphHopper → OpenRouteService → Haversine.
"""
import os
from typing import Dict, List, Optional, Tuple

import requests

# Tipo: (lat, lon)
Coord = Tuple[float, float]

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"


class GoogleRoutesService:
    """Cálculo de rotas via Google Directions API."""

    DEBUG = True

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")

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
            params = {
                "origin": f"{origem[0]},{origem[1]}",
                "destination": f"{destino[0]},{destino[1]}",
                "mode": "driving",
                "language": "pt-BR",
                "key": self.api_key,
            }

            if self.DEBUG:
                print(f"[GoogleRoutes] Rota: {params['origin']} → {params['destination']}")

            resp = requests.get(DIRECTIONS_URL, params=params, timeout=15)
            data = resp.json()

            if data.get("status") != "OK":
                if self.DEBUG:
                    print(f"[GoogleRoutes] Erro: {data.get('status')} - {data.get('error_message', '')}")
                return None

            route = data["routes"][0]
            leg = route["legs"][0]

            distancia_km = round(leg["distance"]["value"] / 1000, 2)
            duracao_min = round(leg["duration"]["value"] / 60, 1)

            if self.DEBUG:
                print(f"[GoogleRoutes] ✓ {distancia_km} km, {duracao_min} min")

            return {
                "distancia_km": distancia_km,
                "duracao_min": duracao_min,
                "coords_origem": origem,
                "coords_destino": destino,
                "metodo": "google_directions",
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
        Calcula rota otimizada com múltiplos waypoints via Google Directions.

        Google otimiza a ordem automaticamente com optimize:true.

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
            origin_str = f"{origem[0]},{origem[1]}"
            destination_str = origin_str if retornar_origem else f"{waypoints[-1][0]},{waypoints[-1][1]}"

            # Waypoints com optimize:true para Google reordenar
            wp_list = waypoints if retornar_origem else waypoints[:-1]
            waypoints_str = "optimize:true|" + "|".join(
                f"{w[0]},{w[1]}" for w in wp_list
            )

            params = {
                "origin": origin_str,
                "destination": destination_str,
                "waypoints": waypoints_str,
                "mode": "driving",
                "language": "pt-BR",
                "key": self.api_key,
            }

            if self.DEBUG:
                print(f"[GoogleRoutes] Rota otimizada: {len(waypoints)} paradas")

            resp = requests.get(DIRECTIONS_URL, params=params, timeout=20)
            data = resp.json()

            if data.get("status") != "OK":
                if self.DEBUG:
                    print(f"[GoogleRoutes] Erro: {data.get('status')} - {data.get('error_message', '')}")
                return None

            route = data["routes"][0]
            waypoint_order = route.get("waypoint_order", list(range(len(wp_list))))

            # Somar distância e duração de todas as legs
            distancia_total = 0
            duracao_total = 0
            for leg in route["legs"]:
                distancia_total += leg["distance"]["value"]
                duracao_total += leg["duration"]["value"]

            distancia_km = round(distancia_total / 1000, 2)
            duracao_min = round(duracao_total / 60, 1)

            # Reordenar waypoints conforme Google otimizou
            sequencia_otimizada = [wp_list[i] for i in waypoint_order]

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
                "metodo": "google_directions",
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

