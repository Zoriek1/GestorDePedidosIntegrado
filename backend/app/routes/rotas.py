# -*- coding: utf-8 -*-
"""
Rotas de Otimização - Blueprint para endpoints de rotas otimizadas
"""
import os

from flask import Blueprint, request

from app import db
from app.models import Pedido, RotaOtimizada
from app.middleware import requires_any_role
from app.schemas.common import error_response, success_response
from app.services.distancia import distancia_service
from app.services.graphhopper import graphhopper_service

rotas_bp = Blueprint("rotas", __name__, url_prefix="/api/pedidos")


@rotas_bp.route("/rota-otimizada", methods=["POST"])
@requires_any_role("admin", "atendente", "entregador")
def calcular_rota_otimizada():
    """
    Calcula rota otimizada para múltiplos pedidos
    CRÍTICO: Preservar funcionalidade exata
    """
    try:
        data = request.get_json() or {}
        pedido_ids = data.get("pedido_ids", [])
        nome_rota = data.get("nome", "Rota Otimizada")

        if not pedido_ids:
            # Se não especificar IDs, usar pedidos elegíveis
            pedidos = Pedido.query.filter(
                Pedido.oculto is False,
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

        if len(pedidos_com_coords) < 2:
            return error_response("É necessário pelo menos 2 pedidos com coordenadas válidas", 400)

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

        db.session.add(rota)
        db.session.commit()

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

        return success_response(
            {
                "rota_id": rota.id,
                "nome": rota.nome,
                "distancia_total_km": round(rota.distancia_total, 2),
                "tempo_total_min": round(rota.tempo_total, 2),
                "pedidos": pedidos_data,
                "waypoints": waypoints,
                "route_details": route_result,
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
    """Obtém rota otimizada por ID"""
    try:
        rota = RotaOtimizada.query.get(rota_id)
        if not rota:
            return error_response("Rota não encontrada", 404)

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
            }
        )

    except Exception as e:
        return error_response(f"Erro ao obter rota: {str(e)}", 500)
