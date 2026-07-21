# Spec 11 — Próximos passos (roadmap pós-implementação)

> **Data:** 2026-07-21. Fases A–F implementadas, Gate 0 concluído, suíte 786/786.
> Este documento define o roadmap após a conclusão da implementação multi-tenant.
> O deploy imediato segue o runbook [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).

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
- [ ] **Health endpoint:** `GET /api/admin/tenant-health` (admin only) — resumo por loja (pedidos/dia, outbox pendente, último envio Meta, status OAuth).

Ferramentas sugeridas: Prometheus + Grafana (já existentes no stack?) ou logs estruturados com export para Datadog/CloudWatch. Se não houver infra de métricas, começar com logs JSON estruturados por tenant.

---

## 3. Revisão de segurança

Antes de liberar multiempresa para produção:

- [ ] **Timing attack em tenant resolution:** confirmar que `g.tenant_store_id` é resolvido antes de qualquer query de negócio e que IDs inválidos não vazam tempo de processamento diferente.
- [ ] **Segredos em memória:** após `runtime_config()`, os segredos descriptografados (`META_CAPI_ACCESS_TOKEN`, `GA4_API_SECRET`, `UTMIFY_API_TOKEN`) devem ser zerados via `del` + `gc.collect()` ao fim do request/ciclo do worker.
- [ ] **Cookies de sessão:** `SameSite=Strict`, `Secure`, `HttpOnly`, `__Host-` prefix. Validar que o JWT nunca é armazenado em `localStorage` (confirmado no Zustand, mas auditar).
- [ ] **CORS:** revisar se `cors.py` está restrito às origens conhecidas por ambiente.
- [ ] **Rate limiting por tenant:** evitar que uma loja consuma todos os recursos (ex.: worker enfileiramento em loop). Implementar `MAX_OUTBOX_PER_CYCLE` por `store_ref_id`.
- [ ] **Chaves de criptografia:** documentar procedimento de rotação de `SECRET_KEY` (impacta todos os segredos AES-GCM). Validar backup/restore com chave rotacionada.

---

## 4. Ativar 2ª loja em produção

Após Fases 1–2 + métricas + revisão de segurança:

- [ ] Criar a 2ª loja no banco: `INSERT INTO stores (name, slug, active) VALUES ('Loja 2', 'loja-2', true)`.
- [ ] Criar `store_settings` para a loja 2 (via API `POST /api/config/integrations` ou migration).
- [ ] Criar usuário admin para a loja 2 (`flask create-admin` adaptado ou `POST /api/users`).
- [ ] Setar `FORCE_MULTI_TENANT=1` no ambiente de produção.
- [ ] Smoke pós-ativação: admin loja 1 vê só loja 1; admin loja 2 vê só loja 2; worker processa ambas.
- [ ] Monitorar métricas por 48h antes de declarar sucesso.

---

## 5. UTMify síncrono

Atualmente WIP (não commitado). O envio síncrono de conversões é o último canal de marketing não coberto pelo outbox assíncrono.

- [ ] Finalizar implementação do dispatcher síncrono UTMify.
- [ ] Integrar com `MarketingConversionOutbox` ou criar fluxo separado.
- [ ] Testar com 2 lojas e tokens distintos (teste de isolamento).

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
| Ruff | ~25 ocorrências globais | Média |
| Black | ~62 arquivos fora do formato | Média |
| `tsc --noEmit` | Erros preexistentes no frontend | Média |
| Testes de worker em Postgres | Cobertos em SQLite; validar em Postgres real antes da 2ª loja | Baixa |
| Documentação de API | Swagger/OpenAPI incompleto para novos endpoints | Baixa |

Sugestão: dedicar 1 sprint de 2–3 dias para zerar Ruff + Black + `tsc --noEmit`.

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

| Ordem | Item | Bloqueia 2ª loja? |
|---|---|---|
| 1 | Fase 1 — Deploy com 1 loja | Sim (primeiro passo) |
| 2 | Fase 2 — Verificar `store_settings` | Sim |
| 3 | Métricas e alertas por tenant | Recomendado |
| 4 | Revisão de segurança | Recomendado |
| 5 | Ativar 2ª loja em produção | — (é o objetivo) |
| 6 | UTMify síncrono | Não |
| 7 | Landing page → store mapping | Sim (para leads públicos multi-loja) |
| 8 | Cleanup de débitos (Ruff/Black/tsc) | Não |

---

## Referências cruzadas

- Estado atual completo: [08-estado-atual-e-proximos-passos.md](08-estado-atual-e-proximos-passos.md)
- Blueprint executável: [09-blueprint-fases-c-d.md](09-blueprint-fases-c-d.md)
- Runbook de deploy: [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md)
- Specs temáticas: [01](01-banco-models-migrations.md) a [07](07-seguranca-testes-rollout.md)