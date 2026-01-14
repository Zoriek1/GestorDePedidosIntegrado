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
        
        EXCEÇÃO: Rotas do backend (API, docs, Meta Gateway) devem retornar
        404 JSON ao invés de index.html.
        """
        from flask import request, jsonify
        
        request_path = request.path
        
        # Se for rota do backend, retornar 404 JSON
        if (request_path.startswith("/api/") or 
            request_path.startswith("/docs/") or 
            request_path.startswith("/capig/") or 
            request_path.startswith("/meta-gateway/")):
            return jsonify({
                "error": "Not Found",
                "message": f"Rota não encontrada: {request_path}",
                "path": request_path
            }), 404
        
        # Para outras rotas, servir index.html (SPA routing)
        frontend_dir = Path(__file__).parent.parent.parent / "frontend_v2" / "dist"
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
