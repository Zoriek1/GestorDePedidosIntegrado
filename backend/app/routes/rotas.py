# -*- coding: utf-8 -*-
"""
Rotas de Otimização - Blueprint para endpoints de rotas otimizadas
"""
<<<<<<< HEAD
import os

=======
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
from flask import Blueprint, request

from app import db
from app.middleware import requires_any_role
from app.models import Pedido, RotaOtimizada
from app.schemas.common import error_response, success_response
from app.services.distancia import distancia_service
<<<<<<< HEAD
from app.services.graphhopper import graphhopper_service
=======
from app.utils.google_maps_url import build_google_maps_url, build_step_by_step_urls
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14

rotas_bp = Blueprint("rotas", __name__, url_prefix="/api/pedidos")


@rotas_bp.route("/rota-otimizada", methods=["POST"])
@requires_any_role("admin", "atendente", "entregador")
def calcular_rota_otimizada():
    """
    Calcula rota otimizada para múltiplos pedidos.

    Provider primário: Google Directions API (optimize:true).
    Fallback: GraphHopper nearest-neighbor heuristic.
    """
    try:
        data = request.get_json() or {}
        pedido_ids = data.get("pedido_ids", [])
        nome_rota = data.get("nome", "Rota Otimizada")

        if not pedido_ids:
            pedidos = Pedido.query.filter(
<<<<<<< HEAD
                Pedido.oculto is False,
=======
                Pedido.oculto.is_(False),
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
                Pedido.status != "concluido",
                Pedido.tipo_pedido == "Entrega",
                Pedido.distancia_km.isnot(None),
            ).all()
        else:
            pedidos = Pedido.query.filter(
                Pedido.id.in_(pedido_ids),
                Pedido.status != "concluido",
                Pedido.tipo_pedido == "Entrega",
            ).all()

        if len(pedidos) < 2:
            return error_response(
                "É necessário pelo menos 2 pedidos para calcular rota otimizada",
                400,
                details={"pedidos_encontrados": len(pedidos)},
            )

<<<<<<< HEAD
        # Obter coordenadas da floricultura
        origem = distancia_service.coords_floricultura
        if not origem:
            return error_response("Não foi possível obter coordenadas da floricultura", 500)

        # Converter para formato (lat, lon) para GraphHopper
        origem_gh = (origem[1], origem[0])

        # Coletar waypoints dos pedidos
        pedidos_com_coords = []
        for pedido in pedidos:
            if pedido.coords_lat and pedido.coords_lon:
                pedidos_com_coords.append(
                    {
                        "pedido": pedido,
                        "coords": (pedido.coords_lat, pedido.coords_lon),
                        "coords_gh": (pedido.coords_lon, pedido.coords_lat),
                    }
                )
=======
        # Coordenadas da floricultura (lon, lat) → converter para (lat, lon)
        origem_lonlat = distancia_service.coords_floricultura
        if not origem_lonlat:
            return error_response("Não foi possível obter coordenadas da floricultura", 500)

        origem = (origem_lonlat[1], origem_lonlat[0])  # (lat, lon)

        # Coletar pedidos com coordenadas válidas
        pedidos_com_coords = []
        for pedido in pedidos:
            if pedido.coords_lat and pedido.coords_lon:
                pedidos_com_coords.append(pedido)
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14

        if len(pedidos_com_coords) < 2:
            return error_response("É necessário pelo menos 2 pedidos com coordenadas válidas", 400)

<<<<<<< HEAD
        # Ordenar por horário de entrega (mais cedo primeiro)
        pedidos_com_coords.sort(
            key=lambda p: (p["pedido"].dia_entrega, p["pedido"].horario or "00:00")
        )

        # Construir waypoints para GraphHopper
        waypoints = [origem_gh]  # Começar na floricultura
        for item in pedidos_com_coords:
            waypoints.append(item["coords_gh"])
        waypoints.append(origem_gh)  # Voltar para floricultura

        # Calcular rota usando GraphHopper
        graphhopper_key = os.environ.get("GRAPHHOPPER_API_KEY", "")
        if not graphhopper_key:
            return error_response(
                "GraphHopper API key não configurada",
                500,
                details={"message": "Configure GRAPHHOPPER_API_KEY no .env"},
            )

        route_result = graphhopper_service.calculate_route(waypoints)

        if not route_result or "error" in route_result:
            return error_response(
                "Erro ao calcular rota",
                500,
                details=route_result.get("error", "Erro desconhecido"),
            )

        # Criar registro de rota otimizada
        rota = RotaOtimizada(
            nome=nome_rota,
            pedido_ids=",".join(str(p["pedido"].id) for p in pedidos_com_coords),
            distancia_total=route_result.get("distance", 0) / 1000,  # Converter m para km
            tempo_total=route_result.get("time", 0) / 60,  # Converter s para min
            coordenadas=str(waypoints),
            instrucoes=str(route_result.get("instructions", [])),
        )
=======
        # Waypoints no formato (lat, lon)
        waypoints = [(p.coords_lat, p.coords_lon) for p in pedidos_com_coords]

        # ------------------------------------------------------------------
        # Calcular rota otimizada
        # ------------------------------------------------------------------
        resultado = None
        metodo = "nearest_neighbor"

        # TENTATIVA 1: Google Directions (optimize:true)
        try:
            from app.services.google_routes import google_routes_service

            resultado = google_routes_service.calcular_rota_otimizada(
                origem, waypoints, retornar_origem=True
            )
            if resultado:
                metodo = "google_directions"
        except Exception as e:
            print(f"[ROTAS] Google Directions falhou: {e}")

        # TENTATIVA 2: GraphHopper nearest-neighbor
        if not resultado:
            try:
                from app.services.graphhopper import graphhopper_service

                resultado = graphhopper_service.calcular_rota_otimizada(
                    origem, waypoints, retornar_origem=True
                )
                if resultado:
                    metodo = resultado.get("metodo", "graphhopper")
            except Exception as e:
                print(f"[ROTAS] GraphHopper falhou: {e}")

        # TENTATIVA 3: Haversine nearest-neighbor (local, sem API)
        if not resultado:
            resultado = _nearest_neighbor_haversine(origem, waypoints)
            metodo = "haversine_nearest"

        if not resultado:
            return error_response("Nenhum provedor de rota disponível", 500)

        # ------------------------------------------------------------------
        # Reordenar pedidos conforme sequência otimizada
        # ------------------------------------------------------------------
        seq_otimizada = resultado.get("sequencia_otimizada", waypoints)
        pedidos_ordenados = _reordenar_pedidos(pedidos_com_coords, seq_otimizada)
        sequencia_ids = [p.id for p in pedidos_ordenados]
        waypoints_ordenados = [(p.coords_lat, p.coords_lon) for p in pedidos_ordenados]

        # ------------------------------------------------------------------
        # Google Maps URLs
        # ------------------------------------------------------------------
        google_url = build_google_maps_url(origem, waypoints_ordenados, return_to_origin=True)
        step_urls = build_step_by_step_urls(origem, waypoints_ordenados, return_to_origin=True)

        # ------------------------------------------------------------------
        # Salvar no banco
        # ------------------------------------------------------------------
        rota = RotaOtimizada(
            nome=nome_rota,
            distancia_total_km=resultado["distancia_total_km"],
            duracao_total_min=resultado["duracao_total_min"],
            origem_lat=origem[0],
            origem_lon=origem[1],
            num_pedidos=len(pedidos_ordenados),
            metodo_otimizacao=metodo,
        )
        rota.set_sequencia_pedidos(sequencia_ids)
        rota.set_waypoints_coords([[lat, lon] for lat, lon in waypoints_ordenados])
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14

        db.session.add(rota)
        db.session.commit()

<<<<<<< HEAD
        # Preparar resposta
        pedidos_data = []
        for item in pedidos_com_coords:
            pedido = item["pedido"]
            pedidos_data.append(
                {
                    "id": pedido.id,
                    "cliente": pedido.cliente,
                    "destinatario": pedido.destinatario,
                    "endereco": pedido.endereco,
                    "dia_entrega": pedido.dia_entrega.strftime("%Y-%m-%d")
                    if pedido.dia_entrega
                    else "",
                    "horario": pedido.horario,
                    "coords": {"lat": pedido.coords_lat, "lon": pedido.coords_lon},
                }
            )

=======
        # ------------------------------------------------------------------
        # Resposta no formato esperado pelo frontend
        # ------------------------------------------------------------------
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
        return success_response(
            {
                "rota_id": rota.id,
                "nome": rota.nome,
<<<<<<< HEAD
                "distancia_total_km": round(rota.distancia_total, 2),
                "tempo_total_min": round(rota.tempo_total, 2),
                "pedidos": pedidos_data,
                "waypoints": waypoints,
                "route_details": route_result,
=======
                "distancia_total_km": rota.distancia_total_km,
                "duracao_total_min": rota.duracao_total_min,
                "sequencia_pedidos": sequencia_ids,
                "num_pedidos": rota.num_pedidos,
                "metodo_otimizacao": metodo,
                "origem": {"lat": origem[0], "lon": origem[1]},
                "waypoints": [[lat, lon] for lat, lon in waypoints_ordenados],
                "google_maps_url": google_url,
                "google_maps_step_by_step": step_urls,
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
            },
            message="Rota otimizada calculada com sucesso",
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao calcular rota otimizada: {str(e)}", 500)


@rotas_bp.route("/rota-otimizada/<int:rota_id>", methods=["GET"])
@requires_any_role("admin", "atendente", "entregador")
def obter_rota_otimizada(rota_id):
    """Obtém rota otimizada por ID e gera Google Maps URLs."""
    try:
        rota = RotaOtimizada.query.get(rota_id)
        if not rota:
            return error_response("Rota não encontrada", 404)

<<<<<<< HEAD
        # Parsear pedido_ids
        pedido_ids = [int(id) for id in rota.pedido_ids.split(",") if id]
        pedidos = Pedido.query.filter(Pedido.id.in_(pedido_ids)).all()

        pedidos_data = [p.to_dict() for p in pedidos]

        return success_response(
            {
                "rota": {
                    "id": rota.id,
                    "nome": rota.nome,
                    "distancia_total_km": rota.distancia_total,
                    "tempo_total_min": rota.tempo_total,
                    "created_at": rota.created_at.isoformat() if rota.created_at else None,
                },
                "pedidos": pedidos_data,
=======
        sequencia_ids = rota.get_sequencia_pedidos()
        waypoints_coords = rota.get_waypoints_coords()
        origem = (rota.origem_lat, rota.origem_lon)

        # Converter waypoints para tuples (lat, lon)
        stops = [(w[0], w[1]) for w in waypoints_coords] if waypoints_coords else []

        google_url = build_google_maps_url(origem, stops, return_to_origin=True) if stops else None
        step_urls = build_step_by_step_urls(origem, stops, return_to_origin=True) if stops else []

        return success_response(
            {
                "rota_id": rota.id,
                "nome": rota.nome or "",
                "distancia_total_km": rota.distancia_total_km,
                "duracao_total_min": rota.duracao_total_min,
                "sequencia_pedidos": sequencia_ids,
                "num_pedidos": rota.num_pedidos,
                "metodo_otimizacao": rota.metodo_otimizacao or "",
                "origem": {"lat": rota.origem_lat, "lon": rota.origem_lon},
                "waypoints": waypoints_coords,
                "google_maps_url": google_url,
                "google_maps_step_by_step": step_urls,
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
            }
        )

    except Exception as e:
        return error_response(f"Erro ao obter rota: {str(e)}", 500)
<<<<<<< HEAD
=======


@rotas_bp.route("/gerar-rota-maps", methods=["POST"])
@requires_any_role("admin", "atendente", "entregador")
def gerar_rota_maps():
    """
    Gera link do Google Maps respeitando a ordem dos IDs recebidos.
    Sem otimização — a sequência é a que o usuário escolheu.

    Input:  { "pedido_ids": [10, 5, 22] }
    Output: { "google_maps_url": "...", "step_by_step": [...], "sem_coords": [...] }
    """
    try:
        data = request.get_json() or {}
        pedido_ids = data.get("pedido_ids", [])

        if not pedido_ids:
            return error_response("Nenhum pedido selecionado", 400)

        # Origem (floricultura)
        origem_lonlat = distancia_service.coords_floricultura
        if not origem_lonlat:
            return error_response("Coordenadas da floricultura não configuradas", 500)

        origem = (origem_lonlat[1], origem_lonlat[0])  # (lat, lon)

        # Buscar pedidos mantendo a ordem recebida
        pedidos_map = {
            p.id: p
            for p in Pedido.query.filter(Pedido.id.in_(pedido_ids)).all()
        }

        stops = []
        sem_coords = []
        pedidos_na_rota = []

        for pid in pedido_ids:
            pedido = pedidos_map.get(pid)
            if not pedido:
                continue
            if pedido.coords_lat and pedido.coords_lon:
                stops.append((pedido.coords_lat, pedido.coords_lon))
                pedidos_na_rota.append({
                    "id": pedido.id,
                    "cliente": pedido.cliente or "",
                    "destinatario": pedido.destinatario or "",
                    "endereco": pedido.endereco or f"{pedido.rua or ''} {pedido.numero or ''}".strip(),
                })
            else:
                sem_coords.append(pid)

        if not stops:
            return error_response(
                "Nenhum pedido tem coordenadas. Calcule as distâncias primeiro.",
                400,
                details={"sem_coords": sem_coords},
            )

        google_url = build_google_maps_url(origem, stops, return_to_origin=True)
        step_urls = build_step_by_step_urls(origem, stops, return_to_origin=True)

        return success_response({
            "google_maps_url": google_url,
            "google_maps_step_by_step": step_urls,
            "pedidos": pedidos_na_rota,
            "sem_coords": sem_coords,
        })

    except Exception as e:
        return error_response(f"Erro ao gerar rota: {str(e)}", 500)


# ------------------------------------------------------------------
# Helpers internos
# ------------------------------------------------------------------


def _nearest_neighbor_haversine(origem, waypoints):
    """Nearest-neighbor usando Haversine (sem API externa)."""
    import math

    def _haversine(c1, c2):
        lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
        lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 6371 * 2 * math.asin(math.sqrt(a))

    restantes = list(waypoints)
    sequencia = []
    atual = origem
    dist_total = 0.0

    while restantes:
        dists = [(i, _haversine(atual, w)) for i, w in enumerate(restantes)]
        idx, d = min(dists, key=lambda x: x[1])
        sequencia.append(restantes.pop(idx))
        dist_total += d
        atual = sequencia[-1]

    # Retorno à origem
    dist_total += _haversine(atual, origem)

    return {
        "distancia_total_km": round(dist_total, 2),
        "duracao_total_min": round(dist_total * 2, 1),  # ~30 km/h média urbana
        "sequencia_otimizada": sequencia,
        "num_waypoints": len(waypoints),
        "metodo": "haversine_nearest",
    }


def _reordenar_pedidos(pedidos, sequencia_coords):
    """Reordena pedidos para corresponder à sequência de coordenadas otimizada."""
    ordenados = []
    usados = set()

    for coord in sequencia_coords:
        melhor = None
        melhor_dist = float("inf")
        for p in pedidos:
            if p.id in usados:
                continue
            d = abs(p.coords_lat - coord[0]) + abs(p.coords_lon - coord[1])
            if d < melhor_dist:
                melhor_dist = d
                melhor = p
        if melhor:
            ordenados.append(melhor)
            usados.add(melhor.id)

    # Adicionar pedidos que não foram matched
    for p in pedidos:
        if p.id not in usados:
            ordenados.append(p)

    return ordenados
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
