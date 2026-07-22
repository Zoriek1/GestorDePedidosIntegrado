# Cookie Policy

## Overview

This application does **not** use session cookies. All authentication is handled via JWT Bearer tokens sent in the `Authorization` header.

## Cookies Read

The backend reads the following cookies **server-side** for Meta attribution tracking only:

| Cookie | Purpose | Source |
|--------|---------|--------|
| `_fbc` | Facebook Click ID — attribute ad clicks to purchases | Meta Pixel |
| `_fbp` | Facebook Browser ID — identify browsers for attribution | Meta Pixel |

These values arrive as fields on `Pedido` / `Lead` records (populated by the frontend) and are forwarded to Meta Conversions API for event matching. The backend never sets, modifies, or issues these cookies.

## Cookies Set

**None.** The backend does not call `set_cookie`, `response.cookies`, or use `session[]` anywhere.

## SESSION_COOKIE_* Config

Not applicable. Flask's `SESSION_COOKIE_*` configuration keys (`SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE`) are irrelevant because no server-side or client-side sessions are used.

## CSRF Protection

CSRF attacks target cookie-based session authentication. Since this app uses JWT Bearer tokens (sent via `Authorization` header, not cookies), CSRF protection is **inherent** — browsers never auto-attach Bearer tokens to cross-origin requests. No additional CSRF token mechanism is needed.

## CORS Hardening

CORS is restricted to a hardcoded allowlist of HTTPS origins. The `Access-Control-Allow-Origin` header is reflected from the request's `Origin` only when it matches the allowlist. `Vary: Origin` is set to prevent cache poisoning.
