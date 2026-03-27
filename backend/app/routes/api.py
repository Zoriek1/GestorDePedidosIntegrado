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
from app.middleware import requires_edit_auth
from app.models import Cliente, FontePedido, Pedido
from app.models.pedido import datetime_now_brazil
from app.utils.backup_helper import (
    get_backup_stats,
    get_last_backup_time,
    has_recent_backup,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

# ============================================
# ENDPOINT DE CRIAÇÃO DE PEDIDO - MIGRADO
# ============================================
# ATENÇÃO: Este endpoint foi migrado para app/routes/pedidos.py
# Mantido aqui temporariamente para compatibilidade
# NOVO LOCAL: app/routes/pedidos.py -> criar_pedido()


@api_bp.route("/pedidos", methods=["POST"])
@requires_edit_auth
def criar_pedido():
    """
    MIGRADO: Este endpoint foi movido para app/routes/pedidos.py
    Mantido aqui apenas para compatibilidade durante transição
    """
    # Proxy para a implementação nova para evitar divergência entre rotas duplicadas.
    from app.routes.pedidos import criar_pedido as criar_pedido_v2

    handler = getattr(criar_pedido_v2, "__wrapped__", criar_pedido_v2)
    return handler()

    try:
        data = request.get_json()

        # Verificação inicial de dados
        if not data:
            return jsonify({"error": "Nenhum dado fornecido"}), 400

        # Extração de dados do JSON
        # Step 1 - Dados do Cliente
        cliente = data.get("cliente", "").strip()
        telefone_cliente_raw = data.get("telefone_cliente", data.get("telefone", "")).strip()
        # Remover formatação do telefone (máscara deve existir apenas no frontend)
        telefone_cliente = re.sub(r"[^\d]", "", telefone_cliente_raw)
        destinatario = data.get("destinatario", "").strip()
        tipo_pedido = data.get("tipo_pedido", "Entrega")
        # Aceitar tanto fonte_pedido_id (novo) quanto fonte_pedido (string) para compatibilidade
        fonte_pedido_id = data.get("fonte_pedido_id")
        fonte_pedido = data.get("fonte_pedido", "").strip()  # Mantido para compatibilidade

        # Step 2 - Produto e Agendamento
        produto = data.get("produto", "").strip()
        flores_cor = data.get("flores_cor", "").strip()
        valor = data.get("valor", "").strip()
        horario = data.get("horario", data.get("hora_entrega", "")).strip()
        dia_entrega_str = data.get("dia_entrega", data.get("data_entrega", "")).strip()

        # Step 3 - Logística (campos de endereço separados)
        cep = data.get("cep", "").strip()
        rua = data.get("rua", "").strip()
        numero = data.get("numero", "").strip()
        bairro = data.get("bairro", "").strip()
        cidade = data.get("cidade", "").strip()
        endereco = data.get("endereco", "").strip()
        obs_entrega = data.get("obs_entrega", "").strip()

        # Step 4 - Finalização
        mensagem = data.get("mensagem", "").strip()
        pagamento = data.get("pagamento", "").strip()
        observacoes = data.get("observacoes", "").strip()
        status_pagamento = data.get("status_pagamento", "").strip()

        # Quantidade (compatibilidade)
        quantidade_raw = data.get("quantidade", 1)

        # Validação de campos obrigatórios
        campos_obrigatorios = {
            "telefone_cliente": telefone_cliente,
            "destinatario": destinatario,
            "produto": produto,
            "horario": horario,
            "dia_entrega": dia_entrega_str,
        }

        campos_faltantes = [campo for campo, valor in campos_obrigatorios.items() if not valor]
        if campos_faltantes:
            return (
                jsonify(
                    {
                        "error": f'Campos obrigatórios ausentes: {", ".join(campos_faltantes)}',
                        "campos_enviados": list(data.keys()),
                    }
                ),
                400,
            )

        # Conversão de quantidade para inteiro
        try:
            if isinstance(quantidade_raw, str):
                quantidade_raw = quantidade_raw.strip()
            quantidade = (
                int(quantidade_raw) if quantidade_raw and str(quantidade_raw).strip() else 1
            )
            if quantidade < 0:
                quantidade = 1
        except (ValueError, TypeError):
            quantidade = 1

        # Validação de formato de horário: aceita HH:MM ou intervalo HH:MM - HH:MM
        pattern_simples = r"^([01]?\d|2[0-3]):[0-5]\d$"
        pattern_intervalo = r"^([01]?\d|2[0-3]):[0-5]\d\s*-\s*([01]?\d|2[0-3]):[0-5]\d$"

        if not (re.match(pattern_simples, horario) or re.match(pattern_intervalo, horario)):
            return (
                jsonify(
                    {
                        "error": "Formato de horário inválido",
                        "horario_recebido": horario,
                        "formato_esperado": "HH:MM (ex: 14:30) ou intervalo HH:MM - HH:MM (ex: 08:00 - 10:00)",
                    }
                ),
                400,
            )

        # Se for intervalo, validar que horário final é depois do inicial
        if " - " in horario:
            partes = horario.split(" - ")
            if len(partes) == 2:
                try:
                    h1, m1 = map(int, partes[0].strip().split(":"))
                    h2, m2 = map(int, partes[1].strip().split(":"))
                    minutos_inicial = h1 * 60 + m1
                    minutos_final = h2 * 60 + m2
                    if minutos_final <= minutos_inicial:
                        return (
                            jsonify(
                                {
                                    "error": "O horário final deve ser depois do horário inicial",
                                    "horario_recebido": horario,
                                }
                            ),
                            400,
                        )
                except (ValueError, IndexError):
                    return (
                        jsonify(
                            {
                                "error": "Formato de intervalo inválido",
                                "horario_recebido": horario,
                            }
                        ),
                        400,
                    )

        # Conversão de data de entrega
        try:
            # Aceita formatos: YYYY-MM-DD ou DD/MM/YYYY
            if "/" in dia_entrega_str:
                dia_entrega = datetime.strptime(dia_entrega_str, "%d/%m/%Y").date()
            else:
                dia_entrega = datetime.strptime(dia_entrega_str, "%Y-%m-%d").date()
        except ValueError as e:
            return (
                jsonify(
                    {
                        "error": "Formato de data inválido",
                        "data_recebida": dia_entrega_str,
                        "formatos_aceitos": ["YYYY-MM-DD", "DD/MM/YYYY"],
                        "detalhes": str(e),
                    }
                ),
                400,
            )

        # Gerenciar cliente_id - criar cliente se necessário
        raw_cliente_id = data.get("cliente_id", "")
        cliente_id = raw_cliente_id.strip() if isinstance(raw_cliente_id, str) else raw_cliente_id

        # Se cliente_id não foi fornecido mas temos nome e telefone, buscar ou criar cliente
        if not cliente_id and cliente and telefone_cliente:
            # Buscar cliente existente por telefone
            cliente_existente = Cliente.buscar_por_telefone(telefone_cliente)

            if cliente_existente:
                # Cliente já existe, usar o ID
                cliente_id = cliente_existente.id
            else:
                # Criar novo cliente
                try:
                    novo_cliente = Cliente(
                        nome=cliente,
                        telefone=telefone_cliente,
                        email=None,
                        observacoes=None,
                    )
                    db.session.add(novo_cliente)
                    db.session.flush()  # Para obter o ID sem fazer commit
                    cliente_id = novo_cliente.id
                    print(
                        f"[INFO] Novo cliente criado: ID={cliente_id}, Nome={cliente}, Telefone={telefone_cliente}"
                    )
                except Exception as e:
                    print(f"[ERRO] Erro ao criar cliente: {e}")
                    # Continuar sem cliente_id se houver erro
                    cliente_id = None

        # Converter cliente_id para int se não for None
        cliente_id_int = int(cliente_id) if cliente_id else None

        # Processar fonte_pedido_id
        fonte_pedido_id_int = None
        if fonte_pedido_id:
            try:
                fonte_pedido_id_int = int(fonte_pedido_id)
            except (ValueError, TypeError):
                fonte_pedido_id_int = None
        elif fonte_pedido:  # Compatibilidade: se enviou string, buscar ID
            fonte = FontePedido.query.filter_by(nome=fonte_pedido, ativo=True).first()
            if fonte:
                fonte_pedido_id_int = fonte.id

        # Debug: Log dos campos recebidos
        print(
            f"[DEBUG] Criando pedido - fonte_pedido_id: {fonte_pedido_id_int}, fonte_pedido (legacy): '{fonte_pedido}', pagamento: '{pagamento}'"
        )
        print(f"[DEBUG] Dados recebidos: {list(data.keys())}")

        # Capturar fbc e fbp se enviados (Meta Pixel parameters)
        # fbc: Facebook Click ID (vem do parâmetro fbclid na URL)
        # fbp: Facebook Browser ID (vem do cookie _fbp criado pelo Pixel)
        fbc = data.get("fbc", "").strip() if data.get("fbc") else None
        fbp = data.get("fbp", "").strip() if data.get("fbp") else None

        # Criar instância do pedido
        pedido = Pedido(
            # Step 1
            cliente=cliente if cliente else None,
            telefone_cliente=telefone_cliente,
            destinatario=destinatario,
            tipo_pedido=tipo_pedido,
            fonte_pedido=fonte_pedido if fonte_pedido else None,  # Mantido para compatibilidade
            fonte_pedido_id=fonte_pedido_id_int,
            # Step 2
            produto=produto,
            flores_cor=flores_cor if flores_cor else None,
            valor=valor if valor else None,
            horario=horario,
            dia_entrega=dia_entrega,
            # Step 3 - Endereço
            cep=cep if cep else None,
            rua=rua if rua else None,
            numero=numero if numero else None,
            bairro=bairro if bairro else None,
            cidade=cidade if cidade else None,
            endereco=endereco if endereco else None,
            obs_entrega=obs_entrega if obs_entrega else None,
            # Step 4
            mensagem=mensagem if mensagem else None,
            pagamento=pagamento if pagamento else None,
            observacoes=observacoes if observacoes else None,
            status_pagamento=status_pagamento if status_pagamento else None,
            # Meta Pixel parameters (melhora qualidade de correspondência de eventos)
            fbc=fbc,
            fbp=fbp,
            # Controle
            status="agendado",
            quantidade=quantidade,
            # Relacionamento com cliente
            cliente_id=cliente_id_int,
        )

        # Inserir no banco de dados
        db.session.add(pedido)
        db.session.commit()

        # Debug: Verificar se os campos foram salvos
        print(
            f"[DEBUG] Pedido #{pedido.id} criado - fonte_pedido salvo: '{pedido.fonte_pedido}', pagamento salvo: '{pedido.pagamento}'"
        )

        # Inserir pedido na tabela auxiliar da fonte (se houver fonte)
        if fonte_pedido_id_int:
            try:
                from app.models.pedido_fonte import PedidoFonte

                resultado_fonte = PedidoFonte.adicionar_pedido(
                    pedido.id, fonte_pedido_id_int, valor if valor else None
                )
                if resultado_fonte:
                    print(
                        f"[DEBUG] Pedido #{pedido.id} inserido na tabela da fonte: {resultado_fonte.get('tabela')}, número sequencial: {resultado_fonte.get('numero_sequencial')}"
                    )
                else:
                    print(
                        f"[WARN] Não foi possível inserir pedido #{pedido.id} na tabela da fonte (fonte_id: {fonte_pedido_id_int})"
                    )
            except Exception as e:
                # Não falhar a criação do pedido se houver erro na inserção na tabela auxiliar
                print(f"[ERRO] Erro ao inserir pedido na tabela da fonte: {e}")

        # Enviar push notification em background (não bloqueia a resposta)
        try:
            from flask import current_app

            from app.services.notification_service import (
                format_delivery_datetime,
                send_push_to_all_async,
            )

            # Formatar data/hora de entrega
            entrega_info = format_delivery_datetime(pedido.dia_entrega, pedido.horario)
            if entrega_info:
                body = f"#{pedido.id} - {destinatario} | {produto} | Entrega: {entrega_info}"
            else:
                body = f"#{pedido.id} - {destinatario} | {produto}"

            send_push_to_all_async(
                app=current_app._get_current_object(),
                title="Novo Pedido!",
                body=body,
                url="/",
            )
        except Exception:
            pass  # Best-effort: não falhar criação do pedido

        # Resposta de sucesso
        return (
            jsonify(
                {
                    "success": True,
                    "pedido_id": pedido.id,
                    "message": "Pedido criado com sucesso",
                    "pedido": pedido.to_dict(),
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Erro interno do servidor", "detalhes": str(e)}), 500


# ============================================
# ENDPOINT DE LISTAGEM DE PEDIDOS - MIGRADO
# ============================================
# ATENÇÃO: Este endpoint foi migrado para app/routes/pedidos.py
# NOVO LOCAL: app/routes/pedidos.py -> listar_pedidos()


@api_bp.route("/pedidos", methods=["GET"])
def listar_pedidos():
    """
    MIGRADO: Este endpoint foi movido para app/routes/pedidos.py
    Mantido aqui apenas para compatibilidade durante transição

    Se filtrar_por_criacao ou data_inicio/data_fim estiverem presentes,
    redireciona para a nova rota em pedidos.py que tem suporte completo.
    """
    try:
        # Se tiver parâmetros da nova API (filtrar_por_criacao ou datas), usar nova rota
        filtrar_por_criacao = request.args.get("filtrar_por_criacao", "").lower() == "true"
        data_inicio = request.args.get("data_inicio")
        data_fim = request.args.get("data_fim")

        if filtrar_por_criacao or data_inicio or data_fim:
            # Redirecionar para a nova rota que tem suporte completo
            from app.routes.pedidos import listar_pedidos as nova_listar_pedidos

            return nova_listar_pedidos()

        # Comportamento antigo (sem filtrar_por_criacao) - manter para compatibilidade
        # Parâmetros de filtro
        status = request.args.get("status")
        limit = request.args.get("limit", type=int)
        search = request.args.get("search", "").strip()

        # Query base - excluir pedidos ocultos/arquivados e soft-deleted (comportamento antigo)
        query = Pedido.query.filter(Pedido.oculto.is_(False)).filter(Pedido.deleted_at.is_(None))

        # Aplicar filtros
        if status:
            query = query.filter(Pedido.status == status)

        # Busca por cliente ou destinatário
        if search:
            query = query.filter(
                db.or_(
                    Pedido.cliente.ilike(f"%{search}%"),
                    Pedido.destinatario.ilike(f"%{search}%"),
                )
            )

        # Ordenar por data de entrega e horário (mais próximos primeiro: hoje antes de amanhã, mais cedo antes de mais tarde)
        query = query.order_by(Pedido.dia_entrega.asc(), Pedido.horario.asc())

        # Aplicar limite
        if limit:
            query = query.limit(limit)

        pedidos = query.all()

        return jsonify(
            {
                "success": True,
                "count": len(pedidos),
                "pedidos": [p.to_dict() for p in pedidos],
            }
        )

    except Exception as e:
        return jsonify({"error": "Erro interno do servidor", "detalhes": str(e)}), 500


# ============================================
# ENDPOINT DE PEDIDOS POR DATA - MIGRADO
# ============================================
# ATENÇÃO: Este endpoint foi migrado para app/routes/pedidos.py
# NOVO LOCAL: app/routes/pedidos.py -> get_pedidos_por_data()


@api_bp.route("/pedidos/por-data", methods=["GET"])
def get_pedidos_por_data():
    """
    MIGRADO: Este endpoint foi movido para app/routes/pedidos.py
    Mantido aqui apenas para compatibilidade durante transição
    """
    try:
        data_str = request.args.get("data")

        if not data_str:
            return (
                jsonify(
                    {
                        "error": 'Parâmetro "data" é obrigatório',
                        "formato_esperado": "YYYY-MM-DD (ex: 2025-12-20)",
                    }
                ),
                400,
            )

        # Converter data para formato do banco (YYYY-MM-DD)
        try:
            # Aceita formatos: YYYY-MM-DD ou DD/MM/YYYY
            if "/" in data_str:
                # Formato DD/MM/YYYY -> YYYY-MM-DD
                partes = data_str.split("/")
                if len(partes) == 3:
                    dia, mes, ano = partes
                    data_entrega = datetime.strptime(f"{ano}-{mes}-{dia}", "%Y-%m-%d").date()
                else:
                    return jsonify({"error": "Formato de data inválido"}), 400
            else:
                # Formato YYYY-MM-DD
                data_entrega = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError as e:
            return (
                jsonify(
                    {
                        "error": "Formato de data inválido",
                        "detalhes": str(e),
                        "formato_esperado": "YYYY-MM-DD ou DD/MM/YYYY",
                    }
                ),
                400,
            )

        # Buscar todos os pedidos do dia (não ocultos)
        pedidos = Pedido.query.filter(
            Pedido.dia_entrega == data_entrega, Pedido.oculto is False
        ).all()

        # Agrupar por horário e contar
        horarios = {}
        for pedido in pedidos:
            horario = pedido.horario.strip() if pedido.horario else ""
            if horario:
                if horario in horarios:
                    horarios[horario] += 1
                else:
                    horarios[horario] = 1

        return jsonify(
            {
                "success": True,
                "data": data_str,
                "data_formatada": data_entrega.strftime("%Y-%m-%d"),
                "total_pedidos": len(pedidos),
                "horarios": horarios,
            }
        )

    except Exception as e:
        return jsonify({"error": "Erro interno do servidor", "detalhes": str(e)}), 500


@api_bp.route("/pedidos/<int:pedido_id>", methods=["GET"])
def obter_pedido(pedido_id):
    """Obtém pedido específico"""
    try:
        pedido = Pedido.query.get(pedido_id)

        if not pedido:
            return (
                jsonify({"error": "Pedido não encontrado", "pedido_id": pedido_id}),
                404,
            )

        return jsonify({"success": True, "pedido": pedido.to_dict()})

    except Exception as e:
        return jsonify({"error": "Erro ao obter pedido", "detalhes": str(e)}), 500


@api_bp.route("/pedidos/<int:pedido_id>/status", methods=["PUT", "POST"])
def atualizar_status(pedido_id):
    """Atualiza status do pedido"""
    try:
        data = request.get_json() or {}
        novo_status = data.get("status") or request.form.get("status")

        if not novo_status:
            return jsonify({"error": "Status não fornecido"}), 400

        # Validar status
        status_validos = [
            "agendado",
            "em_producao",
            "pronto_entrega",
            "em_rota",
            "pronto_retirada",
            "concluido",
        ]
        if novo_status not in status_validos:
            return (
                jsonify({"error": "Status inválido", "status_validos": status_validos}),
                400,
            )

        # Atualizar pedido
        pedido = Pedido.query.get(pedido_id)

        if not pedido:
            return (
                jsonify({"error": "Pedido não encontrado", "pedido_id": pedido_id}),
                404,
            )

        pedido.status = novo_status
        pedido.updated_at = datetime_now_brazil()

        if novo_status == "concluido" and (
            not pedido.status_pagamento or pedido.status_pagamento.upper() == "PENDENTE"
        ):
            pedido.status_pagamento = "Pago"

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Status atualizado para {novo_status}",
                "pedido": pedido.to_dict(),
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Erro ao atualizar status", "detalhes": str(e)}), 500


# ============================================
# ENDPOINT MARCAR IMPRESSO - MIGRADO
# ============================================
# ATENÇÃO: Este endpoint foi migrado para app/routes/pedidos.py
# NOVO LOCAL: app/routes/pedidos.py -> marcar_impresso()


@api_bp.route("/pedidos/<int:pedido_id>/marcar-impresso", methods=["POST", "PUT", "OPTIONS"])
def marcar_impresso(pedido_id):
    """
    MIGRADO: Este endpoint foi movido para app/routes/pedidos.py
    Mantido aqui apenas para compatibilidade durante transição
    """
    print(f"[BACKEND] marcar_impresso: Recebido pedido_id={pedido_id}, method={request.method}")

    # Suporte a OPTIONS para CORS
    if request.method == "OPTIONS":
        print("[BACKEND] marcar_impresso: Respondendo OPTIONS para CORS")
        return jsonify({"success": True}), 200

    try:
        print(f"[BACKEND] marcar_impresso: Buscando pedido {pedido_id} no banco...")
        pedido = Pedido.query.get(pedido_id)

        if not pedido:
            print(f"[BACKEND] marcar_impresso: Pedido {pedido_id} não encontrado")
            return (
                jsonify({"error": "Pedido não encontrado", "pedido_id": pedido_id}),
                404,
            )

        print(
            f"[BACKEND] marcar_impresso: Pedido encontrado - ID={pedido.id}, Cliente={pedido.cliente}, Impresso atual={pedido.impresso}"
        )
        print("[BACKEND] marcar_impresso: Marcando como impresso...")

        pedido.impresso = True
        pedido.updated_at = datetime.utcnow()

        print("[BACKEND] marcar_impresso: Fazendo commit no banco...")
        db.session.commit()

        print(f"[BACKEND] marcar_impresso: Sucesso - pedido {pedido_id} marcado como impresso")

        return jsonify(
            {
                "success": True,
                "message": "Pedido marcado como impresso",
                "pedido": pedido.to_dict(),
            }
        )

    except Exception as e:
        print(f"[BACKEND] marcar_impresso: Erro - {str(e)}")
        import traceback

        traceback.print_exc()
        db.session.rollback()
        return (
            jsonify({"error": "Erro ao marcar pedido como impresso", "detalhes": str(e)}),
            500,
        )


# ============================================
# ENDPOINT DE ATUALIZAÇÃO DE PEDIDO - MIGRADO
# ============================================
# ATENÇÃO: Este endpoint foi migrado para app/routes/pedidos.py
# NOVO LOCAL: app/routes/pedidos.py -> atualizar_pedido()


@api_bp.route("/pedidos/<int:pedido_id>", methods=["PUT"])
def atualizar_pedido(pedido_id):
    """
    MIGRADO: Este endpoint foi movido para app/routes/pedidos.py
    Mantido aqui apenas para compatibilidade durante transição
    """
    from app.routes.pedidos import atualizar_pedido as atualizar_pedido_v2

    handler = getattr(atualizar_pedido_v2, "__wrapped__", atualizar_pedido_v2)
    return handler(pedido_id)

    try:
        print(f"[API] Atualizando pedido {pedido_id}")
        pedido = Pedido.query.get(pedido_id)

        if not pedido:
            print(f"[API] Pedido {pedido_id} não encontrado")
            return (
                jsonify({"error": "Pedido não encontrado", "pedido_id": pedido_id}),
                404,
            )

        data = request.get_json()
        print(f"[API] Dados recebidos: {list(data.keys()) if data else 'Nenhum dado'}")

        # Atualizar campos fornecidos
        if "cliente" in data:
            pedido.cliente = data["cliente"]
        if "telefone_cliente" in data:
            pedido.telefone_cliente = data["telefone_cliente"]
        if "destinatario" in data:
            pedido.destinatario = data["destinatario"]
        if "tipo_pedido" in data:
            pedido.tipo_pedido = data["tipo_pedido"]
        if "fonte_pedido_id" in data:
            try:
                pedido.fonte_pedido_id = (
                    int(data["fonte_pedido_id"]) if data["fonte_pedido_id"] else None
                )
            except (ValueError, TypeError):
                pedido.fonte_pedido_id = None
        elif "fonte_pedido" in data:  # Compatibilidade: aceitar string também
            fonte = FontePedido.query.filter_by(nome=data["fonte_pedido"], ativo=True).first()
            if fonte:
                pedido.fonte_pedido_id = fonte.id
            pedido.fonte_pedido = data["fonte_pedido"]  # Mantido para compatibilidade
        if "produto" in data:
            pedido.produto = data["produto"]
        if "flores_cor" in data:
            pedido.flores_cor = data["flores_cor"]
        if "valor" in data:
            pedido.valor = data["valor"]
        if "horario" in data:
            pedido.horario = data["horario"]
        if "dia_entrega" in data:
            dia_entrega_str = data["dia_entrega"]
            if "/" in dia_entrega_str:
                pedido.dia_entrega = datetime.strptime(dia_entrega_str, "%d/%m/%Y").date()
            else:
                pedido.dia_entrega = datetime.strptime(dia_entrega_str, "%Y-%m-%d").date()
        # Campos de endereço - se qualquer um mudar, limpar a distância para recalcular
        endereco_mudou = False
        if "cep" in data and data["cep"] != pedido.cep:
            pedido.cep = data["cep"]
            endereco_mudou = True
        if "rua" in data and data["rua"] != pedido.rua:
            pedido.rua = data["rua"]
            endereco_mudou = True
        if "numero" in data and data["numero"] != pedido.numero:
            pedido.numero = data["numero"]
            endereco_mudou = True
        if "bairro" in data and data["bairro"] != pedido.bairro:
            pedido.bairro = data["bairro"]
            endereco_mudou = True
        if "cidade" in data and data["cidade"] != pedido.cidade:
            pedido.cidade = data["cidade"]
            endereco_mudou = True
        if "endereco" in data and data["endereco"] != pedido.endereco:
            pedido.endereco = data["endereco"]
            endereco_mudou = True

        # Se o endereço mudou, limpar distância para forçar recálculo
        if endereco_mudou:
            pedido.distancia_km = None
            print(f"[DEBUG] Endereço do pedido {pedido_id} alterado - distância resetada")
        if "obs_entrega" in data:
            pedido.obs_entrega = data["obs_entrega"]
        if "mensagem" in data:
            pedido.mensagem = data["mensagem"]
        if "pagamento" in data:
            pedido.pagamento = data["pagamento"]
        if "observacoes" in data:
            pedido.observacoes = data["observacoes"]
        if "status_pagamento" in data:
            pedido.status_pagamento = data["status_pagamento"]
        if "status" in data:
            pedido.status = data["status"]

        pedido.updated_at = datetime.utcnow()

        db.session.commit()
        print(f"[API] Pedido {pedido_id} atualizado com sucesso")

        return jsonify(
            {
                "success": True,
                "message": "Pedido atualizado com sucesso",
                "pedido": pedido.to_dict(),
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"[API] Erro ao atualizar pedido {pedido_id}: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Erro ao atualizar pedido", "detalhes": str(e)}), 500


# ============================================
# ENDPOINT DE DELEÇÃO DE PEDIDO - REMOVIDO
# ============================================
# Este endpoint foi removido pois foi migrado para app/routes/pedidos.py
# O endpoint correto está em: pedidos_bp.route('/<int:pedido_id>', methods=['DELETE'])
# Localização: app/routes/pedidos.py -> deletar_pedido()


@api_bp.route("/stats", methods=["GET"])
def obter_estatisticas():
    """Retorna estatísticas dos pedidos"""
    try:
        stats = Pedido.get_statistics()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"error": "Erro ao obter estatísticas", "detalhes": str(e)}), 500


@api_bp.route("/backup/status", methods=["GET"])
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


@api_bp.route("/pedidos/overdue", methods=["GET"])
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


@api_bp.route("/cleanup", methods=["POST"])
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


@api_bp.route("/pedidos/<int:pedido_id>/distancia", methods=["GET"])
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


@api_bp.route("/pedidos/calcular-distancias", methods=["POST"])
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


@api_bp.route("/pedidos/<int:pedido_id>/calcular-taxa", methods=["POST"])
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


@api_bp.route("/pedidos/rota-otimizada", methods=["POST"])
def calcular_rota_otimizada():
    """
    MIGRADO: Este endpoint foi movido para app/routes/rotas.py
    Mantido aqui apenas para compatibilidade durante transição
    """
    try:
        import os

        from app.models import RotaOtimizada
        from app.services.distancia import distancia_service
        from app.services.graphhopper import graphhopper_service

        data = request.get_json() or {}
        pedido_ids = data.get("pedido_ids", [])
        nome_rota = data.get("nome", "Rota Otimizada")

        if not pedido_ids:
            # Se não especificar IDs, usar pedidos elegíveis
            pedidos = Pedido.query.filter(
                Pedido.oculto is False,
                Pedido.status != "concluido",
                Pedido.tipo_pedido == "Entrega",
                Pedido.distancia_km.isnot(None),  # Apenas pedidos com distância calculada
            ).all()
        else:
            pedidos = Pedido.query.filter(
                Pedido.id.in_(pedido_ids),
                Pedido.status != "concluido",
                Pedido.tipo_pedido == "Entrega",
            ).all()

        if len(pedidos) < 2:
            return (
                jsonify(
                    {
                        "error": "É necessário pelo menos 2 pedidos para calcular rota otimizada",
                        "pedidos_encontrados": len(pedidos),
                    }
                ),
                400,
            )

        # Obter coordenadas da floricultura
        origem = distancia_service.coords_floricultura
        if not origem:
            return (
                jsonify({"error": "Não foi possível obter coordenadas da floricultura"}),
                500,
            )

        # Converter para formato (lat, lon) para GraphHopper
        origem_gh = (origem[1], origem[0])

        # Coletar waypoints dos pedidos (apenas os que têm coordenadas)
        pedidos_com_coords = []

        for pedido in pedidos:
            if pedido.coords_lat and pedido.coords_lon:
                pedidos_com_coords.append(pedido)
            else:
                # Tentar geocodificar se não tiver coordenadas (usando apenas campos separados)
                resultado = distancia_service.calcular_distancia_pedido(
                    pedido_id=pedido.id,
                    rua=pedido.rua,
                    numero=pedido.numero,
                    bairro=pedido.bairro,
                    cidade=pedido.cidade,
                    cep=pedido.cep,
                    cliente_id=pedido.cliente_id,
                )

                # Verificar se houve erro ou se obteve coordenadas
                if resultado and "error" not in resultado and "coords_destino_lat" in resultado:
                    lat = resultado["coords_destino_lat"]
                    lon = resultado["coords_destino_lon"]
                    pedido.coords_lat = lat
                    pedido.coords_lon = lon
                    pedidos_com_coords.append(pedido)
                elif resultado and "error" in resultado:
                    print(
                        f"[AVISO] Pedido {pedido.id} não pôde ser geocodificado: {resultado['error']}"
                    )

        if len(pedidos_com_coords) < 2:
            return (
                jsonify(
                    {
                        "error": "É necessário pelo menos 2 pedidos com coordenadas válidas",
                        "waypoints_encontrados": len(pedidos_com_coords),
                    }
                ),
                400,
            )

        # NOVA LÓGICA: Agrupar pedidos por horário antes de otimizar
        grupos_horario = agrupar_pedidos_por_horario(pedidos_com_coords)

        sequencia_pedidos_final = []
        waypoints_finais = []
        distancia_total = 0.0
        duracao_total = 0.0

        # Para cada grupo de horário, otimizar geograficamente
        for grupo in grupos_horario:
            if len(grupo) == 0:
                continue

            # Se grupo tem apenas 1 pedido, adicionar diretamente
            if len(grupo) == 1:
                pedido = grupo[0]
                sequencia_pedidos_final.append(pedido.id)
                waypoints_finais.append((pedido.coords_lat, pedido.coords_lon))
                continue

            # Coletar waypoints do grupo
            waypoints_grupo = [(p.coords_lat, p.coords_lon) for p in grupo]

            # Otimizar ordem geográfica dentro do grupo
            resultado_grupo = graphhopper_service.calcular_rota_otimizada(
                origem_gh, waypoints_grupo, retornar_origem=False
            )

            if resultado_grupo:
                waypoints_otimizados_grupo = resultado_grupo.get(
                    "sequencia_otimizada", waypoints_grupo
                )
                distancia_total += resultado_grupo.get("distancia_total_km", 0)
                duracao_total += resultado_grupo.get("duracao_total_min", 0)
            else:
                # Se falhar otimização, usar ordem original por horário
                waypoints_otimizados_grupo = waypoints_grupo

            # Mapear waypoints otimizados de volta para pedidos do grupo
            sequencia_grupo = mapear_waypoints_para_pedidos(waypoints_otimizados_grupo, grupo)

            # Adicionar à sequência final
            sequencia_pedidos_final.extend(sequencia_grupo)
            waypoints_finais.extend(waypoints_otimizados_grupo)

        # Validar sequência final (verificar duplicatas)
        sequencia_validada = []
        ids_vistos = set()
        for pedido_id in sequencia_pedidos_final:
            if pedido_id not in ids_vistos:
                sequencia_validada.append(pedido_id)
                ids_vistos.add(pedido_id)
            else:
                print(f"[AVISO] Pedido {pedido_id} duplicado na sequência, removendo duplicata")

        # Se a sequência validada tem menos pedidos, usar a original mas sem duplicatas
        if len(sequencia_validada) < len(pedidos_com_coords):
            print(
                f"[AVISO] Sequência validada perdeu pedidos. Original: {len(sequencia_pedidos_final)}, Validada: {len(sequencia_validada)}"
            )
            # Tentar recuperar pedidos faltantes
            for pedido in pedidos_com_coords:
                if pedido.id not in ids_vistos:
                    sequencia_validada.append(pedido.id)
                    ids_vistos.add(pedido.id)

        sequencia_pedidos = sequencia_validada

        # Verificar se a sequência está invertida comparando com ordem esperada por horário
        def get_horario_pedido(pedido_id):
            for p in pedidos_com_coords:
                if p.id == pedido_id:
                    try:
                        if p.horario:
                            # Se for intervalo, usar horário inicial
                            horario_str = p.horario
                            if " - " in horario_str:
                                partes = horario_str.split(" - ")
                                if len(partes) >= 1:
                                    horario_str = partes[0].strip()
                            if ":" in horario_str:
                                h, m = map(int, horario_str.split(":"))
                                return h * 60 + m
                    except (ValueError, IndexError):
                        pass
            return 9999  # Valor alto para pedidos sem horário válido

        # Verificar ordem temporal da sequência
        if len(sequencia_pedidos) >= 2:
            horarios_sequencia = [get_horario_pedido(pid) for pid in sequencia_pedidos]

            # Verificar se a sequência está em ordem crescente de horário
            # Se não estiver, pode estar invertida
            ordem_crescente = all(
                horarios_sequencia[i] <= horarios_sequencia[i + 1]
                for i in range(len(horarios_sequencia) - 1)
            )

            # Se a ordem está decrescente e não há valores inválidos, provavelmente está invertida
            ordem_decrescente = all(
                horarios_sequencia[i] >= horarios_sequencia[i + 1]
                for i in range(len(horarios_sequencia) - 1)
            )

            if (
                ordem_decrescente
                and not ordem_crescente
                and all(h < 9999 for h in horarios_sequencia)
            ):
                print(
                    "[INFO] Detectada sequência invertida (ordem decrescente de horários). Revertendo..."
                )
                sequencia_pedidos = sequencia_pedidos[::-1]
                waypoints_finais = waypoints_finais[::-1]

        # Calcular distância e duração total se não foram calculadas por grupos
        if distancia_total == 0 or duracao_total == 0:
            # Calcular rota completa para obter distância e duração totais
            # Converter waypoints para formato (lat, lon) do GraphHopper
            waypoints_gh = [(wp[0], wp[1]) for wp in waypoints_finais]
            resultado_rota_completa = graphhopper_service.calcular_rota_otimizada(
                origem_gh, waypoints_gh, retornar_origem=True
            )

            if resultado_rota_completa:
                distancia_total = resultado_rota_completa.get("distancia_total_km", 0)
                duracao_total = resultado_rota_completa.get("duracao_total_min", 0)
                # Atualizar waypoints finais com a sequência otimizada completa
                waypoints_otimizados_completa = resultado_rota_completa.get(
                    "sequencia_otimizada", waypoints_finais
                )

                # Re-mapear waypoints otimizados para pedidos mantendo a ordem temporal
                # Mas respeitando a otimização geográfica dentro dos grupos
                sequencia_pedidos_nova = mapear_waypoints_para_pedidos(
                    waypoints_otimizados_completa, pedidos_com_coords
                )

                # Validar que não perdemos pedidos
                if len(sequencia_pedidos_nova) == len(sequencia_pedidos):
                    sequencia_pedidos = sequencia_pedidos_nova
                    waypoints_finais = waypoints_otimizados_completa
                else:
                    print(
                        "[AVISO] Re-mapeamento perdeu pedidos. Mantendo sequência original baseada em horário."
                    )
            else:
                # Fallback: usar estimativa baseada em distâncias individuais
                distancia_total = sum(p.distancia_km or 0 for p in pedidos_com_coords)
                duracao_total = distancia_total * 2  # Estimativa: 2 min/km
                print("[AVISO] Não foi possível calcular rota completa. Usando estimativas.")

        # Salvar rota no banco
        rota = RotaOtimizada(
            nome=nome_rota,
            distancia_total_km=round(distancia_total, 2),
            duracao_total_min=round(duracao_total, 1),
            origem_lat=origem[1],
            origem_lon=origem[0],
            num_pedidos=len(sequencia_pedidos),
            metodo_otimizacao="hybrid_temporal_geographic",  # Novo método híbrido
        )
        rota.set_sequencia_pedidos(sequencia_pedidos)
        rota.set_waypoints_coords(waypoints_finais)

        db.session.add(rota)

        # Salvar coordenadas dos pedidos se ainda não tiverem
        try:
            db.session.commit()
        except Exception as commit_error:
            print(f"[ERRO] Erro ao salvar rota: {commit_error}")
            db.session.rollback()
            raise

        # Gerar link do GraphHopper Maps para visualização
        graphhopper_key = os.environ.get("GRAPHHOPPER_API_KEY", "")
        graphhopper_maps_url = None

        if graphhopper_key:
            # Construir URL do GraphHopper Maps com todos os pontos
            waypoints_coords = rota.get_waypoints_coords()
            points_params = f"point={origem[1]},{origem[0]}"  # Origem (lat,lon)

            for wp in waypoints_coords:
                points_params += f"&point={wp[0]},{wp[1]}"

            # Sempre adicionar retorno à origem
            points_params += f"&point={origem[1]},{origem[0]}"  # Retornar à origem

            graphhopper_maps_url = f"https://graphhopper.com/maps/?{points_params}&profile=car&layer=Omniscale&key={graphhopper_key}"

        return jsonify(
            {
                "success": True,
                "rota_id": rota.id,
                "nome": rota.nome,
                "distancia_total_km": rota.distancia_total_km,
                "duracao_total_min": rota.duracao_total_min,
                "sequencia_pedidos": rota.get_sequencia_pedidos(),
                "num_pedidos": rota.num_pedidos,
                "metodo_otimizacao": rota.metodo_otimizacao,
                "origem": {"lat": rota.origem_lat, "lon": rota.origem_lon},
                "waypoints": rota.get_waypoints_coords(),
                "graphhopper_maps_url": graphhopper_maps_url,
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"[ERRO] Exceção ao calcular rota otimizada: {e}")
        import traceback

        traceback.print_exc()
        return (
            jsonify({"error": "Erro ao calcular rota otimizada", "detalhes": str(e)}),
            500,
        )


# ============================================
# ENDPOINT DE ROTA OTIMIZADA POR ID - MIGRADO
# ============================================
# ATENÇÃO: Este endpoint foi migrado para app/routes/rotas.py
# Mantido aqui temporariamente para compatibilidade
# NOVO LOCAL: app/routes/rotas.py -> obter_rota_otimizada()


@api_bp.route("/pedidos/rota-otimizada/<int:rota_id>", methods=["GET"])
def obter_rota_otimizada(rota_id):
    """
    MIGRADO: Este endpoint foi movido para app/routes/rotas.py
    Mantido aqui apenas para compatibilidade durante transição
    """
    try:
        import os

        from app.models import RotaOtimizada

        rota = RotaOtimizada.query.get(rota_id)

        if not rota:
            return jsonify({"error": "Rota não encontrada", "rota_id": rota_id}), 404

        # Buscar informações dos pedidos na sequência
        pedidos_info = []
        for pedido_id in rota.get_sequencia_pedidos():
            pedido = Pedido.query.get(pedido_id)
            if pedido:
                pedidos_info.append(
                    {
                        "id": pedido.id,
                        "cliente": pedido.cliente,
                        "destinatario": pedido.destinatario,
                        "endereco": pedido.endereco,
                        "distancia_km": pedido.distancia_km,
                        "coords_lat": pedido.coords_lat,
                        "coords_lon": pedido.coords_lon,
                    }
                )

        # Gerar URL do GraphHopper Maps ou Google Maps
        graphhopper_key = os.environ.get("GRAPHHOPPER_API_KEY", "")
        graphhopper_maps_url = None
        google_maps_url = None
        google_maps_step_by_step = []

        # Coletar coordenadas dos pedidos se waypoints não estiverem salvos
        waypoints_coords = rota.get_waypoints_coords()
        if not waypoints_coords or len(waypoints_coords) == 0:
            # Usar coordenadas dos pedidos como fallback
            waypoints_coords = []
            for pedido_info in pedidos_info:
                if pedido_info.get("coords_lat") and pedido_info.get("coords_lon"):
                    waypoints_coords.append([pedido_info["coords_lat"], pedido_info["coords_lon"]])

        # Gerar URL do GraphHopper Maps se tiver chave e waypoints
        if graphhopper_key and waypoints_coords and len(waypoints_coords) > 0:
            points_params = f"point={rota.origem_lat},{rota.origem_lon}"  # Origem

            for wp in waypoints_coords:
                points_params += f"&point={wp[0]},{wp[1]}"

            # Sempre adicionar retorno à origem
            points_params += f"&point={rota.origem_lat},{rota.origem_lon}"

            graphhopper_maps_url = f"https://graphhopper.com/maps/?{points_params}&profile=car&layer=Omniscale&key={graphhopper_key}"

        # Gerar URL do Google Maps como alternativa (sempre disponível)
        if waypoints_coords and len(waypoints_coords) > 0:
            # Construir URL do Google Maps com waypoints
            origem_str = f"{rota.origem_lat},{rota.origem_lon}"

            # Se houver apenas um waypoint, usar formato simples
            if len(waypoints_coords) == 1:
                wp = waypoints_coords[0]
                google_maps_url = (
                    f"https://www.google.com/maps/dir/{origem_str}/{wp[0]},{wp[1]}/{origem_str}"
                )
            else:
                # Para múltiplos waypoints, usar formato com waypoints intermediários
                waypoints_str = "/".join([f"{wp[0]},{wp[1]}" for wp in waypoints_coords])
                destino_str = f"{waypoints_coords[-1][0]},{waypoints_coords[-1][1]}"
                google_maps_url = f"https://www.google.com/maps/dir/{origem_str}/{waypoints_str}/{destino_str}/{origem_str}"

        rota_dict = rota.to_dict()
        rota_dict["graphhopper_maps_url"] = graphhopper_maps_url
        rota_dict["google_maps_url"] = google_maps_url
        rota_dict["google_maps_step_by_step"] = google_maps_step_by_step

        return jsonify({"success": True, "rota": rota_dict, "pedidos": pedidos_info})

    except Exception as e:
        return (
            jsonify({"error": "Erro ao obter rota otimizada", "detalhes": str(e)}),
            500,
        )


@api_bp.route("/health", methods=["GET"])
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


@api_bp.route("/cep/<cep>", methods=["GET"])
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


@api_bp.route("/fontes-pedido", methods=["GET"])
def listar_fontes_pedido():
    """Lista todas as fontes de pedido ativas"""
    try:
        apenas_ativas = request.args.get("ativas", "true").lower() == "true"
        print(f"[API] Listando fontes (apenas ativas: {apenas_ativas})...")

        if apenas_ativas:
            fontes = FontePedido.get_ativas()
        else:
            fontes = FontePedido.get_all()

        print(f"[API] {len(fontes)} fontes encontradas")

        return jsonify(
            {
                "success": True,
                "count": len(fontes),
                "fontes": [f.to_dict() for f in fontes],
            }
        )
    except Exception as e:
        print(f"[API] Erro ao listar fontes: {e}")
        import traceback

        traceback.print_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Erro ao listar fontes",
                    "detalhes": str(e),
                    "sugestao": "Execute a migração: python backend/scripts/migrations/migrate_fonte_pedido.py",
                }
            ),
            500,
        )


@api_bp.route("/fontes-pedido/all", methods=["GET"])
def listar_todas_fontes():
    """Lista todas as fontes (ativas e inativas)"""
    try:
        print("[API] Listando todas as fontes...")
        fontes = FontePedido.get_all()
        print(f"[API] {len(fontes)} fontes encontradas")

        return jsonify(
            {
                "success": True,
                "count": len(fontes),
                "fontes": [f.to_dict() for f in fontes],
            }
        )
    except Exception as e:
        print(f"[API] Erro ao listar fontes: {e}")
        import traceback

        traceback.print_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Erro ao listar fontes",
                    "detalhes": str(e),
                    "sugestao": "Execute a migração: python backend/scripts/migrations/migrate_fonte_pedido.py",
                }
            ),
            500,
        )


@api_bp.route("/fontes-pedido", methods=["POST"])
@requires_edit_auth
def criar_fonte_pedido():
    """Cria nova fonte de pedido"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Nenhum dado fornecido"}), 400

        nome = data.get("nome", "").strip()

        if not nome:
            return jsonify({"error": "Nome da fonte é obrigatório"}), 400

        # Verificar se já existe
        fonte_existente = FontePedido.query.filter_by(nome=nome).first()
        if fonte_existente:
            return (
                jsonify(
                    {
                        "error": "Fonte com este nome já existe",
                        "fonte_id": fonte_existente.id,
                    }
                ),
                400,
            )

        # Criar nova fonte
        fonte = FontePedido(nome=nome, ativo=data.get("ativo", True))

        db.session.add(fonte)
        db.session.commit()

        # Criar tabela auxiliar para a nova fonte (se estiver ativa)
        if fonte.ativo:
            try:
                from app.models.pedido_fonte import PedidoFonte

                sucesso, nome_tabela = PedidoFonte.criar_tabela_para_fonte(fonte.id)
                if sucesso:
                    print(f"[INFO] Tabela '{nome_tabela}' criada para fonte '{fonte.nome}'")
            except Exception as e:
                print(f"[WARN] Erro ao criar tabela para nova fonte: {e}")
                # Não falhar a criação da fonte se houver erro na tabela

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Fonte criada com sucesso",
                    "fonte": fonte.to_dict(),
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Erro ao criar fonte", "detalhes": str(e)}), 500


@api_bp.route("/fontes-pedido/<int:fonte_id>", methods=["PUT"])
@requires_edit_auth
def atualizar_fonte_pedido(fonte_id):
    """Atualiza fonte de pedido"""
    try:
        fonte = FontePedido.query.get(fonte_id)

        if not fonte:
            return jsonify({"error": "Fonte não encontrada", "fonte_id": fonte_id}), 404

        data = request.get_json()

        if "nome" in data:
            novo_nome = data["nome"].strip()
            if novo_nome and novo_nome != fonte.nome:
                # Verificar se outro já tem este nome
                existente = FontePedido.query.filter_by(nome=novo_nome).first()
                if existente and existente.id != fonte_id:
                    return jsonify({"error": "Fonte com este nome já existe"}), 400
                fonte.nome = novo_nome

        if "ativo" in data:
            fonte.ativo = bool(data["ativo"])

        fonte.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Fonte atualizada com sucesso",
                "fonte": fonte.to_dict(),
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Erro ao atualizar fonte", "detalhes": str(e)}), 500


@api_bp.route("/fontes-pedido/<int:fonte_id>", methods=["DELETE"])
@requires_edit_auth
def deletar_fonte_pedido(fonte_id):
    """Desativa fonte de pedido (soft delete)"""
    from app.schemas.common import error_response
    from app.utils.destructive_action_guard import (
        BackupRequiredException,
        ensure_backup_before_destructive_action,
    )

    try:
        fonte = FontePedido.query.get(fonte_id)

        if not fonte:
            return jsonify({"error": "Fonte não encontrada", "fonte_id": fonte_id}), 404

        # Fail-closed: garantir backup antes de operação destrutiva (P0.2)
        # Nota: Embora seja soft delete, mantemos guard para consistência
        try:
            ensure_backup_before_destructive_action(
                reason="delete_fonte_pedido", context={"fonte_id": fonte_id}
            )
        except BackupRequiredException as backup_error:
            error_msg = str(backup_error)
            return error_response(
                "Backup necessário antes de operação destrutiva. Falha ao criar backup. Operação bloqueada por segurança.",
                503,
                details={"error": error_msg, "fonte_id": fonte_id},
            )

        # Soft delete: apenas desativar
        fonte.ativo = False
        fonte.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Fonte desativada com sucesso",
                "fonte": fonte.to_dict(),
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Erro ao desativar fonte", "detalhes": str(e)}), 500


# ============================================
# ENDPOINTS DE PEDIDOS POR FONTE
# ============================================


@api_bp.route("/pedidos/fonte/<int:fonte_id>", methods=["GET"])
def listar_pedidos_fonte(fonte_id):
    """
    Lista pedidos de uma fonte específica
    Retorna pedidos com numeração sequencial da fonte
    """
    try:
        from app.models.pedido_fonte import PedidoFonte

        # Verificar se fonte existe
        fonte = FontePedido.query.get(fonte_id)
        if not fonte:
            return jsonify({"error": "Fonte não encontrada", "fonte_id": fonte_id}), 404

        # Parâmetros de paginação
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int) or 0

        # Buscar pedidos da fonte
        pedidos = PedidoFonte.obter_pedidos(fonte_id, limit=limit, offset=offset)

        return jsonify(
            {
                "success": True,
                "fonte": fonte.to_dict(),
                "count": len(pedidos),
                "pedidos": pedidos,
            }
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return (
            jsonify({"error": "Erro ao listar pedidos da fonte", "detalhes": str(e)}),
            500,
        )


@api_bp.route("/pedidos/fonte/<int:fonte_id>/consolidado", methods=["GET"])
def estatisticas_fonte(fonte_id):
    """
    Retorna estatísticas consolidadas de uma fonte
    Inclui: total de pedidos, total de vendas, último número sequencial
    """
    try:
        from app.models.pedido_fonte import PedidoFonte

        # Verificar se fonte existe
        fonte = FontePedido.query.get(fonte_id)
        if not fonte:
            return jsonify({"error": "Fonte não encontrada", "fonte_id": fonte_id}), 404

        # Obter estatísticas
        estatisticas = PedidoFonte.obter_estatisticas(fonte_id)

        # Obter nome da tabela
        from app.utils.fonte_helper import get_tabela_fonte

        nome_tabela = get_tabela_fonte(fonte_id)

        return jsonify(
            {
                "success": True,
                "fonte": fonte.to_dict(),
                "tabela": nome_tabela,
                "estatisticas": estatisticas,
            }
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return (
            jsonify({"error": "Erro ao obter estatísticas da fonte", "detalhes": str(e)}),
            500,
        )


# ============================================
# ENDPOINTS DE AUTENTICAÇÃO
# ============================================

# ============================================
# ENDPOINTS DE AUTENTICAÇÃO - MIGRADOS
# ============================================
# Estes endpoints foram migrados para app/routes/auth.py
# Mantidos aqui temporariamente para compatibilidade durante transição
# TODO: Remover após validação completa

# @api_bp.route('/auth/login', methods=['POST'])
# def login():
#     """MIGRADO: Ver app/routes/auth.py"""
#     pass

# @api_bp.route('/auth/check', methods=['GET'])
# def check_auth_status():
#     """MIGRADO: Ver app/routes/auth.py"""
#     pass


@api_bp.route("/debug/geocode", methods=["GET", "POST"])
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


@api_bp.route("/debug/limpar-distancias", methods=["POST"])
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


@api_bp.route("/debug/config-floricultura", methods=["GET"])
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


@api_bp.route("/debug/reset-floricultura", methods=["POST"])
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


@api_bp.route("/debug/testar-apis", methods=["GET"])
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


@api_bp.route("/exportar-planilha", methods=["POST"])
@requires_edit_auth
def exportar_planilha():
    """Exporta vendas do mês atual para Google Sheets"""
    try:
        import importlib.util
        import sys
        from pathlib import Path

        # Obter caminho absoluto do script
        backend_dir = Path(__file__).parent.parent.parent
        script_path = backend_dir / "scripts" / "export" / "exportar_vendas_sheets.py"

        # Verificar se arquivo existe
        if not script_path.exists():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Script não encontrado: {script_path}",
                        "detalhes": "Arquivo exportar_vendas_sheets.py não encontrado",
                    }
                ),
                500,
            )

        # Adicionar backend ao path (necessário para imports do app dentro do script)
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        # Carregar módulo dinamicamente
        spec = importlib.util.spec_from_file_location("exportar_vendas_sheets", str(script_path))
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

        # Definir __file__ no módulo para que o script possa calcular caminhos corretamente
        module.__file__ = str(script_path)

        # Executar o módulo
        spec.loader.exec_module(module)

        # Nota: O script agora resolve credenciais automaticamente
        # via _resolve_credentials_path() em backend/user/config/ ou variável de ambiente

        # Chamar função exportar_vendas
        if not hasattr(module, "exportar_vendas"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Função exportar_vendas não encontrada no módulo",
                    }
                ),
                500,
            )

        resultado = module.exportar_vendas()

        if resultado:
            return jsonify({"success": True, "message": "Planilha atualizada com sucesso!"})
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Erro ao exportar. Verifique as credenciais do Google.",
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
                    "error": "Erro ao exportar planilha",
                    "detalhes": str(e),
                }
            ),
            500,
        )


@api_bp.route("/exportar-planilha-leads", methods=["POST"])
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
