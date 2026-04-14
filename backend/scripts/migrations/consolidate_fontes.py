# -*- coding: utf-8 -*-
"""
Migration: Consolidar fontes de pedido com nomes por vendedor → canal base

Problema: o sistema antigo criava fontes como "WhatsApp Caio", "WhatsApp Paula"
em vez de usar uma fonte única "WhatsApp" com o vendedor rastreado via vendedor_id.

Isso impede o disparo de comissões porque o mapeamento de commission_config usa
source="whatsapp", mas map_fonte_to_source("WhatsApp Caio") retorna "whatsapp_caio".

Solução:
  1. Detectar fontes que são variantes de um canal base (ex: "WhatsApp Caio" → "WhatsApp")
  2. Criar (ou reutilizar) a fonte base se não existir
  3. Redirecionar todos os pedidos da variante para a fonte base
  4. Desativar a fonte variante (soft delete)

Uso:
  python scripts/migrations/consolidate_fontes.py --dry-run   # apenas mostra o que faria
  python scripts/migrations/consolidate_fontes.py             # executa a migração
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app import create_app, db  # noqa: E402
from app.models.fonte_pedido import FontePedido  # noqa: E402
from app.models.pedido import Pedido  # noqa: E402

# Canais base reconhecidos (ordem importa: mais longo primeiro)
BASE_CHANNELS = [
    "WhatsApp",
    "Instagram",
    "Facebook",
    "Site",
    "Balcão",
    "Indicação",
    "Indicacao",
    "TikTok",
]


def detect_base_channel(nome: str) -> str | None:
    """
    Retorna o canal base se o nome for uma variante (ex: "WhatsApp Caio" → "WhatsApp").
    Retorna None se o nome já for um canal base ou não reconhecido.
    """
    nome_lower = nome.lower().strip()
    for canal in BASE_CHANNELS:
        canal_lower = canal.lower()
        if nome_lower == canal_lower:
            return None  # já é o canal base
        if nome_lower.startswith(canal_lower + " ") or nome_lower.startswith(canal_lower + "_"):
            return canal
    return None


def consolidate(dry_run: bool = True):
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print(f"CONSOLIDAR FONTES {'(DRY-RUN)' if dry_run else '(EXECUTANDO)'}")
        print("=" * 60)

        fontes = FontePedido.query.filter_by(ativo=True).order_by(FontePedido.nome).all()
        print(f"\nTotal de fontes ativas: {len(fontes)}\n")

        grupos: dict[str, list[FontePedido]] = {}
        for fonte in fontes:
            base = detect_base_channel(fonte.nome)
            if base:
                grupos.setdefault(base, []).append(fonte)

        if not grupos:
            print("Nenhuma fonte variante detectada. Nada a fazer.")
            return

        total_pedidos_migrados = 0

        for canal_base, variantes in grupos.items():
            print(f"\nCanal base: {canal_base!r}")

            # Buscar ou planejar criação da fonte base
            fonte_base = FontePedido.query.filter(
                db.func.lower(FontePedido.nome) == canal_base.lower(),
                FontePedido.ativo == True,  # noqa: E712
            ).first()

            if fonte_base:
                print(f"  Fonte base existente: id={fonte_base.id!r}")
            else:
                print(f"  Fonte base NÃO existe — será criada: {canal_base!r}")
                if not dry_run:
                    fonte_base = FontePedido(nome=canal_base, ativo=True)
                    db.session.add(fonte_base)
                    db.session.flush()
                    print(f"  Criada com id={fonte_base.id}")

            for variante in variantes:
                count = Pedido.query.filter_by(fonte_pedido_id=variante.id).count()
                print(f"  Variante {variante.nome!r} (id={variante.id}): {count} pedidos")

                if not dry_run and fonte_base:
                    if count > 0:
                        Pedido.query.filter_by(fonte_pedido_id=variante.id).update(
                            {"fonte_pedido_id": fonte_base.id}
                        )
                        total_pedidos_migrados += count
                    variante.ativo = False
                    print(f"    → Pedidos redirecionados para {canal_base!r}, fonte desativada")
                else:
                    total_pedidos_migrados += count
                    print(f"    → (dry-run) seriam redirecionados para {canal_base!r}")

        if not dry_run:
            db.session.commit()
            print(f"\n✓ Migração concluída. {total_pedidos_migrados} pedidos redirecionados.")
        else:
            print(f"\n(dry-run) {total_pedidos_migrados} pedidos seriam migrados.")
            print("Execute sem --dry-run para aplicar as alterações.")

        print("\nFontes ativas após migração:")
        fontes_ativas = FontePedido.query.filter_by(ativo=True).order_by(FontePedido.nome).all()
        for f in fontes_ativas:
            print(f"  id={f.id:3d}  {f.nome}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    consolidate(dry_run=dry_run)
