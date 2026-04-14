# -*- coding: utf-8 -*-
"""
Rotas de Autenticação
Suporta HTTP Basic Auth (legado) e JWT (módulo Recebíveis)
"""
import base64

from flask import Blueprint, request

from app.middleware import check_auth, log_debug
from app.schemas.common import error_response, success_response

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ---------------------------------------------------------------------------
# POST /api/auth/login
# Aceita {username, password} (Basic/legado) ou {email, password} (JWT/DB)
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    """Login — retorna JWT para usuários DB, ou confirmação para usuários env-var."""
    try:
        data = request.get_json() or {}

        # Suporte a {email, password} (novo) e {username, password} (legado)
        email = (data.get("email") or data.get("username") or "").strip()
        password = (data.get("password") or "").strip()

        log_debug("Login attempt", {"email": email, "password_len": len(password)})

        if not email or not password:
            return error_response("Email e senha são obrigatórios", 400)

        # --- Tentar autenticação via banco (usuários DB) ---
        try:
            from app import db as _db
            from app.models.user import User
            from app.services.auth_service import generate_token, verify_password

            # Aceita email ou nome (case-insensitive)
            db_user = User.query.filter_by(email=email, is_active=True).first()
            if not db_user:
                db_user = User.query.filter(
                    _db.func.lower(User.name) == email.lower(),
                    User.is_active == True,  # noqa: E712
                ).first()

            if db_user and verify_password(password, db_user.password_hash):
                token = generate_token(db_user)
                log_debug("JWT login success", {"email": email, "role": db_user.role})
                return success_response(
                    {
                        "access_token": token,
                        "user": db_user.to_dict(),
                    },
                    message="Login realizado com sucesso",
                )
        except Exception as e:
            # Banco ainda não migrado ou outro erro — continuar para Basic Auth
            log_debug("DB login error (fallback to basic)", {"error": str(e)})

        # --- Fallback: autenticação via env vars (Basic Auth legado) ---
        is_authenticated, role = check_auth(email, password)
        if is_authenticated:
            log_debug("Basic login success", {"username": email, "role": role})
            return success_response(
                {"username": email, "role": role or "admin"},
                message="Login realizado com sucesso",
            )

        log_debug("Login failed", {"email": email})
        return error_response("Credenciais inválidas", 401)

    except Exception as e:
        log_debug("Login exception", {"error": str(e)})
        return error_response(f"Erro ao processar login: {str(e)}", 500)


# ---------------------------------------------------------------------------
# POST /api/auth/logout  (client-side — apenas confirma)
# ---------------------------------------------------------------------------
@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Logout — token é invalidado pelo cliente (sem blacklist)."""
    return success_response({}, message="Logout realizado")


# ---------------------------------------------------------------------------
# GET /api/auth/me  — retorna usuário autenticado (JWT)
# ---------------------------------------------------------------------------
@auth_bp.route("/me", methods=["GET"])
def me():
    """Retorna dados do usuário JWT autenticado."""
    try:
        from app.services.auth_service import decode_token, extract_bearer_token

        token = extract_bearer_token(request.headers.get("Authorization"))
        if not token:
            return error_response("Token JWT obrigatório", 401)

        payload = decode_token(token)
        if not payload:
            return error_response("Token inválido ou expirado", 401)

        # Buscar dados atualizados no banco
        from app.models.user import User

        user = User.query.filter_by(id=payload["user_id"], is_active=True).first()
        if not user:
            return error_response("Usuário não encontrado", 404)

        return success_response({"user": user.to_dict()})

    except Exception as e:
        return error_response(f"Erro: {str(e)}", 500)


# ---------------------------------------------------------------------------
# PUT /api/auth/password  — altera própria senha (JWT)
# ---------------------------------------------------------------------------
@auth_bp.route("/password", methods=["PUT"])
def change_password():
    """Altera a senha do usuário autenticado via JWT."""
    try:
        from app.services.auth_service import decode_token, extract_bearer_token, hash_password, verify_password

        token = extract_bearer_token(request.headers.get("Authorization"))
        if not token:
            return error_response("Token JWT obrigatório", 401)

        payload = decode_token(token)
        if not payload:
            return error_response("Token inválido ou expirado", 401)

        data = request.get_json() or {}
        current_password = (data.get("current_password") or "").strip()
        new_password = (data.get("new_password") or "").strip()

        if not current_password or not new_password:
            return error_response("current_password e new_password são obrigatórios", 400)

        if len(new_password) < 8:
            return error_response("Nova senha deve ter pelo menos 8 caracteres", 400)

        from app import db
        from app.models.user import User

        user = User.query.filter_by(id=payload["user_id"], is_active=True).first()
        if not user:
            return error_response("Usuário não encontrado", 404)

        if not verify_password(current_password, user.password_hash):
            return error_response("Senha atual incorreta", 401)

        user.password_hash = hash_password(new_password)
        db.session.commit()

        return success_response({}, message="Senha alterada com sucesso")

    except Exception as e:
        return error_response(f"Erro: {str(e)}", 500)


# ---------------------------------------------------------------------------
# GET /api/auth/check  — compatibilidade legado (Basic Auth)
# ---------------------------------------------------------------------------
@auth_bp.route("/check", methods=["GET"])
def check_auth_status():
    """Verifica se a requisição está autenticada (Basic Auth legado)."""
    try:
        auth = request.authorization
        log_debug(
            "Auth check start",
            {
                "has_request_authorization": bool(auth),
                "has_authorization_header": bool(request.headers.get("Authorization")),
            },
        )

        if not auth:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Basic "):
                try:
                    encoded = auth_header[6:]
                    decoded = base64.b64decode(encoded).decode("utf-8")
                    username, password = decoded.split(":", 1)
                    auth = type("obj", (object,), {"username": username, "password": password})()
                except Exception:
                    pass

        if auth and hasattr(auth, "username") and hasattr(auth, "password"):
            is_authenticated, role = check_auth(auth.username, auth.password)
            if is_authenticated:
                return success_response(
                    {"authenticated": True, "role": role or "admin"}, message="Autenticado"
                )

        return success_response({"authenticated": False}, message="Não autenticado")

    except Exception as e:
        log_debug("Auth check exception", {"error": str(e)})
        return error_response(f"Erro ao verificar autenticação: {str(e)}", 500)
