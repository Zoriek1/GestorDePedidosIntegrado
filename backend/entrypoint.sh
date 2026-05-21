#!/bin/sh
set -e

# Migrations (quando usar Flask-Migrate)
if command -v flask >/dev/null 2>&1; then
    flask db upgrade 2>/dev/null || true
fi

# Migrations customizadas idempotentes
python scripts/migrations/add_pedido_id_to_leads.py
python scripts/migrations/add_default_vendor_to_nuvemshop_store.py
python scripts/migrations/add_followup_to_leads.py

exec python wsgi.py
