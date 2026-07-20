# Spec 06 — Workers e integrações externas

## Status de implementação

**Fases D e hardening fail-closed (Fase F parcial) concluídas no código** (commits `83fc747` e `99e5945`):

- `store_ref_id` adicionado a `meta_capi_outbox`, `meta_capi_lead_outbox`,
  `marketing_conversion_outbox` e `bling_outbox`.
- Migration idempotente em `add_store_ref_to_outboxes.py`, com backfill pelo pedido/lead
  referenciado, índices/FKs e validação de nulos/órfãos. Registrada no `entrypoint.sh`.
- Tenant copiado da entidade origem no enqueue; poll, retry e reprocessamento preservam o
  `store_ref_id` original da linha.
- `MetaConversionsApiService`, GA4/Google Ads e UTMify resolvem configuração por linha/grupo
  via `runtime_config(row.store_ref_id)`; nunca selecionam token apenas por `os.environ`.
- Agrupamento por tenant permitido sem compartilhar instâncias/config entre grupos.
- Safety-net diário filtra/agrupa por tenant.
- Credencial Bling selecionada por `BlingTokenService.get_credential(store_ref_id)`;
  `BLING_STORE_ID` removido como seletor operacional. No hardening `99e5945`, rotas instanciam
  `BlingIntegrationService(store_ref_id)` e o service/token service selecionam a credencial por
  loja explicitamente (não mais WIP).
- Falhas isoladas: erro de configuração de A não bloqueia lote de B.
- Logs incluem `store_ref_id` e destino com redaction de tokens.
- Empresa inativa: novos enqueues bloqueados; linhas pendentes marcadas como falha permanente
  (`store_inactive`) — decisão de produto documentada em 09-blueprint.
- 5 testes direcionados em `test_tenant_workers.py`; suíte backend completa: 786/786 testes.
- **Hardening concluído (fail-closed, `99e5945`)**: job de taxa de entrega carrega `store_ref_id`
  na fila e filtra o pedido pelo tenant (sem `g.current_store` no worker).
- **Restante do hardening (Fase F) pendente:** `NOT NULL`, uniques finais, remoção de fallbacks
  `.env`, cifrar token Nuvemshop e métricas/alertas por tenant.

## Pastas afetadas

- `backend/app/integrations/`
- `backend/app/services/`