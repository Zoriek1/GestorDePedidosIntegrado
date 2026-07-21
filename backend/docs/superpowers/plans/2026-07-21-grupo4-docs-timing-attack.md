# Grupo 4: Documentação Alertas + Timing Attack Audit

> **Tarefas:** 3.3 (Documentação) + 4.1 (Timing attack)

**Goal:** Auditar resistência a timing attacks e criar documentação de segurança.

**Architecture:** bcrypt (timing-safe) para senhas, HMAC (timing-safe) para tokens, AES-GCM para encryption.

**Tech Stack:** bcrypt, PyJWT, hmac, cryptography

## Global Constraints

- bcrypt 4.x, PyJWT 2.x, cryptography 41.x
- HS256 para JWT (HMAC-based)
- AES-GCM para encrypt/decrypt de secrets

---

## Tarefa 4.1: Timing attack audit

**Files:**
- Review: `app/services/auth_service.py:45-50` (verify_password)
- Review: `app/services/auth_service.py:80-91` (decode_token)
- Review: `app/services/oauth_state.py` (sign_state/verify_state)
- Review: `app/services/track_token.py` (make_track_token/parse_track_token)
- Review: `app/utils/crypto.py` (encrypt_secret/decrypt_secret)

- [ ] **Step 1: Auditar `verify_password`**
  - `bcrypt.checkpw()` — ✅ SAFE (bcrypt internal timing-safe comparison)

- [ ] **Step 2: Auditar `decode_token`**
  - `jwt.decode()` HS256 — ✅ SAFE (HMAC internal timing-safe comparison)

- [ ] **Step 3: Auditar `oauth_state.py`**
  - Verificar se usa `hmac.compare_digest()` — ✅ SAFE

- [ ] **Step 4: Auditar `track_token.py`**
  - Verificar se usa `hmac.compare_digest()` — ✅ SAFE

- [ ] **Step 5: Auditar `crypto.py`**
  - AES-GCM tag verification — ✅ SAFE (cryptography library)

- [ ] **Step 6: Buscar comparações inseguras com `==`**

```bash
rg "==\s*['\"].*secret|secret.*==\s*['\"]" --type py -n -i
```

- [ ] **Step 7: Criar `docs/security/timing-attack-audit.md`**

- [ ] **Step 8: Commit**

```bash
git add docs/security/timing-attack-audit.md
git commit -m "docs(security): timing attack audit - no vulnerabilities found"
```

---

## Tarefa 4.2: Documentação de alertas de segurança

**Files:**
- Create: `docs/security/security-alerts.md`

- [ ] **Step 1: Criar documentação com:**
  - Rate Limiting (60/min global, 10/min login, in-memory)
  - Autenticação (JWT Bearer, RBAC, sem session cookies)
  - Criptografia (AES-GCM, key derivation)
  - CORS (allowlist, Vary: Origin)
  - IP Resolution (CF-Connecting-IP preferido)
  - Secure Config (zeroing de segredos)
  - Pontos de atenção (rate limit in-memory, sem rotação automática)

- [ ] **Step 2: Commit**

```bash
git add docs/security/security-alerts.md
git commit -m "docs(security): security mechanisms and alerts documentation"
```
