#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para testar custom_fields dos pedidos Nuvemshop via API.

Uso:
    python testar_custom_fields.py                    # Lista últimos 10 pedidos
    python testar_custom_fields.py --limit 5          # Lista últimos 5 pedidos
    python testar_custom_fields.py --days 3          # Busca pedidos dos últimos 3 dias
    python testar_custom_fields.py --order-id 123456 # Ver pedido específico
"""
import argparse
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para importar módulos do app
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

import requests
from dotenv import load_dotenv

# Carregar variáveis de ambiente
env_path = backend_dir / ".env"
load_dotenv(env_path)


def get_base_url():
    """Retorna a URL base da API"""
    host = os.environ.get("HOST", "localhost")
    port = os.environ.get("PORT", "5000")
    return f"http://{host}:{port}/api"


def get_auth():
    """Retorna credenciais de autenticação"""
    username = "admin"
    password = os.environ.get("ADMIN_PASSWORD", "plante1998")
    return (username, password)


def test_pedidos_recentes(limit=10, days=1):
    """Testa endpoint de pedidos recentes"""
    base_url = get_base_url()
    auth = get_auth()

    url = f"{base_url}/integrations/nuvemshop/debug/pedidos-recentes"
    params = {"limit": limit, "days": days}

    print(f"\n🔍 Buscando últimos {limit} pedidos dos últimos {days} dia(s)...")
    print(f"URL: {url}")
    print(f"Params: {params}\n")

    try:
        response = requests.get(url, params=params, auth=auth, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data.get("success"):
            print(f"❌ Erro na resposta: {data.get('message', 'Erro desconhecido')}")
            return

        pedidos = data.get("data", {}).get("pedidos", [])
        total = data.get("data", {}).get("total", 0)

        print(f"✅ Encontrados {total} pedido(s)\n")
        print("=" * 80)

        for i, pedido in enumerate(pedidos, 1):
            print(f"\n📦 Pedido #{i}")
            print(f"   Order ID: {pedido.get('order_id')}")
            print(f"   Order Number: {pedido.get('order_number')}")
            print(f"   Criado em: {pedido.get('created_at')}")

            # Custom fields raw
            custom_fields = pedido.get("custom_fields_raw", [])
            if custom_fields:
                print("\n   📋 Custom Fields (raw):")
                for cf in custom_fields:
                    print(f"      - {cf.get('name')}: {cf.get('value')}")
            else:
                print("\n   ⚠️  Nenhum custom_field encontrado")

            # Custom fields extraídos
            extraidos = pedido.get("custom_fields_extraidos", {})
            if extraidos.get("dia_entrega") or extraidos.get("horario"):
                print("\n   ✨ Custom Fields Extraídos:")
                if extraidos.get("dia_entrega"):
                    print(f"      - Data: {extraidos['dia_entrega']}")
                if extraidos.get("horario"):
                    print(f"      - Horário: {extraidos['horario']}")
                if extraidos.get("campo_nome"):
                    print(f"      - Campo: {extraidos['campo_nome']}")

            # Mapeamento
            mapeamento = pedido.get("mapeamento", {})
            print("\n   🗺️  Mapeamento:")
            print(f"      - Dia Entrega: {mapeamento.get('dia_entrega', 'N/A')}")
            print(f"      - Horário: {mapeamento.get('horario', 'N/A')}")
            print(f"      - Fonte: {mapeamento.get('agendamento_source', 'N/A')}")
            print(f"      - Schedule Pending: {mapeamento.get('schedule_pending', 'N/A')}")

            # Status importação
            if pedido.get("ja_importado"):
                print(f"\n   ✅ Já importado (Pedido ID: {pedido.get('pedido_id')})")
            else:
                print("\n   ⏳ Ainda não importado")

            print("-" * 80)

        print("\n✅ Teste concluído!\n")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erro HTTP {e.response.status_code}: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback

        traceback.print_exc()


def test_pedido_especifico(order_id):
    """Testa endpoint de pedido específico"""
    base_url = get_base_url()
    auth = get_auth()

    url = f"{base_url}/integrations/nuvemshop/debug/pedido/{order_id}"

    print(f"\n🔍 Buscando pedido específico: {order_id}")
    print(f"URL: {url}\n")

    try:
        response = requests.get(url, auth=auth, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data.get("success"):
            print(f"❌ Erro na resposta: {data.get('message', 'Erro desconhecido')}")
            return

        pedido = data.get("data", {})

        print("=" * 80)
        print(f"\n📦 Pedido #{pedido.get('order_id')}")
        print(f"   Order Number: {pedido.get('order_number')}")
        print(f"   Criado em: {pedido.get('created_at')}")

        # Custom fields raw
        custom_fields = pedido.get("custom_fields_raw", [])
        if custom_fields:
            print("\n📋 Custom Fields (raw):")
            for cf in custom_fields:
                print(f"   - {cf.get('name')}: {cf.get('value')}")
        else:
            print("\n⚠️  Nenhum custom_field encontrado")

        # Custom fields extraídos
        extraidos = pedido.get("custom_fields_extraidos", {})
        if extraidos.get("dia_entrega") or extraidos.get("horario"):
            print("\n✨ Custom Fields Extraídos:")
            if extraidos.get("dia_entrega"):
                print(f"   - Data: {extraidos['dia_entrega']}")
            if extraidos.get("horario"):
                print(f"   - Horário: {extraidos['horario']}")
            if extraidos.get("campo_nome"):
                print(f"   - Campo: {extraidos['campo_nome']}")

        # Mapeamento completo
        mapeamento = pedido.get("mapeamento", {})
        print("\n🗺️  Mapeamento Completo:")
        print(f"   - Dia Entrega: {mapeamento.get('dia_entrega', 'N/A')}")
        print(f"   - Horário: {mapeamento.get('horario', 'N/A')}")
        print(f"   - Fonte: {mapeamento.get('agendamento_source', 'N/A')}")
        print(f"   - Schedule Pending: {mapeamento.get('schedule_pending', 'N/A')}")
        print(f"   - Shipping Option: {mapeamento.get('shipping_option_text', 'N/A')}")

        # Status importação
        status = pedido.get("status_importacao", {})
        print("\n📊 Status de Importação:")
        print(f"   - Já importado: {status.get('ja_importado', False)}")
        if status.get("pedido_id"):
            print(f"   - Pedido ID local: {status['pedido_id']}")
            print(f"   - Schedule Pending: {status.get('schedule_pending', 'N/A')}")
            print(f"   - Fonte Agendamento: {status.get('agendamento_source', 'N/A')}")

        # Pedido local (se existir)
        pedido_local = pedido.get("pedido_local")
        if pedido_local:
            print("\n💾 Pedido Local:")
            print(f"   - ID: {pedido_local.get('id')}")
            print(f"   - Cliente: {pedido_local.get('cliente')}")
            print(f"   - Destinatário: {pedido_local.get('destinatario')}")
            print(f"   - Dia Entrega: {pedido_local.get('dia_entrega')}")
            print(f"   - Horário: {pedido_local.get('horario')}")
            print(f"   - Produto: {pedido_local.get('produto')}")
            print(f"   - Valor: {pedido_local.get('valor')}")

        # JSON completo (opcional, comentado para não poluir output)
        # print(f"\n📄 JSON Completo:")
        # print(json.dumps(pedido.get('order_json', {}), indent=2, ensure_ascii=False))

        print("\n" + "=" * 80)
        print("\n✅ Teste concluído!\n")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"❌ Pedido {order_id} não encontrado na API Nuvemshop")
        else:
            print(f"❌ Erro HTTP {e.response.status_code}: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback

        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Testa custom_fields dos pedidos Nuvemshop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python testar_custom_fields.py
  python testar_custom_fields.py --limit 5
  python testar_custom_fields.py --days 3
  python testar_custom_fields.py --order-id 123456789
        """,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Número de pedidos a buscar (padrão: 10)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Buscar pedidos dos últimos N dias (padrão: 1)",
    )
    parser.add_argument(
        "--order-id",
        type=str,
        help="ID do pedido específico para visualizar",
    )

    args = parser.parse_args()

    if args.order_id:
        test_pedido_especifico(args.order_id)
    else:
        test_pedidos_recentes(limit=args.limit, days=args.days)


if __name__ == "__main__":
    main()
