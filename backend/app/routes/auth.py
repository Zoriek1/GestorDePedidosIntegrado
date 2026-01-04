# -*- coding: utf-8 -*-
"""
Rotas de Autenticação - Blueprint para endpoints de autenticação
"""
import base64

from flask import Blueprint, request

from app.middleware import check_auth, log_debug
from app.schemas.common import error_response, success_response

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """Valida credenciais e retorna confirmação"""
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        log_debug("Login attempt", {"username": username, "password_len": len(password)})

        if not username or not password:
            return error_response('Usuário e senha são obrigatórios', 400)

        if check_auth(username, password):
            log_debug("Login success", {"username": username})
            return success_response(
                {'username': username},
                message='Login realizado com sucesso'
            )
        else:
            log_debug("Login failed", {"username": username})
            return error_response('Credenciais inválidas', 401)

    except Exception as e:
        log_debug("Login exception", {"error": str(e)})
        return error_response(f'Erro ao processar login: {str(e)}', 500)


@auth_bp.route('/check', methods=['GET'])
def check_auth_status():
    """Verifica se a requisição está autenticada"""
    try:
        # Tentar obter credenciais do request.authorization (Flask decodifica automaticamente)
        auth = request.authorization
        log_debug(
            "Auth check start",
            {
                "has_request_authorization": bool(auth),
                "has_authorization_header": bool(request.headers.get("Authorization")),
            },
        )

        # Se não estiver disponível, decodificar manualmente do header
        if not auth:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Basic '):
                try:
                    # Decodificar Base64
                    encoded = auth_header[6:]  # Remove "Basic "
                    decoded = base64.b64decode(encoded).decode('utf-8')
                    username, password = decoded.split(':', 1)
                    auth = type('obj', (object,), {'username': username, 'password': password})()
                except Exception:
                    log_debug("Auth check decode failed", {"reason": "basic_decode_exception"})
                    pass

        # Validar credenciais
        if auth and hasattr(auth, 'username') and hasattr(auth, 'password'):
            log_debug(
                "Auth check credentials present",
                {"username": getattr(auth, "username", None), "password_len": len(getattr(auth, "password", "") or "")},
            )
            if check_auth(auth.username, auth.password):
                return success_response({'authenticated': True}, message='Autenticado')

        return success_response({'authenticated': False}, message='Não autenticado')

    except Exception as e:
        log_debug("Auth check exception", {"error": str(e)})
        return error_response(f'Erro ao verificar autenticação: {str(e)}', 500)
