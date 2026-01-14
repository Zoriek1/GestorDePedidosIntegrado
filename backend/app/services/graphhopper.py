# -*- coding: utf-8 -*-
"""
Serviço de Cálculo de Rotas usando GraphHopper
Calcula rotas simples e otimizadas com múltiplos waypoints
"""
import math
import os
from typing import Dict, List, Optional, Tuple

import requests


class GraphHopperService:
    """Serviço para cálculo de rotas usando GraphHopper API"""

    # API pública do GraphHopper
    ROUTE_URL = "https://graphhopper.com/api/1/route"
    OPTIMIZE_URL = "https://graphhopper.com/api/1/vrp"  # Vehicle Routing Problem (otimização)

    # Debug mode
    DEBUG = True

    def __init__(self):
        self.api_key = os.environ.get("GRAPHHOPPER_API_KEY", "")
        # Variável é opcional - não mostrar avisos desnecessários
        # O sistema funciona sem ela (usa fallback)
        if self.api_key and self.DEBUG:
            print("[DEBUG] GraphHopper API key configurada")

    def calcular_rota(
        self,
        coords_origem: Tuple[float, float],
        coords_destino: Tuple[float, float],
        vehicle: str = "car",
    ) -> Optional[Dict]:
        """
        Calcula rota entre dois pontos usando GraphHopper

        Args:
            coords_origem: Tuple (latitude, longitude) do ponto de origem
            coords_destino: Tuple (latitude, longitude) do ponto de destino
            vehicle: Tipo de veículo ('car', 'bike', 'foot', etc.)

        Returns:
            Dict com distancia_km, duracao_min, coords_origem, coords_destino, ou None se falhar
        """
        if not coords_origem or not coords_destino:
            return None

        # Se não tiver API key, retornar None imediatamente (não tentar usar API)
        if not self.api_key:
            if self.DEBUG:
                # GRAPHHOPPER_API_KEY é opcional - usar fallback silenciosamente
                pass
            return None

        # GraphHopper usa formato: point=lat,lon
        origem_str = f"{coords_origem[0]},{coords_origem[1]}"
        destino_str = f"{coords_destino[0]},{coords_destino[1]}"

        if self.DEBUG:
            print("\n[DEBUG] --- Calculando Rota GraphHopper ---")
            print(f"[DEBUG] Origem:  {origem_str}")
            print(f"[DEBUG] Destino: {destino_str}")
            print(f"[DEBUG] Veículo: {vehicle}")

        try:
            # Construir URL manualmente para garantir múltiplos parâmetros 'point'
            # A biblioteca requests não monta corretamente listas em query params
            url = f"{self.ROUTE_URL}?point={origem_str}&point={destino_str}&vehicle={vehicle}&key={self.api_key}&type=json&instructions=false&calc_points=false"

            if self.DEBUG:
                print(f"[DEBUG] URL: {url[:100]}...")

            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                paths = data.get("paths", [])

                if paths:
                    path = paths[0]
                    distancia_metros = path.get("distance", 0)
                    duracao_segundos = path.get("time", 0) / 1000  # GraphHopper retorna em ms

                    distancia_km = round(distancia_metros / 1000, 2)
                    duracao_min = round(duracao_segundos / 60, 1)

                    if self.DEBUG:
                        print(f"[DEBUG] Resultado: {distancia_km} km, {duracao_min} min")

                    return {
                        "distancia_km": distancia_km,
                        "duracao_min": duracao_min,
                        "coords_origem": coords_origem,
                        "coords_destino": coords_destino,
                    }
            else:
                if self.DEBUG:
                    print(
                        f"[DEBUG] GraphHopper erro: {response.status_code} - {response.text[:200]}"
                    )

        except requests.exceptions.Timeout:
            if self.DEBUG:
                print("[DEBUG] Timeout ao calcular rota com GraphHopper")
        except Exception as e:
            if self.DEBUG:
                print(f"[DEBUG] Erro GraphHopper: {e}")

        return None

    def calcular_rota_otimizada(
        self,
        coords_origem: Tuple[float, float],
        waypoints: List[Tuple[float, float]],
        retornar_origem: bool = True,
        vehicle: str = "car",
    ) -> Optional[Dict]:
        """
        Calcula rota otimizada com múltiplos waypoints

        Args:
            coords_origem: Tuple (latitude, longitude) do ponto de partida
            waypoints: Lista de tuplas (latitude, longitude) dos pontos de parada
            retornar_origem: Se True, retorna ao ponto de origem após visitar todos os waypoints
            vehicle: Tipo de veículo

        Returns:
            Dict com distancia_total_km, duracao_total_min, sequencia_otimizada, ou None se falhar
        """
        if not coords_origem or not waypoints or len(waypoints) == 0:
            return None

        if self.DEBUG:
            print("\n[DEBUG] --- Calculando Rota Otimizada ---")
            print(f"[DEBUG] Origem: {coords_origem}")
            print(f"[DEBUG] Waypoints: {len(waypoints)} pontos")
            print(f"[DEBUG] Retornar origem: {retornar_origem}")

        # Para poucos waypoints, usar heurística Nearest Neighbor
        # Para muitos waypoints, calcular todas as combinações pode ser lento
        if len(waypoints) <= 5:
            return self._calcular_rota_otimizada_exata(
                coords_origem, waypoints, retornar_origem, vehicle
            )
        else:
            return self._calcular_rota_otimizada_heuristica(
                coords_origem, waypoints, retornar_origem, vehicle
            )

    def _calcular_rota_otimizada_exata(
        self,
        coords_origem: Tuple[float, float],
        waypoints: List[Tuple[float, float]],
        retornar_origem: bool,
        vehicle: str,
    ) -> Optional[Dict]:
        """Calcula rota otimizada testando todas as permutações (para poucos waypoints)"""
        from itertools import permutations

        melhor_distancia = float("inf")
        melhor_sequencia = None
        melhor_resultado = None

        # Testar todas as permutações dos waypoints
        for perm in permutations(waypoints):
            sequencia = [coords_origem] + list(perm)
            if retornar_origem:
                sequencia.append(coords_origem)

            # Calcular distância total desta sequência
            distancia_total = 0
            duracao_total = 0

            for i in range(len(sequencia) - 1):
                rota = self.calcular_rota(sequencia[i], sequencia[i + 1], vehicle)
                if rota:
                    distancia_total += rota["distancia_km"]
                    duracao_total += rota["duracao_min"]
                else:
                    distancia_total = float("inf")
                    break

            if distancia_total < melhor_distancia:
                melhor_distancia = distancia_total
                melhor_sequencia = list(perm)
                melhor_resultado = {
                    "distancia_total_km": round(distancia_total, 2),
                    "duracao_total_min": round(duracao_total, 1),
                    "sequencia_otimizada": melhor_sequencia,
                    "num_waypoints": len(waypoints),
                }

        return melhor_resultado

    def _calcular_rota_otimizada_heuristica(
        self,
        coords_origem: Tuple[float, float],
        waypoints: List[Tuple[float, float]],
        retornar_origem: bool,
        vehicle: str,
    ) -> Optional[Dict]:
        """Calcula rota otimizada usando heurística Nearest Neighbor (mais rápida)"""
        waypoints_restantes = waypoints.copy()
        sequencia = []
        ponto_atual = coords_origem
        distancia_total = 0
        duracao_total = 0

        # Algoritmo Nearest Neighbor: sempre escolhe o waypoint mais próximo
        while waypoints_restantes:
            menor_distancia = float("inf")
            proximo_waypoint = None
            proximo_indice = None

            for i, waypoint in enumerate(waypoints_restantes):
                # Calcular distância em linha reta (haversine) para escolher o mais próximo
                dist = self._haversine_distance(ponto_atual, waypoint)
                if dist < menor_distancia:
                    menor_distancia = dist
                    proximo_waypoint = waypoint
                    proximo_indice = i

            if proximo_waypoint:
                sequencia.append(proximo_waypoint)
                waypoints_restantes.pop(proximo_indice)

                # Calcular rota real até este waypoint
                rota = self.calcular_rota(ponto_atual, proximo_waypoint, vehicle)
                if rota:
                    distancia_total += rota["distancia_km"]
                    duracao_total += rota["duracao_min"]
                    ponto_atual = proximo_waypoint
                else:
                    # Se falhar, usar distância em linha reta como fallback
                    distancia_total += menor_distancia
                    duracao_total += menor_distancia * 0.5  # Estimativa: 0.5 min/km
                    ponto_atual = proximo_waypoint

        # Retornar à origem se solicitado
        if retornar_origem:
            rota_retorno = self.calcular_rota(ponto_atual, coords_origem, vehicle)
            if rota_retorno:
                distancia_total += rota_retorno["distancia_km"]
                duracao_total += rota_retorno["duracao_min"]
            else:
                dist_retorno = self._haversine_distance(ponto_atual, coords_origem)
                distancia_total += dist_retorno
                duracao_total += dist_retorno * 0.5

        return {
            "distancia_total_km": round(distancia_total, 2),
            "duracao_total_min": round(duracao_total, 1),
            "sequencia_otimizada": sequencia,
            "num_waypoints": len(waypoints),
            "metodo": "nearest_neighbor",
        }

    def _haversine_distance(
        self, coord1: Tuple[float, float], coord2: Tuple[float, float]
    ) -> float:
        """
        Calcula distância em linha reta entre dois pontos (Haversine)

        Returns:
            Distância em km
        """
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        R = 6371  # Raio da Terra em km

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        )

        c = 2 * math.asin(math.sqrt(a))
        distancia = R * c

        return round(distancia, 2)

    def otimizar_ordem_waypoints(
        self, coords_origem: Tuple[float, float], waypoints: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Otimiza ordem dos waypoints para menor distância total
        Retorna apenas a sequência otimizada, sem calcular rotas completas

        Args:
            coords_origem: Ponto de partida
            waypoints: Lista de waypoints

        Returns:
            Lista de waypoints na ordem otimizada
        """
        if len(waypoints) <= 1:
            return waypoints

        resultado = self._calcular_rota_otimizada_heuristica(
            coords_origem, waypoints, retornar_origem=False, vehicle="car"
        )

        if resultado:
            return resultado.get("sequencia_otimizada", waypoints)

        return waypoints


# Instância global do serviço
graphhopper_service = GraphHopperService()
