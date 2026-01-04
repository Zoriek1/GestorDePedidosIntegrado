# -*- coding: utf-8 -*-
"""
Script de Teste: GraphHopper API
Testa se a API está funcionando corretamente
"""
import os
import sys
from pathlib import Path

# Carregar variáveis de ambiente
from dotenv import load_dotenv

env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from app.services.graphhopper import graphhopper_service  # noqa: E402


def testar_rota_simples():
    """Testa cálculo de rota simples"""
    print("\n" + "="*60)
    print("TESTE 1: Rota Simples")
    print("="*60)

    # Coordenadas de teste em Goiânia
    origem = (-16.6869, -49.2648)  # Centro de Goiânia
    destino = (-16.6941, -49.2587)  # Setor Sul

    print(f"Origem:  {origem}")
    print(f"Destino: {destino}")

    resultado = graphhopper_service.calcular_rota(origem, destino)

    if resultado:
        print("\n✅ SUCESSO!")
        print(f"   Distância: {resultado['distancia_km']} km")
        print(f"   Duração:   {resultado['duracao_min']} min")
    else:
        print("\n❌ FALHOU!")
        print("   Verifique a chave da API no .env")

    return resultado is not None

def testar_rota_otimizada():
    """Testa cálculo de rota otimizada com múltiplos pontos"""
    print("\n" + "="*60)
    print("TESTE 2: Rota Otimizada (3 waypoints)")
    print("="*60)

    origem = (-16.6869, -49.2648)
    waypoints = [
        (-16.6941, -49.2587),  # Setor Sul
        (-16.7000, -49.2700),  # Ponto 2
        (-16.6800, -49.2600)   # Ponto 3
    ]

    print(f"Origem:    {origem}")
    print(f"Waypoints: {len(waypoints)} pontos")

    resultado = graphhopper_service.calcular_rota_otimizada(
        origem, waypoints, retornar_origem=True
    )

    if resultado:
        print("\n✅ SUCESSO!")
        print(f"   Distância Total: {resultado['distancia_total_km']} km")
        print(f"   Duração Total:   {resultado['duracao_total_min']} min")
        print(f"   Método:          {resultado.get('metodo', 'N/A')}")
        print(f"   Sequência:       {len(resultado.get('sequencia_otimizada', []))} pontos")
    else:
        print("\n❌ FALHOU!")
        print("   Verifique a chave da API no .env")

    return resultado is not None

def main():
    print("\n" + "="*60)
    print("TESTE: GraphHopper API")
    print("="*60)

    # Verificar se a API key está configurada
    api_key = os.environ.get('GRAPHHOPPER_API_KEY', '')

    if not api_key:
        print("\n❌ ERRO: GRAPHHOPPER_API_KEY não configurada!")
        print("   Configure no arquivo: backend/.env")
        return False

    print(f"\n✓ API Key configurada: {api_key[:20]}...")

    # Executar testes
    teste1 = testar_rota_simples()
    teste2 = testar_rota_otimizada()

    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    print(f"Rota Simples:    {'✅ PASSOU' if teste1 else '❌ FALHOU'}")
    print(f"Rota Otimizada:  {'✅ PASSOU' if teste2 else '❌ FALHOU'}")

    if teste1 and teste2:
        print("\n🎉 Todos os testes passaram!")
        print("   O sistema está pronto para calcular rotas otimizadas.")
        return True
    else:
        print("\n⚠️ Alguns testes falharam!")
        print("   Verifique os erros acima.")
        return False

if __name__ == '__main__':
    sucesso = main()
    sys.exit(0 if sucesso else 1)

