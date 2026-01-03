# -*- coding: utf-8 -*-
"""
Static Routes - Servir arquivos estáticos do frontend
Gerencia rotas para servir arquivos do frontend PWA
"""
from flask import send_from_directory, abort, request
from pathlib import Path


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
    @app.route('/')
    @app.route('/<path:path>')
    def serve_frontend(path='index.html'):
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
        
        if request_path.startswith('/api/') or request_path.startswith('/docs/'):
            # Se chegou aqui, significa que nenhum blueprint processou esta rota
            # Abortar para retornar 404 (rota não encontrada)
            abort(404)
        
        # Também verificar o path do parâmetro (defensivo)
        if path.startswith('api/') or path.startswith('docs/'):
            abort(404)
        
        try:
            
            # Apontar para o frontend novo (frontend_v2/dist)
            frontend_dir = Path(__file__).parent.parent.parent / 'frontend_v2' / 'dist'
            
            # Normalizar o path para evitar problemas
            if path == '' or path is None:
                path = 'index.html'
            
            # Se o arquivo existe, serve ele
            file_path = frontend_dir / path
            if file_path.exists() and file_path.is_file():
                response = send_from_directory(str(frontend_dir), path)
                
                # Service Worker, index.html e manifest devem ser servidos com no-cache
                # para garantir que sempre busquem a versão mais recente
                if path == 'sw.js' or path == 'index.html' or path == 'manifest.json' or path == 'manifest.webmanifest':
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                
                # Para assets com hash (opcional - melhoria de performance):
                if '/assets/' in path and any(ext in path for ext in ['.js', '.css', '.png', '.ico', '.svg']):
                    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                
                return response
            
            # Caso contrário, serve o index.html (SPA routing)
            response = send_from_directory(str(frontend_dir), 'index.html')
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except Exception as e:
            print(f"[ERRO] Erro ao servir arquivo '{path}': {e}")
            # Tentar servir o index.html como fallback
            try:
                frontend_dir = Path(__file__).parent.parent.parent / 'frontend_v2' / 'dist'
                response = send_from_directory(str(frontend_dir), 'index.html')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
            except:
                abort(404)


