# -*- coding: utf-8 -*-
"""Verificação de integridade pós-migration — item 0.3 do gate de rollout.

Roda no MESMO `DATABASE_URL` já usado para as migrations. Não escreve nada,
apenas SELECTs. Uso:

    python scripts/migrations/_gate_check_integrity.py
"""

import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402

# Tabelas per-tenant que fizeram backfill nas Fases C e D.
TABLES = (
    "pedidos",
    "leads",
    "lead_touchpoints",
    "pedido_sugestoes_endereco",
    "pedido_manual_overrides",
    "rotas_otimizadas",
    "push_subscriptions",
    "clientes",
    "enderecos_clientes",
    "fontes_pedido",
    "pedido_external_refs",
    "audit_log",
    "meta_capi_outbox",
    "meta_capi_lead_outbox",
    "marketing_conversion_outbox",
    "bling_outbox",
)

EXPECTED_UNIQUES = (
    "uq_pedidos_store_numero_pedido",
    "uq_leads_store_dedup_key",
    "uq_push_subscriptions_store_endpoint",
)


def check() -> bool:
    ok = True
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())

    print("== Nulos em store_ref_id (esperado: 0 em todas) ==")
    for table in TABLES:
        if table not in existing_tables:
            print(f"  [SKIP] {table}: tabela não existe")
            continue
        try:
            count = db.session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE store_ref_id IS NULL")
            ).scalar_one()
        except (OperationalError, ProgrammingError) as exc:
            db.session.rollback()
            ok = False
            print(
                f"  [FALHA] {table}: erro na consulta ({exc.__class__.__name__}) — coluna ausente?"
            )
            continue
        tag = "OK" if count == 0 else "FALHA"
        if count != 0:
            ok = False
        print(f"  [{tag}] {table}: {count} nulo(s)")

    print("\n== Órfãos (store_ref_id sem loja correspondente; esperado: 0) ==")
    for table in TABLES:
        if table not in existing_tables:
            continue
        try:
            count = db.session.execute(
                text(
                    f"SELECT COUNT(*) FROM {table} t "
                    f"LEFT JOIN stores s ON s.id = t.store_ref_id "
                    f"WHERE t.store_ref_id IS NOT NULL AND s.id IS NULL"
                )
            ).scalar_one()
        except (OperationalError, ProgrammingError) as exc:
            db.session.rollback()
            ok = False
            print(
                f"  [FALHA] {table}: erro na consulta ({exc.__class__.__name__}) — coluna ausente?"
            )
            continue
        tag = "OK" if count == 0 else "FALHA"
        if count != 0:
            ok = False
        print(f"  [{tag}] {table}: {count} órfã(s)")

    if db.engine.dialect.name == "postgresql":
        print("\n== FKs físicas store_ref_id -> stores (Postgres) ==")
        for table in TABLES:
            if table not in existing_tables:
                continue
            fks = inspector.get_foreign_keys(table)
            has_fk = any(fk.get("constrained_columns") == ["store_ref_id"] for fk in fks)
            tag = "OK" if has_fk else "FALHA"
            if not has_fk:
                ok = False
            print(f"  [{tag}] {table}")

        print("\n== Uniques compostas esperadas ==")
        all_unique_names = set()
        for table in existing_tables:
            for uq in inspector.get_unique_constraints(table):
                if uq.get("name"):
                    all_unique_names.add(uq["name"])
        for name in EXPECTED_UNIQUES:
            tag = "OK" if name in all_unique_names else "FALHA"
            if name not in all_unique_names:
                ok = False
            print(f"  [{tag}] {name}")
    else:
        print(
            "\n[INFO] SQLite: FKs físicas e uniques nomeadas não se aplicam (gate real é Postgres)."
        )

    return ok


def run() -> None:
    app = create_app()
    with app.app_context():
        ok = check()
        print("\n" + ("=" * 40))
        print("[RESULTADO] GATE OK" if ok else "[RESULTADO] GATE FALHOU — ver [FALHA] acima")
        print("=" * 40)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    run()
