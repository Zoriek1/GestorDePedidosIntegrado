# -*- coding: utf-8 -*-
"""
Error Handlers - Tratamento de erros HTTP
Gerencia handlers de erro para a aplicação Flask
"""
from pathlib import Path

from flask import send_from_directory


def register_error_handlers(app):
    """
    Registra handlers de erro HTTP na aplicação

    Args:
        app: Instância da aplicação Flask
    """

    @app.errorhandler(404)
    def not_found(e):
        """
        Handler para erro 404 - Redireciona para index.html (SPA routing)

        Para aplicações SPA (Single Page Application), todas as rotas
        não encontradas devem servir o index.html para que o roteamento
        do frontend funcione corretamente.
        """
        frontend_dir = Path(__file__).parent.parent.parent / "frontend"
        return send_from_directory(str(frontend_dir), "index.html")

    @app.errorhandler(500)
    def internal_error(e):
        """
        Handler para erro 500 - Erro interno do servidor

        Args:
            e: Exceção que causou o erro

        Returns:
            dict: Resposta JSON com erro
        """
        print(f"[ERRO 500] {e}")
        return {"error": "Erro interno do servidor"}, 500
