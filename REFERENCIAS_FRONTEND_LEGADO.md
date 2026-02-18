# Referências ao Frontend Legado (frontend/) no Projeto

Este documento lista todos os lugares onde o frontend legado (`frontend/`) ainda é referenciado no projeto.

## 📁 Estrutura de Diretórios

### Diretório Completo do Frontend Legado
- **`frontend/`** - Diretório completo do frontend legado ainda existe no projeto
  - `frontend/index.html`
  - `frontend/manifest.json`
  - `frontend/package.json`
  - `frontend/sw.js` (Service Worker)
  - `frontend/pages/` (HTML pages: clientes.html, criar-pedido.html, fontes-pedido.html, login.html, painel.html, rota-entrega.html)
  - `frontend/assets/js/` (JavaScript vanilla)
  - `frontend/assets/css/style.css`

---

## 🔧 Código Backend

### 1. `backend/app/cli.py` (Linha 371)
```python
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
```
**Função:** `update_service_worker_cache()` - Atualiza versão do cache do service worker do frontend legado

### 2. `backend/scripts/server/utils/atualizar_cache_frontend.bat`
- **Linha 2:** Comentário menciona "frontend"
- **Linha 8:** `set SW_FILE=frontend\sw.js` - Referência direta ao Service Worker do frontend legado

---

## 📚 Documentação

### 3. `docs/dev.md`
- **Linha 123:** Seção "Frontend Legacy" (`/frontend`)
- **Linha 527:** Outra menção a "Frontend Legacy" (`/frontend`)

### 4. `docs/architecture.md`
- **Linha 12:** "- **Frontend Legacy** (`/frontend`): PWA vanilla JS com Service Worker e IndexedDB"
- **Linha 15:** "Ambos os frontends consomem a mesma API REST em `/api/*`."
- **Linha 74:** Seção "### Frontend Legacy (`/frontend`)"
- **Linha 292:** Outra menção a "Frontend Legacy"
- **Linha 295:** "Ambos os frontends consomem a mesma API REST em `/api/*`."
- **Linha 354:** "### Frontend Legacy (`/frontend`)"

### 5. `docs/migration_report.md`
- **Linha 12:** Tabela comparativa menciona `frontend/` (HTML/JS/jQuery)
- **Linha 30:** "- **Ponto de Atenção:** `backend/app/static.py` ainda aponta para `../../frontend` (V1)." (⚠️ **OBSOLETO** - já foi corrigido para `frontend_v2/dist`)
- **Linha 37:** "### Passo 1: Build do Frontend V2"
- **Linha 53:** "Futuramente, a pasta `frontend` antiga pode ser arquivada ou removida."

### 6. `docs/routes.json`
- **Linhas 8-10, 17-19:** Referências genéricas a `serve_frontend` (não específicas ao legado)

### 7. `docs/routes.md`
- **Linhas 15-16:** Referências genéricas a `serve_frontend` (não específicas ao legado)

### 8. `backend/docs/ARCHITECTURE.md`
- **Linha 197:** "- **Frontend V1**: Diretório `frontend/` (HTML/JS puro) - Ainda existe para fallback, mas não deve receber novas features"

---

## 💬 Comentários e Referências Genéricas

### 9. `backend/app/routes/api.py`
- **Linha 4:** Comentário "API completa para o frontend PWA" (genérico)
- **Linha 49:** Comentário sobre formatação de telefone no frontend (genérico)
- **Linha 1763:** Comentário sobre CORS para frontend (genérico)
- **Linha 1939:** Comentário sobre formato esperado pelo frontend (genérico)

### 10. `backend/app/routes/meta_gateway.py`
- **Linha 359:** Comentário "Este endpoint recebe eventos do frontend/outras fontes" (genérico)

### 11. `backend/app/static.py`
- **Linha 4:** Comentário "Gerencia rotas para servir arquivos do frontend PWA" (genérico)
- **Linha 64:** Comentário sobre rotas estáticas do frontend (genérico)
- **Linha 81:** Função `serve_frontend()` (nome genérico, mas já aponta para `frontend_v2/dist`)

### 12. `backend/app/errors.py`
- **Linha 26:** Comentário sobre frontend funcionar corretamente (genérico)

### 13. `backend/app/routes/pedidos.py`
- **Linha 291:** Comentário sobre formatação de telefone no frontend (genérico)

### 14. `backend/app/middleware.py`
- **Linha 554:** Comentário sobre arquivos necessários para frontend (genérico)

### 15. `backend/test_server.py`
- **Linha 39:** Comentário "Testando / (frontend)..." (genérico)

### 16. `backend/test_init.py`
- **Linha 34:** Comentário "Verificando frontend..." (genérico)

### 17. `backend/docs/META_FBC_FBP.md`
- **Linha 21:** Comentário sobre frontend enviar dados (genérico)

### 18. `backend/docs/CLOUDFLARE_TUNNEL_META_GATEWAY.md`
- **Linha 24:** Comentário sobre rotas do frontend (genérico)

### 19. `backend/docs/TROUBLESHOOTING.md`
- **Linhas 102, 108, 177, 319, 323, 333:** Múltiplas referências genéricas a "frontend"

### 20. `backend/docs/OPENAPI.md`
- **Linha 7:** Comentário sobre documentação usada pelo frontend (genérico)

---

## 📝 Código Frontend V2

### 21. `frontend_v2/src/features/pedidos/OrdersPage.tsx`
- **Linha 102:** Comentário "Isso corresponde ao comportamento do frontend V1"

---

## ⚙️ Configuração e Scripts

### 22. `.github/workflows/ci.yml`
- **Linha 116-117:** Job "Frontend" (mas já aponta para `frontend_v2`)

---

## 📦 Arquivos de Configuração do Frontend Legado

### 23. `frontend/package.json`
- Arquivo de dependências do frontend legado ainda existe

### 24. `frontend/package-lock.json`
- Lock file do frontend legado ainda existe

### 25. `frontend/.gitignore`
- Gitignore do frontend legado ainda existe

---

## 🎯 Resumo por Prioridade

### 🔴 **Alta Prioridade (Código Ativo)**
1. `backend/app/cli.py` - Função `update_service_worker_cache()` ainda referencia `frontend/`
2. `backend/scripts/server/utils/atualizar_cache_frontend.bat` - Script ainda atualiza SW do frontend legado
3. **Diretório `frontend/` completo** - Ainda existe no projeto

### 🟡 **Média Prioridade (Documentação)**
4. `docs/migration_report.md` - Documentação desatualizada (menciona que static.py aponta para frontend, mas já foi corrigido)
5. `docs/dev.md` - Múltiplas referências ao Frontend Legacy
6. `docs/architecture.md` - Múltiplas referências ao Frontend Legacy
7. `backend/docs/ARCHITECTURE.md` - Menciona Frontend V1 como fallback

### 🟢 **Baixa Prioridade (Comentários Genéricos)**
8. Vários arquivos com comentários genéricos sobre "frontend" (não específicos ao legado)

---

## ✅ Já Corrigido

- ✅ `backend/app/static.py` - **JÁ APONTA PARA `frontend_v2/dist`** (linha 126)
- ✅ `.github/workflows/ci.yml` - **JÁ USA `frontend_v2`** (linha 131)

---

## 📋 Recomendações

1. **Remover ou arquivar** o diretório `frontend/` completo após validação
2. **Atualizar ou remover** `backend/app/cli.py` - função `update_service_worker_cache()`
3. **Atualizar ou remover** `backend/scripts/server/utils/atualizar_cache_frontend.bat`
4. **Atualizar documentação** em `docs/migration_report.md` (remover referência obsoleta ao static.py)
5. **Decidir** se manter referências genéricas a "frontend" em comentários ou especificar "frontend_v2"
