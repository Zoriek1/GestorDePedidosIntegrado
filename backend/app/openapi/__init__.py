# -*- coding: utf-8 -*-
"""
OpenAPI/Swagger Configuration

Configuração do Flask-Smorest para documentação automática da API.
"""
from flask_smorest import Api

# Instância global da API (será inicializada em init_openapi)
api = None


def init_openapi(app):
    """
    Inicializa Flask-Smorest para documentação OpenAPI

    Args:
        app: Instância da aplicação Flask
    """
    global api

    # Configuração do OpenAPI
    app.config["API_TITLE"] = "Plante Uma Flor API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/"
    app.config["OPENAPI_REDOC_PATH"] = "/redoc"
    app.config[
        "OPENAPI_REDOC_URL"
    ] = "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"

    # Criar instância da API
    api = Api(app)

    # Registrar blueprint de documentação usando api.register_blueprint()
    # Nota: Este blueprint documenta os endpoints prioritários
    # Os endpoints reais continuam funcionando normalmente
    try:
        from app.openapi import blueprint

        # Registrar o blueprint do Flask-Smorest no Api (não no app Flask)
        api.register_blueprint(blueprint.blp)
    except Exception as e:
        # Se houver erro ao registrar OpenAPI, continuar sem documentação
        print(f"[AVISO] Erro ao registrar OpenAPI: {e}")
        print("[AVISO] Swagger UI não estará disponível, mas a API continua funcionando")
        import traceback

        traceback.print_exc()

    return api
