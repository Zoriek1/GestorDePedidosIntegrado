# Security Mechanisms — GestorDePedidos Backend

**Last updated:** 2026-07-21

---

## Active Mechanisms

### 1. Rate Limiting (`app/middleware.py`)
- **In-memory** per-IP sliding window: 60 req/min, 1000 req/hour (configurable).
- Applied globally via `before_request`; excluded for `/assets/` paths.
- Returns HTTP 429 with `Retry-After` header.
- IP resolution (`_get_client_ip`) trusts `CF-Connecting-IP` and `X-Real-IP` only when `remote_addr` is a private/Docker address — prevents external spoofing.

### 2. Authentication — JWT (`app/services/auth_service.py`)
- HS256 (HMAC-SHA256) signing via PyJWT.
- Secret sourced from `JWT_SECRET_KEY` or `SECRET_KEY` env vars.
- Configurable expiration via `JWT_EXPIRATION_HOURS` (default 24h).
- Used by `@requires_edit_auth`, `@requires_role`, `@requires_any_role` decorators.

### 3. Authentication — HTTP Basic (`app/middleware.py`)
- Legacy auth path for backward compatibility.
- Supports bcrypt hashes (`ADMIN_PASSWORD_HASH` env var) and plain-text (`ADMIN_PASSWORD` env var, deprecated).
- Tenant isolation enforced via `bind_single_store_identity()`.

### 4. Encryption — AES-GCM (`app/utils/crypto.py`)
- AES-256-GCM (authenticated encryption) for persisting secrets (e.g., OAuth tokens, API keys).
- Key derived via SHA-256 from `SECRET_KEY` + purpose string.
- Nonce: 12 bytes random (`os.urandom`).
- Encrypted format: `v1:<base64(nonce + ciphertext + tag)>`.

### 5. CORS (`app/`)
- Configured via Flask-CORS or custom middleware (check `app/__init__.py` or `config.py`).
- Ensure origins are restricted to known frontend domains in production.

### 6. RBAC — Role-Based Access Control (`app/middleware.py`)
- Roles: `admin`, `atendente`, `vendedor`, `entregador`.
- Permissions defined per role in `PERMISSIONS` dict.
- Decorators: `@requires_role`, `@requires_any_role`, `@requires_permission`.
- Admin has wildcard `["*"]` access.

### 7. OAuth State Signing (`app/services/oauth_state.py`)
- HMAC-SHA256 signed state parameter with expiration (default 600s).
- Bound to `store_ref_id` and `provider` — prevents cross-tenant and cross-provider replay.
- Verified via `hmac.compare_digest()` (timing-safe).

### 8. Public Tracking Tokens (`app/services/track_token.py`)
- Compact signed tokens for order tracking (no auth required).
- HMAC-SHA256 signature truncated to 10 chars (~60 bits).
- Generic 404 response prevents token enumeration.
- Revocable via `_SALT` rotation.

---

## Known Limitations

| # | Limitation | Risk | Mitigation |
|---|-----------|------|------------|
| 1 | **Rate limiting is in-memory** (`request_counts` dict) | Resets on process restart; not shared across workers in multi-process deployments (e.g., gunicorn with multiple workers). | For production multi-worker: use Redis-backed rate limiting (e.g., Flask-Limiter with Redis storage). |
| 2 | **No automatic key rotation** for `SECRET_KEY` / `JWT_SECRET_KEY` | If the key is compromised, all existing tokens and encrypted secrets remain valid until manually rotated. | Implement key versioning or manual rotation procedures. Old tokens encrypted with a previous key should be re-encrypted. |
| 3 | **UTMify integration is synchronous** (`app/services/utmify_service.py`) | Webhook/blocking calls to UTMify can delay responses or cause timeouts under load. | Consider async dispatch (background thread, Celery task, or queue). |
| 4 | **Plain-text password fallback** in `middleware._verify_password()` | Timing-unsafe comparison for legacy plain-text credentials. | Migrate all credentials to bcrypt hashes via `ADMIN_PASSWORD_HASH`. |
| 5 | **Access logging writes to local filesystem** (`log_access`) | Logs stored in `app/logs/` — may not persist in containerized/serverless environments. | Use structured logging to stdout/stderr and a log aggregation service. |
| 6 | **No CSRF protection on state-changing endpoints** | JWT Bearer auth mitigates this for API clients, but browser-based consumers could be vulnerable. | Ensure frontend uses `Authorization` header (not cookies) for state-changing requests. |
