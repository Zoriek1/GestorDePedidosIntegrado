# -*- coding: utf-8 -*-
"""
Teste simples do Waitress para diagnosticar problema
"""
import sys

from flask import Flask

# Criar app simples
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/test')
def test():
    return 'Test OK'

if __name__ == '__main__':
    print("=" * 60, flush=True)
    print("TESTE SIMPLES DO WAITRESS", flush=True)
    print("=" * 60, flush=True)
    print("Criando servidor Waitress...", flush=True)

    try:
        from waitress import serve
        print("Waitress importado com sucesso", flush=True)
        print("Iniciando servidor em 0.0.0.0:5001...", flush=True)
        print("Acesse: http://localhost:5001/", flush=True)
        print("Acesse: http://localhost:5001/test", flush=True)
        print("=" * 60, flush=True)
        sys.stdout.flush()

        serve(app, host='0.0.0.0', port=5001, threads=4)
    except KeyboardInterrupt:
        print("\nServidor parado pelo usuário", flush=True)
    except Exception as e:
        print(f"\nERRO: {e}", flush=True)
        import traceback
        traceback.print_exc()
