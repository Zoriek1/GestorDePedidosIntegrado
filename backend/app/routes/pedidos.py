# -*- coding: utf-8 -*-
"""
Rotas de Pedidos - Blueprint para endpoints de pedidos
"""
import importlib.util
import re
from datetime import datetime
from pathlib import Path

from flask import Blueprint, g, request

# Command Pattern Imports
from app.commands.gerar_comprovante_command import GerarComprovanteCommand
from app.middleware import requires_any_role, requires_edit_auth, requires_role
from app.models.pedido import datetime_now_brazil
from app.models.pedido_external_ref import PedidoExternalRef
from app.models.pedido_manual_override import PedidoManualOverride
from app.repositories.pedido_repository import PedidoRepository
from app.schemas.common import error_response, success_response
from app.schemas.pedido_schema import (
    PedidoCreateSchema,
    PedidoSchema,
    PedidoUpdateSchema,
)
from app.utils.destructive_action_guard import (
    ensure_backup_before_destructive_action,
)

pedidos_bp = Blueprint("pedidos", __name__, url_prefix="/api/pedidos")

pedido_repo = PedidoRepository()
pedido_schema = PedidoSchema()
pedido_create_schema = PedidoCreateSchema()
pedido_update_schema = PedidoUpdateSchema()


@pedidos_bp.route("", methods=["GET"])
def listar_pedidos():
    """Lista pedidos com filtros opcionais"""
    try:
        from datetime import timedelta

        status = request.args.get("status")
        data_inicio = request.args.get("data_inicio")
        data_fim = request.args.get("data_fim")
        search = request.args.get("search")
        filtrar_por_criacao = request.args.get("filtrar_por_criacao", "").lower() == "true"

        # Ordenação e paginação
        # Padrão: ordenar por dia_entrega ASC (mais próximos primeiro: hoje antes de amanhã)
        sort_by = request.args.get("sort_by", "dia_entrega")
        sort_order = request.args.get("sort_order", "asc" if sort_by == "dia_entrega" else "asc")
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        # Converter datas se fornecidas
        data_inicio_obj = None
        data_fim_obj = None
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            except ValueError:
                return error_response("Formato de data_inicio inválido. Use YYYY-MM-DD", 400)
        if data_fim:
            try:
                data_fim_original = datetime.strptime(data_fim, "%Y-%m-%d").date()
                # Se filtrar_por_criacao, converter para fim_exclusivo (dia seguinte 00:00:00)
                if filtrar_por_criacao:
                    data_fim_obj = data_fim_original + timedelta(days=1)
                else:
                    data_fim_obj = data_fim_original
            except ValueError:
                return error_response("Formato de data_fim inválido. Use YYYY-MM-DD", 400)

        # REGRA CRÍTICA: Quando filtrar_por_criacao=True (usado pela tela de vendas),
        # ocultos SEMPRE ENTRAM (excluir_ocultos=False).
        # O campo 'oculto' é apenas para limpeza visual na tela de pedidos.
        # Vendas devem mostrar TODOS os pedidos do mês, incluindo ocultos.
        excluir_ocultos = not filtrar_por_criacao  # False quando filtrar_por_criacao=True

        pedidos, total = pedido_repo.buscar_com_filtros(
            status=status,
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            search=search,
            excluir_ocultos=excluir_ocultos,
            filtrar_por_criacao=filtrar_por_criacao,
            ordenar_por=sort_by,
            ordenar_direcao=sort_order,
            page=page,
            per_page=per_page,
        )

        # Serializar pedidos
        pedidos_data = [p.to_dict() for p in pedidos]

        response_data = {
            "pedidos": pedidos_data,
            "total": total,
        }

        if page is not None and per_page is not None:
            response_data["page"] = page
            response_data["per_page"] = per_page
            response_data["total_pages"] = (total + per_page - 1) // per_page if per_page > 0 else 1

        return success_response(response_data)
    except Exception as e:
        return error_response(f"Erro ao listar pedidos: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>", methods=["GET"])
def obter_pedido(pedido_id):
    """Obtém pedido por ID"""
    try:
        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        return success_response({"pedido": pedido.to_dict()})
    except Exception as e:
        return error_response(f"Erro ao obter pedido: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/status", methods=["PUT", "POST"])
@requires_any_role("admin", "atendente", "entregador")
def atualizar_status(pedido_id):
    """Atualiza status de um pedido"""
    try:
        data = request.get_json() or {}
        novo_status = data.get("status", "").strip()

        if not novo_status:
            return error_response("Status é obrigatório", 400)

        pedido = pedido_repo.atualizar_status(pedido_id, novo_status)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        return success_response(
            {"pedido": pedido.to_dict()}, message="Status atualizado com sucesso"
        )
    except Exception as e:
        return error_response(f"Erro ao atualizar status: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>", methods=["DELETE"])
@requires_role("admin")
def deletar_pedido(pedido_id):
    """Deleta pedido"""

    # Fail-closed: garantir backup antes de operação destrutiva (P0.2)
    # IMPORTANTE: Esta verificação deve estar FORA do try/except genérico
    # para garantir que BackupRequiredException seja tratada corretamente
    from app.utils.destructive_action_guard import BackupRequiredException

    try:
        ensure_backup_before_destructive_action(
            reason="delete_pedido", context={"pedido_id": pedido_id}
        )
    except BackupRequiredException as backup_error:
        # Backup falhou - bloquear operação
        error_msg = str(backup_error)
        print(f"[BLOQUEADO] Operação destrutiva bloqueada: {error_msg}")
        return error_response(
            "Backup necessário antes de operação destrutiva. Falha ao criar backup. Operação bloqueada por segurança.",
            503,
            details={"error": error_msg, "pedido_id": pedido_id},
        )

    # Se chegou aqui, backup foi criado com sucesso
    try:
        print(f"[DELETE_PEDIDO] Iniciando soft delete do pedido #{pedido_id}")
        # Soft delete (P0.3) - não remove fisicamente
        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            print(f"[DELETE_PEDIDO] Pedido #{pedido_id} não encontrado")
            return error_response("Pedido não encontrado", 404)

        if pedido.is_deleted:
            print(
                f"[DELETE_PEDIDO] Pedido #{pedido_id} já foi deletado (deleted_at={pedido.deleted_at})"
            )
            return error_response("Pedido já foi deletado", 400)

        # Obter actor (usuário) se disponível
        actor = "system"  # TODO: extrair de autenticação se disponível

        # Executar soft delete via repository (já registra auditoria)
        print(f"[DELETE_PEDIDO] Chamando soft_delete_pedido para pedido #{pedido_id}")
        pedido_atualizado = pedido_repo.soft_delete_pedido(pedido_id, actor=actor)

        if pedido_atualizado:
            print(
                f"[SUCCESS] Pedido #{pedido_id} soft-deleted com sucesso (deleted_at={pedido_atualizado.deleted_at})"
            )
            return success_response(
                {"pedido": pedido_atualizado.to_dict()},
                message="Pedido arquivado com sucesso (soft delete)",
            )
        else:
            print(
                f"[DELETE_PEDIDO] Falha ao arquivar pedido #{pedido_id} - soft_delete_pedido retornou None"
            )
            return error_response("Falha ao arquivar pedido", 500)

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(
            f"[ERRO] Exceção inesperada ao deletar pedido #{pedido_id}: {error_type}: {error_msg}"
        )
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao deletar pedido: {error_msg}", 500)


@pedidos_bp.route("/exportar-planilha", methods=["POST"])
@requires_any_role("admin", "atendente")
def exportar_planilha():
    """
    Exporta vendas para Google Sheets
    CRÍTICO: Preservar esta funcionalidade exatamente como está
    """
    try:
        backend_dir = Path(__file__).parent.parent.parent
        script_path = backend_dir / "scripts" / "export" / "exportar_vendas_sheets.py"

        if not script_path.exists():
            return error_response("Script não encontrado", 500, details={"path": str(script_path)})

        # Importar e executar script (preservar lógica exata)
        import sys

        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        spec = importlib.util.spec_from_file_location("exportar_vendas_sheets", str(script_path))
        if spec is None or spec.loader is None:
            return error_response("Erro ao carregar módulo", 500)

        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(script_path)
        spec.loader.exec_module(module)

        # Nota: O script agora resolve credenciais automaticamente
        # via _resolve_credentials_path() em backend/user/config/ ou variável de ambiente

        if not hasattr(module, "exportar_vendas"):
            return error_response("Função exportar_vendas não encontrada", 500)

        resultado = module.exportar_vendas()

        if resultado:
            return success_response(message="Planilha atualizada com sucesso!")
        else:
            return error_response("Erro ao exportar. Verifique as credenciais do Google.", 500)

    except FileNotFoundError as e:
        return error_response(
            "Credenciais do Google não configuradas", 400, details={"error": str(e)}
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return error_response("Erro ao exportar planilha", 500, details={"error": str(e)})


@pedidos_bp.route("", methods=["POST"])
@requires_any_role("admin", "atendente")
def criar_pedido():
    """
    Cria novo pedido via API (usado pelo PWA)
    CRÍTICO: Preservar toda a lógica existente de api.py
    """
    try:
        import re
        from datetime import datetime

        from app import db
        from app.models import Cliente, FontePedido, Pedido

        data = request.get_json()

        if not data:
            return error_response("Nenhum dado fornecido", 400)

        # Extração de dados (preservar lógica exata)
        cliente = data.get("cliente", "").strip()
        telefone_cliente_raw = data.get("telefone_cliente", data.get("telefone", "")).strip()
        # Remover formatação do telefone (máscara deve existir apenas no frontend)
        telefone_cliente = re.sub(r"[^\d]", "", telefone_cliente_raw)
        destinatario = data.get("destinatario", "").strip()
        tipo_pedido = data.get("tipo_pedido", "Entrega")
        fonte_pedido_id = data.get("fonte_pedido_id")
        fonte_pedido = data.get("fonte_pedido", "").strip()

        produto = data.get("produto", "").strip()
        flores_cor = data.get("flores_cor", "").strip()
        valor = data.get("valor", "").strip()
        horario = data.get("horario", data.get("hora_entrega", "")).strip()
        dia_entrega_str = data.get("dia_entrega", data.get("data_entrega", "")).strip()

        cep = data.get("cep", "").strip()
        rua = data.get("rua", "").strip()
        numero = data.get("numero", "").strip()
        bairro = data.get("bairro", "").strip()
        cidade = data.get("cidade", "").strip()
        endereco = data.get("endereco", "").strip()
        obs_entrega = data.get("obs_entrega", "").strip()

        mensagem = data.get("mensagem", "").strip()
        pagamento = data.get("pagamento", "").strip()
        observacoes = data.get("observacoes", "").strip()
        status_pagamento = data.get("status_pagamento", "").strip()

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
            return error_response(
                f'Campos obrigatórios ausentes: {", ".join(campos_faltantes)}',
                400,
                details={"campos_enviados": list(data.keys())},
            )

        # Conversão de quantidade
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

        # Validação de horário: aceita HH:MM ou intervalo HH:MM - HH:MM
        pattern_simples = r"^([01]?\d|2[0-3]):[0-5]\d$"
        pattern_intervalo = r"^([01]?\d|2[0-3]):[0-5]\d\s*-\s*([01]?\d|2[0-3]):[0-5]\d$"

        if not (re.match(pattern_simples, horario) or re.match(pattern_intervalo, horario)):
            return error_response(
                "Formato de horário inválido",
                400,
                details={
                    "horario_recebido": horario,
                    "formato_esperado": "HH:MM (ex: 14:30) ou intervalo HH:MM - HH:MM (ex: 08:00 - 10:00)",
                },
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
                        return error_response(
                            "O horário final deve ser depois do horário inicial",
                            400,
                            details={"horario_recebido": horario},
                        )
                except (ValueError, IndexError):
                    return error_response(
                        "Formato de intervalo inválido",
                        400,
                        details={"horario_recebido": horario},
                    )

        # Conversão de data
        try:
            if "/" in dia_entrega_str:
                dia_entrega = datetime.strptime(dia_entrega_str, "%d/%m/%Y").date()
            else:
                dia_entrega = datetime.strptime(dia_entrega_str, "%Y-%m-%d").date()
        except ValueError as e:
            return error_response(
                "Formato de data inválido",
                400,
                details={
                    "data_recebida": dia_entrega_str,
                    "formatos_aceitos": ["YYYY-MM-DD", "DD/MM/YYYY"],
                    "detalhes": str(e),
                },
            )

        # Gerenciar cliente_id
        cliente_id = data.get("cliente_id", "").strip()
        if not cliente_id and cliente and telefone_cliente:
            cliente_existente = Cliente.buscar_por_telefone(telefone_cliente)
            if cliente_existente:
                cliente_id = cliente_existente.id
            else:
                try:
                    novo_cliente = Cliente(
                        nome=cliente,
                        telefone=telefone_cliente,
                        email=None,
                        observacoes=None,
                    )
                    db.session.add(novo_cliente)
                    db.session.flush()
                    cliente_id = novo_cliente.id
                except Exception:
                    cliente_id = None

        cliente_id_int = int(cliente_id) if cliente_id else None

        # Processar fonte_pedido_id
        fonte_pedido_id_int = None
        if fonte_pedido_id:
            try:
                fonte_pedido_id_int = int(fonte_pedido_id)
            except (ValueError, TypeError):
                fonte_pedido_id_int = None
        elif fonte_pedido:
            fonte = FontePedido.query.filter_by(nome=fonte_pedido, ativo=True).first()
            if fonte:
                fonte_pedido_id_int = fonte.id

        # Criar pedido
        pedido = Pedido(
            cliente=cliente if cliente else None,
            telefone_cliente=telefone_cliente,
            destinatario=destinatario,
            tipo_pedido=tipo_pedido,
            fonte_pedido=fonte_pedido if fonte_pedido else None,
            fonte_pedido_id=fonte_pedido_id_int,
            produto=produto,
            flores_cor=flores_cor if flores_cor else None,
            valor=valor if valor else None,
            horario=horario,
            dia_entrega=dia_entrega,
            cep=cep if cep else None,
            rua=rua if rua else None,
            numero=numero if numero else None,
            bairro=bairro if bairro else None,
            cidade=cidade if cidade else None,
            endereco=endereco if endereco else None,
            obs_entrega=obs_entrega if obs_entrega else None,
            mensagem=mensagem if mensagem else None,
            pagamento=pagamento if pagamento else None,
            observacoes=observacoes if observacoes else None,
            status_pagamento=status_pagamento if status_pagamento else None,
            status="agendado",
            quantidade=quantidade,
            cliente_id=cliente_id_int,
        )

        db.session.add(pedido)
        db.session.commit()

        # Inserir na tabela auxiliar da fonte (se houver)
        if fonte_pedido_id_int:
            try:
                from app.models.pedido_fonte import PedidoFonte

                PedidoFonte.adicionar_pedido(
                    pedido.id, fonte_pedido_id_int, valor if valor else None
                )
            except Exception:
                pass  # Não falhar se houver erro

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

        return success_response(
            {"pedido_id": pedido.id, "pedido": pedido.to_dict()},
            message="Pedido criado com sucesso",
            status_code=201,
        )

    except Exception as e:
        from app import db

        db.session.rollback()
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao criar pedido: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>", methods=["PUT"])
@requires_any_role("admin", "atendente")
def atualizar_pedido(pedido_id):
    """
    Atualiza dados completos do pedido
    CRÍTICO: Preservar lógica de resetar distância quando endereço muda
    IMPORTANTE: Registra overrides para pedidos com external_ref (Nuvemshop)
    """
    try:
        from datetime import datetime

        from app import db
        from app.models import FontePedido

        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404, details={"pedido_id": pedido_id})

        data = request.get_json() or {}

        # Verificar se pedido tem external_ref (importado de plataforma externa)
        external_ref = PedidoExternalRef.query.filter_by(pedido_id=pedido_id).first()
        has_external_ref = external_ref is not None

        # Lista de campos que foram alterados (para registro de override)
        changed_fields = []

        # Helper para rastrear mudanças
        def track_change(field_name, old_value, new_value):
            if old_value != new_value:
                changed_fields.append((field_name, new_value))

        # Atualizar campos (preservar lógica exata)
        if "cliente" in data:
            track_change("cliente", pedido.cliente, data["cliente"])
            pedido.cliente = data["cliente"]
        if "telefone_cliente" in data:
            telefone_raw = data["telefone_cliente"].strip()
            new_telefone = re.sub(r"[^\d]", "", telefone_raw)
            track_change("telefone_cliente", pedido.telefone_cliente, new_telefone)
            pedido.telefone_cliente = new_telefone
        if "destinatario" in data:
            track_change("destinatario", pedido.destinatario, data["destinatario"])
            pedido.destinatario = data["destinatario"]
        if "tipo_pedido" in data:
            track_change("tipo_pedido", pedido.tipo_pedido, data["tipo_pedido"])
            pedido.tipo_pedido = data["tipo_pedido"]
        if "fonte_pedido_id" in data:
            try:
                new_fonte_id = int(data["fonte_pedido_id"]) if data["fonte_pedido_id"] else None
                track_change("fonte_pedido_id", pedido.fonte_pedido_id, new_fonte_id)
                pedido.fonte_pedido_id = new_fonte_id
            except (ValueError, TypeError):
                pedido.fonte_pedido_id = None
        elif "fonte_pedido" in data:
            fonte = FontePedido.query.filter_by(nome=data["fonte_pedido"], ativo=True).first()
            if fonte:
                track_change("fonte_pedido_id", pedido.fonte_pedido_id, fonte.id)
                pedido.fonte_pedido_id = fonte.id
            track_change("fonte_pedido", pedido.fonte_pedido, data["fonte_pedido"])
            pedido.fonte_pedido = data["fonte_pedido"]
        if "produto" in data:
            track_change("produto", pedido.produto, data["produto"])
            pedido.produto = data["produto"]
        if "flores_cor" in data:
            track_change("flores_cor", pedido.flores_cor, data["flores_cor"])
            pedido.flores_cor = data["flores_cor"]
        if "valor" in data:
            track_change("valor", pedido.valor, data["valor"])
            pedido.valor = data["valor"]
        if "horario" in data:
            track_change("horario", pedido.horario, data["horario"])
            pedido.horario = data["horario"]
        if "dia_entrega" in data:
            dia_entrega_str = data["dia_entrega"]
            if "/" in dia_entrega_str:
                new_dia = datetime.strptime(dia_entrega_str, "%d/%m/%Y").date()
            else:
                new_dia = datetime.strptime(dia_entrega_str, "%Y-%m-%d").date()
            track_change("dia_entrega", pedido.dia_entrega, new_dia)
            pedido.dia_entrega = new_dia

        # Verificar se endereço mudou (resetar distância)
        endereco_mudou = False
        campos_endereco = ["cep", "rua", "numero", "bairro", "cidade", "endereco"]
        for campo in campos_endereco:
            if campo in data and data[campo] != getattr(pedido, campo):
                track_change(campo, getattr(pedido, campo), data[campo])
                setattr(pedido, campo, data[campo])
                endereco_mudou = True

        if endereco_mudou:
            pedido.distancia_km = None

        if "obs_entrega" in data:
            track_change("obs_entrega", pedido.obs_entrega, data["obs_entrega"])
            pedido.obs_entrega = data["obs_entrega"]
        if "mensagem" in data:
            track_change("mensagem", pedido.mensagem, data["mensagem"])
            pedido.mensagem = data["mensagem"]
        if "pagamento" in data:
            track_change("pagamento", pedido.pagamento, data["pagamento"])
            pedido.pagamento = data["pagamento"]
        if "observacoes" in data:
            track_change("observacoes", pedido.observacoes, data["observacoes"])
            pedido.observacoes = data["observacoes"]

        # Status anterior para hook (ANTES de atualizar)
        status_anterior = pedido.status
        status_pagamento_anterior = pedido.status_pagamento

        if "status_pagamento" in data:
            track_change("status_pagamento", pedido.status_pagamento, data["status_pagamento"])
            pedido.status_pagamento = data["status_pagamento"]

        if "status" in data:
            track_change("status", pedido.status, data["status"])
            pedido.status = data["status"]

        pedido.updated_at = datetime_now_brazil()

        # Registrar overrides para pedidos com external_ref (Nuvemshop)
        # Isso protege os campos editados manualmente de serem sobrescritos por webhooks
        if has_external_ref and changed_fields:
            actor = getattr(g, "user", None) or "admin"
            for field_name, field_value in changed_fields:
                PedidoManualOverride.set_override(
                    pedido_id=pedido_id,
                    field_name=field_name,
                    field_value=str(field_value) if field_value is not None else None,
                    edited_by=actor,
                )

        db.session.commit()

        # Hook: Verificar se mudou para Purchase (status_pagamento = Pago ou Parcial)
        # Não verificar status="concluido" porque pode agendar pedido para ano que vem
        try:
            from app.utils.meta_capi_helper import create_outbox_if_purchase

            create_outbox_if_purchase(pedido, status_anterior, status_pagamento_anterior)
        except Exception as e:
            # Não falhar a atualização se houver erro na outbox
            print(f"[AVISO] Erro ao criar outbox para pedido #{pedido_id}: {e}")

        return success_response(
            {"pedido": pedido.to_dict()}, message="Pedido atualizado com sucesso"
        )

    except Exception as e:
        from app import db

        db.session.rollback()
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao atualizar pedido: {str(e)}", 500)


@pedidos_bp.route("/por-data", methods=["GET"])
def get_pedidos_por_data():
    """Retorna contagem de pedidos por horário para uma data específica"""
    try:
        from datetime import datetime

        data_str = request.args.get("data")
        if not data_str:
            return error_response(
                'Parâmetro "data" é obrigatório',
                400,
                details={"formato_esperado": "YYYY-MM-DD (ex: 2025-12-20)"},
            )

        # Converter data
        try:
            if "/" in data_str:
                partes = data_str.split("/")
                if len(partes) == 3:
                    dia, mes, ano = partes
                    data_entrega = datetime.strptime(f"{ano}-{mes}-{dia}", "%Y-%m-%d").date()
                else:
                    return error_response("Formato de data inválido", 400)
            else:
                data_entrega = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError as e:
            return error_response(
                "Formato de data inválido",
                400,
                details={
                    "detalhes": str(e),
                    "formato_esperado": "YYYY-MM-DD ou DD/MM/YYYY",
                },
            )

        # Buscar pedidos do dia
        pedidos = pedido_repo.buscar_por_data(data_entrega, data_entrega, excluir_ocultos=True)

        # Agrupar por horário
        horarios = {}
        for pedido in pedidos:
            horario = pedido.horario.strip() if pedido.horario else ""
            if horario:
                horarios[horario] = horarios.get(horario, 0) + 1

        return success_response(
            {
                "data": data_str,
                "data_formatada": data_entrega.strftime("%Y-%m-%d"),
                "total_pedidos": len(pedidos),
                "horarios": horarios,
            }
        )

    except Exception as e:
        return error_response(f"Erro ao buscar pedidos por data: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/marcar-impresso", methods=["POST", "PUT", "OPTIONS"])
@requires_any_role("admin", "atendente")
def marcar_impresso(pedido_id):
    """Marca pedido como impresso"""
    try:
        from app import db

        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        pedido.impresso = True
        pedido.updated_at = datetime_now_brazil()
        db.session.commit()

        return success_response(
            {"pedido": pedido.to_dict()}, message="Pedido marcado como impresso"
        )

    except Exception as e:
        from app import db

        db.session.rollback()
        return error_response(f"Erro ao marcar como impresso: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/comprovante", methods=["GET"])
def obter_comprovante(pedido_id):
    """Gera comprovante de pedido (HTML)"""
    try:
        from flask import Response

        command = GerarComprovanteCommand(pedido_id)
        html = command.execute()

        return Response(html, mimetype="text/html")
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return error_response(f"Erro ao gerar comprovante: {str(e)}", 500)


@pedidos_bp.route("/ocultar-concluidos", methods=["POST"])
@requires_role("admin")
def ocultar_concluidos():
    """Oculta todos os pedidos concluídos do painel"""
    try:
        print("[OCULTAR_CONCLUIDOS] Iniciando ocultação de pedidos concluídos...")
        count = pedido_repo.ocultar_concluidos()
        print(f"[OCULTAR_CONCLUIDOS] {count} pedido(s) concluído(s) ocultado(s) com sucesso")

        return success_response(
            {"count": count},
            message=f"{count} pedido(s) concluído(s) ocultado(s) do painel",
        )
    except Exception as e:
        from app import db

        print(f"[OCULTAR_CONCLUIDOS] Erro ao ocultar pedidos concluídos: {str(e)}")
        import traceback

        traceback.print_exc()
        db.session.rollback()
        return error_response(f"Erro ao ocultar pedidos concluídos: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/restore", methods=["POST"])
@requires_role("admin")
def restaurar_pedido(pedido_id):
    """Restaura pedido soft-deleted (P0.3)"""
    try:
        pedido = pedido_repo.get_by_id(pedido_id)
        if not pedido:
            return error_response("Pedido não encontrado", 404)

        if not pedido.is_deleted:
            return error_response("Pedido não está deletado", 400)

        # Obter actor (usuário) se disponível
        actor = "system"  # TODO: extrair de autenticação se disponível

        # Executar restore via repository (já registra auditoria)
        pedido_restaurado = pedido_repo.restore_pedido(pedido_id, actor=actor)

        if pedido_restaurado:
            return success_response(
                {"pedido": pedido_restaurado.to_dict()},
                message="Pedido restaurado com sucesso",
            )
        else:
            return error_response("Falha ao restaurar pedido", 500)

    except Exception as e:
        from app import db

        db.session.rollback()
        return error_response(f"Erro ao restaurar pedido: {str(e)}", 500)


@pedidos_bp.route("/<int:pedido_id>/meta-outbox", methods=["GET"])
@requires_any_role("admin", "atendente")
def verificar_outbox_pedido(pedido_id):
    """Verifica se existe registro na outbox Meta CAPI para um pedido"""
    try:
        from app.models.meta_capi_outbox import MetaCapiOutbox

        entry = MetaCapiOutbox.query.filter_by(order_id=pedido_id).first()
        if entry:
            return success_response(
                {
                    "exists": True,
                    "outbox": entry.to_dict(),
                },
                message="Outbox encontrada",
            )
        else:
            return success_response(
                {"exists": False},
                message="Nenhuma outbox encontrada para este pedido",
            )
    except Exception as e:
        return error_response(f"Erro ao verificar outbox: {str(e)}", 500)


@pedidos_bp.route("/meta-outbox/stats", methods=["GET"])
@requires_any_role("admin", "atendente")
def estatisticas_outbox():
    """Retorna estatísticas da outbox Meta CAPI"""
    try:
        from app.models.meta_capi_outbox import MetaCapiOutbox

        total = MetaCapiOutbox.query.count()
        pending = MetaCapiOutbox.query.filter_by(status="pending").count()
        sent = MetaCapiOutbox.query.filter_by(status="sent").count()
        failed = MetaCapiOutbox.query.filter_by(status="failed").count()

        return success_response(
            {
                "total": total,
                "pending": pending,
                "sent": sent,
                "failed": failed,
            },
            message="Estatísticas da outbox",
        )
    except Exception as e:
        return error_response(f"Erro ao obter estatísticas: {str(e)}", 500)


@pedidos_bp.route("/meta-outbox/criar-faltantes", methods=["POST"])
@requires_any_role("admin")
def criar_outbox_faltantes():
    """
    Cria outboxes faltantes para pedidos pagos que ainda não têm outbox (backfill)

    Body opcional:
    {
        "limit": 100,  // Limite de pedidos para processar (opcional)
        "dry_run": false  // Se true, apenas mostra o que seria criado (opcional)
    }
    """
    try:
        from sqlalchemy import func

        from app.models.meta_capi_outbox import MetaCapiOutbox
        from app.models.pedido import Pedido
        from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

        data = request.get_json() or {}
        limit = data.get("limit")
        dry_run = data.get("dry_run", False)

        if dry_run:
            # Modo dry-run: apenas contar
            query = (
                Pedido.query.filter(
                    func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
                    Pedido.deleted_at.is_(None),
                )
                .outerjoin(MetaCapiOutbox, Pedido.id == MetaCapiOutbox.order_id)
                .filter(MetaCapiOutbox.id.is_(None))
            )
            if limit:
                query = query.limit(limit)
            total_encontrados = query.count()

            return success_response(
                {
                    "dry_run": True,
                    "total_encontrados": total_encontrados,
                    "criados": 0,
                    "message": f"Encontrados {total_encontrados} pedidos sem outbox (dry-run)",
                },
                message="Dry-run: nenhuma outbox foi criada",
            )

        # Modo real: criar outboxes
        query = (
            Pedido.query.filter(
                func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
                Pedido.deleted_at.is_(None),
            )
            .outerjoin(MetaCapiOutbox, Pedido.id == MetaCapiOutbox.order_id)
            .filter(MetaCapiOutbox.id.is_(None))
            .order_by(Pedido.updated_at.desc())
        )

        if limit:
            query = query.limit(limit)

        pedidos_sem_outbox = query.all()

        outbox_repo = MetaCapiOutboxRepository()
        criados = 0
        erros = 0
        erros_detalhes = []

        for pedido in pedidos_sem_outbox:
            try:
                outbox = outbox_repo.create_from_pedido(pedido)
                if outbox:
                    criados += 1
            except Exception as e:
                erros += 1
                erros_detalhes.append(f"Pedido #{pedido.id}: {str(e)}")

        return success_response(
            {
                "total_encontrados": len(pedidos_sem_outbox),
                "criados": criados,
                "erros": erros,
                "erros_detalhes": erros_detalhes if erros > 0 else None,
            },
            message=f"Processados {len(pedidos_sem_outbox)} pedidos: {criados} outboxes criadas, {erros} erros",
        )

    except Exception as e:
        return error_response(f"Erro ao criar outboxes faltantes: {str(e)}", 500)


@pedidos_bp.route("/deleted", methods=["GET"])
@requires_edit_auth
def listar_deletados():
    """Lista pedidos soft-deleted (P0.3)"""
    try:
        pedidos_deletados = pedido_repo.buscar_deletados()
        pedidos_data = [p.to_dict() for p in pedidos_deletados]

        return success_response({"pedidos": pedidos_data, "total": len(pedidos_data)})
    except Exception as e:
        return error_response(f"Erro ao listar pedidos deletados: {str(e)}", 500)
