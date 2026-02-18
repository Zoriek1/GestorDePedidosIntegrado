# -*- coding: utf-8 -*-
"""
Rotas do Meta Conversions API Gateway
Implementa endpoints necessários para o Gateway funcionar
"""
import os

from flask import Blueprint, jsonify, request

meta_gateway_bp = Blueprint("meta_gateway", __name__)


def _add_cors_headers(response):
    """Adiciona headers CORS completos para evitar CORB"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "3600"
    # Prevenir CORB - garantir que o navegador não tente "adivinhar" o tipo
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Headers de cache - nunca cachear rotas do Meta Gateway
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@meta_gateway_bp.route("/capig/autoconfig", methods=["GET", "OPTIONS", "POST"])
def capig_autoconfig():
    """
    Endpoint de autoconfiguração do Conversions API Gateway

    A Meta chama este endpoint para configurar o Gateway automaticamente.
    Retorna informações de configuração necessárias.

    Nota: A Meta pode enviar o token via query string (?t=...) ou hash (#t=...).
    O hash não é enviado ao servidor, então detectamos navegadores e retornamos HTML
    que extrai o token da hash e o envia de volta.
    """
    try:
        # CORS headers (a Meta pode fazer requisições cross-origin)
        from flask import Response

        if request.method == "OPTIONS":
            response = Response()
            return _add_cors_headers(response)

        # Se for POST, processar token do body
        if request.method == "POST":
            data = request.get_json() or {}
            token = data.get("t", "")
        else:
            # Obter token da query string (fornecido pela Meta)
            token = request.args.get("t", "")

        # Verificar se a requisição espera JSON (requisição AJAX da Meta)
        accepts_json = "application/json" in request.headers.get("Accept", "")

        # Verificar se é requisição AJAX (X-Requested-With ou fetch/XMLHttpRequest)
        is_ajax = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "fetch" in request.headers.get("User-Agent", "").lower()
            or accepts_json
        )

        # Verificar se é requisição de navegador (User-Agent contém navegador comum)
        # Se não houver token na query string e for navegador, retornar HTML que extrai da hash
        user_agent = request.headers.get("User-Agent", "").lower()
        is_browser = any(
            browser in user_agent for browser in ["mozilla", "chrome", "safari", "edge", "firefox"]
        )
        accepts_html = "text/html" in request.headers.get("Accept", "")

        # Se tem token na query string, SEMPRE retornar JSON (a Meta pode estar fazendo requisição GET)
        # Se é requisição AJAX, sempre retornar JSON (não HTML)
        # Se não tem token na query string, não espera JSON, não é AJAX, e parece ser navegador, retornar HTML
        if token:
            # Tem token na query string - sempre retornar JSON (pode ser requisição da Meta)
            print("[META_GATEWAY] Token na query string detectado - retornando JSON")
            # Continuar para retornar JSON abaixo
        elif not is_ajax and not accepts_json and (is_browser or accepts_html):
            # Retornar página HTML que extrai token da hash e envia ao backend
            html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Meta Conversions API Gateway - Autoconfig</title>
    <script>
        // Extrair token da hash da URL
        function extractTokenFromHash() {
            const hash = window.location.hash;
            if (hash && hash.startsWith('#t=')) {
                return hash.substring(3); // Remove '#t='
            }
            return null;
        }

        // Enviar token ao backend
        async function sendTokenToBackend(token) {
            try {
                const response = await fetch('/capig/autoconfig', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ t: token })
                });

                const data = await response.json();

                // Tentar múltiplas formas de comunicação com a Meta
                // 1. postMessage para window.opener (janela que abriu)
                if (window.opener && !window.opener.closed) {
                    try {
                        window.opener.postMessage({
                            type: 'capig_config',
                            data: data,
                            success: true
                        }, '*');
                        console.log('Enviado para window.opener');
                    } catch (e) {
                        console.error('Erro ao enviar para window.opener:', e);
                    }
                }

                // 2. postMessage para window.parent (se estiver em iframe)
                if (window.parent && window.parent !== window) {
                    try {
                        window.parent.postMessage({
                            type: 'capig_config',
                            data: data,
                            success: true
                        }, '*');
                        console.log('Enviado para window.parent');
                    } catch (e) {
                        console.error('Erro ao enviar para window.parent:', e);
                    }
                }

                // 3. Atualizar URL com token na query string (para requisições AJAX subsequentes da Meta)
                // A Meta pode fazer uma segunda requisição GET com o token na query string
                if (window.history && window.history.replaceState) {
                    try {
                        // Adicionar token na query string para que a Meta possa fazer requisição GET
                        const newUrl = window.location.pathname + '?t=' + encodeURIComponent(token) + '&config=' + encodeURIComponent(JSON.stringify(data));
                        window.history.replaceState({}, '', newUrl);
                        console.log('URL atualizada com token na query string');
                    } catch (e) {
                        console.error('Erro ao atualizar URL:', e);
                    }
                }

                // 4. Aguardar um pouco e fazer uma requisição GET com token na query string
                // Isso simula o que a Meta faria em uma segunda requisição
                setTimeout(() => {
                    fetch('/capig/autoconfig?t=' + encodeURIComponent(token), {
                        headers: {
                            'Accept': 'application/json'
                        }
                    })
                        .then(r => r.json())
                        .then(configData => {
                            console.log('Configuração obtida via GET:', configData);
                            // Enviar novamente via postMessage
                            if (window.opener && !window.opener.closed) {
                                window.opener.postMessage({
                                    type: 'capig_config',
                                    data: configData,
                                    success: true
                                }, '*');
                            }
                        })
                        .catch(e => console.error('Erro ao obter config via GET:', e));
                }, 500);

                // Atualizar a página com o resultado (após DOM estar pronto)
                const updateUI = () => {
                    const resultEl = document.getElementById('result');
                    const statusEl = document.getElementById('status');
                    if (resultEl) resultEl.textContent = JSON.stringify(data, null, 2);
                    if (statusEl) {
                        if (!window.opener && window.parent === window) {
                            statusEl.textContent = 'Configuração recebida. Você pode fechar esta janela.';
                        } else {
                            statusEl.textContent = 'Token processado com sucesso. Aguardando confirmação da Meta...';
                        }
                    }
                };

                // Executar imediatamente se DOM já estiver pronto, senão aguardar
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', updateUI);
                } else {
                    updateUI();
                }
            } catch (error) {
                console.error('Erro ao enviar token:', error);

                // Atualizar UI com erro
                const updateErrorUI = () => {
                    const statusEl = document.getElementById('status');
                    if (statusEl) statusEl.textContent = 'Erro: ' + error.message;
                };

                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', updateErrorUI);
                } else {
                    updateErrorUI();
                }

                // Enviar erro também
                if (window.opener && !window.opener.closed) {
                    window.opener.postMessage({
                        type: 'capig_config',
                        error: error.message,
                        success: false
                    }, '*');
                }
            }
        }

        // Função auxiliar para atualizar elementos do DOM de forma segura
        function safeUpdateElement(id, text) {
            const el = document.getElementById(id);
            if (el) el.textContent = text;
        }

        // Executar quando DOM estiver pronto
        function init() {
            const token = extractTokenFromHash();
            if (token) {
                safeUpdateElement('token-status', 'Token encontrado na URL');
                sendTokenToBackend(token);
            } else {
                // Verificar se há config na query string (de requisição anterior)
                const urlParams = new URLSearchParams(window.location.search);
                const configParam = urlParams.get('config');
                if (configParam) {
                    try {
                        const data = JSON.parse(decodeURIComponent(configParam));
                        safeUpdateElement('result', JSON.stringify(data, null, 2));
                        safeUpdateElement('token-status', 'Configuração carregada');
                        safeUpdateElement('status', 'Configuração disponível');
                    } catch (e) {
                        // Ignorar
                    }
                } else {
                    safeUpdateElement('token-status', 'Token não encontrado na hash da URL');
                    // Tentar buscar configuração sem token
                    fetch('/capig/autoconfig', {
                        headers: {
                            'Accept': 'application/json'
                        }
                    })
                        .then(r => r.json())
                        .then(data => {
                            safeUpdateElement('result', JSON.stringify(data, null, 2));
                            safeUpdateElement('status', 'Configuração carregada (sem token)');
                        })
                        .catch(e => {
                            safeUpdateElement('status', 'Erro ao carregar configuração: ' + e.message);
                        });
                }
            }
        }

        // Listener para mensagens da Meta (caso ela esteja tentando se comunicar)
        window.addEventListener('message', function(event) {
            console.log('Mensagem recebida:', event.data, 'de:', event.origin);
            // Se a Meta estiver pedindo a configuração
            if (event.data && event.data.type === 'get_capig_config') {
                const token = extractTokenFromHash();
                if (token) {
                    sendTokenToBackend(token);
                }
            }
        });

        // Executar quando DOM estiver pronto
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            // DOM já está pronto
            init();
        }
    </script>
</head>
<body>
    <h1>Meta Conversions API Gateway - Autoconfig</h1>
    <p id="token-status">Processando...</p>
    <p id="status">Aguardando token...</p>
    <pre id="result"></pre>
</body>
</html>
            """
            response = Response(html_template)
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            return _add_cors_headers(response)

        # Log para debug
        print("[META_GATEWAY] Autoconfig chamado")
        print(f"[META_GATEWAY] Method: {request.method}")
        print(f"[META_GATEWAY] Token presente: {bool(token)}")
        print(f"[META_GATEWAY] Accept: {request.headers.get('Accept', '')}")
        print(f"[META_GATEWAY] User-Agent: {request.headers.get('User-Agent', '')[:100]}")
        print(f"[META_GATEWAY] Is AJAX: {is_ajax}")
        print(f"[META_GATEWAY] Accepts JSON: {accepts_json}")
        print(f"[META_GATEWAY] Request path: {request.path}")
        print(f"[META_GATEWAY] Request args: {dict(request.args)}")

        # Verificar se o Gateway está configurado
        pixel_id = os.environ.get("META_PIXEL_ID", "")
        access_token = os.environ.get("META_CAPI_ACCESS_TOKEN", "")

        if not pixel_id or not access_token:
            response = jsonify(
                {
                    "error": "Meta CAPI não configurado",
                    "message": "META_PIXEL_ID e META_CAPI_ACCESS_TOKEN devem estar configurados",
                }
            )
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return _add_cors_headers(response), 500

        # Retornar configuração
        # A Meta espera um JSON com informações de configuração
        config = {
            "pixel_id": pixel_id,
            "api_version": os.environ.get("META_CAPI_API_VERSION", "v21.0"),
            "status": "configured",
            "endpoint": f"/meta-gateway/{pixel_id}/events",
            "token_received": bool(token),  # Para debug
        }

        response = jsonify(config)
        # Garantir Content-Type correto para evitar CORB
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        print(f"[META_GATEWAY] Retornando config: {config}")
        return _add_cors_headers(response), 200

    except Exception as e:
        print(f"[META_GATEWAY] Erro: {str(e)}")
        import traceback

        traceback.print_exc()
        response = jsonify({"error": "Erro ao processar autoconfiguração", "message": str(e)})
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return _add_cors_headers(response), 500


@meta_gateway_bp.route("/meta-gateway/<pixel_id>/events", methods=["POST"])
def meta_gateway_events(pixel_id):
    """
    Endpoint do Gateway para receber eventos

    Este endpoint recebe eventos do frontend/outras fontes e os encaminha
    para a Meta via Conversions API.

    Args:
        pixel_id: ID do Pixel (deve corresponder ao configurado)
    """
    try:
        request_host = request.host or ""
        gateway_domain = os.environ.get("META_CAPI_GATEWAY_DOMAIN") or ""
        if gateway_domain and gateway_domain not in request_host:
            print(
                "[META_GATEWAY] AVISO: host nao corresponde ao dominio esperado.",
                {"host": request_host, "expected_domain": gateway_domain},
            )

        print(
            "[META_GATEWAY] Evento recebido",
            {
                "method": request.method,
                "path": request.path,
                "host": request_host,
                "content_length": request.content_length,
                "remote_addr": request.remote_addr,
            },
        )
        # Verificar se pixel_id corresponde ao configurado
        configured_pixel_id = os.environ.get("META_PIXEL_ID", "")
        if pixel_id != configured_pixel_id:
            response = jsonify(
                {
                    "error": "Pixel ID inválido",
                    "message": f"Pixel ID {pixel_id} não corresponde ao configurado",
                }
            )
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return _add_cors_headers(response), 400

        # Obter payload do request
        payload = request.get_json()
        if not payload:
            response = jsonify(
                {"error": "Payload vazio", "message": "É necessário enviar um payload JSON"}
            )
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return _add_cors_headers(response), 400

        # Validar estrutura básica
        if "data" not in payload:
            response = jsonify(
                {"error": "Payload inválido", "message": "Campo 'data' é obrigatório"}
            )
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return _add_cors_headers(response), 400

        # Extrair eventos do payload
        events = payload.get("data", [])
        print(
            "[META_GATEWAY] Payload recebido",
            {"events_count": len(events), "has_test_event_code": "test_event_code" in payload},
        )

        # Enviar para Meta usando integração direta (não Gateway recursivo)
        # O Gateway apenas recebe e valida, depois encaminha diretamente para Meta
        import requests

        pixel_id = os.environ.get("META_PIXEL_ID", "")
        access_token = os.environ.get("META_CAPI_ACCESS_TOKEN", "")
        api_version = os.environ.get("META_CAPI_API_VERSION", "v21.0")

        if not pixel_id or not access_token:
            response = jsonify(
                {
                    "error": "Meta CAPI não configurado",
                    "message": "META_PIXEL_ID e META_CAPI_ACCESS_TOKEN devem estar configurados",
                }
            )
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return _add_cors_headers(response), 500

        # Montar payload para Meta (preservar test_event_code se fornecido)
        meta_payload = {"data": events}
        if "test_event_code" in payload:
            meta_payload["test_event_code"] = payload["test_event_code"]

        # URL direta da Meta (não usar Gateway recursivo)
        meta_url = f"https://graph.facebook.com/{api_version}/{pixel_id}/events"

        # Headers
        headers = {"Content-Type": "application/json"}

        # Query params
        params = {"access_token": access_token}

        try:
            # Enviar diretamente para Meta
            response = requests.post(
                meta_url, json=meta_payload, headers=headers, params=params, timeout=30
            )

            # Parse resposta
            response.raise_for_status()
            result = response.json()
            result["_status_code"] = response.status_code
            print(
                "[META_GATEWAY] Envio para Meta concluido",
                {
                    "status_code": response.status_code,
                    "events_received": result.get("events_received", 0),
                },
            )

            response_json = jsonify(result)
            response_json.headers["Content-Type"] = "application/json; charset=utf-8"
            return _add_cors_headers(response_json), 200

        except requests.exceptions.RequestException as e:
            # Capturar erro
            status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
            error_msg = str(e)

            error_response = {}
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_response = e.response.json()
                except Exception:
                    error_response = {"error": {"message": error_msg}}

            response_json = jsonify(
                {"error": error_msg, "details": error_response, "_status_code": status_code}
            )
            print(
                "[META_GATEWAY] Erro ao enviar para Meta",
                {"status_code": status_code, "error": error_msg},
            )
            response_json.headers["Content-Type"] = "application/json; charset=utf-8"
            return _add_cors_headers(response_json), status_code

    except Exception as e:
        response_json = jsonify({"error": "Erro ao processar eventos", "message": str(e)})
        response_json.headers["Content-Type"] = "application/json; charset=utf-8"
        return _add_cors_headers(response_json), 500


@meta_gateway_bp.route("/meta-gateway/<pixel_id>/events", methods=["GET"])
def meta_gateway_events_get(pixel_id):
    """
    Endpoint GET para verificação de saúde do Gateway
    """
    configured_pixel_id = os.environ.get("META_PIXEL_ID", "")
    if pixel_id != configured_pixel_id:
        response = jsonify({"error": "Pixel ID inválido"})
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return _add_cors_headers(response), 400

    response_json = jsonify({"status": "ok", "pixel_id": pixel_id, "gateway": "active"})
    response_json.headers["Content-Type"] = "application/json; charset=utf-8"
    return _add_cors_headers(response_json), 200


@meta_gateway_bp.route("/meta-gateway/<pixel_id>/health", methods=["GET"])
def meta_gateway_health(pixel_id):
    """
    Endpoint GET para verificação de saúde detalhada do Gateway
    """
    configured_pixel_id = os.environ.get("META_PIXEL_ID", "")
    if pixel_id != configured_pixel_id:
        response = jsonify({"error": "Pixel ID inválido"})
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return _add_cors_headers(response), 400

    gateway_domain = os.environ.get("META_CAPI_GATEWAY_DOMAIN") or ""
    response_json = jsonify(
        {
            "status": "ok",
            "pixel_id": pixel_id,
            "gateway": "active",
            "host": request.host,
            "expected_domain": gateway_domain,
        }
    )
    response_json.headers["Content-Type"] = "application/json; charset=utf-8"
    return _add_cors_headers(response_json), 200
