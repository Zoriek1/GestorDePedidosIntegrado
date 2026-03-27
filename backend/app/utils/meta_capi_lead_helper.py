# -*- coding: utf-8 -*-
"""
Meta CAPI — funil de leads (Contact / Lead). Feature flag e flush imediato.
"""
import os
import re
from typing import Optional

_META_EVENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


def is_lead_funnel_enabled() -> bool:
    return os.environ.get("META_CAPI_LEAD_FUNNEL_ENABLED", "").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def parse_meta_event_id(value: object) -> Optional[str]:
    """Valida event_id para Meta (Pixel/CAPI)."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or len(s) > 100:
        return None
    if not _META_EVENT_ID_RE.match(s):
        return None
    return s


def extract_contact_event_id_from_payload(data: dict) -> Optional[str]:
    for key in ("meta_event_id_contact", "capi_event_id"):
        parsed = parse_meta_event_id(data.get(key))
        if parsed:
            return parsed
    return None


def extract_lead_stage_event_id_from_payload(data: dict) -> Optional[str]:
    parsed = parse_meta_event_id(data.get("meta_event_id_lead"))
    if parsed:
        return parsed
    return None


def is_truthy_meta_pixel_lead(data: dict) -> bool:
    v = data.get("meta_pixel_lead")
    if v is True:
        return True
    if isinstance(v, str) and v.lower() in ("1", "true", "yes", "on"):
        return True
    return False


def try_flush_pending_meta_capi_lead_entries(entry_ids: list[int]) -> None:
    """Envia imediatamente entradas pending dos ids informados (falhas não propagam)."""
    if not entry_ids:
        return
    try:
        from app.commands.send_daily_purchases_to_meta_command import (
            SendDailyPurchasesToMetaCommand,
        )
        from app.repositories.meta_capi_lead_outbox_repository import (
            MetaCapiLeadOutboxRepository,
        )

        repo = MetaCapiLeadOutboxRepository()
        cmd = SendDailyPurchasesToMetaCommand()
        # Chaves alinhadas a _send_lead_batch (lead_*), senão KeyError ao marcar sent/fail.
        stats = {
            "errors": [],
            "lead_sent_success": 0,
            "lead_sent_failed": 0,
            "lead_failed_retryable": 0,
            "lead_failed_permanent": 0,
        }
        batch = []
        for eid in entry_ids:
            row = repo.get_by_id(eid)
            if row and row.status == "pending":
                batch.append(row)
        if not batch:
            print(
                "[META_CAPI_LEAD] Flush imediato: nenhum registro pending entre os ids "
                f"{entry_ids} (já enviado, falhou ou não existe).",
                flush=True,
            )
            return
        cmd._send_lead_batch(batch, stats)
        print(
            "[META_CAPI_LEAD] Flush imediato completo — "
            f"ok={stats['lead_sent_success']} falha={stats['lead_sent_failed']} "
            f"(outbox_ids={entry_ids})",
            flush=True,
        )
    except Exception as e:
        print(f"[AVISO] Meta CAPI lead flush imediato falhou: {e}", flush=True)
