# -*- coding: utf-8 -*-
"""
Script para testar envio via Meta CAPI Gateway e envio direto
"""
import hashlib
import sys
import time
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


def hash_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_test_event() -> dict:
    event_time = int(time.time())
    return {
        "event_name": "Purchase",
        "event_time": event_time,
        "event_id": f"diagnostic_{event_time}",
        "action_source": "website",
        "user_data": {
            "external_id": [hash_sha256("diagnostic")],
        },
        "custom_data": {
            "value": 0.01,
            "currency": "BRL",
            "order_id": f"diagnostic_{event_time}",
        },
    }


def send_request(url: str, payload: dict, headers: dict, params: dict) -> dict:
    try:
        response = requests.post(url, json=payload, headers=headers, params=params, timeout=30)
        return {"ok": True, "status_code": response.status_code, "body": response.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("TESTE META CAPI GATEWAY")
        print("=" * 60)
        print()

        service = MetaConversionsApiService()

        if not service.pixel_id or not service.access_token:
            print("[ERRO] META_PIXEL_ID ou META_CAPI_ACCESS_TOKEN nao configurados.")
            sys.exit(1)

        if not service.test_event_code:
            print("[AVISO] META_TEST_EVENT_CODE nao configurado.")
            print("Configure o test_event_code para evitar enviar eventos reais.")
            sys.exit(1)

        event = build_test_event()
        payload = {"data": [event], "test_event_code": service.test_event_code}

        print("ENVIANDO VIA GATEWAY (se ativo)...")
        if service.use_gateway:
            gateway_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {service.access_token}",
            }
            gateway_result = send_request(service.base_url, payload, gateway_headers, {})
            print(f"- URL: {service.base_url}")
            print(f"- Resultado: {gateway_result}")
        else:
            print("- Gateway desativado. Ignorando envio via gateway.")

        print()
        print("ENVIANDO DIRETAMENTE PARA META...")
        direct_url = f"https://graph.facebook.com/{service.api_version}/{service.pixel_id}/events"
        direct_headers = {"Content-Type": "application/json"}
        direct_params = {"access_token": service.access_token}
        direct_result = send_request(direct_url, payload, direct_headers, direct_params)
        print(f"- URL: {direct_url}")
        print(f"- Resultado: {direct_result}")


if __name__ == "__main__":
    main()
