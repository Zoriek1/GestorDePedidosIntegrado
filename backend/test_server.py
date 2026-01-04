# -*- coding: utf-8 -*-
"""
Script de teste rápido para verificar se o servidor está respondendo
"""
import sys
import time

import requests


def test_server():
    """Testa se o servidor está respondendo"""
    base_url = "http://localhost:5000"

    print("=" * 60)
    print("TESTE DE SERVIDOR")
    print("=" * 60)
    print()

    # Teste 1: Health check
    print("[1/3] Testando /api/health...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"  ✓ Status: {response.status_code}")
        print(f"  ✓ Resposta: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("  ✗ ERRO: Não foi possível conectar ao servidor")
        print("  → O servidor pode não estar rodando ou não está escutando na porta 5000")
        return False
    except requests.exceptions.Timeout:
        print("  ✗ ERRO: Timeout - servidor não respondeu em 5 segundos")
        return False
    except Exception as e:
        print(f"  ✗ ERRO: {e}")
        return False

    # Teste 2: Frontend root
    print()
    print("[2/3] Testando / (frontend)...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"  ✓ Status: {response.status_code}")
        print(f"  ✓ Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        if 'text/html' in response.headers.get('Content-Type', ''):
            print("  ✓ Retornou HTML (correto)")
        else:
            print("  ⚠ Retornou algo diferente de HTML")
    except Exception as e:
        print(f"  ✗ ERRO: {e}")
        return False

    # Teste 3: Deep link
    print()
    print("[3/3] Testando /pedidos (deep link)...")
    try:
        response = requests.get(f"{base_url}/pedidos", timeout=5)
        print(f"  ✓ Status: {response.status_code}")
        if response.status_code == 200:
            print("  ✓ Deep link funcionando (correto)")
        else:
            print(f"  ⚠ Status inesperado: {response.status_code}")
    except Exception as e:
        print(f"  ✗ ERRO: {e}")
        return False

    print()
    print("=" * 60)
    print("✓ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    print("Aguardando 2 segundos para o servidor inicializar...")
    time.sleep(2)

    if not test_server():
        print()
        print("=" * 60)
        print("ERRO: Servidor não está respondendo corretamente")
        print("=" * 60)
        print()
        print("Verifique:")
        print("  1. O servidor está rodando? (python wsgi.py)")
        print("  2. A porta 5000 está livre?")
        print("  3. Há erros no console do servidor?")
        sys.exit(1)
