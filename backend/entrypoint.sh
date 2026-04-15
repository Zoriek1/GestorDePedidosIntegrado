#!/bin/sh
set -e
# Migrations (quando usar Flask-Migrate)
if command -v flask >/dev/null 2>&1; then
    flask db upgrade 2>/dev/null || true
fi
# Migrations customizadas (idempotentes — pulam se a coluna já existe)
python scripts/migrations/add_pedido_id_to_leads.py
exec python wsgi.py
