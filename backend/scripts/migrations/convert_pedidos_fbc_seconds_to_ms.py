# -*- coding: utf-8 -*-
"""Migration: converte `pedidos.fbc` de segundos para milissegundos.

Contexto: até o fix do bug do `creationTime`, `build_fbc_from_fbclid` gerava
timestamps em segundos (`int(time.time())`), mas o formato esperado pela Meta
é `fb.1.{milissegundos}.{fbclid}`. Esses fbc legacy ficaram persistidos em
`pedidos.fbc` e a validação reforçada (`>= 10**12`) os rejeita, forçando
fallback para reconstrução via `lead.created_at`.

Esta migration é idempotente — multiplica o timestamp por 1000 apenas em
registros cujo timestamp está em segundos (< 10**12, i.e. antes do ano ~2001
em ms). Operação lossless: preserva o instante exato do clique original.

Como rodar:
    docker compose exec backend python scripts/migrations/convert_pedidos_fbc_seconds_to_ms.py
"""
import re
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()

_FBC_RE = re.compile(r"^fb\.1\.(\d+)\.(.+)$")
_MS_THRESHOLD = 10**12


def convert_fbc_to_ms():
    with app.app_context():
        print("[MIGRATION] Convertendo pedidos.fbc de segundos para milissegundos...")

        rows = db.session.execute(
            db.text("SELECT id, fbc FROM pedidos WHERE fbc IS NOT NULL AND fbc <> ''")
        ).fetchall()

        scanned = len(rows)
        converted = 0
        already_ms = 0
        malformed = 0

        for pedido_id, fbc in rows:
            m = _FBC_RE.match(fbc.strip())
            if not m:
                malformed += 1
                continue

            ts = int(m.group(1))
            rest = m.group(2)

            if ts >= _MS_THRESHOLD:
                already_ms += 1
                continue

            new_fbc = f"fb.1.{ts * 1000}.{rest}"
            db.session.execute(
                db.text("UPDATE pedidos SET fbc = :fbc WHERE id = :id"),
                {"fbc": new_fbc, "id": pedido_id},
            )
            converted += 1

        db.session.commit()

        print(f"[OK] Escaneados:  {scanned}")
        print(f"[OK] Convertidos: {converted} (segundos -> ms)")
        print(f"[OK] Ja em ms:    {already_ms} (skip)")
        print(f"[OK] Malformados: {malformed} (skip, nao bate regex fb.1.ts.fbclid)")
        print("[OK] Migration concluida")


if __name__ == "__main__":
    convert_fbc_to_ms()
