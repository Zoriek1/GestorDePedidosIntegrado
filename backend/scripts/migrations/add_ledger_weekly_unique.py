# -*- coding: utf-8 -*-
"""
Migration: índice UNIQUE parcial em ledger_entry para salários semanais.

Objetivo
--------
Impedir duplicação de fixo_semanal / almoco / transporte para o mesmo
(user_id, week_ref, category) quando o admin clica em "Gerar semanal" 2x
em paralelo. Hoje o pré-check Python (LedgerService) tem janela de race
entre o read e o commit. Com este índice o segundo INSERT é rejeitado pelo
banco e o serviço captura IntegrityError tratando como duplicata.

O índice é PARCIAL (só linhas active não-voidadas com week_ref preenchido),
pra não bloquear estornos / lançamentos manuais sem week_ref.

Pré-checagem
------------
Se já existem duplicatas active no banco, a migration ABORTA e lista as
entradas. O usuário deve apagar as duplicatas pela lixeira do admin (UI)
e rodar de novo.

Uso
---
    cd backend && python scripts/migrations/add_ledger_weekly_unique.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db

SALARY_CATEGORIES = ("fixo_semanal", "almoco", "transporte")


def is_sqlite() -> bool:
    return db.engine.dialect.name == "sqlite"


def index_exists(name: str) -> bool:
    from sqlalchemy import inspect as sa_inspect

    insp = sa_inspect(db.engine)
    for ix in insp.get_indexes("ledger_entry"):
        if ix.get("name") == name:
            return True
    return False


def find_duplicates() -> list:
    """Retorna lista de (user_id, week_ref, category, count, ids) com duplicata ativa."""
    rows = db.session.execute(
        db.text(
            """
            SELECT user_id, week_ref, category, COUNT(*) AS qtd
            FROM ledger_entry
            WHERE voided = :voided_false
              AND week_ref IS NOT NULL
              AND category IN :cats
            GROUP BY user_id, week_ref, category
            HAVING COUNT(*) > 1
            """
        ).bindparams(db.bindparam("cats", expanding=True)),
        {"voided_false": False, "cats": list(SALARY_CATEGORIES)},
    ).fetchall()

    detalhado = []
    for uid, week, cat, qtd in rows:
        ids = [
            r[0]
            for r in db.session.execute(
                db.text(
                    """
                    SELECT id FROM ledger_entry
                    WHERE user_id = :uid AND week_ref = :week
                      AND category = :cat AND voided = :voided_false
                    ORDER BY id
                    """
                ),
                {"uid": uid, "week": week, "cat": cat, "voided_false": False},
            ).fetchall()
        ]
        detalhado.append((uid, week, cat, qtd, ids))
    return detalhado


def migrate():
    print(f"[MIGRATION] add_ledger_weekly_unique (banco: {db.engine.dialect.name})")

    if index_exists("uq_ledger_weekly_active"):
        print("[MIGRATION]   uq_ledger_weekly_active já existe — nada a fazer.")
        return

    duplicates = find_duplicates()
    if duplicates:
        print(
            "[MIGRATION] ABORTADO: existem duplicatas active de salário semanal.\n"
            "  Apague pela lixeira do admin (UI: Recebíveis → Extrato) e rode novamente."
        )
        for uid, week, cat, qtd, ids in duplicates:
            print(f"   - user_id={uid} week={week} category={cat} qtd={qtd} ids={ids}")
        sys.exit(1)

    if is_sqlite():
        ddl = (
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_weekly_active "
            "ON ledger_entry(user_id, week_ref, category) "
            "WHERE voided=0 AND week_ref IS NOT NULL "
            "AND category IN ('fixo_semanal','almoco','transporte')"
        )
        db.session.execute(db.text(ddl))
        db.session.commit()
    else:
        ddl = (
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_weekly_active "
            "ON ledger_entry(user_id, week_ref, category) "
            "WHERE voided = FALSE AND week_ref IS NOT NULL "
            "AND category IN ('fixo_semanal','almoco','transporte')"
        )
        with db.engine.connect() as conn:
            conn.execute(db.text("SET lock_timeout = '5s'"))
            conn.execute(db.text(ddl))
            conn.commit()

    print("[MIGRATION]   uq_ledger_weekly_active criado.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate()
