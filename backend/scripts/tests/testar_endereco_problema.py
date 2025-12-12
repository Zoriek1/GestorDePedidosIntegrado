# -*- coding: utf-8 -*-
"""
Script de Teste: Endereço Problemático
Testa geocodificação de endereços com problemas comuns
"""
import os
import sys
from pathlib import Path

# Configurar encoding UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Carregar variáveis de ambiente
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from app.services.distancia import distancia_service

def testar_endereco(endereco_original, pedido_id=None):
    """Testa geocodificação de um endereço"""
    print(f"\n{'='*80}")
    print(f"TESTE: Pedido {pedido_id if pedido_id else '?'}")
    print(f"{'='*80}")
    print(f"Endereço original:")
    print(f"  {endereco_original}")
    
    # Limpar endereço
    endereco_limpo = distancia_service.limpar_endereco(endereco_original)
    print(f"\nEndereço limpo:")
    print(f"  {endereco_limpo}")
    
    # Tentar geocodificar
    print(f"\nTentando geocodificar...")
    coords = distancia_service.geocodificar(endereco_limpo, normalizar=False)
    
    if coords:
        print(f"\n✅ SUCESSO!")
        print(f"   Coordenadas: lon={coords[0]}, lat={coords[1]}")
        print(f"   Google Maps: https://www.google.com/maps?q={coords[1]},{coords[0]}")
        
        # Tentar calcular distância
        origem = distancia_service.coords_floricultura
        if origem:
            print(f"\n   Calculando distância da floricultura...")
            resultado = distancia_service.calcular_distancia(origem, coords)
            if resultado:
                print(f"   Distância: {resultado['distancia_km']} km")
                print(f"   Duração: {resultado['duracao_min']} min")
                print(f"   Método: {resultado.get('metodo', 'N/A')}")
            else:
                print(f"   ⚠️ Não foi possível calcular distância")
        
        return True
    else:
        print(f"\n❌ FALHOU!")
        print(f"   Não foi possível geocodificar o endereço")
        print(f"\n💡 Dicas:")
        print(f"   - Verifique se o endereço está correto")
        print(f"   - Tente com endereço mais simples: Rua + Bairro + Cidade")
        print(f"   - Remova complementos como 'Residencial', 'Condomínio', etc")
        return False

def main():
    print("\n" + "="*80)
    print("TESTE: Endereços Problemáticos")
    print("="*80)
    
    # Endereços de teste
    enderecos_teste = [
        {
            'id': 69,
            'endereco': 'Rua Doutor João de Abreu, 0 -Capuava Residencial Privê - Goiânia - CEP: 74445-302'
        },
        {
            'id': 'teste1',
            'endereco': 'Rua Doutor João de Abreu, Capuava, Goiânia, GO'
        },
        {
            'id': 'teste2',
            'endereco': 'Rua Doutor João de Abreu, 74445-302, Goiânia'
        }
    ]
    
    resultados = []
    for teste in enderecos_teste:
        sucesso = testar_endereco(teste['endereco'], teste['id'])
        resultados.append({
            'id': teste['id'],
            'sucesso': sucesso
        })
    
    # Resumo
    print(f"\n{'='*80}")
    print("RESUMO DOS TESTES")
    print(f"{'='*80}")
    
    for resultado in resultados:
        status = '✅ PASSOU' if resultado['sucesso'] else '❌ FALHOU'
        print(f"Pedido {resultado['id']}: {status}")
    
    sucessos = sum(1 for r in resultados if r['sucesso'])
    total = len(resultados)
    
    print(f"\n{sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("\n🎉 Todos os testes passaram!")
        return True
    else:
        print("\n⚠️ Alguns testes falharam!")
        return False

if __name__ == '__main__':
    sucesso = main()
    sys.exit(0 if sucesso else 1)

