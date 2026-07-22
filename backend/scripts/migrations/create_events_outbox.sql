-- Migration: Create unified events_outbox table
-- Run: python scripts/migrations/create_events_outbox.py

CREATE TABLE IF NOT EXISTS events_outbox (
    id SERIAL PRIMARY KEY,
    store_ref_id INTEGER REFERENCES stores(id),
    lead_id INTEGER REFERENCES leads(id),
    pedido_id INTEGER REFERENCES pedidos(id),
    destino VARCHAR(30) NOT NULL,
    evento VARCHAR(80) NOT NULL,
    dedup_key VARCHAR(64) NOT NULL UNIQUE,
    event_time TIMESTAMP NOT NULL,
    payload_json TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    error_type VARCHAR(20),
    last_error TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_outbox_status ON events_outbox(status);
CREATE INDEX IF NOT EXISTS idx_events_outbox_store ON events_outbox(store_ref_id);
CREATE INDEX IF NOT EXISTS idx_events_outbox_destino ON events_outbox(destino);
CREATE INDEX IF NOT EXISTS idx_events_outbox_lead ON events_outbox(lead_id);
CREATE INDEX IF NOT EXISTS idx_events_outbox_pedido ON events_outbox(pedido_id);
CREATE INDEX IF NOT EXISTS idx_events_outbox_error_type ON events_outbox(error_type);
