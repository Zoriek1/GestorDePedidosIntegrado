# Phase 0: Plano de Commits

Plano sugerido de commits para Phase 0, organizados em commits lógicos e incrementais.

## Estrutura de Commits

### Commit 1: Phase0-1 - Telemetry Module
**Arquivos:**
- `frontend/assets/js/telemetry.js` (novo)

**Mensagem:**
```
feat(phase0): add telemetry module with IndexedDB storage

- Add centralized event logging system
- IndexedDB storage in separate DB (puf_telemetry)
- Buffer/flush mechanism for performance (750ms interval)
- Aggressive sanitization of sensitive data
- Fallback to localStorage if IndexedDB fails
- Export logs as JSON file
- Max 200 logs stored (ring buffer)
```

---

### Commit 2: Phase0-2 - Global Error Handlers
**Arquivos:**
- `frontend/assets/js/app.js` (modificado)

**Mensagem:**
```
feat(phase0): add global error handlers and telemetry init

- Initialize telemetry on app startup
- Add window.onerror handler → telemetry
- Add window.onunhandledrejection handler → telemetry
- Log DB health check on startup
- Add Service Worker message listener
- Log SW registration errors
```

---

### Commit 3: Phase0-3 - API Instrumentation
**Arquivos:**
- `frontend/assets/js/api.js` (modificado)

**Mensagem:**
```
feat(phase0): instrument API layer with request/response logging

- Generate unique requestId for each request
- Log API requests (method, url, requestId)
- Log API responses (status, duration, requestId)
- Log API errors with context
- Normalize error responses (ok, status, code, message, details, requestId)
- Adjust default timeout to 15s
- Extend unhandledrejection handler to log to telemetry
```

---

### Commit 4: Phase0-4 - DB Instrumentation
**Arquivos:**
- `frontend/assets/js/db.js` (modificado)

**Mensagem:**
```
feat(phase0): instrument IndexedDB layer with logging and health check

- Add logging to DB init/open operations
- Log schema upgrades
- Log read/write operations (pendingPedidos, cache)
- Log sync operations with counts
- Add dbHealthCheck() method
- Log DB health on startup
```

---

### Commit 5: Phase0-5 - Diagnostics UI
**Arquivos:**
- `frontend/assets/js/diagnostics.js` (novo)
- `frontend/assets/js/app.js` (modificado - atalho)

**Mensagem:**
```
feat(phase0): add diagnostics modal UI

- Create diagnostics module with modal UI
- Show app version, online status, SW status, DB health
- Display last 50 logs in table format
- Add export logs button (download JSON)
- Add clear logs button with confirmation
- Add keyboard shortcut Ctrl+Shift+D (Cmd+Shift+D on Mac)
- Wire shortcut in app.js setupGlobalListeners()
```

---

### Commit 6: Phase0-6 - Wire Scripts
**Arquivos:**
- `frontend/index.html` (modificado)

**Mensagem:**
```
feat(phase0): wire telemetry and diagnostics scripts

- Add telemetry.js script (before api.js)
- Add diagnostics.js script (after router.js)
- Ensure correct load order for dependencies
```

---

### Commit 7: Phase0-7 - Documentation
**Arquivos:**
- `docs/phase0-smoke.md` (novo)
- `docs/phase0-notes.md` (novo)
- `docs/phase0-commits.md` (novo)

**Mensagem:**
```
docs(phase0): add golden flows checklist and implementation notes

- Add phase0-smoke.md with 12 critical user flows
- Add phase0-notes.md with implementation details
- Add phase0-commits.md with commit plan
- Document how to use diagnostics
- Document limitations and known issues
```

---

## Ordem de Execução

Execute os commits na ordem listada (1-7). Cada commit é independente e pode ser testado isoladamente, mas a ordem garante que dependências sejam resolvidas corretamente.

## Validação Após Cada Commit

Após cada commit, validar:
- [ ] Código compila sem erros
- [ ] App carrega sem erros no console
- [ ] Funcionalidades existentes continuam funcionando
- [ ] Logs aparecem em telemetry (após commit 1)
- [ ] Diagnóstico abre (após commit 5)

## Commit Final (Opcional)

Se preferir um único commit grande:

```
feat(phase0): implement freeze behavior instrumentation

Add comprehensive observability and diagnostics without changing
functional behavior:

- Telemetry module with IndexedDB storage and buffer/flush
- Global error handlers (window.onerror, unhandledrejection)
- API layer instrumentation (request/response/error logging)
- DB layer instrumentation (operations + health check)
- Diagnostics UI modal (Ctrl+Shift+D)
- Golden flows documentation
- Implementation notes

See docs/phase0-notes.md for details.
```

---

**Nota:** Preferir commits incrementais para facilitar review e rollback se necessário.

