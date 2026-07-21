# Multi-Tenant Store Mapping

## Store Model

`app/models/store.py` — Table `stores`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | Internal tenant ID |
| `name` | String(120) | Display name |
| `slug` | String(60) | Unique, indexed. `"default"` is the legacy single-tenant store |
| `active` | Boolean | `True` = store processes work; `False` = inactive |
| `created_at` | DateTime | |
| `updated_at` | DateTime | Auto-updated |

## StoreSetting (1:1)

`app/models/store_setting.py` — Table `store_settings`

Each store has at most one `StoreSetting` row (FK `store_ref_id` → `stores.id`, `unique=True`, `ondelete="CASCADE"`).

### Fields

- **Marketing dispatch toggle**: `marketing_dispatch_enabled`
- **Meta CAPI**: `meta_pixel_id`, `meta_capi_access_token_encrypted`
- **GA4**: `ga4_measurement_id`, `ga4_api_secret_encrypted`, `ga4_validate_only`
- **Google Ads / Data Manager**: `google_datamanager_enabled`, `google_ads_customer_id`, `google_ads_conversion_action_id`
- **Utmify**: `utmify_enabled`, `utmify_api_token_encrypted`, `utmify_platform`, `utmify_is_test`
- **Operational**: `endereco_floricultura`, `loja_cep`

### Secrets

Three fields are stored encrypted (`SECRET_FIELDS` map in the model):

| Plaintext field | Encrypted column |
|-----------------|------------------|
| `meta_capi_access_token` | `meta_capi_access_token_encrypted` |
| `ga4_api_secret` | `ga4_api_secret_encrypted` |
| `utmify_api_token` | `utmify_api_token_encrypted` |

Read/write via `set_secret()` / `get_secret()` using `encrypt_secret` / `decrypt_secret` with a `:store-settings` purpose tag.

## Runtime Config Resolution

`app/services/integration_settings_service.py:259` — `runtime_config(store_ref_id)`

```
runtime_config(store_ref_id)
│
├─ store_ref_id is None?
│   └─ Resolve default store (slug="default")
│       └─ No default store? RuntimeError → rollback → _environment_runtime_config()
│
├─ Store not found in DB?
│   └─ _disabled_runtime_config()
│
├─ No StoreSetting row for this store?
│   ├─ slug == "default" → _environment_runtime_config()  (env-var fallback)
│   └─ any other slug → _disabled_runtime_config()         (disabled)
│
└─ StoreSetting exists
    └─ Build dict from StoreSetting columns + decrypted secrets
       (GOOGLE_DATAMANAGER_CREDENTIALS_JSON stays from app.config — platform credential, not tenant)
```

### Fallback Summary

| Scenario | Result |
|----------|--------|
| No settings + default store | Env vars (`_environment_runtime_config`) |
| No settings + non-default store | Disabled (`_disabled_runtime_config`) — booleans=False, strings="" |
| Store not found | Disabled |
| DB error resolving default | Env vars |

`_disabled_runtime_config()` takes env vars then forcibly sets all feature flags to `False` and all string/secret fields to `""`.

## Tables with `store_ref_id`

All tenant-scoped models inherit `store_ref_id` via the `TenantScoped` mixin (`app/services/tenant_scope.py`):

| Table | Model | FK target |
|-------|-------|-----------|
| `store_settings` | `StoreSetting` | `stores.id` (CASCADE) |
| `meta_capi_outbox` | `MetaCapiOutbox` | `stores.id` (RESTRICT) |
| `meta_capi_lead_outbox` | `MetaCapiLeadOutbox` | `stores.id` (RESTRICT) |
| `bling_outbox` | `BlingOutbox` | `stores.id` (RESTRICT) |
| `marketing_conversion_outbox` | `MarketingConversionOutbox` | `stores.id` (RESTRICT) |
| `pedidos` | `Pedido` | via `TenantScoped` |
| `clientes` | `Cliente` | via `TenantScoped` |
| `fontes_pedido` | `FontePedido` | via `TenantScoped` |
| `users` | `User` | via `TenantScoped` |

> `nuvemshop_webhook_deliveries` uses `store_id` (string, Nuvemshop external ID), **not** `store_ref_id`. It is not tenant-scoped via `TenantScoped`.

## TenantScope — Global SELECT Filter

`TenantScoped` mixin adds a `store_ref_id` column and registers a SQLAlchemy `do_orm_execute` listener that auto-filters SELECTs by `g.tenant_store_id`:

- **Multi-store active** (`g.tenant_multi=True`): only rows matching `g.tenant_store_id`
- **Single-store**: rows matching `g.tenant_store_id` OR `store_ref_id IS NULL` (legacy rows)
- **No tenant in multi-store**: `false()` — no rows returned (fail-closed)
- **No request context**: no filter applied (CLI, workers)
- **Escape hatch**: execution option `include_all_tenants=True`

## Worker Iteration Pattern

Workers (Meta CAPI, Bling, marketing conversion) iterate over pending outbox rows, optionally filtered by `store_ref_id`:

```
Store.query.filter_by(active=True).all()  →  for each store:
    process_pending(limit=per_store_limit, store_ref_id=store.id)
```

Each worker accepts `store_ref_id` parameter; when provided, queries filter to that store only. The `per_store_limit` caps rows per store per cycle.

## Inactive Store Policy

`app/services/tenancy.py:51` — `is_store_inactive(store_ref_id)`

- Returns `True` **only** when a `Store` row exists with `active=False`
- `None` or non-existent store → `False` (fail-open, preserves legacy behavior)

### Enforcement points

| Layer | Action |
|-------|--------|
| **Enqueue guards** (bling_helper, meta_capi_outbox_repository, meta_capi_lead_outbox_repository, marketing_conversion_service) | Skip enqueue, return early |
| **Outbox workers** (Meta CAPI `_partition_by_store`, Bling `process_pending`, marketing_conversion_dispatcher) | `mark_failed(entry.id, "store_inactive")` — permanent failure, no retry |
| **Nuvemshop webhook** (service.py:157) | `_mark_failed(delivery, "store_inactive")` |

Rows of inactive stores are never sent to external APIs; pending rows are invalidated with error code `"store_inactive"`.
