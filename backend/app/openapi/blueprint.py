# -*- coding: utf-8 -*-
"""
OpenAPI Blueprint - Documentação dos endpoints prioritários

Esta é uma versão inicial que documenta os endpoints principais do frontend.
A documentação pode ser evoluída incrementalmente para incluir mais endpoints.
"""
from flask_smorest import Blueprint

from app.openapi.schemas import (
    AuthCheckResponseSchema,
    ClientesBuscarQuerySchema,
    ClientesBuscarResponseSchema,
    HealthResponseSchema,
    PedidosQuerySchema,
    PedidosResponseSchema,
    StatsResponseSchema,
)

# Criar blueprint do Flask-Smorest (não do Flask normal)
blp = Blueprint(
    "openapi_docs",
    __name__,
    description="Documentação dos endpoints prioritários da API",
)


# Documentação dos endpoints prioritários do frontend
# Nota: Estes endpoints são apenas para documentação no Swagger UI
# Os endpoints reais continuam funcionando normalmente em app/routes/


@blp.route("/api/health", methods=["GET"])
@blp.doc(
    summary="Health Check",
    description="Verifica se a API está funcionando normalmente",
    tags=["Health"],
)
@blp.response(200, HealthResponseSchema, description="API funcionando")
@blp.response(500, HealthResponseSchema, description="API com problemas")
def health_check_doc():
    """
    Health Check

    Endpoint para verificar o status da API.
    Não requer autenticação.
    """
    # Importar e chamar endpoint real
    from app.routes.api import health_check

    return health_check()


@blp.route("/api/auth/check", methods=["GET"])
@blp.doc(
    summary="Verificar Autenticação",
    description="Verifica se a requisição está autenticada",
    tags=["Autenticação"],
    security=[{"BasicAuth": []}],
)
@blp.response(200, AuthCheckResponseSchema, description="Resposta de autenticação")
def auth_check_doc():
    """
    Verificar Autenticação

    Verifica se as credenciais fornecidas são válidas.
    Requer autenticação HTTP Basic.
    """
    # Importar e chamar endpoint real
    from app.routes.auth import check_auth_status

    return check_auth_status()


@blp.route("/api/pedidos", methods=["GET"])
@blp.doc(
    summary="Listar Pedidos",
    description="Lista pedidos com filtros opcionais",
    tags=["Pedidos"],
)
@blp.arguments(PedidosQuerySchema, location="query")
@blp.response(200, PedidosResponseSchema, description="Lista de pedidos")
def pedidos_list_doc(**kwargs):
    """
    Listar Pedidos

    Retorna lista de pedidos com filtros opcionais:
    - status: Filtrar por status
    - data_inicio: Data inicial (YYYY-MM-DD)
    - data_fim: Data final (YYYY-MM-DD)
    - search: Busca textual
    """
    # Importar e chamar endpoint real
    from app.routes.pedidos import listar_pedidos

    return listar_pedidos()


@blp.route("/api/stats", methods=["GET"])
@blp.doc(
    summary="Obter Estatísticas",
    description="Retorna estatísticas dos pedidos",
    tags=["Estatísticas"],
)
@blp.response(200, StatsResponseSchema, description="Estatísticas")
def stats_doc():
    """
    Obter Estatísticas

    Retorna estatísticas consolidadas dos pedidos.
    """
    # Importar e chamar endpoint real
    from app.routes.api import obter_estatisticas

    return obter_estatisticas()


@blp.route("/api/clientes/search", methods=["GET"])
@blp.doc(
    summary="Buscar Clientes",
    description="Busca clientes por termo (autocomplete)",
    tags=["Clientes"],
)
@blp.arguments(ClientesBuscarQuerySchema, location="query")
@blp.response(200, ClientesBuscarResponseSchema, description="Lista de clientes")
def clientes_buscar_doc(**kwargs):
    """
    Buscar Clientes

    Busca clientes por termo de busca (nome ou telefone).
    Útil para autocomplete.

    Query Parameters:
    - q (obrigatório): Termo de busca
    - limit (opcional): Limite de resultados (padrão: 10)
    """
    # Importar e chamar endpoint real
    from app.routes.clientes import buscar_clientes_autocomplete

    return buscar_clientes_autocomplete()
