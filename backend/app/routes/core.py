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
from app.middleware import requires_any_role, requires_edit_auth
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



core_bp = Blueprint("core", __name__, url_prefix="/api")
@core_bp.route("/stats", methods=["GET"])
def obter_estatisticas():
    """Retorna estatísticas dos pedidos"""
    try:
        stats = Pedido.get_statistics()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"error": "Erro ao obter estatísticas", "detalhes": str(e)}), 500


@core_bp.route("/backup/status", methods=["GET"])
@requires_any_role("admin")
def obter_status_backup():
    """Retorna status dos backups do sistema"""
    try:
        stats = get_backup_stats()
        last_backup = get_last_backup_time()
        has_recent = has_recent_backup(hours=24)

        response = {
            "success": True,
            "backup_stats": {
                "total_backups": stats["count"],
                "total_size_mb": round(stats["total_size_mb"], 2),
                "oldest_backup": stats["oldest"].isoformat() if stats["oldest"] else None,
                "newest_backup": stats["newest"].isoformat() if stats["newest"] else None,
                "has_recent_backup": has_recent,
                "last_backup": {
                    "path": str(last_backup[0]) if last_backup else None,
                    "datetime": last_backup[1].isoformat() if last_backup else None,
                    "size_mb": round(last_backup[2], 2) if last_backup else None,
                }
                if last_backup
                else None,
            },
        }

        return jsonify(response)
    except Exception as e:
        return (
            jsonify({"error": "Erro ao obter status dos backups", "detalhes": str(e)}),
            500,
        )


@core_bp.route("/pedidos/overdue", methods=["GET"])
@requires_any_role("admin", "atendente")
def pedidos_atrasados():
    """Retorna pedidos atrasados"""
    try:
        overdue_pedidos = Pedido.get_overdue_pedidos()

        return jsonify(
            {
                "success": True,
                "count": len(overdue_pedidos),
                "pedidos": [p.to_dict() for p in overdue_pedidos],
            }
        )

    except Exception as e:
        return (
            jsonify({"error": "Erro ao obter pedidos atrasados", "detalhes": str(e)}),
            500,
        )


@core_bp.route("/cleanup", methods=["POST"])
@requires_any_role("admin")
def limpar_pedidos_antigos():
    """Arquiva (oculta) pedidos antigos - NÃO deleta do banco de dados"""
    try:
        data = request.get_json() or {}
        days = data.get("days", 1)

        count = Pedido.cleanup_old_pedidos(days=days)

        return jsonify(
            {
                "success": True,
                "message": f"{count} pedidos antigos arquivados (ocultos da lista)",
                "count": count,
            }
        )

    except Exception as e:
        return (
            jsonify({"error": "Erro ao limpar pedidos antigos", "detalhes": str(e)}),
            500,
        )


@core_bp.route("/pedidos/<int:pedido_id>/distancia", methods=["GET"])
def calcular_distancia_pedido_endpoint(pedido_id):
    """Calcula e retorna a distância da floricultura até o endereço do pedido"""
    try:
        from app.services.distancia import distancia_service

        pedido = Pedido.query.get(pedido_id)

        if not pedido:
            return (
                jsonify({"error": "Pedido não encontrado", "pedido_id": pedido_id}),
                404,
            )

        # Verificar se tem query param force_recalc
        force_recalc = request.args.get("force_recalc", "false").lower() == "true"

        # Se já tem distância calculada e não é forçado, retornar do cache
        if pedido.distancia_km is not None and not force_recalc:
            print(
                f"[DEBUG] Pedido {pedido_id}: retornando distância do cache: {pedido.distancia_km} km"
            )
            return jsonify(
                {
                    "success": True,
                    "pedido_id": pedido_id,
                    "distancia_km": pedido.distancia_km,
                    "endereco": pedido.endereco,
                    "cached": True,
                }
            )

        print("\n[DEBUG] ========== CALCULANDO DISTÂNCIA INDIVIDUAL ==========")
        print(f"[DEBUG] Pedido ID: {pedido_id}")
        print(
            f"[DEBUG] Campos: rua={pedido.rua}, num={pedido.numero}, bairro={pedido.bairro}, cidade={pedido.cidade}, cep={pedido.cep}"
        )
        print(f"[DEBUG] Forçar recálculo: {force_recalc}")

        # Calcular distância usando APENAS campos separados (não usa pedido.endereco)
        resultado = distancia_service.calcular_distancia_pedido(
            pedido_id=pedido_id,
            rua=pedido.rua,
            numero=pedido.numero,
            bairro=pedido.bairro,
            cidade=pedido.cidade,
            cep=pedido.cep,
            cliente_id=pedido.cliente_id,
        )

        # Verificar se houve erro de validação
        if isinstance(resultado, dict) and resultado.get("error"):
            print(f"[ERRO] Validação falhou: {resultado['error']}")
            return (
                jsonify(
                    {
                        "success": False,
                        "pedido_id": pedido_id,
                        "error": resultado["error"],
                        "detalhes": resultado.get("detalhes"),
                        "campos_recebidos": resultado.get("campos_recebidos"),
                    }
                ),
                400,
            )

        if resultado:
            # Salvar no banco para cache
            pedido.distancia_km = resultado["distancia_km"]
            # Salvar coordenadas se disponíveis
            if "coords_destino_lat" in resultado:
                pedido.coords_lat = resultado["coords_destino_lat"]
            if "coords_destino_lon" in resultado:
                pedido.coords_lon = resultado["coords_destino_lon"]
            db.session.commit()

            # Enfileirar cálculo de frete (não altera lógica de distância)
            try:
                from app.services.fila_taxa_entrega import enfileirar_calculo_taxa

                enfileirar_calculo_taxa(pedido_id)
            except Exception:
                pass

            return jsonify(
                {
                    "success": True,
                    "pedido_id": pedido_id,
                    "distancia_km": resultado["distancia_km"],
                    "duracao_min": resultado["duracao_min"],
                    "metodo": resultado.get("metodo"),
                    "cached": False,
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "pedido_id": pedido_id,
                        "error": "Não foi possível calcular a distância",
                        "detalhes": "Resultado inesperado do serviço de distância",
                    }
                ),
                500,
            )

    except Exception as e:
        print(f"[ERRO] Exceção ao calcular distância do pedido {pedido_id}: {e}")
        return jsonify({"error": "Erro ao calcular distância", "detalhes": str(e)}), 500


@core_bp.route("/pedidos/calcular-distancias", methods=["POST"])
def calcular_distancias_lote():
    """Calcula distâncias para múltiplos pedidos em lote"""
    try:
        from app.services.distancia import distancia_service

        data = request.get_json() or {}
        pedido_ids = data.get("pedido_ids", [])
        force_recalc = data.get("force_recalc", False)  # Forçar recálculo mesmo se já tiver cache

        if not pedido_ids:
            # Se não especificar IDs, calcular apenas para pedidos:
            # - Não ocultos
            # - Não concluídos (status != 'concluido')
            # - Tipo Entrega (tipo_pedido == 'Entrega')
            pedidos = Pedido.query.filter(
                Pedido.oculto is False,
                Pedido.status != "concluido",
                Pedido.tipo_pedido == "Entrega",
            ).all()
        else:
            # Se especificar IDs, aplicar os mesmos filtros
            pedidos = Pedido.query.filter(
                Pedido.id.in_(pedido_ids),
                Pedido.status != "concluido",
                Pedido.tipo_pedido == "Entrega",
            ).all()

        resultados = []
        calculados = 0
        do_cache = 0
        erros = 0
        ignorados = 0

        for pedido in pedidos:
            try:
                # Se já tem distância e não é forçado, usar cache
                if pedido.distancia_km is not None and not force_recalc:
                    resultados.append(
                        {
                            "id": pedido.id,
                            "distancia_km": pedido.distancia_km,
                            "cached": True,
                        }
                    )
                    do_cache += 1
                    continue

                # Pular pedidos sem endereço
                if not pedido.endereco:
                    resultados.append(
                        {"id": pedido.id, "distancia_km": None, "error": "Sem endereço"}
                    )
                    ignorados += 1
                    continue

                # Pular pedidos do tipo Retirada
                if pedido.tipo_pedido == "Retirada":
                    resultados.append(
                        {
                            "id": pedido.id,
                            "distancia_km": None,
                            "error": "Tipo Retirada - não requer entrega",
                        }
                    )
                    ignorados += 1
                    continue

                # Calcular distância usando campos separados para melhor precisão
                resultado = distancia_service.calcular_distancia_pedido(
                    pedido_id=pedido.id,
                    rua=pedido.rua,
                    numero=pedido.numero,
                    bairro=pedido.bairro,
                    cidade=pedido.cidade,
                    cep=pedido.cep,
                    cliente_id=pedido.cliente_id,
                )

                if resultado:
                    pedido.distancia_km = resultado["distancia_km"]
                    # Salvar coordenadas se disponíveis
                    if "coords_destino_lat" in resultado:
                        pedido.coords_lat = resultado["coords_destino_lat"]
                    if "coords_destino_lon" in resultado:
                        pedido.coords_lon = resultado["coords_destino_lon"]
                    resultados.append(
                        {
                            "id": pedido.id,
                            "distancia_km": resultado["distancia_km"],
                            "duracao_min": resultado["duracao_min"],
                            "endereco": pedido.endereco,
                            "coords_destino": resultado.get("coords_destino"),
                            "cached": False,
                        }
                    )
                    calculados += 1
                else:
                    resultados.append(
                        {
                            "id": pedido.id,
                            "distancia_km": None,
                            "endereco": pedido.endereco,
                            "campos": {
                                "rua": pedido.rua,
                                "numero": pedido.numero,
                                "bairro": pedido.bairro,
                                "cidade": pedido.cidade,
                                "cep": pedido.cep,
                            },
                            "error": "Falha na geocodificação",
                        }
                    )
                    erros += 1

            except Exception as pedido_error:
                # Erro ao processar pedido individual - não interrompe o lote
                print(f"[ERRO] Erro ao calcular distância do pedido {pedido.id}: {pedido_error}")
                resultados.append(
                    {
                        "id": pedido.id,
                        "distancia_km": None,
                        "error": f"Erro interno: {str(pedido_error)[:50]}",
                    }
                )
                erros += 1

        # Salvar distâncias calculadas no banco
        try:
            db.session.commit()
        except Exception as commit_error:
            print(f"[ERRO] Erro ao salvar distâncias: {commit_error}")
            db.session.rollback()
        else:
            # Enfileirar cálculo de frete para cada pedido que teve distância calculada (não altera lógica de distância)
            try:
                from app.services.fila_taxa_entrega import enfileirar_calculo_taxa

                for r in resultados:
                    if r.get("distancia_km") is not None and not r.get("cached"):
                        enfileirar_calculo_taxa(r["id"])
            except Exception:
                pass

        # Ordenar por distância (None no final)
        resultados.sort(key=lambda x: (x["distancia_km"] is None, x["distancia_km"] or 0))

        return jsonify(
            {
                "success": True,
                "total": len(resultados),
                "calculados": calculados,
                "do_cache": do_cache,
                "erros": erros,
                "ignorados": ignorados,
                "resultados": resultados,
            }
        )

    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Erro ao calcular distâncias", "detalhes": str(e)}),
            500,
        )


@core_bp.route("/pedidos/<int:pedido_id>/calcular-taxa", methods=["POST"])
def calcular_taxa_pedido(pedido_id):
    """Calcula e retorna a taxa de entrega para um pedido"""
    try:
        from app.services.distancia import distancia_service
        from app.services.taxa_entrega import taxa_entrega_service

        pedido = Pedido.query.get(pedido_id)

        if not pedido:
            return (
                jsonify({"error": "Pedido não encontrado", "pedido_id": pedido_id}),
                404,
            )

        # Verificar se já tem distância calculada
        if pedido.distancia_km is None:
            # Calcular distância primeiro
            resultado = distancia_service.calcular_distancia_pedido(
                pedido_id=pedido_id,
                rua=pedido.rua,
                numero=pedido.numero,
                bairro=pedido.bairro,
                cidade=pedido.cidade,
                cep=pedido.cep,
                cliente_id=pedido.cliente_id,
            )

            if not resultado:
                return (
                    jsonify(
                        {
                            "success": False,
                            "pedido_id": pedido_id,
                            "error": "Não foi possível calcular a distância para calcular a taxa",
                            "endereco": pedido.endereco,
                        }
                    ),
                    400,
                )

            # Salvar distância e coordenadas
            pedido.distancia_km = resultado["distancia_km"]
            if "coords_destino_lat" in resultado:
                pedido.coords_lat = resultado["coords_destino_lat"]
            if "coords_destino_lon" in resultado:
                pedido.coords_lon = resultado["coords_destino_lon"]
            db.session.commit()

        # Calcular taxa de entrega
        taxa = taxa_entrega_service.calcular_taxa(pedido.distancia_km)

        # Salvar taxa no pedido
        pedido.taxa_entrega = taxa
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "pedido_id": pedido_id,
                "distancia_km": pedido.distancia_km,
                "taxa_entrega": taxa,
                "endereco": pedido.endereco,
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"[ERRO] Exceção ao calcular taxa do pedido {pedido_id}: {e}")
        return (
            jsonify({"error": "Erro ao calcular taxa de entrega", "detalhes": str(e)}),
            500,
        )


def agrupar_pedidos_por_horario(pedidos):
    """
    Agrupa pedidos por data de entrega e ordena por horário dentro de cada grupo.
    Cria grupos de horários próximos (janela de 2 horas).

    Returns:
        Lista de grupos, onde cada grupo é uma lista de pedidos ordenados por horário
    """
    from collections import defaultdict

    # Agrupar por data de entrega
    pedidos_por_data = defaultdict(list)
    for pedido in pedidos:
        if pedido.dia_entrega:
            pedidos_por_data[pedido.dia_entrega].append(pedido)

    grupos_finais = []

    # Para cada data, ordenar por horário e criar grupos de horários próximos
    for data_entrega in sorted(pedidos_por_data.keys()):
        pedidos_do_dia = pedidos_por_data[data_entrega]

        # Ordenar por horário (mais cedo primeiro)
        def parse_horario(horario_str):
            try:
                if not horario_str:
                    return 0
                # Se for intervalo, usar o horário inicial para ordenação
                if " - " in horario_str:
                    partes = horario_str.split(" - ")
                    if len(partes) >= 1:
                        horario_str = partes[0].strip()
                if ":" in horario_str:
                    h, m = map(int, horario_str.split(":"))
                    return h * 60 + m  # Converter para minutos desde meia-noite
                return 0
            except (ValueError, IndexError):
                return 0

        pedidos_do_dia.sort(key=lambda p: parse_horario(p.horario or "00:00"))

        # Criar grupos de horários próximos (janela de 2 horas)
        grupos_horario = []
        grupo_atual = []
        horario_base = None

        for pedido in pedidos_do_dia:
            horario_minutos = parse_horario(pedido.horario or "00:00")

            if horario_base is None:
                horario_base = horario_minutos
                grupo_atual = [pedido]
            elif horario_minutos - horario_base <= 120:  # 2 horas em minutos
                grupo_atual.append(pedido)
            else:
                # Novo grupo
                if grupo_atual:
                    grupos_horario.append(grupo_atual)
                horario_base = horario_minutos
                grupo_atual = [pedido]

        # Adicionar último grupo
        if grupo_atual:
            grupos_horario.append(grupo_atual)

        grupos_finais.extend(grupos_horario)

    return grupos_finais


def mapear_waypoints_para_pedidos(waypoints_otimizados, pedidos_com_coords):
    """
    Mapeia waypoints otimizados de volta para pedidos com validação rigorosa.
    Evita duplicatas e usa tolerância precisa.

    Returns:
        Lista de IDs de pedidos na ordem correta
    """
    import math

    sequencia_pedidos = []
    pedidos_disponiveis = pedidos_com_coords.copy()
    pedidos_mapeados = set()  # Para evitar duplicatas

    # Criar mapeamento inicial de coordenadas para pedidos
    coords_para_pedido = {}
    for pedido in pedidos_com_coords:
        if pedido.coords_lat and pedido.coords_lon:
            coords_para_pedido[(pedido.coords_lat, pedido.coords_lon)] = pedido

    # Tolerância de distância (em graus) - aproximadamente 11 metros
    TOLERANCIA_DISTANCIA = 0.0001

    for waypoint in waypoints_otimizados:
        if not pedidos_disponiveis:
            break

        pedido_encontrado = None
        menor_dist = float("inf")
        indice_encontrado = -1

        # Tentar match exato primeiro
        coords_waypoint = (round(waypoint[0], 6), round(waypoint[1], 6))
        if coords_waypoint in coords_para_pedido:
            pedido_exato = coords_para_pedido[coords_waypoint]
            if pedido_exato.id not in pedidos_mapeados:
                pedido_encontrado = pedido_exato
                # Encontrar índice na lista disponível
                for i, p in enumerate(pedidos_disponiveis):
                    if p.id == pedido_exato.id:
                        indice_encontrado = i
                        break

        # Se não encontrou match exato, buscar por proximidade
        if not pedido_encontrado:
            for i, pedido in enumerate(pedidos_disponiveis):
                if pedido.id in pedidos_mapeados:
                    continue  # Já mapeado

                if pedido.coords_lat and pedido.coords_lon:
                    # Calcular distância usando fórmula de Haversine aproximada
                    lat_diff = pedido.coords_lat - waypoint[0]
                    lon_diff = pedido.coords_lon - waypoint[1]
                    dist = math.sqrt(lat_diff**2 + lon_diff**2)

                    if dist < menor_dist and dist <= TOLERANCIA_DISTANCIA:
                        menor_dist = dist
                        pedido_encontrado = pedido
                        indice_encontrado = i

        # Adicionar pedido encontrado à sequência
        if pedido_encontrado and pedido_encontrado.id not in pedidos_mapeados:
            sequencia_pedidos.append(pedido_encontrado.id)
            pedidos_mapeados.add(pedido_encontrado.id)
            if indice_encontrado >= 0:
                pedidos_disponiveis.pop(indice_encontrado)

    # Adicionar pedidos restantes que não foram mapeados (não devem ter coordenadas válidas)
    for pedido in pedidos_disponiveis:
        if pedido.id not in pedidos_mapeados:
            sequencia_pedidos.append(pedido.id)
            pedidos_mapeados.add(pedido.id)

    return sequencia_pedidos


# ============================================
# ENDPOINTS DE ROTAS OTIMIZADAS - MIGRADOS
# ============================================
# ATENÇÃO: Este endpoint foi migrado para app/routes/rotas.py
# Mantido aqui temporariamente para compatibilidade durante transição
# TODO: Remover após validação completa e atualização do frontend
# NOVO LOCAL: app/routes/rotas.py -> calcular_rota_otimizada()


@core_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        # Verificar se o banco está acessível
        Pedido.query.count()

        return jsonify(
            {
                "success": True,
                "status": "healthy",
                "message": "API funcionando normalmente",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "status": "unhealthy", "error": str(e)}), 500


# ============================================
# ENDPOINT PROXY PARA VIACEP
# ============================================

# Cache em memória para CEPs (TTL de 24 horas)
_cep_cache: dict[str, tuple[dict, datetime]] = {}
CEP_CACHE_TTL_HOURS = 24


@core_bp.route("/cep/<cep>", methods=["GET"])
def buscar_cep(cep):
    """
    Proxy para busca de CEP via ViaCEP API
    Permite que o frontend faça requisições same-origin, mantendo CSP restrita

    Args:
        cep: CEP no formato 00000000 ou 00000-000

    Returns:
        JSON com dados do endereço ou erro
    """
    import re

    import requests

    try:
        # Limpar CEP (remover caracteres não numéricos)
        clean_cep = re.sub(r"\D", "", cep)

        # Validar formato (deve ter 8 dígitos)
        if len(clean_cep) != 8:
            return (
                jsonify(
                    {
                        "error": "CEP inválido",
                        "message": "CEP deve ter 8 dígitos",
                        "cep_recebido": cep,
                        "cep_limpo": clean_cep,
                    }
                ),
                400,
            )

        # Verificar cache antes de fazer requisição
        now = datetime.now()
        if clean_cep in _cep_cache:
            cached_data, cached_time = _cep_cache[clean_cep]
            # Verificar se cache ainda é válido (TTL de 24 horas)
            time_diff = now - cached_time
            if time_diff.total_seconds() < CEP_CACHE_TTL_HOURS * 3600:
                # Retornar do cache
                return jsonify(cached_data), 200
            else:
                # Cache expirado, remover
                del _cep_cache[clean_cep]

        # Fazer requisição para ViaCEP com retry e backoff exponencial
        viacep_url = f"https://viacep.com.br/ws/{clean_cep}/json/"

        max_retries = 2
        backoff_delays = [1, 2]  # 1s, 2s
        response = None
        last_exception = None

        for attempt in range(max_retries + 1):  # 0, 1, 2 (3 tentativas no total)
            try:
                response = requests.get(
                    viacep_url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "PlanteUmaFlor-GestorPedidos/1.0",
                    },
                    timeout=8,  # Timeout reduzido para 8s
                )
                # Se chegou aqui, requisição foi bem-sucedida
                break
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < max_retries:
                    # Aguardar antes de tentar novamente (backoff exponencial)
                    import time

                    time.sleep(backoff_delays[attempt])
                    continue
                # Última tentativa falhou
                raise
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries:
                    # Aguardar antes de tentar novamente (backoff exponencial)
                    import time

                    time.sleep(backoff_delays[attempt])
                    continue
                # Última tentativa falhou
                raise

        # Se não houve resposta após todas as tentativas, tratar erro
        if response is None:
            if isinstance(last_exception, requests.exceptions.Timeout):
                return (
                    jsonify(
                        {
                            "error": "Timeout ao consultar ViaCEP",
                            "message": "A requisição para ViaCEP excedeu o tempo limite após múltiplas tentativas",
                        }
                    ),
                    504,
                )
            else:
                return (
                    jsonify(
                        {
                            "error": "Erro de rede ao consultar ViaCEP",
                            "message": "Falha na comunicação com ViaCEP após múltiplas tentativas",
                            "detalhes": str(last_exception),
                        }
                    ),
                    502,
                )

        # Verificar status HTTP
        if not response.ok:
            return (
                jsonify(
                    {
                        "error": "Erro ao consultar ViaCEP",
                        "status_code": response.status_code,
                        "message": "Falha na comunicação com ViaCEP",
                    }
                ),
                502,
            )

        # Verificar Content-Type
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return (
                jsonify(
                    {
                        "error": "Resposta inválida do ViaCEP",
                        "content_type": content_type,
                        "message": "ViaCEP retornou formato inesperado",
                    }
                ),
                502,
            )

        # Parse JSON
        try:
            data = response.json()
        except ValueError as e:
            return (
                jsonify(
                    {
                        "error": "Erro ao processar resposta do ViaCEP",
                        "message": "Resposta não é JSON válido",
                        "detalhes": str(e),
                    }
                ),
                502,
            )

        # Verificar se CEP não foi encontrado
        if data.get("erro") is True:
            return (
                jsonify(
                    {
                        "error": "CEP não encontrado",
                        "message": "CEP não existe na base do ViaCEP",
                        "cep": clean_cep,
                    }
                ),
                404,
            )

        # Validar campos obrigatórios
        if not data.get("localidade") or not data.get("uf"):
            return (
                jsonify(
                    {
                        "error": "Resposta incompleta do ViaCEP",
                        "message": "Dados do endereço incompletos",
                        "data": data,
                    }
                ),
                502,
            )

        # Preparar dados formatados (mesmo formato esperado pelo frontend)
        result_data = {
            "cep": data.get("cep", clean_cep),
            "rua": data.get("logradouro", ""),
            "bairro": data.get("bairro", ""),
            "cidade": data.get("localidade", ""),
            "uf": data.get("uf", ""),
            "complemento": data.get("complemento", ""),
            "ibge": data.get("ibge", ""),
            "ddd": data.get("ddd", ""),
        }

        # Salvar no cache
        _cep_cache[clean_cep] = (result_data, datetime.now())

        # Retornar dados formatados
        return jsonify(result_data), 200

    except (ValueError, KeyError) as e:
        # Erro no processamento da resposta (já tratado acima, mas manter para segurança)
        return (
            jsonify(
                {
                    "error": "Erro ao processar resposta do ViaCEP",
                    "message": "Resposta inválida do ViaCEP",
                    "detalhes": str(e),
                }
            ),
            502,
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "error": "Erro interno ao buscar CEP",
                    "message": "Erro inesperado no servidor",
                    "detalhes": str(e),
                }
            ),
            500,
        )


# ============================================
# ENDPOINTS DE FONTES DE PEDIDO
# ============================================


@core_bp.route("/exportar-planilha-leads", methods=["POST"])
@requires_edit_auth
def exportar_planilha_leads():
    """Exporta tabela leads para Google Sheets (planilha separada de VENDAS_*)."""
    try:
        import importlib.util
        import sys
        from pathlib import Path

        backend_dir = Path(__file__).parent.parent.parent
        script_path = backend_dir / "scripts" / "export" / "exportar_leads_sheets.py"

        if not script_path.exists():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Script não encontrado: {script_path}",
                        "detalhes": "Arquivo exportar_leads_sheets.py não encontrado",
                    }
                ),
                500,
            )

        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        spec = importlib.util.spec_from_file_location("exportar_leads_sheets", str(script_path))
        if spec is None or spec.loader is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Erro ao carregar módulo",
                        "detalhes": "Não foi possível criar spec do módulo",
                    }
                ),
                500,
            )

        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(script_path)
        spec.loader.exec_module(module)

        if not hasattr(module, "exportar_leads"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Função exportar_leads não encontrada no módulo",
                    }
                ),
                500,
            )

        resultado = module.exportar_leads()

        if resultado:
            return jsonify(
                {
                    "success": True,
                    "message": "Planilha de leads atualizada com sucesso!",
                }
            )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Erro ao exportar leads. Verifique credenciais Google e se a planilha existe.",
                }
            ),
            500,
        )

    except FileNotFoundError as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Credenciais do Google não configuradas",
                    "detalhes": str(e),
                }
            ),
            400,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Erro ao exportar planilha de leads",
                    "detalhes": str(e),
                }
            ),
            500,
        )
