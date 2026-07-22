# -*- coding: utf-8 -*-
"""
Backfill de outbox do funil de leads (Meta CAPI).

Cria as linhas de `MetaCapiLeadOutbox` que estão FALTANDO para leads históricos —
tipicamente os que foram criados/transicionados enquanto
`META_CAPI_LEAD_FUNNEL_ENABLED` estava desligado e, por isso, nunca enfileiraram.

NÃO reenvia nada já enviado: apenas insere linhas `pending` faltantes. É
idempotente — a constraint `(lead_id, funnel_stage)` + uma checagem prévia
garantem que leads que já têm a linha (inclusive as `sent`) são pulados. O envio
em si fica por conta do serviço `capi-worker`, que faz polling do outbox e manda
em lotes (não há flush aqui — por isso não "reenvia todo o CAPI").

Estágios backfillados:
  - Lead  (status `whatsapp_iniciado` ou `compra_realizada`, COM telefone)
           → evento `Lead`. `meta_event_id_lead` é gerado (uuid) se ausente.
  - LeadDisqualified (status `descarte`) → evento `LeadDisqualified`.

Contact NÃO é backfillável: depende de `meta_event_id_contact` (event_id vindo do
Pixel do navegador), que não foi gravado no período sem a flag —
`build_contact_event_from_lead` levantaria ValueError. Esses cliques são ignorados.

event_time: usamos `lead.created_at` (único timestamp disponível no lead). Eventos
com mais de 7 dias são reposicionados para "agora" pela própria Meta/sanitização.

Uso:
  python scripts/meta/criar_outbox_lead_faltantes.py --dry-run
  python scripts/meta/criar_outbox_lead_faltantes.py --since 2026-05-01
  python scripts/meta/criar_outbox_lead_faltantes.py --only disqualified --limit 200
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Raiz do backend no path + carregar .env antes de importar app
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(backend_dir / ".env")

from app import create_app, db  # noqa: E402
from app.models.lead import Lead  # noqa: E402
from app.models.meta_capi_lead_outbox import MetaCapiLeadOutbox  # noqa: E402
from app.models.pedido import TIMEZONE_BRASIL  # noqa: E402
from app.repositories.meta_capi_lead_outbox_repository import (  # noqa: E402
    MetaCapiLeadOutboxRepository,
)
from app.utils.meta_capi_lead_helper import is_lead_funnel_enabled  # noqa: E402

WHATSAPP_EVENT = "whatsapp_click"
# Leads "qualificados" que deveriam ter disparado o evento Lead no fluxo vivo.
LEAD_STAGE_STATUSES = ("whatsapp_iniciado", "compra_realizada")
DISQUALIFIED_STATUS = "descarte"
# Chunk para o IN (...) de checagem de existência (segurança p/ Postgres).
_CHUNK = 5000

app = create_app()


def _parse_day(value: str, *, end: bool) -> datetime:
    """'YYYY-MM-DD' (ou ISO) → datetime tz-aware BRT (início ou fim do dia)."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        if end:
            parsed = parsed.replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=TIMEZONE_BRASIL
            )
        else:
            parsed = parsed.replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=TIMEZONE_BRASIL
            )
    return parsed


def _query_candidates(statuses, since, until, limit, *, require_phone: bool):
    q = Lead.query.filter(Lead.event == WHATSAPP_EVENT, Lead.status.in_(statuses))
    if require_phone:
        q = q.filter(Lead.phone.isnot(None), Lead.phone != "")
    if since:
        q = q.filter(Lead.created_at >= since)
    if until:
        q = q.filter(Lead.created_at <= until)
    q = q.order_by(Lead.created_at.asc())
    if limit:
        q = q.limit(limit)
    return q.all()


def _existing_stage_lead_ids(lead_ids, stage):
    """lead_ids que JÁ possuem linha de outbox para o estágio (qualquer status)."""
    existing = set()
    for i in range(0, len(lead_ids), _CHUNK):
        chunk = lead_ids[i : i + _CHUNK]
        rows = (
            MetaCapiLeadOutbox.query.with_entities(MetaCapiLeadOutbox.lead_id)
            .filter(
                MetaCapiLeadOutbox.lead_id.in_(chunk),
                MetaCapiLeadOutbox.funnel_stage == stage,
            )
            .all()
        )
        existing.update(r.lead_id for r in rows)
    return existing


def _backfill_lead_stage(repo, since, until, limit, dry_run, stats):
    candidates = _query_candidates(LEAD_STAGE_STATUSES, since, until, limit, require_phone=True)
    existing = _existing_stage_lead_ids([lead.id for lead in candidates], repo.STAGE_LEAD)
    faltantes = [lead for lead in candidates if lead.id not in existing]

    print(
        f"[LEAD] candidatos={len(candidates)} já_tinham_outbox={len(existing)} "
        f"faltando={len(faltantes)}"
    )
    for lead in faltantes:
        if dry_run:
            stats["lead_seria_criado"] += 1
            continue
        try:
            if not lead.meta_event_id_lead:
                lead.meta_event_id_lead = str(uuid4())
                db.session.commit()
            row = repo.create_lead_stage_from_lead(lead, event_time=lead.created_at)
            if row:
                stats["lead_criado"] += 1
            else:
                stats["lead_pulado"] += 1  # corrida: criado por outro processo
        except Exception as e:  # ex.: telefone inválido em build_lead_event
            db.session.rollback()
            stats["lead_erro"] += 1
            print(f"  [ERRO] lead #{lead.id}: {e}")


def _backfill_disqualified(repo, since, until, limit, dry_run, stats):
    candidates = _query_candidates((DISQUALIFIED_STATUS,), since, until, limit, require_phone=False)
    existing = _existing_stage_lead_ids([lead.id for lead in candidates], repo.STAGE_DISQUALIFIED)
    faltantes = [lead for lead in candidates if lead.id not in existing]

    print(
        f"[DISQUALIFIED] candidatos={len(candidates)} já_tinham_outbox={len(existing)} "
        f"faltando={len(faltantes)}"
    )
    for lead in faltantes:
        if dry_run:
            stats["disq_seria_criado"] += 1
            continue
        try:
            row = repo.create_disqualified_from_lead(lead, event_time=lead.created_at)
            if row:
                stats["disq_criado"] += 1
            else:
                stats["disq_pulado"] += 1
        except Exception as e:
            db.session.rollback()
            stats["disq_erro"] += 1
            print(f"  [ERRO] lead #{lead.id}: {e}")


def backfill(only=None, since=None, until=None, limit=None, dry_run=False):
    with app.app_context():
        print("=" * 64)
        print("BACKFILL OUTBOX FUNIL DE LEADS (Meta CAPI)")
        print("=" * 64)
        if dry_run:
            print("[DRY-RUN] Nenhuma linha será gravada.")
        print(f"[INFO] META_CAPI_LEAD_FUNNEL_ENABLED = {is_lead_funnel_enabled()}")
        print(f"[INFO] janela: since={since} until={until} limit={limit} only={only or 'todos'}")
        print("[INFO] Contact NÃO é backfillável (sem meta_event_id_contact histórico) — ignorado.")
        print("-" * 64)

        repo = MetaCapiLeadOutboxRepository()
        stats = {
            "lead_criado": 0,
            "lead_pulado": 0,
            "lead_erro": 0,
            "lead_seria_criado": 0,
            "disq_criado": 0,
            "disq_pulado": 0,
            "disq_erro": 0,
            "disq_seria_criado": 0,
        }

        if only in (None, "lead"):
            _backfill_lead_stage(repo, since, until, limit, dry_run, stats)
        if only in (None, "disqualified"):
            _backfill_disqualified(repo, since, until, limit, dry_run, stats)

        print("-" * 64)
        print("RESUMO")
        if dry_run:
            print(f"  Lead          seriam criados: {stats['lead_seria_criado']}")
            print(f"  LeadDisqualified seriam criados: {stats['disq_seria_criado']}")
        else:
            print(
                f"  Lead          criados={stats['lead_criado']} "
                f"pulados={stats['lead_pulado']} erros={stats['lead_erro']}"
            )
            print(
                f"  LeadDisqualified criados={stats['disq_criado']} "
                f"pulados={stats['disq_pulado']} erros={stats['disq_erro']}"
            )
            print()
            print(
                "  Linhas gravadas como 'pending'. O serviço capi-worker as enviará "
                "no polling — acompanhe os logs do container capi-worker."
            )
        print("=" * 64)
        return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cria outboxes faltantes do funil de leads (sem reenviar o que já saiu)."
    )
    parser.add_argument(
        "--only",
        choices=["lead", "disqualified"],
        default=None,
        help="Restringe a um estágio (default: ambos).",
    )
    parser.add_argument("--since", type=str, default=None, help="Data inicial (YYYY-MM-DD, BRT).")
    parser.add_argument("--until", type=str, default=None, help="Data final (YYYY-MM-DD, BRT).")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Máximo de leads por estágio (default: todos).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Só mostra o que seria criado, sem gravar.",
    )
    args = parser.parse_args()

    since = _parse_day(args.since, end=False) if args.since else None
    until = _parse_day(args.until, end=True) if args.until else None

    try:
        stats = backfill(
            only=args.only, since=since, until=until, limit=args.limit, dry_run=args.dry_run
        )
        erros = stats["lead_erro"] + stats["disq_erro"]
        sys.exit(1 if erros else 0)
    except KeyboardInterrupt:
        print("\n[AVISO] Cancelado pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO] Falha fatal: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
