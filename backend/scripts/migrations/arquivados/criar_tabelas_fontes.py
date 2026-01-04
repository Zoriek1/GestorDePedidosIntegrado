# -*- coding: utf-8 -*-
"""
Script de migração para criar tabelas separadas por fonte de pedido
Este script:
1. Lista todas as fontes ativas em fontes_pedido
2. Para cada fonte, cria tabela pedidos_{nome_normalizado}
3. Popula tabelas com pedidos existentes que já têm fonte_pedido_id
4. Gera numeração sequencial baseada na data de criação
"""
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models.fonte_pedido import FontePedido  # noqa: E402
from app.models.pedido import Pedido  # noqa: E402
from app.models.pedido_fonte import PedidoFonte  # noqa: E402
from app.utils.fonte_helper import criar_tabela_fonte, get_tabela_fonte  # noqa: E402


def criar_tabelas_fontes():
    """Executa migração completa de tabelas por fonte"""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 60)
            print("Migração: Criar tabelas separadas por fonte de pedido")
            print("=" * 60)

            # 1. Listar todas as fontes ativas
            print("\n[1/4] Listando fontes ativas...")
            fontes = FontePedido.query.filter_by(ativo=True).all()

            if not fontes:
                print("   ⚠ Nenhuma fonte ativa encontrada!")
                print(
                    "   Execute primeiro: python backend/scripts/migrations/migrate_fonte_pedido.py"
                )
                return False

            print(f"   ✓ {len(fontes)} fonte(s) ativa(s) encontrada(s)")
            for fonte in fontes:
                nome_tabela = get_tabela_fonte(fonte.id)
                print(f"      - {fonte.nome} → {nome_tabela}")

            # 2. Criar tabelas para cada fonte
            print("\n[2/4] Criando tabelas para cada fonte...")
            tabelas_criadas = {}

            for fonte in fontes:
                nome_tabela = get_tabela_fonte(fonte.id)
                if nome_tabela:
                    criada = criar_tabela_fonte(nome_tabela)
                    if criada:
                        print(f"   ✓ Tabela '{nome_tabela}' criada")
                        tabelas_criadas[fonte.id] = nome_tabela
                    else:
                        print(f"   ℹ Tabela '{nome_tabela}' já existe")
                        tabelas_criadas[fonte.id] = nome_tabela

            # 3. Buscar pedidos existentes com fonte_pedido_id
            print("\n[3/4] Buscando pedidos existentes...")
            pedidos = (
                Pedido.query.filter(Pedido.fonte_pedido_id.isnot(None))
                .order_by(Pedido.created_at)
                .all()
            )

            print(f"   ✓ {len(pedidos)} pedido(s) com fonte identificada encontrado(s)")

            # 4. Popular tabelas com pedidos existentes
            print("\n[4/4] Populando tabelas com pedidos existentes...")

            pedidos_por_fonte = {}
            for pedido in pedidos:
                fonte_id = pedido.fonte_pedido_id
                if fonte_id not in pedidos_por_fonte:
                    pedidos_por_fonte[fonte_id] = []
                pedidos_por_fonte[fonte_id].append(pedido)

            total_inseridos = 0
            total_erros = 0

            for fonte_id, lista_pedidos in pedidos_por_fonte.items():
                fonte = FontePedido.query.get(fonte_id)
                nome_tabela = get_tabela_fonte(fonte_id)

                if not nome_tabela:
                    print(f"   ⚠ Não foi possível obter nome da tabela para fonte ID {fonte_id}")
                    continue

                print(f"\n   Processando fonte: {fonte.nome} ({len(lista_pedidos)} pedidos)...")

                # Verificar quantos já existem na tabela
                with db.engine.connect() as conn:
                    result = conn.execute(
                        text(
                            f"""
                        SELECT COUNT(*) FROM {nome_tabela}
                    """
                        )
                    )
                    ja_existem = result.fetchone()[0] or 0

                if ja_existem > 0:
                    print(f"      ℹ {ja_existem} pedido(s) já existem na tabela. Pulando...")
                    continue

                # Inserir pedidos ordenados por data de criação
                inseridos_fonte = 0

                for pedido in lista_pedidos:
                    # Verificar se já existe
                    existe = PedidoFonte.verificar_pedido_na_fonte(pedido.id, fonte_id)
                    if existe:
                        continue

                    # Inserir na tabela da fonte
                    resultado = PedidoFonte.adicionar_pedido(pedido.id, fonte_id, pedido.valor)

                    if resultado:
                        inseridos_fonte += 1
                        total_inseridos += 1
                    else:
                        total_erros += 1

                if inseridos_fonte > 0:
                    print(
                        f"      ✓ {inseridos_fonte} pedido(s) inserido(s) na tabela '{nome_tabela}'"
                    )
                else:
                    print("      ℹ Nenhum pedido novo para inserir")

            # Resumo final
            print("\n" + "=" * 60)
            print("RESUMO DA MIGRAÇÃO")
            print("=" * 60)
            print(f"   Fontes processadas: {len(fontes)}")
            print(f"   Tabelas criadas/verificadas: {len(tabelas_criadas)}")
            print(f"   Pedidos inseridos: {total_inseridos}")
            if total_erros > 0:
                print(f"   ⚠ Erros: {total_erros}")
            print("=" * 60)

            return True

        except Exception as e:
            print(f"\n[ERRO] Erro durante migração: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = criar_tabelas_fontes()
    print("\n" + "=" * 60)
    if success:
        print("✓ Migração concluída com sucesso!")
    else:
        print("✗ Migração falhou. Verifique os erros acima.")
    print("=" * 60)
