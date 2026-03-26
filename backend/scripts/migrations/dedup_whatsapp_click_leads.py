# -*- coding: utf-8 -*-
"""
Migration: desduplicar eventos whatsapp_click por pessoa e janela de 4 horas.

Motivação:
- A mesma pessoa pode ter disparado múltiplos eventos whatsapp_click antes da
  guarda de deduplicação ser implantada no frontend (2026-03-26).
- Regra: dentro de uma janela de 4 horas, manter apenas 1 evento por pessoa.

Identificação de pessoa:
  1. fbp  — cookie do Meta Pixel (estável por navegador, preferido)
  2. token_rastreio — fallback quando fbp está ausente

Critério de qual manter dentro do grupo:
  - Se algum evento tem ``phone`` vinculado → manter o mais antigo com phone.
  - Se nenhum tem phone → manter o mais antigo (primeiro token gerado).
  - Todos os outros do grupo são deletados.

Uso:
  python dedup_whatsapp_click_leads.py           # roda de verdade
  python dedup_whatsapp_click_leads.py --dry-run # apenas simula, não deleta
"""
import sys
from datetime import timedelta
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db
from app.models.lead import Lead

DEDUP_WINDOW = timedelta(hours=4)

app = create_app()


def dedup_whatsapp_click_leads(dry_run: bool = False):
    with app.app_context():
        inspector = db.inspect(db.engine)
        if "leads" not in inspector.get_table_names():
            print("[SKIP] Tabela leads não existe")
            return

        prefix = "[DRY-RUN] " if dry_run else ""

        # ------------------------------------------------------------------
        # 1. Buscar todos os whatsapp_click em ordem cronológica
        # ------------------------------------------------------------------
        leads = (
            db.session.query(Lead)
            .filter(Lead.event == "whatsapp_click")
            .filter(Lead.created_at.isnot(None))
            .order_by(Lead.created_at.asc())
            .all()
        )

        print(f"[INFO] Total de eventos whatsapp_click encontrados: {len(leads)}")

        # ------------------------------------------------------------------
        # 2. Agrupar por (person_key, janela de 4h)
        #    person_key = fbp se disponível, senão token_rastreio
        #    window_start = created_at do primeiro evento do grupo
        # ------------------------------------------------------------------
        # { (person_key, window_start): [Lead, ...] }
        groups: dict[tuple, list] = {}

        skipped_no_id = 0
        for lead in leads:
            person_key = lead.fbp or lead.token_rastreio
            if not person_key:
                skipped_no_id += 1
                continue

            placed = False
            for (pk, window_start), group in groups.items():
                if pk != person_key:
                    continue
                if lead.created_at - window_start <= DEDUP_WINDOW:
                    group.append(lead)
                    placed = True
                    break

            if not placed:
                groups[(person_key, lead.created_at)] = [lead]

        if skipped_no_id:
            print(f"[WARN] {skipped_no_id} eventos sem fbp e sem token_rastreio — ignorados")

        # ------------------------------------------------------------------
        # 3. Determinar quais deletar em cada grupo com duplicatas
        # ------------------------------------------------------------------
        ids_to_delete: list[int] = []
        groups_with_dupes = 0

        for (person_key, _), group in groups.items():
            if len(group) <= 1:
                continue

            groups_with_dupes += 1
            label = person_key[:16] + ("..." if len(person_key) > 16 else "")

            with_phone = [row for row in group if row.phone]

            if with_phone:
                keep = with_phone[0]   # mais antigo com phone vinculado
                to_delete = [row for row in group if row.id != keep.id]
                print(
                    f"  {prefix}[PHONE] {label}: {len(group)} eventos "
                    f"→ manter id={keep.id} phone={keep.phone} "
                    f"| deletar ids={[row.id for row in to_delete]}"
                )
            else:
                keep = group[0]        # mais antigo (primeiro token gerado)
                to_delete = group[1:]
                print(
                    f"  {prefix}[TOKEN] {label}: {len(group)} eventos "
                    f"→ manter id={keep.id} token={keep.token_rastreio} "
                    f"| deletar ids={[row.id for row in to_delete]}"
                )

            ids_to_delete.extend(row.id for row in to_delete)

        # ------------------------------------------------------------------
        # 4. Relatório e execução
        # ------------------------------------------------------------------
        print(f"\n[INFO] Grupos com duplicatas: {groups_with_dupes}")
        print(f"[INFO] Registros a deletar:    {len(ids_to_delete)}")

        if not ids_to_delete:
            print("[OK] Nenhuma duplicata encontrada. Nada a fazer.")
            return

        if dry_run:
            print("[DRY-RUN] Nenhum registro foi deletado. Rode sem --dry-run para aplicar.")
            return

        try:
            deleted = (
                db.session.query(Lead)
                .filter(Lead.id.in_(ids_to_delete))
                .delete(synchronize_session=False)
            )
            db.session.commit()
            print(f"[OK] {deleted} registros duplicados deletados com sucesso.")
        except Exception as e:
            db.session.rollback()
            print(f"[ERRO] Falha ao deletar duplicatas: {e}")
            raise


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    dedup_whatsapp_click_leads(dry_run=dry_run)
