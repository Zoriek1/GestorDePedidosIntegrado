# Runbook — Rollout Fases 0–2

> **Gate 0 concluído em 2026-07-20** — todos os itens de 0.1 a 0.7 validados, incluindo backup/restore
> com dados reais de produção.
> **Fases A–F implementadas em 2026-07-21** — NOT NULL, Nuvemshop token, frontend/offline, validação
> de integrações e UI grid entregues. Suíte: 786/786.
> **Próximo passo: Fase 1 (deploy em produção com 1 loja).**

Gate PostgreSQL (staging) → deploy em produção com 1 loja → verificação de `store_settings`.
Escopo deliberadamente limitado às fases **0, 1 e 2**: nenhuma segunda loja é ativada aqui
(`is_multi_store()` permanece `False` em produção). Continuação (ativar 2ª loja) fica para
runbooks seguintes.

## Princípios que tornam 0–2 seguras

- **Schema aditivo**: todas as migrations só adicionam colunas/índices/FKs; nada é destrutivo.
- **Trigger data-driven**: `backend/app/services/tenancy.py::is_multi_store()` só liga o modo estrito
  quando há **>1 loja ativa** (ou `FORCE_MULTI_TENANT`). Com 1 loja ativa, o comportamento é idêntico
  ao atual — os fallbacks single-store (`.env`, `BLING_STORE_ID`, tolerância a `store_ref_id NULL`)
  continuam valendo.
- **Reversível**: rollback = voltar a imagem anterior; o schema extra permanece compatível.

## Estado de partida

- Commits no branch `multi-tenant`: Fases A–F completas (17 commits de implementação).
- Suíte SQLite: **786/786**. Gate 0 validado em PostgreSQL real à parte (ver seções 0.4 a 0.7):
  migrations idempotentes, concorrência de `numero_pedido` (2 passed) e smoke de isolamento com 2
  lojas (4 passed) executados contra Postgres real; backup/restore com dados reais de produção
  (909 pedidos) confirmado.
- NOT NULL em 19 tabelas aplicado idempotente (SQLite + Postgres).
- Token Nuvemshop cifrado com AES-GCM.
- React Query keys escopadas por tenant; cache purged em troca de identidade.
- IntegrationValidationLog + grid de validação de integrações funcional.
- Deploy: `docker compose` (`db` postgres:16 + `backend` + `capi-worker` + `bling-worker`). Só o
  `backend` roda as migrations (via `backend/entrypoint.sh`); os workers apenas leem a fila.

---

## Fase 0 — Gate PostgreSQL (em STAGING, nunca em produção)

Objetivo: provar migrations, constraints, concorrência de numeração e isolamento com 2 lojas em
Postgres real, antes de tocar produção.

### 0.1 — Preparar staging

- Provisionar um ambiente igual ao de produção com Postgres 16.
- `.env` de staging = cópia do de produção, porém com **credenciais de teste** (Meta/Bling/Nuvemshop
  em modo sandbox/desligado) e `SECRET_KEY` própria de staging. Nunca apontar staging para dados/
  webhooks reais.
- Subir só o banco e o backend:
  ```sh
  docker compose up -d db
  docker compose up -d backend   # entrypoint.sh roda TODA a cadeia de migrations em Postgres
  docker compose logs -f backend # confirmar cada migration [ADD]/[SUCCESS]/[SKIP]
  ```

### 0.2 — Idempotência das migrations

Reexecutar a cadeia e confirmar que nada quebra nem duplica:
```sh
docker compose exec backend sh -c 'cd /app/backend && sh entrypoint.sh'   # ou re-rodar os scripts
```
Esperado: migrations reportam `[SKIP]`/nenhuma alteração; sem erro de constraint duplicada.

### 0.3 — Verificar integridade pós-migration (SQL no Postgres)

Rodar contra o banco de staging (`docker compose exec db psql -U gestor -d gestor_pedidos`):

- **Nulos** nas tabelas per-tenant que fizeram backfill (deve ser 0):
  `pedidos, leads, clientes, enderecos_clientes, fontes_pedido, pedido_external_refs,
  lead_touchpoints, pedido_sugestoes_endereco, pedido_manual_overrides, rotas_otimizadas,
  push_subscriptions, audit_log, meta_capi_outbox, meta_capi_lead_outbox,
  marketing_conversion_outbox, bling_outbox`.
  ```sql
  SELECT 'pedidos' t, COUNT(*) FROM pedidos WHERE store_ref_id IS NULL
  UNION ALL SELECT 'leads', COUNT(*) FROM leads WHERE store_ref_id IS NULL
  -- ... repetir para cada tabela acima
  ;
  ```
- **Órfãos** (store_ref_id sem loja correspondente): join contra `stores` deve dar 0 por tabela.
- **FKs físicas** `fk_<t>_store_ref_id_stores` existem (só criadas em Postgres).
- **Uniques compostas** existem: `uq_pedidos_store_numero_pedido`, `uq_leads_store_dedup_key`,
  `uq_push_subscriptions_store_endpoint`, e as de clientes/fontes/refs externas.
- `numero_pedido` da loja existente foi preservado (`numero_pedido = id` no backfill C.1).

### 0.4 — Teste de concorrência do `numero_pedido` (ARTEFATO CRIADO)

`allocate_order_number` serializa por `SELECT ... FOR UPDATE` na linha da `Store`
(`backend/app/services/order_number_allocator.py`). SQLite não exercita isso (FOR UPDATE é no-op).
Criado `backend/tests/test_order_number_concurrency_pg.py` que:

- **Pula** se `TEST_DATABASE_URL` (Postgres) não estiver definido — não roda no dev SQLite.
- Cria 1 loja e dispara **K threads**, cada uma com sessão/conexão própria, alocando+inserindo
  `M` pedidos concorrentes na **mesma** loja.
- Asserta que o conjunto de `numero_pedido` é exatamente `{1..K*M}` — **sem duplicado, sem buraco**.
- Repete com 2 lojas em paralelo para provar que os mutexes por tenant não se bloqueiam entre si.

Rodar em staging:
```sh
TEST_DATABASE_URL=postgresql://gestor:...@localhost:5432/gestor_staging \
  docker compose exec -e TEST_DATABASE_URL backend python -m pytest tests/test_order_number_concurrency_pg.py -q
```

**✅ Executado em 2026-07-20** contra Postgres real (banco descartável): `2 passed`. Confirma o mutex
por tenant sem duplicado/furo, e que duas lojas não se bloqueiam entre si.

### 0.5 — Smoke de isolamento com 2 lojas (via API, Postgres real)

A suíte pytest usa SQLite fixo (`conftest.py`), então o isolamento em Postgres é validado pela **API
do backend do compose** com 2 lojas:

- Criar uma 2ª loja **em staging** e `store_settings` própria (credenciais de teste).
- Com `FORCE_MULTI_TENANT=1` no backend de staging, exercitar a matriz da Spec 07:
  - Admin da loja A lê/escreve só A; admin de B só B; ID conhecido da outra loja → 404.
  - Pedidos/leads/clientes/fontes/stats/export não vazam entre lojas.
  - Numeração reinicia por loja.
  - Workers: um ciclo processa A e B com credenciais/destinos distintos; falha de A não altera B;
    loja inativa não gera envio (script/checagem manual do outbox por `store_ref_id`).
- Rodar também a suíte SQLite completa em staging (`docker compose exec backend python -m pytest -q`)
  como rede de segurança de regressão.

**✅ Executado em 2026-07-20**: `backend/tests/test_domain_isolation_pg_smoke.py` (login via API real,
GET de pedido cross-tenant → 404, listagem sem vazamento, `numero_pedido` reiniciando por loja) contra
Postgres real com `FORCE_MULTI_TENANT=1` — `4 passed`.

**Nota de escopo — isolamento de workers:** este smoke cobre o domínio síncrono via HTTP. O isolamento
de workers com credenciais/destinos distintos, falha isolada e empresa inativa **já está coberto
exaustivamente** por `backend/tests/test_tenant_workers.py` (SQLite, endpoints externos mockados). Como
essa lógica usa apenas construções SQLAlchemy genéricas (sem SQL específico de dialeto, ao contrário do
`FOR UPDATE` da numeração), o risco de comportamento divergente em Postgres é baixo e não foi
revalidado separadamente aqui. Se quiser fechar 100% antes do rollout real (2ª loja em produção),
um ciclo do `capi-worker`/`bling-worker` reais contra o Postgres de staging, com 2 lojas e destinos
mockados/sandbox, seria o próximo passo — não bloqueia o gate 0.

### 0.6 — Critérios de saída do gate 0

- [x] Migrations aplicam e reexecutam sem erro em Postgres. *(2026-07-20)*
- [x] Zero nulos/órfãos nas tabelas per-tenant; FKs e uniques compostas presentes. *(2026-07-20)*
- [x] Teste de concorrência de `numero_pedido` verde (sem duplicado) em Postgres. *(2026-07-20)*
- [x] Smoke de isolamento (domínio/HTTP) com 2 lojas verde em staging. *(2026-07-20; workers cobertos
      em SQLite, ver nota de escopo acima)*
- [x] Backup/restore testado com **dados reais de produção**. *(2026-07-20)* — `pg_dump -F c` do
      banco de produção (Hostinger) restaurado (`pg_restore`) em banco Postgres local descartável;
      cadeia completa de migrations (incluindo Fases A→D) reexecutada em cima dos dados reais e
      confirmada idempotente; `_gate_check_integrity.py` → `GATE OK`. Ver detalhes abaixo.

### 0.7 — Resultado do backup/restore com dados reais (2026-07-20)

- **Origem**: `pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -F c` executado dentro do container `db` em
  produção (Hostinger), copiado para fora do container e baixado via `scp` para a máquina local.
- **Restore**: `pg_restore` num banco Postgres local descartável (`gestor_gate_restore`, container
  Docker `pg-gate`, nunca no banco de produção). Avisos de `role "admin" does not exist` durante o
  restore são esperados e inofensivos — o usuário de restore (`gestor`) já fica dono dos objetos
  criados; não afeta dados nem schema.
- **Dados confirmados**: 909 pedidos, 10 usuários restaurados.
- **Migrations em cima dos dados reais**: cadeia completa do `entrypoint.sh` executada duas vezes
  (para provar idempotência) — primeira execução aplicou as Fases A→D com sucesso (`[SUCCESS]` em
  fundação multi-tenant, `store_settings`, `users.store_ref_id` com backfill de 10 linhas, C.1–C.4,
  Fase D das outboxes, backfill de integrações); segunda execução: tudo `[SKIP]`, confirmando
  idempotência com dados reais.
- **Integridade pós-migration**: `_gate_check_integrity.py` → `[RESULTADO] GATE OK` (zero nulos,
  zero órfãos, FKs e uniques compostas presentes).
- **Nota**: os 6 scripts de migration legados (pré-multi-tenant) que dependem de `PYTHONPATH=.`
  falharam na primeira tentativa por falta dessa variável na sessão local — não é um problema do
  código; após `$env:PYTHONPATH = "."`, todos aplicaram/pularam normalmente.

---

## Fase 1 — Deploy em produção com 1 loja

`is_multi_store()` permanece `False` (só a loja `default` ativa) → sem mudança de comportamento.

### 1.1 — Antes do deploy

- **Backup do banco de produção** imediatamente antes (dump + verificação de restore em ambiente à
  parte, se possível).
- Congelar janela de baixo tráfego.

### 1.2 — Deploy

```sh
git pull                # branch multi-tenant já mergeado no fluxo de release do projeto
docker compose build backend capi-worker bling-worker
docker compose up -d backend capi-worker bling-worker
docker compose logs -f backend   # confirmar migrations rodando na ordem do entrypoint
```
O `backend/entrypoint.sh` executa a cadeia até `add_store_ref_to_outboxes.py` (Fase D). Os workers
sobem sem rodar migrations.

### 1.3 — Verificação pós-deploy

- Repetir os checks de nulos/órfãos/FKs (0.3) no banco de produção.
- Confirmar `is_multi_store() == False` (só 1 loja ativa).
- Smoke autenticado single-store: login admin, listar/criar pedido (número segue a sequência atual),
  lead público/whatsapp-start funciona (loja default resolve), Bling/Meta enfileiram normalmente.
- Observar os logs dos workers: ciclos processam a fila; nenhum erro novo de tenant.

### 1.4 — Rollback da Fase 1

- Voltar a imagem/anterior do `backend` e workers (`docker compose up -d` com a tag anterior).
- O schema aditivo permanece — a versão anterior tolera as colunas extras.
- **Não** apagar `stores`/`store_settings`.

---

## Fase 2 — Verificar `store_settings` da loja default

O import `.env → store_settings` **já é feito automaticamente** por
`scripts/migrations/create_store_settings.py` (chama `settings_from_environment(default_store)`,
idempotente). Aqui a tarefa é **verificar**, não importar.

### 2.1 — Confirmar o import

- Nos logs do deploy: `[ADD] store_settings do tenant default importada do ambiente` (primeira vez)
  ou `[SKIP]` (já existente).
- `SELECT * FROM store_settings WHERE store_ref_id = (SELECT id FROM stores WHERE slug='default');`
  deve existir 1 linha.

### 2.2 — Comparar config sem vazar segredo

- Chamar `GET /api/config/integrations` (admin) — retorna os campos **mascarados** e flags `has_*`.
- Conferir que cada credencial presente no `.env` aparece como `has_<campo> = true` e que os campos
  não-secretos (pixel id, measurement id, customer id, plataforma UTMify, endereço/CEP) batem com o
  `.env`. Nunca logar/imprimir o valor em claro.

### 2.3 — Confirmar leitura pelo banco

- `uses_environment_fallback(None)` deve ser `False` para a loja default (há `store_settings`
  persistida), i.e., a app passa a ler config do banco, não mais do `.env`.
- Smoke: um envio Meta/UTMify usa a config vinda de `store_settings` (verificável por um evento de
  teste ou pelo log com `store_ref_id`).

### 2.4 — Critérios de saída da Fase 2

- [ ] `store_settings` da default existe e reflete o `.env` (flags `has_*` corretas).
- [ ] `uses_environment_fallback` = `False` para a default.
- [ ] Nenhum segredo em log/resposta.

---

## Fora do escopo 0–2 (não bloqueiam, ficam para depois)

- **Ativar a 2ª loja em produção** — só depois das Fases 1–2 validadas.
- **Métricas e alertas por tenant** — taxa de erro, latência, volume por `store_ref_id`.
- **Revisão de segurança** — timing attack, segredos em memória, cookies/sessão.
- **UTMify síncrono** — envio síncrono de conversões (atualmente WIP).
- **Landing page → store mapping** — `resolve_public_write_company()` atualmente sempre resolve `default`.
- **Cleanup de débitos** — Ruff (25), Black (62 arquivos), `tsc --noEmit`.
- **Ver [11-proximos-passos.md](11-proximos-passos.md)** para o roadmap completo pós-implementação.

## Artefatos produzidos

1. `backend/tests/test_order_number_concurrency_pg.py` (0.4) — criado e validado (2 passed em Postgres real).
2. `backend/scripts/migrations/_gate_check_integrity.py` — verificação de nulos/órfãos/FKs/uniques (0.3/0.6), rodado contra dados reais de produção.
3. `backend/tests/test_domain_isolation_pg_smoke.py` (0.5) — criado e validado (4 passed em Postgres real com `FORCE_MULTI_TENANT=1`).