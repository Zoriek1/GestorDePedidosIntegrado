# Spec 11 — Próximos passos (roadmap pós-implementação)

> **Data:** 2026-07-21, revisado em 2026-07-22. Fases A–F implementadas, Gate 0 concluído.
> Este documento define o roadmap após a conclusão da implementação multi-tenant.
> O deploy imediato segue o runbook [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).

---

## Revisão de 2026-07-22 — lacunas encontradas depois do "completo"

O status de 21/07 (“implementação completa, 786/786”) não capturava quatro defeitos
que **só aparecem a partir da segunda loja**. Com uma loja só, a suíte inteira passa
mesmo com eles presentes. Corrigidos nos commits `ae78c4e`..`a5e3e9c`:

| Defeito | Área que o spec dava como ✅ |
|---|---|
| `secure_runtime_config()` chamado sem `store_ref_id` em 4 pontos — 500 em `/api/admin/marketing-conversions/config` | Fase D (workers por empresa) e Fase F (hardening) |
| Índice `ux_users_name_active_ci` era único **global**: duas lojas não podiam ter uma “Maria” ativa cada | Critério global “duas lojas operam simultaneamente” |
| Login buscava usuário sem filtrar loja; e-mails iguais em tenants distintos entrariam na conta errada | Spec 04 — resolução de tenant |
| Sem caminho de provisionamento: `Store` só era criada em testes e migrations | §4 previa `INSERT` manual |

Entregue acima do previsto: **`flask cli create-store`** (Store + StoreSetting + admin
numa transação) substitui o `INSERT INTO stores` manual do §4 e antecipa parte do
“onboarding de nova loja” listado como futuro no §8.

Também entregue: `stores.email_domain` resolve o tenant no login pelo domínio do
e-mail (`maria@floriculturax.com` → loja X), com fallback para busca global quando
o domínio não pertence a nenhuma loja.

**Lição para o processo:** critério de conclusão de trabalho multi-tenant precisa
incluir um teste com **duas** lojas. `backend/tests/test_tenant_isolation.py` passa a
ser esse piso.

---

## 1. Deploy em produção (prioridade máxima)

Ver runbook completo em [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).

| Passo | Ação | Estado |
|---|---|---|
| Fase 1.1 | Backup do banco de produção (dump + verificação de restore) | ⬜ Pendente |
| Fase 1.2 | `git pull` branch `multi-tenant`, `docker compose build && up -d` | ⬜ Pendente |
| Fase 1.3 | Smoke autenticado single-store (login, pedido, lead, Bling/Meta) | ⬜ Pendente |
| Fase 2.1 | Confirmar `store_settings` da default existe (1 linha) | ⬜ Pendente |
| Fase 2.2 | `GET /api/config/integrations` → flags `has_*` corretas, campos mascarados | ⬜ Pendente |
| Fase 2.3 | `uses_environment_fallback = False` para a default | ⬜ Pendente |

---

## 2. Métricas e alertas por tenant

Após o deploy em produção, antes de ativar a 2ª loja:

- [ ] **Taxa de erro por `store_ref_id`:** instrumentar middleware/error handlers para emitir métrica com tag `store` (ID + slug).
- [ ] **Latência por tenant:** `before_request` / `after_request` com `g.tenant_store_id`.
- [ ] **Volume por tenant:** número de pedidos, leads, envios Meta/Bling por dia por loja.
- [ ] **Alertas:** configurar thresholds — taxa de erro > 1%, latência p95 > 2s, zero eventos Meta em 24h para loja ativa.
- [x] **Health endpoint:** `GET /api/admin/tenant-health` — já implementado em `app/routes/admin.py:97`.

Ferramentas sugeridas: Prometheus + Grafana (já existentes no stack?) ou logs estruturados com export para Datadog/CloudWatch. Se não houver infra de métricas, começar com logs JSON estruturados por tenant.

---

## 3. Revisão de segurança

Antes de liberar multiempresa para produção:

- [ ] **Timing attack em tenant resolution:** confirmar que `g.tenant_store_id` é resolvido antes de qualquer query de negócio e que IDs inválidos não vazam tempo de processamento diferente.
- [x] **Segredos em memória:** implementado em `app/services/secure_config.py` — o context manager zera as chaves de `SECRET_KEYS` e força `gc.collect()` na saída.
- [ ] **Cookies de sessão:** `SameSite=Strict`, `Secure`, `HttpOnly`, `__Host-` prefix. Validar que o JWT nunca é armazenado em `localStorage` (confirmado no Zustand, mas auditar).
- [ ] **CORS:** revisar se `cors.py` está restrito às origens conhecidas por ambiente.
- [ ] **Rate limiting por tenant:** evitar que uma loja consuma todos os recursos (ex.: worker enfileiramento em loop). Implementar `MAX_OUTBOX_PER_CYCLE` por `store_ref_id`.
- [ ] **Chaves de criptografia:** documentar procedimento de rotação de `SECRET_KEY` (impacta todos os segredos AES-GCM). Validar backup/restore com chave rotacionada.

---

## 4. Ativar 2ª loja em produção

Após Fases 1–2 + métricas + revisão de segurança:

- [ ] Provisionar a 2ª loja com um único comando (substitui os três passos manuais anteriores):
      ```bash
      docker compose exec backend flask cli create-store \
        --name "Loja 2" --slug loja-2 \
        --email-domain loja2.com.br --admin-email dono@loja2.com.br
      ```
      Cria `Store` + `StoreSetting` + usuário admin numa transação.
- [ ] **Não** setar `FORCE_MULTI_TENANT`: `is_multi_store()` liga sozinho ao existir a 2ª loja ativa. A flag serve só para exercitar o modo estrito com uma loja em homologação.
- [ ] Resolver o §6 (landing page → loja) **antes** se a loja 2 tiver captação pública de leads.
- [ ] Smoke pós-ativação: admin loja 1 vê só loja 1; admin loja 2 vê só loja 2; worker processa ambas.
- [ ] Monitorar métricas por 48h antes de declarar sucesso.

---

## 5. UTMify síncrono — ✅ concluído

Estava marcado como WIP não commitado; na verdade já está implementado e no
histórico. `build_utmify_order_payload()` e `post_utmify_order()` em
`app/services/utmify_api.py`, acionados por `app/utils/utmify_helper.py` a partir de
`pedido_repository.py` e `routes/pedidos.py`.

Já é tenant-aware: `utmify_helper.py:100` usa
`secure_runtime_config(getattr(pedido, "store_ref_id", None))`.

- [x] Dispatcher síncrono implementado.
- [x] Credencial resolvida por loja.
- [ ] Falta apenas o teste de isolamento com 2 lojas e tokens distintos.

---

## 6. Landing page → store mapping

Hoje `resolve_public_write_company()` sempre resolve `default`. Para suportar múltiplas lojas com leads públicos:

- [ ] Definir estratégia de mapeamento: domínio (ex.: `loja1.com.br` → store 1, `loja2.com.br` → store 2) ou path/utm (ex.: `?store=loja-2`).
- [ ] Implementar em `resolve_public_write_company()`.
- [ ] Se for por domínio, adicionar verificação de `Host` header no middleware.
- [ ] Testar lead público com duas lojas em staging.

---

## 7. Cleanup de débitos técnicos

Débitos preexistentes às Fases A–F:

| Ferramenta | Débito | Prioridade |
|---|---|---|
| Ruff | ✅ **zerado** (verificado 2026-07-22 em `app/ tests/ scripts/`) | — |
| Black | ✅ **zerado** — 318 arquivos conformes | — |
| `tsc --noEmit` | Erros preexistentes no frontend, a maioria `@mui/icons-material` sem os membros exportados | Média |
| Testes de worker em Postgres | Cobertos em SQLite; validar em Postgres real antes da 2ª loja | Baixa |
| Documentação de API | Swagger/OpenAPI incompleto para novos endpoints | Baixa |

Atenção ao rodar o typecheck: o `tsconfig.json` da raiz é solution-style (`files: []`
com `references`), então **`npx tsc --noEmit` não checa nada** — é preciso
`npx tsc -p tsconfig.app.json --noEmit`. Esse no-op mascarou um `useToast` usado sem
import no `IntegrationModal`, que teria quebrado o modal em runtime.

---

## 8. Funcionalidades futuras (fora do escopo multi-tenant)

Itens que não bloqueiam a operação multiempresa mas são desejáveis:

- **Dashboard por loja:** métricas de vendas, leads, entregas no frontend filtráveis por tenant (admin multi-loja).
- **Onboarding de nova loja:** wizard de criação de loja + import de configurações via UI (hoje é manual).
- **Multi-admin cross-tenant:** um super admin que pode alternar entre lojas (hoje cada usuário pertence a 1 loja).
- **Integração Bling por loja com UI:** hoje Bling usa credencial estática; ideal seria tela de OAuth similar à Nuvemshop.
- **Notificações push por loja:** escopo de `push_subscriptions` já tem `store_ref_id`; garantir que VAPID keys podem ser por loja no futuro.

---

## Resumo de prioridades

Atualizado em 2026-07-22.

| Ordem | Item | Bloqueia 2ª loja? | Estado |
|---|---|---|---|
| 1 | Fase 1 — Deploy com 1 loja | Sim (primeiro passo) | ⬜ Pendente |
| 2 | Fase 2 — Verificar `store_settings` | Sim | ⬜ Pendente |
| 3 | **Landing page → store mapping (§6)** | **Sim**, se a loja 2 captar leads públicos | ⬜ Pendente |
| 4 | Métricas e alertas por tenant | Recomendado | 🟨 Health endpoint pronto; falta instrumentar |
| 5 | Revisão de segurança | Recomendado | 🟨 Segredos, CORS, timing e rotação feitos; falta rate limit por tenant |
| 6 | Ativar 2ª loja em produção | — (é o objetivo) | ⬜ CLI pronto |
| 7 | UTMify síncrono | Não | ✅ Implementado; falta teste de 2 lojas |
| 8 | Cleanup de débitos | Não | 🟨 Ruff/Black zerados; `tsc` pendente |

O §6 subiu de prioridade: `resolve_public_store_id()` em
`app/services/auth_context.py:179` devolve **sempre** a loja `default`, então todo
lead público cairia na loja 1. É a única lacuna que bloqueia de fato a operação
multiempresa.

---

## Referências cruzadas

- Estado atual completo: [08-estado-atual-e-proximos-passos.md](08-estado-atual-e-proximos-passos.md)
- Blueprint executável: [09-blueprint-fases-c-d.md](09-blueprint-fases-c-d.md)
- Runbook de deploy: [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md)
- Specs temáticas: [01](01-banco-models-migrations.md) a [07](07-seguranca-testes-rollout.md)