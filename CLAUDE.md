# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

### Backend (from `backend/`)
```bash
pip install -r requirements.txt
python main.py                        # dev server on :5000

# Tests
pytest                                # all tests
pytest tests/test_recebiveis.py       # single file
pytest tests/test_recebiveis.py::test_settle_idempotente  # single test
pytest --timeout=30

# Lint / format
ruff check . --fix
black .
```

### Frontend (from `frontend_v2/`)
```bash
npm install
npm run dev        # Vite dev server on :5173
npm run build
npm run lint
```

### Combined fix (Windows, from root)
```powershell
scripts/fix.ps1    # ruff + black + eslint --fix
scripts/check.ps1  # same checks without writing
```

### Create first admin user
```bash
cd backend && flask create-admin
```

### Database migrations (custom scripts — not Alembic)
```bash
python scripts/migrations/add_auth_and_ledger.py
python scripts/migrations/add_payroll_calendar.py
# etc. — run each migration script once in order
```

### Docker (VPS deploy)
```bash
cp backend/.env.example .env  # fill in secrets
docker compose up -d
```

---

## Architecture

### Backend — Flask 3 + SQLAlchemy 2

**Layer stack** (top → bottom):
```
routes/          Blueprint HTTP handlers — validate input, call service/repo, return JSON
services/        Pure business logic (no HTTP, no db.session.commit)
repositories/    DB queries; extend BaseRepository[Model]
models/          SQLAlchemy models + to_dict()
```

All routes return via `success_response()` / `error_response()` from `app/schemas/common.py`.

**Blueprints registered in `factory.py`:**
- `api_bp` — legacy catch-all (routes/api.py, ~3k lines, being migrated away)
- `pedidos_bp`, `clientes_bp`, `rotas_bp`, `leads_bp` — domain blueprints
- `ledger_bp` — recebíveis module (`/api/ledger/*`)
- `users_bp` — user management (`/api/users/*`)
- `auth_bp` — JWT auth (`/api/auth/*`)
- `config_bp`, `notifications_bp`, `nuvemshop_bp`, `storefront_bp`, `meta_gateway_bp`

**Auth:** Selective JWT via `@require_auth()` decorator (`app/decorators/auth_decorator.py`). Most read routes are open; write/financial routes require JWT. The decorator injects `request.current_user = {user_id, role, name, email}`.

Roles: `admin` | `vendedor` | `viewer`.

**Database:** SQLite in dev (`~/var/lib/database/database.db`), PostgreSQL in prod (`DATABASE_URL`). WAL mode + FK enforcement set in `extensions.py`. Tables created via `db.create_all()` on startup — no Alembic. Schema changes use standalone migration scripts in `backend/scripts/migrations/` (each checks `column_exists()` before ALTER).

**Money:** Pedido.valor is a BRL-formatted string; use `parse_brl_money()` from `app/utils/money.py` to convert. LedgerEntry.amount is `db.Numeric(12, 2)` (positive only, use `float(entry.amount)` when serializing).

**Timestamps:** Always use `datetime_now_brazil()` (Brazil/São Paulo tz). Defined in `app/models/pedido.py` and duplicated in `app/models/ledger_entry.py` / `app/models/user.py`.

### Recebíveis Module (Ledger)

Three new models in `app/models/user.py`: `User`, `PayrollConfig`, `CommissionConfig`.  
One model in `app/models/ledger_entry.py`: `LedgerEntry`.

**Flow (double-entry):**
1. When a `Pedido.status_pagamento` transitions to `Pago` or `Parcial` in `pedido_repository.atualizar_status`, `commission_service.generate_commission()` is called → inserts a `CREDIT` entry (`status='active'`) with `category=comissao_{source}`.
2. `ledger_service.generate_weekly_credits()` (called via admin endpoint or CLI) creates `fixo_semanal`/`almoco`/`transporte` credits for all active vendedores — idempotent by `(user_id, week_ref, category)`.
3. Vendedor (or admin) settles all active credits at once via `POST /api/ledger/settle` → creates one DEBIT (`category='pagamento'`) and links all CREDIT entries to it via `settled_by_id`.
4. `GET /api/ledger/balance` returns `{total_credits, overdue_credits, due_today_credits, upcoming_credits, total_debits, balance}`. Balance = all active CREDITs − unallocated DEBITs.

**Commission idempotency:** Partial UNIQUE index `WHERE voided=0 AND pedido_id IS NOT NULL` — one active commission per order. Estorno (pedido edit) voids the old CREDIT and creates a new one.

**`get_due_date_for_commission(ref_date, payment_day)`** in `commission_service.py` is wired into `generate_commission` using the vendedor's `PayrollConfig.payment_day`. `get_monday()` is centralized in `app/utils/date_utils.py`.

### Frontend — React 19 + TypeScript + Vite

Feature-based structure under `src/features/`. Each feature owns its components, hooks, and API layer.

**State management:** React Query (`@tanstack/react-query`) for server state. Auth state in Zustand store (`features/auth/authStore.tsx`). Offline state in Dexie (IndexedDB).

**API layer:** `src/api/http.ts` — `createApiRequest()` factory attaches JWT from auth store. Feature-specific hooks live in `features/<feature>/services/<feature>Api.ts`.

**Ledger UI:** `features/ledger/` — `LedgerPage.tsx` with subcomponents: `BalanceCard`, `EntryList`, `PendingPaymentsCard`, `AttributedOrdersCard`, `PaymentDialog`, `WeeklyGenerateBtn`.

**Router:** `src/app/router.tsx` — uses React Router v6 with lazy loading. `RequireAuth` wrapper redirects unauthenticated users to `/login`. Routes `capig/*` and `meta-gateway/*` are intentionally empty (handled by Flask).

**PWA:** Service Worker via Workbox. Offline data in Dexie. Push notifications via VAPID (`PushSubscription` model in backend).

---

## Key patterns

**New migration script template:**
```python
from app import create_app, db

def column_exists(table, col):
    from sqlalchemy import inspect
    return col in [c["name"] for c in inspect(db.engine).get_columns(table)]

if __name__ == "__main__":
    with create_app().app_context():
        if not column_exists("my_table", "new_col"):
            db.session.execute(db.text("ALTER TABLE my_table ADD COLUMN new_col TEXT"))
            db.session.commit()
```

**New route blueprint pattern:**
```python
bp = Blueprint("feature", __name__, url_prefix="/api/feature")

@bp.post("/")
@require_auth(roles=["admin"])
def create():
    current = request.current_user  # {user_id, role, name, email}
    ...
    return success_response(data, status_code=201)
```

**Test fixtures:** `conftest.py` provides `app` fixture with in-memory SQLite. Tests set `BCRYPT_LOG_ROUNDS=4` and `JWT_SECRET_KEY` before importing auth services. Admin password forced to `testpass` unless `PYTEST_KEEP_ADMIN_PASSWORD=1`.

---

## External integrations

| Integration | Config vars | Purpose |
|---|---|---|
| Meta CAPI | `META_PIXEL_ID`, `META_CAPI_ACCESS_TOKEN` | Purchase/Lead events via outbox |
| Nuvemshop | `NUVEMSHOP_APP_ID`, `NUVEMSHOP_CLIENT_SECRET` | Import site orders |
| UTMify | `UTMIFY_ENABLED`, `UTMIFY_API_TOKEN` | Revenue attribution |
| Google Sheets/Drive | `GOOGLE_CREDENTIALS_JSON` | Backup + leads export |
| GraphHopper / ORS | `GRAPHHOPPER_API_KEY` | Delivery route optimization |

Meta CAPI uses an **outbox pattern**: events are written to `MetaCapiOutbox` / `MetaCapiLeadOutbox` tables and flushed by a background scheduler (`meta_scheduler_entrypoint.py`).
