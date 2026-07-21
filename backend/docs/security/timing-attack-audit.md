# Timing Attack Audit — GestorDePedidos Backend

**Date:** 2026-07-21
**Scope:** All Python files in `app/` that perform comparisons involving secrets, tokens, or passwords.

---

## Audit Points

| # | File | Line | Comparison | Mechanism | Verdict |
|---|------|------|-----------|-----------|---------|
| 1 | `app/services/auth_service.py` | 48 | `verify_password()` — plain vs bcrypt hash | `bcrypt.checkpw()` (constant-time internally) | SAFE |
| 2 | `app/services/auth_service.py` | 86 | `decode_token()` — JWT signature verification | `jwt.decode()` HS256 (HMAC-SHA256, constant-time) | SAFE |
| 3 | `app/services/oauth_state.py` | 64 | `verify_state()` — OAuth state signature | `hmac.compare_digest()` | SAFE |
| 4 | `app/services/track_token.py` | 92 | `parse_track_token()` — tracking token signature | `hmac.compare_digest()` | SAFE |
| 5 | `app/utils/crypto.py` | 51 | `decrypt_secret()` — AES-GCM tag verification | `AESGCM.decrypt()` (constant-time tag check by cryptography lib) | SAFE |
| 6 | `app/middleware.py` | 71 | `_verify_password()` — plaintext fallback path | `stored == provided` (Python `==`, timing-unsafe) | **WARN** |

---

## Detailed Analysis

### 1. `auth_service.verify_password()` — SAFE
Uses `bcrypt.checkpw()` which internally performs constant-time comparison of the derived key. Brute-force timing is dominated by the bcrypt cost factor (12 rounds), making timing attacks infeasible regardless of the comparison.

### 2. `auth_service.decode_token()` — SAFE
PyJWT's `jwt.decode()` with `algorithm="HS256"` uses HMAC-SHA256 for signature verification. The HMAC comparison is performed by the underlying cryptography library in constant time.

### 3. `oauth_state.verify_state()` — SAFE
Explicitly uses `hmac.compare_digest()` for the signature comparison. This is the recommended Python idiom for timing-safe string comparison.

### 4. `track_token.parse_track_token()` — SAFE
Explicitly uses `hmac.compare_digest()` for the truncated HMAC-SHA256 signature. Additionally, the token is short (10-char signature, ~60 bits) and the endpoint returns a generic 404, providing defense-in-depth.

### 5. `crypto.decrypt_secret()` — SAFE
AES-GCM authentication tag verification is performed by the `cryptography` library's `AESGCM.decrypt()`. The library uses constant-time comparison for the 16-byte GCM tag. An invalid tag raises `InvalidTag` immediately — there is no information leakage through timing.

### 6. `middleware._verify_password()` — WARN (known limitation)
**Line 71:** `return stored == provided` — uses Python's native `==` operator, which short-circuits on the first differing byte.

**Risk context:** This code path is only reached when the stored credential is **not** a bcrypt hash (i.e., legacy plain-text passwords set via `ADMIN_PASSWORD`/`ATENDENTE_PASSWORD`/`ENTREGADOR_PASSWORD` env vars). When `ADMIN_PASSWORD_HASH` is set with a bcrypt hash, `bcrypt.checkpw()` is used instead (SAFE).

**Mitigation:** Replace env-var plain-text passwords with bcrypt hashes. The `_admin_credential()` function already prefers `ADMIN_PASSWORD_HASH` over `ADMIN_PASSWORD`.

**Recommended fix (future):**
```python
# middleware.py, line 71
# Replace:
return stored == provided
# With:
import hmac as _hmac
return _hmac.compare_digest(stored, provided)
```
Note: `hmac.compare_digest` only works for `str` of equal length. For plain-text fallback, consider comparing encoded bytes with `hmac.compare_digest(stored.encode(), provided.encode())` and handling length-mismatch explicitly, or simply migrating to bcrypt hashes exclusively.

---

## Other `==` Comparisons in App Code (not vulnerable)

| File | Pattern | Reason not vulnerable |
|------|---------|----------------------|
| `app/services/integration_validation/__init__.py` | `field == "meta_capi_access_token"` | Comparing field names (not secrets) |
| `app/services/meta_capi.py` | `status_code == 401` | HTTP status code comparison |
| `app/routes/leads.py`, `app/routes/pedidos.py` | `Lead.token_rastreio == token` | SQLAlchemy ORM query filter — comparison happens in the database, not in Python timing |

---

## Conclusion

**5 of 6 comparison points are timing-safe.** The single timing-unsafe comparison (`middleware._verify_password` plain-text fallback) is a legacy compatibility path with known risk. The recommended action is to migrate all stored credentials to bcrypt hashes, which eliminates the vulnerable code path entirely.

No critical timing attack vulnerabilities were found in the production code paths.
