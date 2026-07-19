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
python scripts/migrations/add_situacao_to_leads.py
python scripts/migrations/add_slot_entrega_to_pedidos.py
python scripts/migrations/add_delivery_details_to_pedidos.py
python scripts/migrations/add_fiscal_fields_to_pedidos.py
python scripts/migrations/add_session_fields_to_lead_touchpoints.py
python scripts/migrations/add_whatsapp_marketing_tracking.py
python scripts/migrations/add_pedido_id_to_push_subscriptions.py
python scripts/migrations/add_codigo_whatsapp_to_pedidos.py
python scripts/migrations/backfill_slot_inicio_from_horario.py
python scripts/migrations/add_search_trgm_unaccent.py
python scripts/migrations/create_catalogo_arranjos.py
python scripts/migrations/create_bling_integration.py
python scripts/migrations/create_pedido_sugestoes_endereco.py

exec python wsgi.py
