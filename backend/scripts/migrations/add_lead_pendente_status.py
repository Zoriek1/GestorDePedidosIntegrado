# -*- coding: utf-8 -*-
"""
Migration: introduz o status `lead_pendente` no funil de leads.

Modelo
------
`Lead.status` é `String(50)` livre — não há ENUM a alterar. A migration é
sobretudo **documental**: registra a introdução do novo estado e faz um
backfill defensivo de leads `pendente_whatsapp` que já têm telefone
preenchido (estado que, no modelo antigo, surgia silenciosamente em alguns
caminhos como o bulk/disqualify ou a criação inicial via form).

No modelo novo:
- `pendente_whatsapp` = lead do anúncio, **sem telefone**.
- `lead_pendente`    = lead com telefone capturado, aguardando triagem.
- Confirmar (whatsapp_iniciado) e desqualificar (descarte) exigem telefone.

Idempotente
-----------
Só altera linhas que ainda batem no critério (status='pendente_whatsapp'
AND phone IS NOT NULL AND TRIM(phone) <> '').

Uso
---
    docker compose exec backend python scripts/migrations/add_lead_pendente_status.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db


def migrate():
    print(f"[MIGRATION] add_lead_pendente_status (banco: {db.engine.dialect.name})")

    result = db.session.execute(
        db.text(
            "UPDATE leads SET status = 'lead_pendente' "
            "WHERE status = 'pendente_whatsapp' "
            "AND phone IS NOT NULL AND TRIM(phone) <> ''"
        )
    )
    affected = result.rowcount or 0
    db.session.commit()

    print(
        f"[MIGRATION]   backfill: {affected} lead(s) 'pendente_whatsapp' com telefone → 'lead_pendente'."
    )
    print("[MIGRATION]   pronto.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
