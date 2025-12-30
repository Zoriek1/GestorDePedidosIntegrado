# -*- coding: utf-8 -*-
"""
Rotas de Autenticação - Blueprint para endpoints de autenticação
"""
from flask import Blueprint, request, jsonify
from app.middleware import check_auth
from app.schemas.common import success_response, error_response
import base64

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """Valida credenciais e retorna confirmação"""
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return error_response('Usuário e senha são obrigatórios', 400)
        
        if check_auth(username, password):
            return success_response(
                {'username': username},
                message='Login realizado com sucesso'
            )
        else:
            return error_response('Credenciais inválidas', 401)
            
    except Exception as e:
        return error_response(f'Erro ao processar login: {str(e)}', 500)


@auth_bp.route('/check', methods=['GET'])
def check_auth_status():
    """Verifica se a requisição está autenticada"""
    try:
        # Tentar obter credenciais do request.authorization (Flask decodifica automaticamente)
        auth = request.authorization
        
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
                    pass
        
        # Validar credenciais
        if auth and hasattr(auth, 'username') and hasattr(auth, 'password'):
            if check_auth(auth.username, auth.password):
                return success_response({'authenticated': True}, message='Autenticado')
        
        return success_response({'authenticated': False}, message='Não autenticado')
            
    except Exception as e:
        return error_response(f'Erro ao verificar autenticação: {str(e)}', 500)

