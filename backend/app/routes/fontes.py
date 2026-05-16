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

# ============================================
# ENDPOINT DE CRIAÇÃO DE PEDIDO - MIGRADO
# ============================================
# ATENÇÃO: Este endpoint foi migrado para app/routes/pedidos.py
# Mantido aqui temporariamente para compatibilidade
# NOVO LOCAL: app/routes/pedidos.py -> criar_pedido()



fontes_bp = Blueprint("fontes", __name__, url_prefix="/api")
@fontes_bp.route("/fontes-pedido", methods=["GET"])
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


@fontes_bp.route("/fontes-pedido/all", methods=["GET"])
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


@fontes_bp.route("/fontes-pedido", methods=["POST"])
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


@fontes_bp.route("/fontes-pedido/<int:fonte_id>", methods=["PUT"])
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


@fontes_bp.route("/fontes-pedido/<int:fonte_id>", methods=["DELETE"])
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


@fontes_bp.route("/pedidos/fonte/<int:fonte_id>", methods=["GET"])
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


@fontes_bp.route("/pedidos/fonte/<int:fonte_id>/consolidado", methods=["GET"])
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

# @fontes_bp.route('/auth/login', methods=['POST'])
# def login():
#     """MIGRADO: Ver app/routes/auth.py"""
#     pass

# @fontes_bp.route('/auth/check', methods=['GET'])
# def check_auth_status():
#     """MIGRADO: Ver app/routes/auth.py"""
#     pass


