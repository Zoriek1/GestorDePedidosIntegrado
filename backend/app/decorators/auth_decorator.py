# -*- coding: utf-8 -*-
"""
@require_auth — Decorator JWT-only para as rotas do módulo Recebíveis
"""
from functools import wraps
from typing import List, Optional

from flask import jsonify, request

from app.services.auth_service import decode_token, extract_bearer_token


def require_auth(roles: Optional[List[str]] = None):
    """
    Decorator que exige JWT Bearer válido.

    Injeta `request.current_user` com o payload do token:
      {user_id, role, name, email}

    Args:
        roles: Lista de roles permitidos. None = qualquer role autenticado.

    Exemplos:
        @require_auth()
        @require_auth(roles=['admin'])
        @require_auth(roles=['admin', 'vendedor'])
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            token = extract_bearer_token(auth_header)

            if not token:
                return (
                    jsonify({"error": "Acesso negado", "message": "Token JWT obrigatório"}),
                    401,
                )

            payload = decode_token(token)
            if not payload:
                return (
                    jsonify(
                        {
                            "error": "Token inválido ou expirado",
                            "message": "Faça login novamente",
                        }
                    ),
                    401,
                )

            # Confirma usuário e loja no banco (não confia só nas claims) e popula
            # g.current_store + request.current_user.
            from app.services.auth_context import load_request_identity

            current_user, error = load_request_identity(payload)
            if error:
                body, status = error
                return jsonify(body), status

            # Checagem de role usa a role autoritativa do banco.
            if roles and current_user.get("role") not in roles:
                return (
                    jsonify(
                        {
                            "error": "Acesso negado",
                            "message": f"Esta operação requer um dos roles: {', '.join(roles)}",
                            "user_role": current_user.get("role"),
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)

        decorated._auth = f"jwt:{','.join(roles) if roles else 'any'}"
        return decorated

    return decorator
