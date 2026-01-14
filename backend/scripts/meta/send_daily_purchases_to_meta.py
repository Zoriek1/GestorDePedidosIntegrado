# -*- coding: utf-8 -*-
"""
Script diário para enviar compras para Meta Conversions API
Executado via Windows Task Scheduler
"""
import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Carregar variáveis de ambiente do arquivo .env ANTES de importar app
from dotenv import load_dotenv

env_path = backend_dir / ".env"
load_dotenv(env_path)

from app import create_app
from app.commands.send_daily_purchases_to_meta_command import SendDailyPurchasesToMetaCommand


def main():
    """Função principal do script"""
    # Inicializar Flask app context
    app = create_app()

    with app.app_context():
        try:
            print("=" * 60)
            print("META CAPI - Envio Diário de Compras")
            print("=" * 60)

            # Executar command
            command = SendDailyPurchasesToMetaCommand()
            result = command.execute()

            # Verificar se houve erros críticos
            if result.get("errors"):
                print(f"\n[AVISO] {len(result['errors'])} erro(s) encontrado(s):")
                for error in result["errors"]:
                    print(f"  - {error}")

            # Exit code baseado no resultado
            if result.get("sent_failed", 0) > 0 and result.get("sent_success", 0) == 0:
                # Falhou tudo
                print("\n[ERRO] Todos os envios falharam")
                sys.exit(1)
            elif result.get("errors") and len(result["errors"]) > 5:
                # Muitos erros
                print("\n[ERRO] Muitos erros encontrados")
                sys.exit(1)
            else:
                # Sucesso (ou falhas parciais aceitáveis)
                print("\n[SUCCESS] Processamento concluído")
                sys.exit(0)

        except Exception as e:
            print(f"\n[ERRO FATAL] {str(e)}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
