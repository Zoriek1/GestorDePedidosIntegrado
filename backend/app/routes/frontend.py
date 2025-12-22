# -*- coding: utf-8 -*-
"""
Rotas do frontend PWA
"""
from pathlib import Path

from flask import Blueprint, abort, send_from_directory

frontend_bp = Blueprint('frontend', __name__)


def _frontend_dir():
    return Path(__file__).parent.parent.parent / 'frontend'


@frontend_bp.route('/')
@frontend_bp.route('/<path:path>')
def serve_frontend(path='index.html'):
    """Serve arquivos do frontend PWA"""
    try:
        frontend_dir = _frontend_dir()

        # Normalizar o path para evitar problemas
        if path == '' or path is None:
            path = 'index.html'

        # Se o arquivo existe, serve ele
        file_path = frontend_dir / path
        if file_path.exists() and file_path.is_file():
            return send_from_directory(str(frontend_dir), path)

        # Caso contrário, serve o index.html (SPA routing)
        return send_from_directory(str(frontend_dir), 'index.html')
    except Exception as exc:
        print(f"[ERRO] Erro ao servir arquivo '{path}': {exc}")
        # Tentar servir o index.html como fallback
        try:
            return send_from_directory(str(frontend_dir), 'index.html')
        except Exception:
            abort(404)


def register_frontend(app):
    app.register_blueprint(frontend_bp)

    @app.errorhandler(404)
    def not_found(error):
        """Redireciona 404 para index.html (SPA)"""
        frontend_dir = _frontend_dir()
        return send_from_directory(str(frontend_dir), 'index.html')

    @app.errorhandler(500)
    def internal_error(error):
        """Tratamento de erro 500"""
        print(f"[ERRO 500] {error}")
        return {"error": "Erro interno do servidor"}, 500
