# -*- coding: utf-8 -*-
"""
Script para verificar se as configurações do Meta CAPI estão corretas
"""
import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Carregar variáveis de ambiente do arquivo .env ANTES de importar app
from dotenv import load_dotenv

env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    print(f"[AVISO] Arquivo .env não encontrado em: {env_path}")

from app import create_app
from app.services.meta_capi import MetaConversionsApiService

app = create_app()

with app.app_context():
    print("=" * 60)
    print("VERIFICAÇÃO DE CONFIGURAÇÃO META CAPI")
    print("=" * 60)
    print()
    
    service = MetaConversionsApiService()
    
    # Verificar cada variável
    configs = {
        "META_PIXEL_ID": service.pixel_id,
        "META_CAPI_ACCESS_TOKEN": service.access_token,
        "META_CAPI_API_VERSION": service.api_version,
        "META_TEST_EVENT_CODE": service.test_event_code,
        "META_CAPI_USE_GATEWAY": service.use_gateway,
        "META_CAPI_GATEWAY_DOMAIN": service.gateway_domain,
        "META_CAPI_GATEWAY_ENDPOINT": service.gateway_endpoint,
    }
    
    print("📋 Configurações encontradas:")
    print("-" * 60)
    
    all_ok = True
    
    for key, value in configs.items():
        if key == "META_PIXEL_ID":
            if value:
                # Mostrar apenas últimos 4 dígitos por segurança
                masked = "***" + value[-4:] if len(value) > 4 else "***"
                print(f"✅ {key}: {masked}")
            else:
                print(f"❌ {key}: NÃO CONFIGURADO")
                all_ok = False
        elif key == "META_CAPI_ACCESS_TOKEN":
            if value:
                # Mostrar apenas primeiros e últimos caracteres por segurança
                masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                print(f"✅ {key}: {masked}")
            else:
                print(f"❌ {key}: NÃO CONFIGURADO")
                all_ok = False
        elif key == "META_CAPI_API_VERSION":
            print(f"ℹ️  {key}: {value} (padrão: v21.0)")
        elif key == "META_TEST_EVENT_CODE":
            if value:
                print(f"ℹ️  {key}: *** (modo teste ativo)")
            else:
                print(f"ℹ️  {key}: Não configurado (modo produção)")
        elif key == "META_CAPI_USE_GATEWAY":
            if value:
                print(f"✅ {key}: Ativado (usando Gateway)")
            else:
                print(f"ℹ️  {key}: Desativado (integração direta)")
        elif key == "META_CAPI_GATEWAY_DOMAIN":
            print(f"ℹ️  {key}: {value}")
        elif key == "META_CAPI_GATEWAY_ENDPOINT":
            if value:
                print(f"ℹ️  {key}: {value[:50]}... (endpoint customizado)")
            else:
                print(f"ℹ️  {key}: Não configurado (usará endpoint padrão)")
    
    print()
    print("=" * 60)
    
    if all_ok:
        print("✅ Todas as configurações obrigatórias estão presentes!")
        print()
        if service.use_gateway:
            print("🌐 Gateway ativado - eventos serão enviados via Gateway")
            if service.gateway_endpoint:
                endpoint = service.gateway_endpoint
            else:
                endpoint = f"https://{service.gateway_domain}/meta-gateway/{service.pixel_id}/events"
            print(f"   Endpoint: {endpoint}")
        else:
            print("🔗 Integração direta - eventos serão enviados diretamente para Meta")
            endpoint = f"https://graph.facebook.com/{service.api_version}/{service.pixel_id}/events"
            print(f"   Endpoint: {endpoint}")
        print()
        print("📝 Próximos passos:")
        print("   1. Execute: python backend/scripts/meta/send_daily_purchases_to_meta.py")
        print("   2. Verifique: python backend/scripts/meta/verificar_outbox.py")
    else:
        print("❌ Configurações obrigatórias faltando!")
        print()
        print("📝 Adicione no arquivo backend/.env:")
        if not service.pixel_id:
            print("   META_PIXEL_ID=seu_pixel_id_aqui")
        if not service.access_token:
            print("   META_CAPI_ACCESS_TOKEN=seu_access_token_aqui")
        print()
        print("💡 Dica: Reinicie o servidor após adicionar as variáveis")
