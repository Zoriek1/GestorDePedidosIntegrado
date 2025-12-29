# -*- coding: utf-8 -*-
"""
Rotas de Autenticação - Blueprint para endpoints de autenticação
"""
from flask import Blueprint, request, jsonify
from app.middleware import check_auth
from app.schemas.common import success_response, error_response

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
        # Verificar se há header de autenticação
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Basic '):
            return success_response({'authenticated': True}, message='Autenticado')
        else:
            return success_response({'authenticated': False}, message='Não autenticado')
            
    except Exception as e:
        return error_response(f'Erro ao verificar autenticação: {str(e)}', 500)

