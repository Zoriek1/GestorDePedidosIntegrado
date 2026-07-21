# Grupo 3: Cookies Hardening + CORS

> **Tarefas:** 4.3 (Cookies) + 4.4 (CORS)

**Goal:** Auditar cookies, documentar decisão de não usar session cookies, e hardenar CORS.

**Architecture:** App usa JWT Bearer tokens — zero cookies de sessão. CORS usa flask-cors + after_request para refletir Origin com allowlist.

**Tech Stack:** Flask, flask-cors, pytest

## Global Constraints

- Flask 3.0.0, flask-cors 4.0.0
- HTTPS via Cloudflare Tunnel
- Origens permitidas: localhost, hostname local, gestaopedidos.planteumaflor.online, lpb.planteumaflor.com, planteumaflor.com

---

## Tarefa 3.1: Cookie audit — documentar decisão

**Files:**
- Create: `docs/security/cookie-policy.md`

- [ ] **Step 1: Verificar ausência de cookies**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\backend"
rg "set_cookie|response\.cookies|from flask import.*session" --type py -n
```

Esperado: zero resultados.

- [ ] **Step 2: Criar documentação**

```markdown
# Cookie Policy

## Decisão: Sem session cookies

O backend **não usa session cookies**. A autenticação é feita via JWT Bearer tokens
enviados no header `Authorization`.

### Cookies lidos (não escritos)

| Cookie | Origem | Uso |
|--------|--------|-----|
| `_fbc` | Facebook | Click ID para atribuição UTM |
| `_fbp` | Facebook | Browser ID para Meta CAPI |

Ambos são somente leitura — o backend extrai valores para tracking, nunca os define.

### Implicações de segurança

- **Sem CSRF via session cookies** — JWT Bearer é imune a CSRF clássico
- **Sem SESSION_COOKIE_SECURE** necessário — não há session cookies
- **Sem SameSite** necessário — não há cookies de sessão
- Tokens JWT são transmitidos no header Authorization, não em cookies

### Proteção contra XSS

- Tokens JWT devem ser armazenados em memoria (não localStorage em produção)
- Frontend deve usar httpOnly se armazenar tokens em cookies (decisão do frontend)
```

- [ ] **Step 3: Commit**

```bash
git add docs/security/cookie-policy.md
git commit -m "docs(security): cookie audit - document no session cookies decision"
```

---

## Tarefa 3.2: CORS hardening — `Vary: Origin`

**Files:**
- Modify: `app/cors.py:116-126`

**Interfaces:**
- Modifica: `_cors_reflect_origin()` after_request hook

- [ ] **Step 1: Verificar bug atual**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\backend"
rg "Vary" --type py -n
```

Esperado: zero resultados — confirma que `Vary: Origin` não está setado.

- [ ] **Step 2: Adicionar `Vary: Origin`**

```python
# app/cors.py, dentro de _cors_reflect_origin(), após line 125:
@app.after_request
def _cors_reflect_origin(response):
    if not request.path.startswith("/api/"):
        return response
    origin = getattr(request, "origin", None) or request.headers.get("Origin")
    if origin:
        origin = origin.strip()
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"  # NOVO
    return response
```

- [ ] **Step 3: Verificar se flask-cors já adiciona Vary**

Se `flask-cors` já adiciona `Vary`, pode haver duplicata. Verificar com:

```bash
python -c "
from app import create_app
app = create_app()
with app.test_client() as c:
    r = c.get('/api/health', headers={'Origin': 'https://gestaopedidos.planteumaflor.online'})
    print('Vary:', r.headers.get('Vary'))
    print('ACAO:', r.headers.get('Access-Control-Allow-Origin'))
"
```

- [ ] **Step 4: Testar**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\backend"
python -m pytest tests/ -k "cors" -v
```

- [ ] **Step 5: Commit**

```bash
git add app/cors.py
git commit -m "fix(security): add Vary: Origin header to CORS responses"
```

---

## Tarefa 3.3: CORS — preflight cache

**Files:**
- Review: `app/cors.py:104-114`

- [ ] **Step 1: Avaliar max_age**

Flask-CORS suporta `max_age` para cache de preflight. Com `max_age=3600`, browsers cacheiam preflight por 1h.

```python
# app/cors.py, adicionar ao dict de resources:
CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600,  # NOVO: cache preflight por 1h
    }
})
```

- [ ] **Step 2: Commit**

```bash
git add app/cors.py
git commit -m "perf(security): add CORS preflight cache (max_age=3600)"
```
