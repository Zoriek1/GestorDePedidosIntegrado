# -*- coding: utf-8 -*-
"""
Script para diagnosticar configuração do Meta CAPI Gateway
"""
import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Carregar variáveis de ambiente
from dotenv import load_dotenv

env_path = backend_dir / ".env"
load_dotenv(env_path, override=True)

import requests

from app import create_app
from app.services.meta_capi import MetaConversionsApiService


def mask_value(value: str, head: int = 4, tail: int = 4) -> str:
    if not value:
        return "N/A"
    if len(value) <= head + tail:
        return "***"
    return f"{value[:head]}...{value[-tail:]}"


def http_probe(url: str) -> dict:
    try:
        response = requests.get(url, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        text_preview = response.text[:200].replace("\n", " ").strip()
        return {
            "ok": True,
            "status_code": response.status_code,
            "content_type": content_type,
            "preview": text_preview,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("DIAGNOSTICO META CAPI GATEWAY")
        print("=" * 60)
        print()

        service = MetaConversionsApiService()

        print("CONFIGURACOES:")
        print(f"- META_PIXEL_ID: {mask_value(service.pixel_id)}")
        print(f"- META_CAPI_ACCESS_TOKEN: {mask_value(service.access_token)}")
        print(f"- META_CAPI_API_VERSION: {service.api_version}")
        print(f"- META_TEST_EVENT_CODE: {'ATIVO' if service.test_event_code else 'DESATIVADO'}")
        print(f"- META_CAPI_USE_GATEWAY: {service.use_gateway}")
        print(f"- META_CAPI_GATEWAY_DOMAIN: {service.gateway_domain}")
        print(f"- META_CAPI_GATEWAY_ENDPOINT: {service.gateway_endpoint or 'N/A'}")
        print(f"- BASE_URL_CALCULADA: {service.base_url}")
        print()

        if service.use_gateway:
            domain = service.gateway_domain
            pixel_id = service.pixel_id or "PIXEL_NAO_CONFIGURADO"
            autoconfig_url = f"https://{domain}/capig/autoconfig"
            events_url = f"https://{domain}/meta-gateway/{pixel_id}/events"

            print("TESTE DE CONECTIVIDADE (GATEWAY):")
            print(f"- AUTOCONFIG: {autoconfig_url}")
            autoconfig_result = http_probe(autoconfig_url)
            print(f"  Resultado: {autoconfig_result}")
            print(f"- EVENTS (GET): {events_url}")
            events_result = http_probe(events_url)
            print(f"  Resultado: {events_result}")
        else:
            print("GATEWAY DESATIVADO - INTEGRACAO DIRETA COM META")
            if service.pixel_id:
                direct_url = (
                    f"https://graph.facebook.com/{service.api_version}/{service.pixel_id}/events"
                )
                print(f"- URL DIRETA: {direct_url}")

        print()
        print("DICA:")
        print("- Se a BASE_URL_CALCULADA nao esta no dominio esperado,")
        print("  verifique META_CAPI_GATEWAY_ENDPOINT e META_CAPI_GATEWAY_DOMAIN no .env.")


if __name__ == "__main__":
    main()
