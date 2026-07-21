# -*- coding: utf-8 -*-
"""
Rotas da API REST - PWA v3.0
API completa para o frontend PWA
"""
from __future__ import annotations

import re
from datetime import datetime

from flask import Blueprint, jsonify, request

from app import db
from app.middleware import requires_edit_auth, requires_role
from app.models import Cliente, FontePedido, Pedido
from app.models.pedido import datetime_now_brazil
from app.utils.backup_helper import (
    get_backup_stats,
    get_last_backup_time,
    has_recent_backup,
)

# ============================================
# ENDPOINT DE CRIAÇÃO DE PEDIDO - MIGRADO
# ============================================
# ATENÇÃO: Este endpoint foi migrado para app/routes/pedidos.py
# Mantido aqui temporariamente para compatibilidade
# NOVO LOCAL: app/routes/pedidos.py -> criar_pedido()



debug_bp = Blueprint("debug", __name__, url_prefix="/api")
@debug_bp.route("/debug/geocode", methods=["GET", "POST"])
@requires_role("admin")
def debug_geocode():
    """
    Endpoint de debug para testar geocodificação de um endereço.
    Mostra detalhes completos do que a API retorna.

    GET: /api/debug/geocode?endereco=Rua+X,+123
    GET: /api/debug/geocode?rua=Rua+X&numero=123&bairro=Centro&cidade=Goiania&cep=74000000
    POST: {"endereco": "Rua X, 123"} ou {"rua": "Rua X", "numero": "123", ...}

    SEGURANÇA: Requer autenticação
    """
    # Verificar se debug endpoints estão habilitados
    import os

    if not os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true":
        return (
            jsonify(
                {
                    "error": "Endpoint de debug desabilitado",
                    "message": "Defina ENABLE_DEBUG_ENDPOINTS=true no .env para habilitar",
                }
            ),
            403,
        )

    try:
        from app.services.distancia import distancia_service

        # Aceitar tanto GET (query param) quanto POST (json body)
        if request.method == "GET":
            endereco = request.args.get("endereco", "")
            rua = request.args.get("rua", "")
            numero = request.args.get("numero", "")
            bairro = request.args.get("bairro", "")
            cidade = request.args.get("cidade", "")
            cep = request.args.get("cep", "")
        else:
            data = request.get_json() or {}
            endereco = data.get("endereco", "")
            rua = data.get("rua", "")
            numero = data.get("numero", "")
            bairro = data.get("bairro", "")
            cidade = data.get("cidade", "")
            cep = data.get("cep", "")

        # Verificar se tem campos separados ou endereço completo
        tem_campos_separados = rua or bairro or cep

        if not endereco and not tem_campos_separados:
            return (
                jsonify(
                    {
                        "error": "Endereço é obrigatório",
                        "uso": [
                            "GET /api/debug/geocode?endereco=Rua+X,+123,+Bairro,+Cidade",
                            "GET /api/debug/geocode?rua=Rua+X&numero=123&bairro=Centro&cidade=Goiania&cep=74000000",
                            'POST {"endereco": "Rua X, 123"}',
                            'POST {"rua": "Rua X", "numero": "123", "bairro": "Centro", "cidade": "Goiânia", "cep": "74000-000"}',
                        ],
                    }
                ),
                400,
            )

        print("\n[DEBUG] ========== TESTE DE GEOCODIFICAÇÃO ==========")
        print(f"[DEBUG] Endereço original: {endereco}")
        print(
            f"[DEBUG] Campos separados: rua={rua}, num={numero}, bairro={bairro}, cidade={cidade}, cep={cep}"
        )

        # Construir endereço otimizado para geocodificação
        if tem_campos_separados and rua and bairro:
            # Se tem campos separados válidos (rua + bairro), usar construir_endereco_para_geocode
            endereco_para_geocode = distancia_service.construir_endereco_para_geocode(
                rua=rua, numero=numero, bairro=bairro, cidade=cidade, cep=cep
            )
            if endereco_para_geocode:
                print(f"[DEBUG] Endereço construído dos campos: {endereco_para_geocode}")
            else:
                print("[DEBUG] Validação de campos falhou, tentando com endereço completo...")
                endereco_para_geocode = (
                    distancia_service.limpar_endereco(endereco) if endereco else None
                )
        else:
            # Fallback: usar endereço completo limpo
            endereco_para_geocode = (
                distancia_service.limpar_endereco(endereco) if endereco else None
            )
            print(f"[DEBUG] Endereço limpo: {endereco_para_geocode}")

        # Usar a função de geocodificação do serviço (usa Nominatim + OpenRouteService)
        print("[DEBUG] Chamando geocodificar()...")
        coords = distancia_service.geocodificar(endereco_para_geocode, normalizar=False)

        if not coords:
            return jsonify(
                {
                    "success": False,
                    "endereco_original": endereco,
                    "campos_separados": {
                        "rua": rua,
                        "numero": numero,
                        "bairro": bairro,
                        "cidade": cidade,
                        "cep": cep,
                    }
                    if tem_campos_separados
                    else None,
                    "endereco_para_geocode": endereco_para_geocode,
                    "error": "Nenhum resultado encontrado (Nominatim e OpenRouteService falharam)",
                    "dica": "Verifique se o endereço está correto e completo. Tente com: Rua, Número, Bairro, Cidade",
                }
            )

        # Calcular distância da floricultura
        distancia = None
        duracao = None
        coords_floricultura = distancia_service.coords_floricultura

        if coords_floricultura:
            resultado_dist = distancia_service.calcular_distancia(coords_floricultura, coords)
            if resultado_dist:
                distancia = resultado_dist["distancia_km"]
                duracao = resultado_dist["duracao_min"]

        return jsonify(
            {
                "success": True,
                "endereco_original": endereco,
                "campos_separados": {
                    "rua": rua,
                    "numero": numero,
                    "bairro": bairro,
                    "cidade": cidade,
                    "cep": cep,
                }
                if tem_campos_separados
                else None,
                "endereco_para_geocode": endereco_para_geocode,
                "coords": {"longitude": coords[0], "latitude": coords[1]},
                "google_maps_link": f"https://www.google.com/maps?q={coords[1]},{coords[0]}",
                "distancia_km": distancia,
                "duracao_min": duracao,
                "coords_floricultura": {
                    "longitude": coords_floricultura[0] if coords_floricultura else None,
                    "latitude": coords_floricultura[1] if coords_floricultura else None,
                }
                if coords_floricultura
                else None,
            }
        )

    except Exception as e:
        print(f"[ERRO] Exceção no debug de geocodificação: {e}")
        import traceback

        traceback.print_exc()
        return (
            jsonify({"error": "Erro ao testar geocodificação", "detalhes": str(e)}),
            500,
        )


@debug_bp.route("/debug/limpar-distancias", methods=["POST"])
@requires_role("admin")
def debug_limpar_distancias():
    """
    Endpoint de debug para limpar todas as distâncias cacheadas.
    Força recálculo na próxima chamada.

    SEGURANÇA: Requer autenticação
    """
    # Verificar se debug endpoints estão habilitados
    import os

    if not os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true":
        return (
            jsonify(
                {
                    "error": "Endpoint de debug desabilitado",
                    "message": "Defina ENABLE_DEBUG_ENDPOINTS=true no .env para habilitar",
                }
            ),
            403,
        )

    try:
        # Limpar todas as distâncias
        pedidos = Pedido.query.filter(Pedido.distancia_km.isnot(None)).all()
        count = len(pedidos)

        for pedido in pedidos:
            pedido.distancia_km = None

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"{count} distâncias limpas do cache",
                "count": count,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Erro ao limpar distâncias", "detalhes": str(e)}), 500


@debug_bp.route("/debug/config-floricultura", methods=["GET"])
@requires_role("admin")
def debug_config_floricultura():
    """
    Endpoint de debug para verificar a configuração da floricultura.
    Mostra o endereço configurado e as coordenadas geocodificadas.

    SEGURANÇA: Requer autenticação - Expõe informações sensíveis
    """
    # Verificar se debug endpoints estão habilitados
    import os

    if not os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true":
        return (
            jsonify(
                {
                    "error": "Endpoint de debug desabilitado",
                    "message": "Defina ENABLE_DEBUG_ENDPOINTS=true no .env para habilitar",
                }
            ),
            403,
        )

    try:
        import os

        from app.services.distancia import distancia_service

        endereco = os.environ.get("ENDERECO_FLORICULTURA", "")
        api_key = os.environ.get("OPENROUTE_API_KEY", "")

        # Forçar re-geocodificação da floricultura
        distancia_service._coords_floricultura = None
        coords = distancia_service.coords_floricultura

        return jsonify(
            {
                "success": True,
                "endereco_configurado": endereco,
                "api_key_configurada": bool(api_key),
                "api_key_preview": api_key[:20] + "..." if api_key else None,
                "coords_floricultura": {
                    "longitude": coords[0] if coords else None,
                    "latitude": coords[1] if coords else None,
                }
                if coords
                else None,
                "google_maps_link": f"https://www.google.com/maps?q={coords[1]},{coords[0]}"
                if coords
                else None,
                "status": "OK" if coords else "ERRO - Não foi possível geocodificar",
            }
        )

    except Exception as e:
        return (
            jsonify({"error": "Erro ao verificar configuração", "detalhes": str(e)}),
            500,
        )


@debug_bp.route("/debug/reset-floricultura", methods=["POST"])
@requires_role("admin")
def debug_reset_floricultura():
    """
    Força recálculo das coordenadas da floricultura.

    SEGURANÇA: Requer autenticação
    """
    # Verificar se debug endpoints estão habilitados
    import os

    if not os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true":
        return (
            jsonify(
                {
                    "error": "Endpoint de debug desabilitado",
                    "message": "Defina ENABLE_DEBUG_ENDPOINTS=true no .env para habilitar",
                }
            ),
            403,
        )

    try:
        from app.services.distancia import distancia_service

        # Limpar cache
        distancia_service._coords_floricultura = None
        distancia_service._enderecos_invalidos.clear()

        # Forçar re-geocodificação
        coords = distancia_service.coords_floricultura

        return jsonify(
            {
                "success": True,
                "message": "Cache da floricultura limpo e recalculado",
                "endereco": distancia_service.endereco_floricultura,
                "coords": {
                    "longitude": coords[0] if coords else None,
                    "latitude": coords[1] if coords else None,
                }
                if coords
                else None,
                "google_maps_link": f"https://www.google.com/maps?q={coords[1]},{coords[0]}"
                if coords
                else None,
            }
        )

    except Exception as e:
        return (
            jsonify({"error": "Erro ao resetar floricultura", "detalhes": str(e)}),
            500,
        )


@debug_bp.route("/debug/testar-apis", methods=["GET"])
@requires_role("admin")
def debug_testar_apis():
    """
    Testa conectividade com as APIs externas (GraphHopper, OpenRouteService, Nominatim)

    SEGURANÇA: Requer autenticação - Expõe API keys parcialmente
    """
    # Verificar se debug endpoints estão habilitados
    import os

    if not os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true":
        return (
            jsonify(
                {
                    "error": "Endpoint de debug desabilitado",
                    "message": "Defina ENABLE_DEBUG_ENDPOINTS=true no .env para habilitar",
                }
            ),
            403,
        )

    try:
        import os

        import requests

        resultados = {
            "graphhopper": {"status": "não testado", "details": {}},
            "openroute": {"status": "não testado", "details": {}},
            "nominatim": {"status": "não testado", "details": {}},
        }

        # Teste 1: GraphHopper API
        graphhopper_key = os.environ.get("GRAPHHOPPER_API_KEY", "")
        if graphhopper_key:
            try:
                # Testar com uma rota simples (Goiânia)
                test_params = {
                    "point": ["-16.6869,-49.2648", "-16.6941,-49.2587"],
                    "vehicle": "car",
                    "key": graphhopper_key,
                    "type": "json",
                }
                response = requests.get(
                    "https://graphhopper.com/api/1/route",
                    params=test_params,
                    timeout=10,
                )

                if response.status_code == 200:
                    resultados["graphhopper"]["status"] = "OK"
                    resultados["graphhopper"]["details"] = {
                        "message": "API funcionando corretamente",
                        "key_preview": graphhopper_key[:20] + "...",
                    }
                else:
                    resultados["graphhopper"]["status"] = "ERRO"
                    resultados["graphhopper"]["details"] = {
                        "code": response.status_code,
                        "message": response.text[:300],
                        "key_preview": graphhopper_key[:20] + "...",
                    }
            except Exception as e:
                resultados["graphhopper"]["status"] = "ERRO"
                resultados["graphhopper"]["details"] = {"error": str(e)}
        else:
            resultados["graphhopper"]["status"] = "NÃO CONFIGURADO"
            resultados["graphhopper"]["details"] = {
                "message": "GRAPHHOPPER_API_KEY não definida no .env"
            }

        # Teste 2: OpenRouteService API
        openroute_key = os.environ.get("OPENROUTE_API_KEY", "")
        if openroute_key:
            try:
                test_body = {"coordinates": [[-49.2648, -16.6869], [-49.2587, -16.6941]]}
                response = requests.post(
                    "https://api.openrouteservice.org/v2/directions/driving-car",
                    headers={"Authorization": openroute_key},
                    json=test_body,
                    timeout=10,
                )

                if response.status_code == 200:
                    resultados["openroute"]["status"] = "OK"
                    resultados["openroute"]["details"] = {
                        "message": "API funcionando corretamente",
                        "key_preview": openroute_key[:20] + "...",
                    }
                else:
                    resultados["openroute"]["status"] = "ERRO"
                    resultados["openroute"]["details"] = {
                        "code": response.status_code,
                        "message": response.text[:300],
                        "key_preview": openroute_key[:20] + "...",
                    }
            except Exception as e:
                resultados["openroute"]["status"] = "ERRO"
                resultados["openroute"]["details"] = {"error": str(e)}
        else:
            resultados["openroute"]["status"] = "NÃO CONFIGURADO"
            resultados["openroute"]["details"] = {
                "message": "OPENROUTE_API_KEY não definida no .env"
            }

        # Teste 3: Nominatim (não precisa de API key)
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                headers={"User-Agent": "PlanteumaFlor-GestorPedidos/1.0"},
                params={"q": "Goiânia, GO, Brasil", "format": "json", "limit": 1},
                timeout=10,
            )

            if response.status_code == 200:
                results = response.json()
                if results:
                    resultados["nominatim"]["status"] = "OK"
                    resultados["nominatim"]["details"] = {
                        "message": "API funcionando corretamente (gratuita)",
                        "found": results[0].get("display_name", "")[:100],
                    }
                else:
                    resultados["nominatim"]["status"] = "AVISO"
                    resultados["nominatim"]["details"] = {
                        "message": "API respondeu mas não encontrou resultados"
                    }
            else:
                resultados["nominatim"]["status"] = "ERRO"
                resultados["nominatim"]["details"] = {
                    "code": response.status_code,
                    "message": response.text[:300],
                }
        except Exception as e:
            resultados["nominatim"]["status"] = "ERRO"
            resultados["nominatim"]["details"] = {"error": str(e)}

        # Resumo geral
        status_geral = "OK"
        problemas = []

        if resultados["graphhopper"]["status"] in ["ERRO", "NÃO CONFIGURADO"]:
            problemas.append("GraphHopper não disponível (rotas otimizadas podem falhar)")

        if resultados["openroute"]["status"] in ["ERRO", "NÃO CONFIGURADO"]:
            problemas.append("OpenRouteService não disponível (fallback de rotas)")

        if resultados["nominatim"]["status"] == "ERRO":
            problemas.append("Nominatim não disponível (geocodificação pode falhar)")

        if problemas:
            status_geral = "PARCIAL" if resultados["nominatim"]["status"] == "OK" else "ERRO"

        return jsonify(
            {
                "success": True,
                "status_geral": status_geral,
                "problemas": problemas,
                "apis": resultados,
                "recomendacoes": {
                    "graphhopper": "Configure GRAPHHOPPER_API_KEY para rotas otimizadas (gratuito até 500 req/dia)",
                    "openroute": "Configure OPENROUTE_API_KEY para backup de rotas (gratuito até 2000 req/dia)",
                    "nominatim": "Não precisa configuração, mas respeite o limite de uso (1 req/segundo)",
                },
            }
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Erro ao testar APIs", "detalhes": str(e)}), 500


