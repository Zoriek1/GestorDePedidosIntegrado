# -*- coding: utf-8 -*-
"""
Dashboard estático de comissões (HTML/CSS/JS embutidos, sem build).

Servido pelo próprio backend para rodar na mesma origem da API
(evita CORS no fetch para /api/auth/login e /api/ledger/commissions).
A página exige login de admin via /api/auth/login antes de mostrar dados,
então a rota de servir o HTML em si é pública.
"""

from pathlib import Path

from flask import Blueprint, send_from_directory

dashboard_bp = Blueprint("dashboard", __name__)

_ASSETS_DIR = Path(__file__).parent.parent.parent / "dashboard_assets"


@dashboard_bp.route("/dashboard", methods=["GET"])
def get_dashboard_comissoes():
    """Serve o dashboard de comissões (dashboard-comissoes.html)."""
    return send_from_directory(_ASSETS_DIR, "dashboard-comissoes.html")
