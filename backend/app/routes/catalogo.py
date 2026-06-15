# -*- coding: utf-8 -*-
"""
Rotas do catálogo curado de arranjos (CAT-01).

- GET  /api/catalogo/arranjos?q=...   → autocomplete por similaridade/frequência.
- POST /api/catalogo/arranjos/promover → promove um nome (florista confirma).

Entrada livre no pedido continua aceita; o catálogo só cresce por promoção explícita.
"""
from __future__ import annotations

from flask import Blueprint, request

from app import db
from app.middleware import requires_edit_auth
from app.models import CatalogoArranjo
from app.schemas.common import error_response, success_response

catalogo_bp = Blueprint("catalogo", __name__, url_prefix="/api/catalogo")


@catalogo_bp.route("/arranjos", methods=["GET"])
@requires_edit_auth
def sugerir_arranjos():
    """Sugere nomes do catálogo para o termo `q` (autocomplete com tolerância a typo no PG)."""
    try:
        q = request.args.get("q", "")
        try:
            limit = int(request.args.get("limit", 8))
        except (TypeError, ValueError):
            limit = 8
        limit = max(1, min(limit, 20))
        nomes = CatalogoArranjo.sugerir(q, limit=limit)
        return success_response({"arranjos": nomes, "total": len(nomes)})
    except Exception as e:
        return error_response(f"Erro ao sugerir arranjos: {str(e)}", 500)


@catalogo_bp.route("/arranjos/promover", methods=["POST"])
@requires_edit_auth
def promover_arranjo():
    """Promove um nome ao catálogo (insere ou incrementa `usos`). Confirmação da florista."""
    try:
        data = request.get_json(silent=True) or {}
        nome = (data.get("nome") or "").strip()
        if not nome:
            return error_response("Informe 'nome'", 400)
        arranjo = CatalogoArranjo.promover(nome)
        return success_response({"arranjo": arranjo.to_dict()}, message="Arranjo no catálogo")
    except Exception as e:
        db.session.rollback()
        return error_response(f"Erro ao promover arranjo: {str(e)}", 500)
