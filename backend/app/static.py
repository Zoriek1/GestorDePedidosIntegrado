# -*- coding: utf-8 -*-
"""
Static Routes - Servir arquivos estáticos do frontend
Gerencia rotas para servir arquivos do frontend PWA
"""
import os
from pathlib import Path

from flask import abort, request, send_from_directory


def add_security_headers(response):
    """
    Adiciona headers de segurança HTTP à resposta

    Args:
        response: Objeto Response do Flask

    Returns:
        Response: Resposta com headers de segurança adicionados
    """
    # Prevenir MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevenir clickjacking (DENY para máxima segurança, ou SAMEORIGIN se necessário)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    # Proteção XSS (legado, mas ainda útil para navegadores antigos)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Política de referrer
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy (limitar acesso a APIs sensíveis)
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Content Security Policy (CSP) - ajustar conforme necessário
    # Permitir recursos do mesmo origin e CDNs comuns
    # ViaCEP agora é acessado via proxy backend (/api/cep/:cep), então não precisa de allowlist externa
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://static.cloudflareinsights.com; "  # unsafe-inline/eval necessário para alguns bundlers
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://gestaopedidos.planteumaflor.online; "  # ViaCEP via proxy backend (/api/cep/:cep) - same-origin
        "worker-src 'self' blob:; "
        "manifest-src 'self';"
    )
    response.headers["Content-Security-Policy"] = csp

    # HSTS (HTTP Strict Transport Security) - apenas em produção com HTTPS
    if (
        os.environ.get("FLASK_ENV") == "production"
        and os.environ.get("USE_HTTPS", "").lower() == "true"
    ):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


def register_static_routes(app):
    """
    Registra rotas para servir arquivos estáticos do frontend PWA

    As rotas são registradas por último (catch-all) para que todas as
    rotas não mapeadas sejam direcionadas para o frontend, permitindo
    que o SPA routing funcione corretamente.

    IMPORTANTE: Esta função registra rotas catch-all que devem ser
    processadas APENAS se nenhum blueprint processou a requisição.
    Rotas da API (/api/*) e OpenAPI (/docs/*) são tratadas pelos
    blueprints registrados anteriormente.

    Args:
        app: Instância da aplicação Flask
    """

    @app.route("/")
    @app.route("/<path:path>")
    def serve_frontend(path="index.html"):
        """
        Serve arquivos do frontend PWA

        Tenta servir o arquivo solicitado. Se não existir, serve o
        index.html para permitir que o roteamento do SPA funcione.

        IMPORTANTE: Esta rota NÃO deve interceptar rotas da API (/api/*)
        nem do OpenAPI (/docs/*) pois essas são tratadas pelos blueprints
        registrados anteriormente.

        Args:
            path: Caminho do arquivo solicitado

        Returns:
            Response: Arquivo solicitado ou index.html como fallback
        """
        # CRÍTICO: Verificar request.path ANTES de processar qualquer coisa
        # Se a requisição é para API ou docs, NÃO processar - deixar Flask retornar 404
        # Os blueprints são registrados ANTES desta rota, então se a rota existe,
        # o blueprint já processou. Se não existe, Flask retornará 404.
        request_path = request.path

        if request_path.startswith("/api/") or request_path.startswith("/docs/"):
            # Se chegou aqui, significa que nenhum blueprint processou esta rota
            # Abortar para retornar 404 (rota não encontrada)
            abort(404)

        # Também verificar o path do parâmetro (defensivo)
        if path.startswith("api/") or path.startswith("docs/"):
            abort(404)

        try:
            # Apontar para o frontend novo (frontend_v2/dist)
            frontend_dir = Path(__file__).parent.parent.parent / "frontend_v2" / "dist"

            # Normalizar o path para evitar problemas
            if path == "" or path is None:
                path = "index.html"

            # Se o arquivo existe, serve ele
            file_path = frontend_dir / path
            if file_path.exists() and file_path.is_file():
                response = send_from_directory(str(frontend_dir), path)

                # Adicionar headers de segurança
                response = add_security_headers(response)

                # Service Worker, index.html e manifest devem ser servidos com no-cache
                # para garantir que sempre busquem a versão mais recente
                if (
                    path == "sw.js"
                    or path == "index.html"
                    or path == "manifest.json"
                    or path == "manifest.webmanifest"
                ):
                    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                    response.headers["Pragma"] = "no-cache"
                    response.headers["Expires"] = "0"

                # Para assets com hash (opcional - melhoria de performance):
                if "/assets/" in path and any(
                    ext in path for ext in [".js", ".css", ".png", ".ico", ".svg"]
                ):
                    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

                return response

            # Caso contrário, serve o index.html (SPA routing)
            response = send_from_directory(str(frontend_dir), "index.html")
            response = add_security_headers(response)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        except Exception as e:
            print(f"[ERRO] Erro ao servir arquivo '{path}': {e}")
            # Tentar servir o index.html como fallback
            try:
                frontend_dir = Path(__file__).parent.parent.parent / "frontend_v2" / "dist"
                response = send_from_directory(str(frontend_dir), "index.html")
                response = add_security_headers(response)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
            except Exception:
                abort(404)
