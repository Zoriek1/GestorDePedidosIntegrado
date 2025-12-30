# Phase 1.3.1 - Relatório de Implementação e Correções

**Data:** 30 de Dezembro de 2024  
**Status:** ✅ Concluído (PWA Hardening + Correções de Ambiente)

Este documento resume todas as alterações realizadas durante a Phase 1.3.1, incluindo funcionalidades de hardening do PWA e correções críticas no ambiente de desenvolvimento backend/frontend.

---

## 1. Hardening do PWA (Offline & Sync)

Implementamos melhorias de robustez para tornar o comportamento offline previsível e seguro.

### A) Cache e Armazenamento (Dexie)
- **Schema Atualizado (`frontend_v2/src/lib/offline/db.ts`):**
  - Adicionado suporte a `tag` na tabela `cache` para políticas granulares.
  - Adicionados campos `status`, `blocked`, `lastStatus` na tabela `outbox` para rastreamento de falhas.
  - Implementada migração de schema (v1 -> v2).
- **Lógica de Cache (`frontend_v2/src/lib/offline/cache.ts`):**
  - **TTL por Tag:** `health` (5m), `stats` (1h), `pedidos`/`default` (24h).
  - **Cap Global:** Limite de 200 entradas para evitar crescimento indefinido.
  - **Cleanup:** Função `cleanupCache()` remove expirados e aplica LRU (Least Recently Used) no excesso.
- **Integração:** Cleanup roda no startup do `OfflineProvider` (best-effort, 1x/dia).

### B) Outbox Pattern (Sincronização)
- **Novos Status:** `PENDING`, `PROCESSING`, `FAILED`, `DONE`.
- **Tratamento de Erros 4xx (`frontend_v2/src/lib/offline/outbox.ts`):**
  - **401/403 (Auth):** Marca item como `blocked=true`, status `FAILED`. Interrompe processamento da fila até re-login.
  - **Outros 4xx (Validação):** Marca item como `blocked=true`, status `FAILED`. Exige intervenção manual (Retry/Delete).
  - **5xx/Network:** Mantém `PENDING` e incrementa tentativas (até 3x).
- **Force Sync Seguro:** O botão "Forçar Sincronização" (e o flush automático) agora verifica se há itens bloqueados por autenticação antes de tentar processar, evitando loops de erro.

### C) Gating e Segurança
- **Diagnósticos em Produção:**
  - Rotas `/offline-diagnostics` e `/test-offline` agora são protegidas por flag.
  - Só acessíveis se `import.meta.env.DEV` for true **OU** `VITE_ENABLE_OFFLINE_DIAGNOSTICS=true`.
  - Em produção sem a flag, redireciona para `/`.
- **Alterações em `router.tsx`:** Implementada lógica de `Navigate` condicional.

### D) UX de Autenticação Offline
- **RequireAuth (`frontend_v2/src/features/auth/RequireAuth.tsx`):**
  - Se offline + sem credenciais: exibe tela "Sem conexão para login" em vez de redirecionar para `/login` (evita loop).
  - Se offline + com credenciais: permite acesso ao app (cache).
- **Global Auth Handler:**
  - `api/http.ts` dispara evento `puf_auth_invalid` ao receber 401/403.
  - `authStore.tsx` escuta o evento e força logout limpo.

### E) Observabilidade (Diagnósticos)
- **Nova UI (`OfflineDiagnostics.tsx`):**
  - Contadores do **Workbox CacheStorage** (health, pedidos, images).
  - Estatísticas do **Dexie Cache** (total, por tag, timestamp mais antigo/recente).
  - Status detalhado do **Outbox** (Pending, Failed, Blocked).
  - Estimativa de uso de Storage do navegador.
  - Botão "Retry" com confirmação para itens bloqueados.

---

## 2. Correções de Ambiente (Backend & Frontend)

Durante os testes, identificamos e corrigimos bloqueios críticos que impediam o app de rodar localmente.

### A) Backend (Flask)
1.  **Erro de Importação `Config`:**
    - **Problema:** `main.py` importava `Config`, mas `app/config.py` exportava `BaseConfig`.
    - **Correção:** Adicionado alias `Config = BaseConfig` em `backend/app/config.py` para manter compatibilidade.
2.  **Travamento no Startup (Porta em uso/Recursão):**
    - **Problema:** O reloader do Flask (modo debug) criava um processo filho que tentava verificar a porta 5000, achava-a ocupada pelo processo pai, e travava pedindo confirmação no stdin (inacessível).
    - **Correção (`backend/main.py`):** Adicionada verificação `if os.environ.get("WERKZEUG_RUN_MAIN") == "true"` para pular o check de porta no processo filho.
3.  **Logs de Debug:**
    - Adicionada instrumentação temporária (agora removível) em `main.py`, `auth.py`, `middleware.py` para rastrear o fluxo de autenticação e startup.

### B) Frontend (Vite)
1.  **Erro 500 / Credenciais Inválidas:**
    - **Problema:** Backend rodava em **HTTPS** (porta 5000), mas o proxy do Vite (`vite.config.ts`) apontava para **HTTP**. O proxy falhava com "Connection Reset" e o Vite retornava 500 para o frontend.
    - **Correção:**
        - Atualizado `vite.config.ts` para usar `VITE_API_TARGET` (default http) e permitir `secure: false` (self-signed certs).
        - Criado `.env` no frontend com `VITE_API_TARGET=https://localhost:5000`.
        - Habilitado proxy também no modo `vite preview`.

---

## 3. Próximos Passos (Recomendação)

O ambiente agora está estável e o PWA hardening está implementado.

1.  **Limpeza:** Remover os logs de instrumentação (`log_debug`) adicionados ao backend (`main.py`, `middleware.py`, `auth.py`, `config.py`) pois já cumpriram seu propósito.
2.  **Validação Final:** Rodar o checklist de smoke test (`docs/phase1_3-smoke.md`) para garantir que tudo (offline, sync, auth) está funcionando como esperado.
3.  **Deploy/Merge:** As alterações estão prontas para serem integradas à branch principal.

**Arquivos Modificados na Fase:**
- `frontend_v2/` (variados componentes de UI, lógica offline, config)
- `backend/app/config.py`, `backend/main.py` (correções de startup)
- `docs/` (documentação técnica e de testes)

