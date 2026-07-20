# -*- coding: utf-8 -*-
"""
Middleware de Segurança - Acesso Remoto
Protege o sistema contra acesso não autorizado
"""
import os
import time
from datetime import datetime
from functools import wraps

from flask import Response, request


def log_debug(msg, data):
    # Logging util (disabled by default to avoid writing local files in production)
    return


# ============================================
# CONFIGURAÇÃO DE USUÁRIOS
# ============================================
# Configure as credenciais via variáveis de ambiente.
# ADMIN_PASSWORD_HASH: hash bcrypt (recomendado).
# ADMIN_PASSWORD: senha plain-text (retrocompatibilidade).
# Senha vazia desabilita o usuário.
def _admin_credential() -> str:
    """Retorna hash bcrypt ou senha plain-text do admin, nesta ordem de preferência."""
    return os.environ.get("ADMIN_PASSWORD_HASH", "") or os.environ.get("ADMIN_PASSWORD", "")


USERS = {
    "admin": {
        "password": _admin_credential(),
        "role": "admin",
    },
    "atendente": {
        "password": os.environ.get("ATENDENTE_PASSWORD", ""),
        "role": "atendente",
    },
    "entregador": {
        "password": os.environ.get("ENTREGADOR_PASSWORD", ""),
        "role": "entregador",
    },
}


def get_user_config(username):
    """Retorna configuração do usuário."""
    user_config = USERS.get(username)
    if user_config is None:
        return None
    # Compatibilidade com formato antigo (string pura de senha)
    if isinstance(user_config, str):
        return {"password": user_config, "role": "admin"}
    return user_config


def _verify_password(stored: str, provided: str) -> bool:
    """
    Verifica senha com suporte a bcrypt e plain-text.
    Hashes bcrypt são identificados pelo prefixo '$2b$' ou '$2a$'.
    """
    if stored.startswith(("$2b$", "$2a$")):
        try:
            import bcrypt as _bcrypt

            return _bcrypt.checkpw(provided.encode("utf-8"), stored.encode("utf-8"))
        except ImportError:
            return False
    # Retrocompatibilidade: comparação plain-text
    return stored == provided


# ============================================
# AUTENTICAÇÃO BÁSICA HTTP
# ============================================
def check_auth(username, password):
    """
    Verifica se o usuário e senha são válidos.
    Retorna (bool, role) onde bool indica se autenticado e role é o papel do usuário.
    """
    user_config = get_user_config(username)
    if user_config is None:
        return False, None

    stored_password = user_config["password"]
    if not stored_password:  # Senha vazia = usuário desabilitado
        return False, None

    is_authenticated = _verify_password(stored_password, password)
    role = user_config.get("role", "admin")
    return is_authenticated, role if is_authenticated else None


def requires_auth(f):
    """
    Decorator para proteger rotas com autenticação HTTP Basic
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization

        if not auth:
            return Response(
                "Acesso negado. Credenciais necessárias.",
                401,
                {
                    "WWW-Authenticate": 'Basic realm="Gestor de Pedidos - Login Necessário"',
                    "Content-Type": "application/json",
                },
            )

        is_authenticated, role = check_auth(auth.username, auth.password)
        if not is_authenticated:
            return Response(
                "Acesso negado. Credenciais necessárias.",
                401,
                {
                    "WWW-Authenticate": 'Basic realm="Gestor de Pedidos - Login Necessário"',
                    "Content-Type": "application/json",
                },
            )

        # Armazenar usuário autenticado no request (opcional)
        request.authenticated_user = auth.username
        request.user_role = role

        return f(*args, **kwargs)

    # Marcar função com tipo de autenticação (para dump_routes.py)
    decorated._auth = "basic"
    return decorated


def requires_edit_auth(f):
    """
    Decorator para proteger apenas rotas críticas de edição (criar/deletar pedidos)
    Aceita JWT Bearer (módulo Recebíveis) ou HTTP Basic Auth (legado).
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import jsonify

        # --- Tentar JWT Bearer primeiro ---
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            payload = None
            try:
                from app.services.auth_service import decode_token, extract_bearer_token

                token = extract_bearer_token(auth_header)
                payload = decode_token(token) if token else None
            except Exception:
                payload = None
            if payload:
                # Token válido: confirma usuário e loja no banco (popula g.current_store).
                from app.services.auth_context import load_request_identity

                current_user, error = load_request_identity(payload)
                if error:
                    body, status = error
                    return jsonify(body), status
                request.authenticated_user = current_user.get("email", "")
                request.user_role = current_user.get("role", "")
                return f(*args, **kwargs)

        # --- Fallback: HTTP Basic Auth ---
        auth = request.authorization

        if not auth:
            return (
                jsonify(
                    {
                        "error": "Acesso negado",
                        "message": "Esta operação requer autenticação. Por favor, faça login.",
                        "requires_auth": True,
                    }
                ),
                401,
            )

        is_authenticated, role = check_auth(auth.username, auth.password)
        if not is_authenticated:
            return (
                jsonify(
                    {
                        "error": "Acesso negado",
                        "message": "Esta operação requer autenticação. Por favor, faça login.",
                        "requires_auth": True,
                    }
                ),
                401,
            )

        request.authenticated_user = auth.username
        request.user_role = role

        return f(*args, **kwargs)

    decorated._auth = "edit"
    return decorated


# ============================================
# SISTEMA DE PERMISSÕES E PAPÉIS
# ============================================

# Definição de permissões por papel
PERMISSIONS = {
    "admin": ["*"],  # Todas as permissões
    "atendente": [
        "pedidos:create",
        "pedidos:update",
        "pedidos:view",
        "pedidos:update_status",
        "clientes:view",
        "clientes:create",
        "clientes:update",
        "vendas:view",
        "fontes:view",
    ],
    "vendedor": [
        "pedidos:create",
        "pedidos:update",
        "pedidos:view",
        "pedidos:update_status",
        "pedidos:marcar_impresso",
        "pedidos:cartao_impresso",
        "pedidos:edit_own",
        "pedidos:delete_own",
        "clientes:view",
        "clientes:create",
        "clientes:update",
        "vendas:view",
        "fontes:view",
        "rotas:view",
        "rotas:create",
        "leads:view",
        "leads:update",
    ],
    "entregador": [
        "pedidos:view",
        "pedidos:update_status",
        "pedidos:assign_delivery",
        "pedidos:complete_delivery",
        "rotas:view",
    ],
}


def has_permission(role: str, permission: str) -> bool:
    """
    Verifica se um papel tem uma permissão específica

    Args:
        role: Papel do usuário (admin, atendente, entregador)
        permission: Permissão a verificar (ex: "pedidos:create")

    Returns:
        True se o papel tem a permissão, False caso contrário
    """
    if not role:
        return False

    role_perms = PERMISSIONS.get(role, [])

    # Admin tem todas as permissões
    if "*" in role_perms:
        return True

    return permission in role_perms


def requires_role(required_role: str):
    """
    Decorator para verificar se o usuário tem um papel específico.
    Aceita JWT Bearer (módulo Recebíveis) ou HTTP Basic Auth (legado).
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import jsonify

            # --- Tentar JWT Bearer primeiro ---
            auth_header = request.headers.get("Authorization", "")
            if auth_header.lower().startswith("bearer "):
                payload = None
                try:
                    from app.services.auth_service import decode_token, extract_bearer_token

                    token = extract_bearer_token(auth_header)
                    payload = decode_token(token) if token else None
                except Exception:
                    payload = None
                if payload:
                    from app.services.auth_context import load_request_identity

                    current_user, error = load_request_identity(payload)
                    if error:
                        body, status = error
                        return jsonify(body), status
                    role = current_user.get("role", "")
                    if role != required_role:
                        return (
                            jsonify(
                                {
                                    "error": "Acesso negado",
                                    "message": f"Esta operação requer papel '{required_role}'",
                                    "user_role": role,
                                }
                            ),
                            403,
                        )
                    request.authenticated_user = current_user.get("email", "")
                    request.user_role = role
                    return f(*args, **kwargs)

            # --- Fallback: HTTP Basic Auth ---
            auth = request.authorization

            if not auth:
                return (
                    jsonify({"error": "Acesso negado", "message": "Autenticação necessária"}),
                    401,
                )

            is_authenticated, role = check_auth(auth.username, auth.password)
            if not is_authenticated:
                return (
                    jsonify({"error": "Acesso negado", "message": "Credenciais inválidas"}),
                    401,
                )

            if role != required_role:
                return (
                    jsonify(
                        {
                            "error": "Acesso negado",
                            "message": f"Esta operação requer papel '{required_role}'",
                            "user_role": role,
                        }
                    ),
                    403,
                )

            request.authenticated_user = auth.username
            request.user_role = role

            return f(*args, **kwargs)

        decorated._auth = f"role:{required_role}"
        return decorated

    return decorator


def requires_any_role(*allowed_roles: str):
    """
    Decorator para verificar se o usuário tem um dos papéis especificados.
    Aceita JWT Bearer (módulo Recebíveis) ou HTTP Basic Auth (legado).
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import jsonify

            # --- Tentar JWT Bearer primeiro ---
            auth_header = request.headers.get("Authorization", "")
            if auth_header.lower().startswith("bearer "):
                payload = None
                try:
                    from app.services.auth_service import decode_token, extract_bearer_token

                    token = extract_bearer_token(auth_header)
                    payload = decode_token(token) if token else None
                except Exception:
                    payload = None
                if payload:
                    from app.services.auth_context import load_request_identity

                    current_user, error = load_request_identity(payload)
                    if error:
                        body, status = error
                        return jsonify(body), status
                    role = current_user.get("role", "")
                    if role not in allowed_roles:
                        return (
                            jsonify(
                                {
                                    "error": "Acesso negado",
                                    "message": f"Esta operação requer um dos papéis: {', '.join(allowed_roles)}",
                                    "user_role": role,
                                }
                            ),
                            403,
                        )
                    request.authenticated_user = current_user.get("email", "")
                    request.user_role = role
                    return f(*args, **kwargs)

            # --- Fallback: HTTP Basic Auth ---
            auth = request.authorization

            if not auth:
                return (
                    jsonify({"error": "Acesso negado", "message": "Autenticação necessária"}),
                    401,
                )

            is_authenticated, role = check_auth(auth.username, auth.password)
            if not is_authenticated:
                return (
                    jsonify({"error": "Acesso negado", "message": "Credenciais inválidas"}),
                    401,
                )

            if role not in allowed_roles:
                return (
                    jsonify(
                        {
                            "error": "Acesso negado",
                            "message": f"Esta operação requer um dos papéis: {', '.join(allowed_roles)}",
                            "user_role": role,
                        }
                    ),
                    403,
                )

            request.authenticated_user = auth.username
            request.user_role = role

            return f(*args, **kwargs)

        decorated._auth = f"roles:{','.join(allowed_roles)}"
        return decorated

    return decorator


def requires_permission(permission: str):
    """
    Decorator para verificar se o usuário tem uma permissão específica

    Args:
        permission: Permissão necessária (ex: "pedidos:create")
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization

            if not auth:
                from flask import jsonify

                return (
                    jsonify(
                        {
                            "error": "Acesso negado",
                            "message": "Autenticação necessária",
                        }
                    ),
                    401,
                )

            is_authenticated, role = check_auth(auth.username, auth.password)
            if not is_authenticated:
                from flask import jsonify

                return (
                    jsonify(
                        {
                            "error": "Acesso negado",
                            "message": "Credenciais inválidas",
                        }
                    ),
                    401,
                )

            if not has_permission(role, permission):
                from flask import jsonify

                return (
                    jsonify(
                        {
                            "error": "Acesso negado",
                            "message": f"Permissão '{permission}' necessária",
                            "user_role": role,
                        }
                    ),
                    403,
                )

            request.authenticated_user = auth.username
            request.user_role = role

            return f(*args, **kwargs)

        decorated._auth = f"permission:{permission}"
        return decorated

    return decorator


# ============================================
# RATE LIMITING SIMPLES
# ============================================
request_counts = {}


def _get_client_ip() -> str:
    """
    Retorna o IP real do cliente de forma segura.

    Só confia em headers de proxy quando o proxy imediato (remote_addr) é uma rede
    privada (Docker bridge, localhost, LAN) — previne spoofing de clientes externos.

    Ordem de preferência dentro do proxy confiável:
      1. CF-Connecting-IP — a Cloudflare define este header com o IP real de quem
         conectou e sobrescreve qualquer valor forjado pelo cliente. É o único
         confiável quando estamos atrás do Cloudflare Tunnel.
      2. X-Real-IP — definido por proxies reversos (nginx) confiáveis.
      NÃO usamos o primeiro elemento de X-Forwarded-For como fonte primária: o cliente
      pode prepender um valor falso (a Cloudflare apenas *anexa* o IP real depois),
      o que permitiria rodar o bucket do rate limit e furar o limite. Mantido apenas
      como último fallback quando não há CF-Connecting-IP nem X-Real-IP.
    """
    import ipaddress

    remote = request.remote_addr or ""
    try:
        is_trusted_proxy = ipaddress.ip_address(remote).is_private
    except ValueError:
        is_trusted_proxy = False

    if is_trusted_proxy:
        cf_ip = (request.headers.get("CF-Connecting-IP") or "").strip()
        if cf_ip:
            return cf_ip
        real_ip = (request.headers.get("X-Real-IP") or "").strip()
        if real_ip:
            return real_ip
        forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if forwarded:
            return forwarded

    return remote


def rate_limit(max_per_minute=60, max_per_hour=1000):
    """
    Rate limiting simples por IP
    Limita requisições para prevenir abuso
    """
    from flask import jsonify

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            ip = _get_client_ip()
            now = time.time()

            # Inicializar contador para este IP
            if ip not in request_counts:
                request_counts[ip] = {"minute": [], "hour": []}

            # Limpar requisições antigas
            request_counts[ip]["minute"] = [t for t in request_counts[ip]["minute"] if now - t < 60]
            request_counts[ip]["hour"] = [t for t in request_counts[ip]["hour"] if now - t < 3600]

            # Verificar limite por minuto
            if len(request_counts[ip]["minute"]) >= max_per_minute:
                response = jsonify(
                    {
                        "error": "Rate limit excedido",
                        "message": f"Máximo de {max_per_minute} requisições por minuto",
                        "retry_after": 60,
                    }
                )
                response.status_code = 429
                response.headers["Retry-After"] = "60"
                return response

            # Verificar limite por hora
            if len(request_counts[ip]["hour"]) >= max_per_hour:
                response = jsonify(
                    {
                        "error": "Rate limit excedido",
                        "message": f"Máximo de {max_per_hour} requisições por hora",
                        "retry_after": 3600,
                    }
                )
                response.status_code = 429
                response.headers["Retry-After"] = "3600"
                return response

            # Registrar requisição
            request_counts[ip]["minute"].append(now)
            request_counts[ip]["hour"].append(now)

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
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f'access_{datetime.now().strftime("%Y-%m-%d")}.log')

    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = username or "anonymous"
        f.write(f"{timestamp} | {ip} | {user} | {method} {endpoint} | {status_code}\n")


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

        # IMPORTANTE: NÃO há autenticação global aqui.
        # A proteção é feita por decorator em cada rota (@requires_edit_auth,
        # @requires_any_role, @require_auth). GETs que devolvem dados internos/PII
        # são gateados individualmente nas blueprints (pedidos, clientes, fontes…).
        # Rotas públicas por design (sem decorator): /api/health, /api/auth/*,
        # /api/pedidos/track/<token> (acompanhamento do cliente via token assinado),
        # além de assets estáticos e do shell do PWA.
        # Este before_request só aplica rate limiting.

        # Rate limiting (aplicado a todas as rotas, exceto assets estáticos)
        if enable_rate_limit and not request.path.startswith("/assets/"):
            ip = _get_client_ip()
            now = time.time()
            if ip not in request_counts:
                request_counts[ip] = {"minute": [], "hour": []}

            request_counts[ip]["minute"] = [t for t in request_counts[ip]["minute"] if now - t < 60]

            if len(request_counts[ip]["minute"]) >= 60:
                return (
                    jsonify(
                        {
                            "error": "Rate limit excedido",
                            "message": "Muitas requisições. Tente novamente em 1 minuto.",
                        }
                    ),
                    429,
                )

    @app.after_request
    def after_request(response):
        """Executado depois de cada requisição"""
        import logging

        from flask import g

        # Calcular duração da requisição
        if hasattr(g, "start_time"):
            duration_ms = (datetime.now() - g.start_time).total_seconds() * 1000

            # Log estruturado de latência
            # Em dev: console formatado
            # Em prod: logger padrão (sem PII)
            is_dev = os.environ.get("FLASK_ENV", "development") == "development"

            if is_dev:
                # Dev: console formatado com timestamp
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(
                    f"[{timestamp}] {request.method:6s} {request.path:30s} {response.status_code:3d} {duration_ms:7.2f} ms"
                )
            else:
                # Prod: logger estruturado
                logger = logging.getLogger("request_timing")
                logger.info(
                    "%s %s %d %.0fms",
                    request.method,
                    request.path,
                    response.status_code,
                    duration_ms,
                )

        # Log de acesso (arquivo)
        username = getattr(request, "authenticated_user", None)
        log_access(
            request.remote_addr,
            request.path,
            request.method,
            response.status_code,
            username,
        )

        return response
