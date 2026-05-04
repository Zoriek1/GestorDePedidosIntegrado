# -*- coding: utf-8 -*-
"""
Exporta a tabela ``leads`` para uma planilha Google Sheets separada da de vendas.

- Planilha alvo: nome fixo configurável por env (não usa VENDAS_*).
- Aba única: ``Leads`` (criada automaticamente se não existir).
- A cada execução: substitui o conteúdo da aba (snapshot).

Requisitos: mesma service account e escopos que ``exportar_vendas_sheets.py``.
Crie manualmente a planilha com o título esperado e compartilhe com a SA (Editor).

Env:
  GOOGLE_SHEETS_LEADS_DOCUMENT_NAME — título da planilha no Drive (default: Leads_GESTOR)

Uso:
  cd backend && python scripts/export/exportar_leads_sheets.py
  python scripts/export/exportar_leads_sheets.py --teste
"""
from __future__ import annotations

import os
import sys
from typing import Any, List

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

import gspread

TIMEZONE_BRASIL = ZoneInfo("America/Sao_Paulo")

_scripts_export = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.abspath(os.path.join(_scripts_export, "..", ".."))
for _p in (_backend, _scripts_export):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from exportar_vendas_sheets import get_google_client, retry_google_operation  # noqa: E402

from app import create_app  # noqa: E402
from app.models.lead import Lead  # noqa: E402

DEFAULT_LEADS_SPREADSHEET_TITLE = "Leads_GESTOR"
WORKSHEET_TITLE = "Leads"
UPDATE_CHUNK_ROWS = 800
URL_MAX_LEN = 800


def _spreadsheet_title() -> str:
    return (os.environ.get("GOOGLE_SHEETS_LEADS_DOCUMENT_NAME") or "").strip() or DEFAULT_LEADS_SPREADSHEET_TITLE


def _clip_text(value: Any, max_len: int) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _fmt_dt_br(dt) -> str:
    if not dt:
        return ""
    if getattr(dt, "tzinfo", None):
        dt = dt.astimezone(TIMEZONE_BRASIL)
    return dt.strftime("%d/%m/%Y %H:%M")


def _headers() -> List[str]:
    return [
        "id",
        "created_at_br",
        "event",
        "status",
        "phone",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "placement",
        "url",
        "referrer",
        "src",
        "sck",
        "token_rastreio",
        "token_valido",
        "fbclid",
        "fbp",
        "ip_address",
        "dedup_key",
    ]


def _lead_row(lead: Lead) -> List[str]:
    tv = lead.token_valido
    token_valido_str = "" if tv is None else ("1" if tv else "0")
    # Placement vem do toque pago mais recente; fallback para first_touch se vazio.
    placement = ""
    if lead.last_touch and lead.last_touch.placement:
        placement = lead.last_touch.placement
    elif lead.first_touch and lead.first_touch.placement:
        placement = lead.first_touch.placement
    return [
        str(lead.id),
        _fmt_dt_br(lead.created_at),
        lead.event or "",
        lead.status or "",
        lead.phone or "",
        lead.utm_source or "",
        lead.utm_medium or "",
        lead.utm_campaign or "",
        lead.utm_content or "",
        lead.utm_term or "",
        placement,
        _clip_text(lead.url, URL_MAX_LEN),
        _clip_text(lead.referrer, URL_MAX_LEN),
        lead.src or "",
        lead.sck or "",
        lead.token_rastreio or "",
        token_valido_str,
        lead.fbclid or "",
        lead.fbp or "",
        lead.ip_address or "",
        lead.dedup_key or "",
    ]


def _end_col_letter(n_cols: int) -> str:
    if n_cols < 1 or n_cols > 26:
        raise ValueError("Esperado entre 1 e 26 colunas para intervalo A1:T")
    return chr(ord("A") + n_cols - 1)


def _get_or_create_leads_worksheet(spreadsheet: gspread.Spreadsheet) -> gspread.Worksheet:
    try:
        return spreadsheet.worksheet(WORKSHEET_TITLE)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=WORKSHEET_TITLE, rows=2000, cols=len(_headers()))


def _update_values_in_chunks(worksheet: gspread.Worksheet, rows_matrix: List[List[str]]) -> None:
    if not rows_matrix:
        return
    n_cols = len(rows_matrix[0])
    end_l = _end_col_letter(n_cols)
    for i in range(0, len(rows_matrix), UPDATE_CHUNK_ROWS):
        chunk = rows_matrix[i : i + UPDATE_CHUNK_ROWS]
        start_row = i + 1
        end_row = i + len(chunk)
        rng = f"A{start_row}:{end_l}{end_row}"
        retry_google_operation(
            lambda w=worksheet, r=rng, c=chunk: w.update(r, c),
            max_retries=2,
        )


def exportar_leads() -> bool:
    title = _spreadsheet_title()
    app = create_app()

    with app.app_context():
        print("=" * 50)
        print(f"EXPORTAÇÃO LEADS → Google Sheets ({title})")
        print("=" * 50)

        try:
            client = get_google_client()
            print("Autenticação Google OK")
        except Exception as e:
            print(f"Erro ao conectar: {e}")
            return False

        try:
            spreadsheet = retry_google_operation(
                lambda: client.open(title),
                max_retries=2,
                backoff_delays=[1, 2],
            )
            print(f"Planilha encontrada: {title}")
        except gspread.SpreadsheetNotFound:
            print(f"\nPlanilha '{title}' não encontrada.")
            print("1. Crie no Google Sheets uma planilha com exatamente esse título")
            print("   (ou defina GOOGLE_SHEETS_LEADS_DOCUMENT_NAME no .env).")
            print("2. Compartilhe com o e-mail da Service Account como Editor.")
            print("3. Execute novamente.")
            return False
        except Exception as e:
            print(f"Erro ao abrir planilha: {e}")
            return False

        leads = Lead.query.order_by(Lead.created_at.desc()).all()
        print(f"Total de leads no banco: {len(leads)}")

        headers = _headers()
        data_rows = [_lead_row(L) for L in leads]
        matrix = [headers] + data_rows

        worksheet = _get_or_create_leads_worksheet(spreadsheet)
        try:
            need_rows = max(len(matrix) + 10, 100)
            need_cols = max(len(headers), worksheet.col_count)
            if worksheet.row_count < need_rows or worksheet.col_count < need_cols:
                worksheet.resize(rows=need_rows, cols=need_cols)
        except Exception:
            pass

        retry_google_operation(lambda: worksheet.clear(), max_retries=2)
        _update_values_in_chunks(worksheet, matrix)

        print("\nExportação de leads concluída.")
        print(f"  {spreadsheet.url}")
        return True


def teste_conexao() -> bool:
    print("Testando conexão com Google Sheets (leads)...")
    try:
        get_google_client()
        print("Conexão OK.")
        return True
    except Exception as e:
        print(f"Erro: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Exportar leads para Google Sheets")
    parser.add_argument("--teste", action="store_true", help="Testar credenciais Google")
    args = parser.parse_args()
    if args.teste:
        raise SystemExit(0 if teste_conexao() else 1)
    raise SystemExit(0 if exportar_leads() else 1)
