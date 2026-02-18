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
            sent_success = result.get("sent_success", 0)
            sent_failed = result.get("sent_failed", 0)
            failed_permanent = result.get("failed_permanent", 0)
            failed_retryable = result.get("failed_retryable", 0)
            errors = result.get("errors", [])

            # Se todos falharam, verificar se são retryable
            if sent_failed > 0 and sent_success == 0:
                if failed_permanent > 0:
                    # Há erros permanentes - falha crítica
                    print(
                        f"\n[ERRO] Todos os envios falharam ({failed_permanent} permanente(s), {failed_retryable} retryable(s))"
                    )
                    sys.exit(1)
                elif failed_retryable > 0:
                    # Todos são retryable - sucesso parcial (será retentado)
                    print(
                        f"\n[AVISO] Todos os envios falharam temporariamente ({failed_retryable} retryable(s))"
                    )
                    print("[INFO] Os eventos serão retentados na próxima execução")
                    sys.exit(0)
                else:
                    # Não há classificação - assumir erro
                    print("\n[ERRO] Todos os envios falharam (tipo desconhecido)")
                    sys.exit(1)
            elif errors and len(errors) > 5:
                # Muitos erros
                print(f"\n[ERRO] Muitos erros encontrados ({len(errors)})")
                sys.exit(1)
            else:
                # Sucesso (ou falhas parciais aceitáveis)
                if sent_success > 0:
                    print(
                        f"\n[SUCCESS] Processamento concluído ({sent_success} enviado(s), {sent_failed} falha(s))"
                    )
                else:
                    print("\n[SUCCESS] Processamento concluído (nenhum evento para enviar)")
                sys.exit(0)

        except Exception as e:
            print(f"\n[ERRO FATAL] {str(e)}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
