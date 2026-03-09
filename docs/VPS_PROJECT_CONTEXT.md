# VPS Project Context (Safe Change Guide)

Purpose: one-file operational context to reduce regressions when changing code in production (VPS).

## 1) High-Level Map

- Monorepo with:
  - `backend/` Flask API + business rules + integrations + serves frontend static build.
  - `frontend_v2/` React + Vite + PWA.
  - `deploy/` example infra configs (`*.example`).
  - `docs/` and `backend/docs/` technical and operational guides.
- Main branch: `main`.

## 2) Runtime Entry Points (Production vs Dev)

- Backend production entry: `backend/wsgi.py`
  - Runs app with Waitress.
  - Starts Meta CAPI daily scheduler thread (23:00 BRT).
- Backend development entry: `backend/main.py`
  - Uses `run_simple(... threaded=True, processes=1)`.
  - Creates startup backup in background thread.
- Flask app factory: `backend/app/factory.py`
  - Critical init order:
    1. config
    2. extensions/db
    3. CORS
    4. blueprints + db init
    5. errors
    6. OpenAPI
    7. static catch-all routes
    8. security middleware
    9. CLI commands
    10. delivery-fee worker

## 3) Frontend/Backend Contract

- Backend serves SPA static build (do not break this assumption):
  - default path resolved by backend expects `frontend_v2/dist`.
  - optional override: `FRONTEND_DIST_PATH`.
- Frontend build/proxy:
  - `frontend_v2/vite.config.ts` proxies `/api` to backend target.
  - PWA service worker denylist includes `/api/*` and Meta Gateway paths.
- If frontend routes or static behavior change, validate:
  - SPA fallback still works.
  - `/api/*` is not intercepted by SPA fallback.

## 4) Critical Env Vars (VPS)

Defined in `backend/app/config.py` and deploy docs:

- Core:
  - `FLASK_ENV` or `APP_ENV` (`production` in VPS)
  - `SECRET_KEY`
  - `ADMIN_PASSWORD`
  - `HOST`, `PORT`
  - `USE_HTTPS`
- Database:
  - `DATABASE_URL` for PostgreSQL (recommended on VPS)
  - fallback is SQLite external path (`~/var/lib/database/database.db`)
- Frontend:
  - `FRONTEND_DIST_PATH` (optional, absolute path to built dist)
- Nuvemshop:
  - `NUVEMSHOP_APP_ID`
  - `NUVEMSHOP_CLIENT_SECRET`
  - `NUVEMSHOP_USER_AGENT`
  - `NUVEMSHOP_PUBLIC_BASE_URL` (must match real public domain)
- Meta CAPI:
  - `META_PIXEL_ID`
  - `META_CAPI_ACCESS_TOKEN`
  - `META_CAPI_USE_GATEWAY`
  - `META_CAPI_GATEWAY_DOMAIN` or `META_CAPI_GATEWAY_ENDPOINT`
- Google:
  - `GOOGLE_APPLICATION_CREDENTIALS` and/or `GOOGLE_CREDENTIALS_JSON`

## 5) Data and Persistence Safety

- DB and backup are critical; do not change without migration/rollback plan.
- Backup system is integrated in runtime and delete flows:
  - docs: `backend/docs/BACKUP.md`.
  - fail-closed guard: destructive actions can be blocked on backup failure.
- Soft-delete/audit expectations exist for orders:
  - avoid bypassing repositories/guards in delete/update flows.

## 6) Integration Hotspots (High Regression Risk)

- Nuvemshop mapping/import:
  - `backend/app/integrations/nuvemshop/mapper.py`
  - `backend/app/integrations/nuvemshop/service.py`
  - route layer: `backend/app/routes/integrations/nuvemshop.py`
  - docs: `backend/docs/NUVEMSHOP_CREDENTIALS.md`
- Meta CAPI outbox/send:
  - `backend/app/services/meta_capi.py`
  - `backend/app/repositories/meta_capi_outbox_repository.py`
  - `backend/app/commands/send_daily_purchases_to_meta_command.py`
  - docs: `backend/docs/META_CAPI_OUTBOX.md`
- Google Sheets export:
  - `backend/scripts/export/exportar_vendas_sheets.py`
  - docs: `backend/docs/CONFIGURAR_GOOGLE_SHEETS.md`

## 7) Architecture Rules to Preserve

- Keep dependency direction:
  - routes -> services/repositories -> models.
- Prefer repository usage over ad-hoc direct db access in route handlers.
- Keep init order in factory intact (especially static catch-all after API blueprints).
- Do not break OpenAPI boot path; failure should degrade gracefully (current behavior).

## 8) Safe Change Protocol (Before Merge/Deploy)

1. Identify impacted layer(s): route/service/repository/model/integration.
2. Verify existing tests in the same domain and update/add minimal focused tests.
3. Run at least targeted tests:
   - backend: `python3 -m pytest -q tests/<affected_files>.py`
   - frontend (if touched): `npm run test -- <affected_test_file>`
4. For integration changes, run smoke checks:
   - `/api/health`
   - key affected endpoint(s)
5. For VPS deploy, validate env vars and service startup logs.

## 9) Recommended Smoke Checklist on VPS

- Backend process up (Waitress/systemd/docker) and listening on expected host/port.
- `GET /api/health` returns healthy.
- SPA loads from domain and authenticated API requests still work.
- Nuvemshop webhook processing endpoint reachable (if enabled).
- Meta CAPI scheduler thread starts (check logs in `wsgi.py` startup).
- Backup status endpoint and latest backup freshness are acceptable.

## 10) Useful References

- Deploy guide: `docs/DEPLOY_VPS.md`
- Backend architecture: `backend/docs/ARCHITECTURE.md`
- Backup operations: `backend/docs/BACKUP.md`
- Meta CAPI outbox: `backend/docs/META_CAPI_OUTBOX.md`
- Nuvemshop credentials/deploy notes: `backend/docs/NUVEMSHOP_CREDENTIALS.md`
- Automations checks: `backend/docs/TESTAR_AUTOMACOES.md`

## 11) Known Caveats

- `backend/requirements.txt` contains optional/deprecated-sensitive packages (`pywebpush` path can fail in some environments). For CI/VPS, pin/install only required subsets when needed.
- Test and runtime behavior can differ between SQLite and PostgreSQL; prefer production-like checks for DB-sensitive changes.
- Some docs/scripts are Windows-oriented; VPS process should follow Linux/service-manager flow in `docs/DEPLOY_VPS.md`.

## 12) Change Impact Matrix (V2)

Use this matrix as default guardrail: changed area -> minimum tests/smokes to run before deploy.

| Changed area | Minimum automated tests | Mandatory smoke checks |
|---|---|---|
| `backend/app/integrations/nuvemshop/*` | `python3 -m pytest -q tests/test_nuvemshop_integration.py` | `/api/health`, process pending webhook/import endpoint, verify one imported order fields |
| `backend/app/services/meta_capi.py` + outbox/command files | `python3 -m pytest -q tests/test_meta_capi.py` | `/api/health`, run Meta send command manually once in staging, inspect outbox counters |
| `backend/scripts/export/exportar_vendas_sheets.py` | `python3 -m pytest -q tests/test_export_sheets.py` | run export script once, validate target spreadsheet tab/date totals |
| `backend/app/routes/api.py` / `app/routes/pedidos.py` / `app/routes/clientes.py` | `python3 -m pytest -q tests/test_api.py tests/test_api_endpoints.py tests/test_repositories.py` | `/api/health`, auth flow, one create/update/delete flow in UI/API |
| `backend/app/repositories/*` / `backend/app/models/*` / schemas | `python3 -m pytest -q tests/test_repositories.py tests/test_models.py tests/test_integration.py` | CRUD smoke on one real entity and DB consistency check |
| Backup or destructive guard (`backup_helper`, scripts/backup, guard) | `python3 -m pytest -q tests/test_backup_automation.py tests/test_backup_status.py tests/test_remote_verify.py tests/test_fail_closed.py` | `/api/backup/status`, latest backup age < 24h, simulate one protected destructive action |
| Geocoding/distance (`services/distancia.py`, google geocoding) | `python3 -m pytest -q tests/test_distancia_cache.py tests/test_google_geocoding.py tests/test_endereco_geocoding.py tests/test_google_maps_url.py` | run one distance calc from API and check no regression in route generation |
| Frontend order form / mapping (`frontend_v2/src/features/pedidos/*`) | `cd frontend_v2 && npm run test -- src/features/pedidos/useCases/__tests__/orderToForm.test.ts src/features/pedidos/__tests__/schemas.test.ts` | open order form, create/edit order, confirm payload fields in network |
| Frontend logger/lib/utils (`frontend_v2/src/lib/*`) | `cd frontend_v2 && npm run test -- src/lib/__tests__/logger.test.ts` | quick UI navigation smoke and console error sanity |
| App bootstrap/runtime (`backend/app/factory.py`, `backend/wsgi.py`, `backend/main.py`, `app/static.py`) | `python3 -m pytest -q tests/test_api.py tests/test_api_endpoints.py` | process starts clean, `/api/health` OK, SPA served, API reachable from frontend domain |

### Full Regression Gate (before production deploy)

Run this when changes touch more than one high-risk area:

```bash
cd backend
python3 -m pytest -q \
  tests/test_remote_verify.py \
  tests/test_api.py \
  tests/test_api_endpoints.py \
  tests/test_integration.py \
  tests/test_backup_automation.py \
  tests/test_meta_capi.py \
  tests/test_export_sheets.py \
  tests/test_nuvemshop_integration.py
```

If frontend changed:

```bash
cd frontend_v2
npm run test -- src/features/pedidos/useCases/__tests__/orderToForm.test.ts
```

### Deploy Decision Rule

- If any matrix-required test fails: do not deploy.
- If tests pass but mandatory smoke fails: rollback or block deploy.
- If warnings only (no fails): deploy allowed, but register technical debt if warning volume increases.

## 13) Docker VPS Runbook (Meta CAPI + PostgreSQL)

Use these commands on the VPS host (inside repo root) when Meta is not sending.

### Step A - Ensure root `.env` has Meta and DB settings

```env
POSTGRES_USER=gestor
POSTGRES_PASSWORD=your_strong_password
POSTGRES_DB=gestor_pedidos

META_PIXEL_ID=your_pixel_id
META_CAPI_ACCESS_TOKEN=your_access_token
META_CAPI_API_VERSION=v21.0
META_CAPI_USE_GATEWAY=false
# Optional:
# META_TEST_EVENT_CODE=TEST123
# META_CAPI_GATEWAY_DOMAIN=gestaopedidos.planteumaflor.online
# META_CAPI_GATEWAY_ENDPOINT=
```

Note: for Docker Compose, root `.env` is the source of truth, not `backend/.env`.

### Step B - Recreate backend with fresh env

```bash
docker compose up -d --force-recreate backend
docker compose ps
```

### Step C - Validate runtime env inside container

```bash
docker compose exec backend env | grep -E 'DATABASE_URL|META_'
```

Expected:
- `DATABASE_URL=postgresql://...@db:5432/...`
- `META_PIXEL_ID` and `META_CAPI_ACCESS_TOKEN` present.

### Step D - Validate DB engine from app context

```bash
docker compose exec backend python3 -c "from app import create_app; app=create_app(); print(app.config.get('SQLALCHEMY_DATABASE_URI'))"
```

Expected output starts with `postgresql://` (not `sqlite:///`).

### Step E - Run Meta diagnostics inside container

```bash
docker compose exec backend python3 scripts/meta/verificar_config_meta.py
docker compose exec backend python3 scripts/maintenance/diagnosticar_gateway.py
docker compose exec backend python3 scripts/meta/verificar_outbox.py
docker compose exec backend python3 scripts/meta/verificar_outbox_failed.py
```

### Step F - Trigger one manual send

```bash
docker compose exec backend python3 scripts/meta/send_daily_purchases_to_meta.py
```

If outbox is empty, create/mark at least one order as `Pago` or `Parcial`, then rerun.

### Step G - Confirm scheduler thread is alive

```bash
docker compose logs --tail=200 backend | grep META_SCHEDULER
```

Expected lines:
- `Iniciado — aguardando 23:00 BRT`
- at 23:00 BRT: `Disparando envio...`

### Step H - Quick failure triage

- Missing Meta vars in Step C: wrong `.env` file or container not recreated.
- SQLite in Step D: backend not using Compose env / wrong service context.
- Outbox always zero: no `Pago/Parcial` transitions captured.
- Permanent failures in outbox: inspect `verificar_outbox_failed.py` and token/payload validity.

