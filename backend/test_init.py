# -*- coding: utf-8 -*-
"""
Teste rapido de inicializacao da aplicacao
"""
import sys
from pathlib import Path

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("TESTE DE INICIALIZACAO")
print("=" * 60)
print()

try:
    print("[1/4] Importando modulos...")
    from app import create_app
    print("  [OK] Modulos importados")

    print()
    print("[2/4] Criando aplicacao Flask...")
    app = create_app()
    print("  [OK] Aplicacao criada")

    print()
    print("[3/4] Verificando rotas...")
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    print(f"  [OK] {len(routes)} rotas registradas")
    print(f"  -> Exemplos: {routes[:5]}")

    print()
    print("[4/4] Verificando frontend...")
    frontend_dir = Path(__file__).parent.parent / 'frontend_v2' / 'dist'
    print(f"  -> Caminho: {frontend_dir}")
    print(f"  -> Existe: {frontend_dir.exists()}")
    if frontend_dir.exists():
        index_file = frontend_dir / 'index.html'
        print(f"  -> index.html existe: {index_file.exists()}")

    print()
    print("=" * 60)
    print("[OK] INICIALIZACAO OK!")
    print("=" * 60)
    print()
    print("A aplicacao esta pronta para rodar com Waitress.")

except Exception as e:
    print()
    print("=" * 60)
    print("[ERRO] ERRO NA INICIALIZACAO")
    print("=" * 60)
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
