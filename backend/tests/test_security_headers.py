# -*- coding: utf-8 -*-
"""Headers de segurança: fonte única em app/static.py, aplicada via after_request.

Houve uma regressão em que um segundo after_request (no factory) sobrescrevia a
CSP e derrubava a allowlist do Google Maps/Fonts, quebrando o autocomplete de
endereço no build de produção. Os testes abaixo travam esse contrato.
"""


def _csp(response) -> str:
    return response.headers.get("Content-Security-Policy", "")


def test_api_responses_carry_security_headers(client):
    """Antes, /api/* não recebia header nenhum: add_security_headers só era
    chamado dentro das rotas estáticas."""
    response = client.get("/api/config/integrations")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "Permissions-Policy" in response.headers
    assert _csp(response)


def test_csp_keeps_google_maps_and_fonts_allowlist(client):
    """O autocomplete de endereço e as fontes dependem destas origens."""
    csp = _csp(client.get("/api/config/integrations"))

    assert "https://maps.googleapis.com" in csp
    assert "https://fonts.googleapis.com" in csp
    assert "https://fonts.gstatic.com" in csp
    assert "worker-src 'self' blob:" in csp


def test_csp_has_hardening_directives(client):
    csp = _csp(client.get("/api/config/integrations"))

    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp
    assert "base-uri 'self'" in csp


def test_security_headers_registered_only_once(app):
    """Dois after_request setando CSP = o último vence silenciosamente."""
    from app.static import add_security_headers

    hooks = app.after_request_funcs.get(None, [])
    assert hooks.count(add_security_headers) == 1
