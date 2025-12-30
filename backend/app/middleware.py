# -*- coding: utf-8 -*-
"""
Middleware de Segurança - Acesso Remoto
Protege o sistema contra acesso não autorizado
"""
from functools import wraps
from flask import request, Response
import os
import hashlib
import time
from datetime import datetime, timedelta
import json

# #region agent log
def log_debug(msg, data):
    try:
        with open(r"c:\Gestor de Pedidos Plante uma flor\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "timestamp": int(time.time()*1000), "location": "middleware.py", "message": msg, "data": data}) + "\n")
    except Exception as e:
        print(f"Log error: {e}")
# #endregion

# ============================================
# CONFIGURAÇÃO DE USUÁRIOS
# ============================================
# Edite aqui seus usuários e senhas
# Para maior segurança, use variáveis de ambiente em produção
USERS = {
    'admin': os.environ.get('ADMIN_PASSWORD', 'plante1998'),
    # Adicione mais usuários se necessário:
    # 'usuario2': 'outra_senha_segura',
}

# Para maior segurança, você pode usar hash de senhas:
# import bcrypt
# USERS_HASHED = {
#     'admin': '$2b$12$...'  # Hash bcrypt da senha
# }


# ============================================
# AUTENTICAÇÃO BÁSICA HTTP
# ============================================
def check_auth(username, password):
    """
    Verifica se o usuário e senha são válidos
    """
    log_debug(
        "check_auth called",
        {
            "username": username,
            "password_len": len(password) if password else 0,
            "password_is_lower": bool(password) and password == password.lower(),
        },
    )
    if username not in USERS:
        log_debug("check_auth failed: user not found", {"username": username, "available_users": list(USERS.keys())})
        return False
    
    expected_password = USERS[username]
    log_debug(
        "check_auth verify",
        {
            "username": username,
            "expected_password_len": len(expected_password) if expected_password else 0,
            "expected_password_is_lower": bool(expected_password) and expected_password == expected_password.lower(),
            "match": password == expected_password,
        },
    )
    
    # Comparação simples (em produção, use hash)
    return password == expected_password
    
    # Se estiver usando hash bcrypt:
    # import bcrypt
    # if username in USERS_HASHED:
    #     return bcrypt.checkpw(
    #         password.encode('utf-8'),
    #         USERS_HASHED[username].encode('utf-8')
    #     )
    # return False


def requires_auth(f):
    """
    Decorator para proteger rotas com autenticação HTTP Basic
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                'Acesso negado. Credenciais necessárias.',
                401,
                {
                    'WWW-Authenticate': 'Basic realm="Gestor de Pedidos - Login Necessário"',
                    'Content-Type': 'application/json'
                }
            )
        
        # Armazenar usuário autenticado no request (opcional)
        request.authenticated_user = auth.username
        
        return f(*args, **kwargs)
    
    # Marcar função com tipo de autenticação (para dump_routes.py)
    decorated._auth = "basic"
    return decorated


def requires_edit_auth(f):
    """
    Decorator para proteger apenas rotas críticas de edição (criar/deletar pedidos)
    Permite acesso livre para visualização e atualização de status
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        
        if not auth or not check_auth(auth.username, auth.password):
            from flask import jsonify
            return jsonify({
                'error': 'Acesso negado',
                'message': 'Esta operação requer autenticação. Por favor, faça login.',
                'requires_auth': True
            }), 401
        
        # Armazenar usuário autenticado no request
        request.authenticated_user = auth.username
        
        return f(*args, **kwargs)
    
    # Marcar função com tipo de autenticação (para dump_routes.py)
    decorated._auth = "edit"
    return decorated


# ============================================
# RATE LIMITING SIMPLES
# ============================================
request_counts = {}

def rate_limit(max_per_minute=60, max_per_hour=1000):
    """
    Rate limiting simples por IP
    Limita requisições para prevenir abuso
    """
    from flask import jsonify
    
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Pegar IP do cliente
            ip = request.remote_addr
            
            # Se vier através de proxy (Nginx), pegar IP real
            if request.headers.get('X-Real-IP'):
                ip = request.headers.get('X-Real-IP')
            elif request.headers.get('X-Forwarded-For'):
                ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            
            now = time.time()
            
            # Inicializar contador para este IP
            if ip not in request_counts:
                request_counts[ip] = {
                    'minute': [],
                    'hour': []
                }
            
            # Limpar requisições antigas
            request_counts[ip]['minute'] = [
                t for t in request_counts[ip]['minute'] 
                if now - t < 60
            ]
            request_counts[ip]['hour'] = [
                t for t in request_counts[ip]['hour'] 
                if now - t < 3600
            ]
            
            # Verificar limite por minuto
            if len(request_counts[ip]['minute']) >= max_per_minute:
                response = jsonify({
                    'error': 'Rate limit excedido',
                    'message': f'Máximo de {max_per_minute} requisições por minuto',
                    'retry_after': 60
                })
                response.status_code = 429
                response.headers['Retry-After'] = '60'
                return response
            
            # Verificar limite por hora
            if len(request_counts[ip]['hour']) >= max_per_hour:
                response = jsonify({
                    'error': 'Rate limit excedido',
                    'message': f'Máximo de {max_per_hour} requisições por hora',
                    'retry_after': 3600
                })
                response.status_code = 429
                response.headers['Retry-After'] = '3600'
                return response
            
            # Registrar requisição
            request_counts[ip]['minute'].append(now)
            request_counts[ip]['hour'].append(now)
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


# ============================================
# LOG DE ACESSOS (Básico)
# ============================================
def log_access(ip, endpoint, method, status_code, username=None):
    """
    Registra acesso para auditoria
    Em produção, use um sistema de logging adequado
    """
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'access_{datetime.now().strftime("%Y-%m-%d")}.log')
    
    with open(log_file, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user = username or 'anonymous'
        f.write(
            f'{timestamp} | {ip} | {user} | {method} {endpoint} | {status_code}\n'
        )


# ============================================
# MIDDLEWARE GLOBAL
# ============================================
def setup_security_middleware(app, enable_auth=True, enable_rate_limit=True):
    """
    Configura middlewares de segurança na aplicação
    """
    from flask import jsonify
    
    @app.before_request
    def before_request():
        """Executado antes de cada requisição"""
        from flask import g
        # Registrar tempo de início para medir duração da requisição
        g.start_time = datetime.now()
        
        # Lista de paths públicos (não precisam autenticação)
        # Esses arquivos são necessários para o PWA funcionar corretamente
        public_paths = [
            '/api/health',
            '/api/auth',  # Endpoints de autenticação são públicos
            '/manifest.json',
            '/sw.js',
            '/favicon.ico',
        ]
        
        # Verificar se o path começa com algum path público
        is_public = any(request.path == path or request.path.startswith(path + '/') for path in public_paths)
        
        # Assets também são públicos (ícones, CSS, JS, imagens)
        # Esses arquivos são necessários para o frontend funcionar
        if request.path.startswith('/assets/'):
            is_public = True
        
        # Rotas de API GET são públicas (visualização livre)
        if request.path.startswith('/api/') and request.method == 'GET':
            is_public = True
        
        # NÃO aplicar autenticação global - apenas rotas específicas usarão @requires_edit_auth
        # Isso permite visualização livre mas protege criação/deleção
        
        # Rate limiting (aplicado a todas as rotas, exceto assets estáticos)
        if enable_rate_limit and not request.path.startswith('/assets/'):
            ip = request.remote_addr
            if request.headers.get('X-Real-IP'):
                ip = request.headers.get('X-Real-IP')
            elif request.headers.get('X-Forwarded-For'):
                ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            
            now = time.time()
            if ip not in request_counts:
                request_counts[ip] = {'minute': [], 'hour': []}
            
            request_counts[ip]['minute'] = [
                t for t in request_counts[ip]['minute'] 
                if now - t < 60
            ]
            
            if len(request_counts[ip]['minute']) >= 60:
                return jsonify({
                    'error': 'Rate limit excedido',
                    'message': 'Muitas requisições. Tente novamente em 1 minuto.'
                }), 429
    
    @app.after_request
    def after_request(response):
        """Executado depois de cada requisição"""
        from flask import g
        import logging
        
        # Calcular duração da requisição
        if hasattr(g, 'start_time'):
            duration_ms = (datetime.now() - g.start_time).total_seconds() * 1000
            
            # Log estruturado de latência
            # Em dev: console formatado
            # Em prod: logger padrão (sem PII)
            is_dev = os.environ.get('FLASK_ENV', 'development') == 'development'
            
            if is_dev:
                # Dev: console formatado com timestamp
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f'[{timestamp}] {request.method:6s} {request.path:30s} {response.status_code:3d} {duration_ms:7.2f} ms')
            else:
                # Prod: logger estruturado (sem PII)
                logger = logging.getLogger('request_timing')
                logger.info(
                    'Request completed',
                    extra={
                        'method': request.method,
                        'path': request.path,
                        'status': response.status_code,
                        'duration_ms': round(duration_ms, 2)
                    }
                )
        
        # Log de acesso (arquivo)
        username = getattr(request, 'authenticated_user', None)
        log_access(
            request.remote_addr,
            request.path,
            request.method,
            response.status_code,
            username
        )
        
        return response
