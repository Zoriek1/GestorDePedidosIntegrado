# -*- coding: utf-8 -*-
"""
Rotas de Autenticação
Suporta HTTP Basic Auth (legado) e JWT (módulo Recebíveis)
"""
import base64
import logging

from flask import Blueprint, request

from app.middleware import check_auth, log_debug, rate_limit
from app.schemas.common import error_response, success_response

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _store_by_email_domain(email: str):
    """Resolve o tenant pelo domínio do e-mail (maria@floriculturax.com -> loja X).

    Retorna None quando o identificador não é e-mail, quando nenhuma loja reivindica
    aquele domínio, ou se a consulta falhar. Nesses casos o login cai na busca
    global (compat com bases single-tenant e com usuários de e-mail pessoal).
    """
    if "@" not in email:
        return None
    domain = email.rsplit("@", 1)[-1].strip().lower()
    if not domain:
        return None
    try:
        from app.models.store import Store

        return Store.query.filter_by(email_domain=domain).first()
    except Exception:
        from app import db as _db

        _db.session.rollback()
        return None


# ---------------------------------------------------------------------------
# POST /api/auth/login
# Aceita {username, password} (Basic/legado) ou {email, password} (JWT/DB)
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
@rate_limit(max_per_minute=10, max_per_hour=100)
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

            # Multi-tenant: o domínio do e-mail resolve a loja ANTES de buscar o
            # usuário. Sem isso, dois tenants com o mesmo e-mail fariam o `.first()`
            # entrar na conta errada em silêncio. Domínio não reivindicado por
            # nenhuma loja mantém o comportamento antigo (busca global).
            login_store = _store_by_email_domain(email)
            if login_store is not None and not login_store.active:
                log_debug("Login em loja inativa", {"email": email, "store": login_store.slug})
                return error_response("Loja inativa. Contate o administrador.", 403)

            # Aceita email ou nome (case-insensitive). O nome é único apenas DENTRO
            # da loja, então entre lojas pode haver duas "Maria": nesse caso não
            # adivinhamos, pedimos o e-mail em vez de logar na conta errada.
            user_query = User.query.filter_by(email=email, is_active=True)
            if login_store is not None:
                user_query = user_query.filter_by(store_ref_id=login_store.id)
            db_user = user_query.first()
            if not db_user:
                name_query = User.query.filter(
                    _db.func.lower(User.name) == email.lower(),
                    User.is_active == True,  # noqa: E712
                )
                if login_store is not None:
                    name_query = name_query.filter(User.store_ref_id == login_store.id)
                name_matches = name_query.all()
                if len(name_matches) == 1:
                    db_user = name_matches[0]
                elif len(name_matches) > 1:
                    log_debug("Login por nome ambíguo", {"name": email})
                    return error_response(
                        "Não foi possível identificar o usuário por esse nome. "
                        "Entre com o seu e-mail.",
                        401,
                    )

            if db_user and verify_password(password, db_user.password_hash):
                # Resolve a loja antes de emitir o token (multi-tenant, Fase A):
                # - vínculo explícito precisa resolver p/ uma loja existente e ativa
                #   (loja ausente/órfã ou inativa bloqueia mesmo com senha válida);
                # - durante o rollout, usuário sem vínculo (store_ref_id NULL) cai na
                #   loja default; se nem a default existir (base legada single-tenant),
                #   segue sem loja para não quebrar a compatibilidade.
                from app.services.auth_context import resolve_user_store

                store = resolve_user_store(db_user)
                if db_user.store_ref_id is not None and store is None:
                    log_debug("Login sem loja", {"email": email})
                    return error_response(
                        "Sua conta não está associada a uma loja válida. "
                        "Contate o administrador.",
                        403,
                    )
                if store is not None and not store.active:
                    log_debug("Login em loja inativa", {"email": email, "store": store.slug})
                    return error_response("Loja inativa. Contate o administrador.", 403)

                token = generate_token(db_user, store)
                log_debug("JWT login success", {"email": email, "role": db_user.role})
                user_payload = {
                    **db_user.to_dict(),
                    "store_ref_id": store.id if store else db_user.store_ref_id,
                    "store_slug": store.slug if store else None,
                    # Só define a navegação do frontend (esconder o menu de Leads).
                    # A autorização real é o guard do leads_bp, que lê do banco a
                    # cada request — por isso a flag fica fora do JWT: virá-la no
                    # banco não exige reemitir tokens, basta um novo login.
                    "leads_enabled": bool(getattr(store, "leads_enabled", False)),
                }
                return success_response(
                    {
                        "access_token": token,
                        "user": user_payload,
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

    except Exception:
        logger.exception("Falha inesperada ao processar login")
        return error_response("Erro ao processar login", 500)


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

        # Resolve a loja pelo usuário no banco (funciona mesmo para tokens legados
        # sem claims de tenant).
        from app.services.auth_context import resolve_user_store

        store = resolve_user_store(user)
        user_payload = {
            **user.to_dict(),
            "store_ref_id": store.id if store else user.store_ref_id,
            "store_slug": store.slug if store else None,
        }
        return success_response({"user": user_payload})

    except Exception:
        logger.exception("Falha em GET /auth/me")
        return error_response("Erro ao obter dados do usuário", 500)


# ---------------------------------------------------------------------------
# PUT /api/auth/password  — altera própria senha (JWT)
# ---------------------------------------------------------------------------
@auth_bp.route("/password", methods=["PUT"])
def change_password():
    """Altera a senha do usuário autenticado via JWT."""
    try:
        from app.services.auth_service import (
            decode_token,
            extract_bearer_token,
            hash_password,
            verify_password,
        )

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

    except Exception:
        logger.exception("Falha ao alterar senha")
        return error_response("Erro ao alterar senha", 500)


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

    except Exception:
        logger.exception("Falha ao verificar autenticação")
        return error_response("Erro ao verificar autenticação", 500)
