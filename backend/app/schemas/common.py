# -*- coding: utf-8 -*-
"""
Schemas Comuns - Helpers para respostas padronizadas
"""
from typing import Any, Dict, Optional

from flask import jsonify


def success_response(
    data: Any = None, message: Optional[str] = None, status_code: int = 200
) -> tuple:
    """
    Cria resposta de sucesso padronizada

    Args:
        data: Dados a serem retornados
        message: Mensagem opcional
        status_code: Código HTTP de status

    Returns:
        Tupla (jsonify response, status_code)
    """
    response = {"success": True}

    if message:
        response["message"] = message

    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        elif isinstance(data, list):
            response["data"] = data
        else:
            response["data"] = data

    return jsonify(response), status_code


def error_response(message: str, code: int = 400, details: Optional[Dict] = None) -> tuple:
    """
    Cria resposta de erro padronizada

    Args:
        message: Mensagem de erro
        code: Código HTTP de status
        details: Detalhes adicionais do erro

    Returns:
        Tupla (jsonify response, status_code)
    """
    response = {"success": False, "error": message}

    if details:
        response["details"] = details

    return jsonify(response), code
