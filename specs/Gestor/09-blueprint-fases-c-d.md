# Blueprint executável — Fases C e D

## Objetivo e uso

Aplicar o isolamento multi-tenant do domínio e dos workers em incrementos pequenos, revisáveis e
com um commit por incremento. Este arquivo é o checklist operacional; as decisões permanentes
continuam descritas na [Spec 05](05-isolamento-dados.md) e na
[Spec 06](06-workers-integracoes.md).

Atualizar este blueprint após cada incremento com status, commit realizado, testes executados e
desvios aprovados. Não marcar uma entrega como concluída enquanto sua migration, testes focados e
verificações de saída não estiverem completos.

### Legenda de status

- ⬜ **Pendente**
- 🚧 **Em andamento**
- ✅ **Concluído**

## Estado dos incrementos

| Incremento | Status | Dependências | Commit esperado |
|---|---|---|---|
| C.1 — Pedidos e leads | ✅ Concluído (rollout pendente) | Fases A e B | `feat(tenant): isolate orders leads and dependent workflows` |
| C.2 — Clientes, endereços e fontes | ✅ Concluído (rollout pendente) | C.1 | `feat(tenant): isolate customers addresses and order sources` |
| C.3 — Referências externas | ✅ Concluído (rollout pendente) | C.1 | `feat(tenant): isolate external order references` |
| C.4 — Auditoria | ✅ Concluído (rollout pendente) | C.1 | `feat(tenant): isolate audit logs` |
| D — Filas e workers | ✅ Concluído (rollout pendente) | C.1, C.2 e C.3 | `feat(workers): resolve tenant per outbox row` |
| F — Hardening fail-closed | ✅ Concluído | D | `feat(tenant): fail-closed multi-store hardening across domain, jobs and Bling` |

## Contexto e decisões travadas

As Fases A (usuários/JWT/contexto) e B (OAuth/callbacks com trigger multiempresa) já foram
entregues no branch `multi-tenant`. Cada `store` representa uma empresa/tenant, e uma empresa pode
ter vários usuários.

- Modelo: tabela compartilhada com `store_ref_id`; não usar tabela ou schema por empresa.
- Leitura: sempre isolar pela empresa do usuário via filtro automático seguro por padrão.
- `is_multi_store()` governa apenas as bordas de compatibilidade para linhas sem empresa e
  contextos sem login; não desliga o isolamento.
- Numeração: `numero_pedido` é sequencial por empresa; `Pedido.id` permanece PK global interna e
  `Pedido.numero` continua sendo o número do endereço.
- Compatibilidade: `store_ref_id` permanece nullable até a Fase F; com uma empresa ativa, o
  comportamento legado deve permanecer funcional.
- Entrega: um commit por incremento, sempre com migration idempotente e testes usando duas
  empresas.

## Receita comum de isolamento

Aplicar esta receita a cada entidade incorporada na Fase C:

- [x] Adicionar `store_ref_id` ao model, com FK nullable, `ON DELETE RESTRICT` e índice; não expor
  o tenant nos serializers públicos.
- [x] Criar migration idempotente seguindo `add_store_ref_to_users.py`: resolver a empresa pelo
  `slug='default'`, fazer backfill direto ou pela entidade-pai, criar índices/uniques, criar FK
  física somente no PostgreSQL e validar nulos/órfãos.
- [x] Registrar a migration no `backend/entrypoint.sh` na ordem correta de dependências.
- [x] Registrar o model no filtro automático de `backend/app/services/tenant_scope.py`.
- [x] Carimbar `store_ref_id` em toda escrita a partir de fonte confiável: `g.current_store`,
  instalação/credencial, entidade-pai ou helper público explícito.
- [x] Converter uniques globais para `(store_ref_id, <campo>)` quando a unicidade pertencer à
  empresa.
- [x] Testar duas empresas em get/list/stats/export/bulk; ID conhecido da outra empresa deve
  resultar em 404.

---

## C.1 — Pedidos e leads, com numeração por empresa

**Status:** ✅ Concluído  
**Dependências:** Fases A e B concluídas.  
**Commit realizado:** `1bdf5db` — `feat(tenant): isolate orders leads and dependent workflows`

### Schema e migration

- [x] Adicionar `Pedido.store_ref_id` e `Pedido.numero_pedido` (`Integer`, nullable, indexados) em
  `backend/app/models/pedido.py` e na serialização.
- [x] Adicionar `Lead.store_ref_id` em `backend/app/models/lead.py` e na serialização.
- [x] Criar `add_store_ref_and_numero_to_orders.py` como migration idempotente.
- [x] Fazer backfill de `pedidos.store_ref_id` e `leads.store_ref_id` para a empresa `default`.
- [x] Fazer backfill de `numero_pedido = id`, preservando os números atuais da empresa existente.
- [x] Criar unique composta `(store_ref_id, numero_pedido)` e os índices/FKs aplicáveis.
- [x] Registrar a migration no entrypoint e validar reexecução, nulos e órfãos.

### Filtro automático — backbone da Fase C

- [x] Criar `backend/app/tenant_scope.py` com listener
  `@event.listens_for(Session, "do_orm_execute")` para injetar
  `with_loader_criteria(..., include_aliases=True)` nos SELECTs dos models registrados.
- [x] Em multiempresa, aplicar `store_ref_id == company_id` de forma estrita.
- [x] Com uma empresa ativa, aplicar `store_ref_id == company_id OR store_ref_id IS NULL` para
  tolerar legado.
- [x] Sem request, não aplicar filtro implícito; workers e jobs devem resolver tenant pela origem.
- [x] Disponibilizar opt-out explícito `execution_options(include_all_tenants=True)` para operações
  administrativas auditadas.
- [x] Em `load_request_identity`, cachear uma vez por request `g.tenant_company_id` e
  `g.tenant_multi`, evitando queries ou recursão dentro do listener.
- [x] Importar/registrar `tenant_scope` em `backend/app/factory.py` depois dos models.
- [x] Confirmar que get/list/stats/export/bulk/update/delete respeitam o escopo e que IDs da outra
  empresa viram 404.

### Escrita e numeração

- [x] Na criação manual em `backend/app/routes/pedidos.py`, gravar
  `store_ref_id=g.current_store.id`.
- [x] Na importação Nuvemshop, copiar `store_ref_id` da instalação resolvida na Fase B.
- [x] Em lead público, resolver tenant via `resolve_public_write_company()`; usar `default` por ora
  como ponto de extensão para futuro mapeamento landing/domínio → empresa.
- [x] Implementar `PedidoRepository.proximo_numero(store_ref_id)` como
  `max(numero_pedido)` da empresa + 1, iniciando em 1 para empresa nova.
- [x] Tratar concorrência da numeração com unique e retry após `IntegrityError`, seguindo o padrão
  de `upsert_commission_config`.
- [x] Fazer buscas por número usarem `numero_pedido` dentro da empresa.
- [x] No frontend de pedidos, exibir `numero_pedido` com fallback temporário para `id`.

### Testes e critérios de saída

- [x] Criar `test_tenant_orders.py` com duas empresas e dados sobrepostos.
- [x] Provar isolamento de pedidos/leads em CRUD, buscas, stats, export e bulk.
- [x] Provar que a numeração reinicia por empresa.
- [x] Provar que a empresa existente preserva os números e que o modo de uma empresa tolera NULL
  legado.
- [x] Validar que o rastreio público usa token, não número do pedido, e não é afetado pela nova
  numeração.
- [x] Executar testes focados, suíte backend completa, Ruff e Black check.
- [x] Executar build Vite e `tsc --noEmit` por haver mudança de UI.
- [x] Revisar diff e criar somente o commit deste incremento.

---

## C.2 — Clientes, endereços e fontes

**Status:** ✅ Concluído  
**Dependência:** C.1 concluída.  
**Commit realizado:** `9c6f46d` — `feat(tenant): isolate customers addresses and order sources`

### Clientes

- [x] Adicionar `Cliente.store_ref_id`, serialização, índice e FK conforme a receita comum.
- [x] Substituir a unique global de `telefone` por `(store_ref_id, telefone)`.
- [x] Revisar `cpf_cnpj`; se sua unicidade for regra local da empresa, convertê-la para unique
  composta no mesmo incremento.
- [x] Adaptar `Cliente.buscar_por_telefone` e `get_statistics` ao escopo automático.
- [x] Na criação manual, usar `g.current_store.id`; no cliente criado por Nuvemshop, herdar a
  empresa da instalação/pedido.

### Endereços

- [x] Adicionar `EnderecoCliente.store_ref_id`, apesar de ser filho de cliente, para proteger
  queries diretas como jobs de geocodificação.
- [x] Fazer backfill a partir do cliente-pai e copiar seu tenant em toda nova escrita.
- [x] Registrar o model no filtro automático e testar tentativa de relação cross-tenant.

### Fontes de pedido

- [x] Adicionar `FontePedido.store_ref_id`, serialização, índice e FK.
- [x] Substituir a unique global de `nome` por `(store_ref_id, nome)`.
- [x] Garantir que `get_ativas` e `get_all` respeitem o escopo automático.
- [x] Fazer as fontes atuais pertencerem à empresa `default`.
- [x] Não semear fontes para novas empresas; criar `Site` localmente apenas na primeira importação
  Nuvemshop da empresa conectada.
- [x] Preservar `pedido.fonte_pedido_id` e `commission_config.fonte_pedido_id`, validando que as
  entidades relacionadas pertencem à mesma empresa.

### Testes e critérios de saída

- [x] Duas empresas podem possuir o mesmo telefone de cliente.
- [x] Duas empresas podem possuir uma fonte chamada `WhatsApp` sem conflito.
- [x] Empresa A não lista, busca, agrega, altera nem associa clientes/fontes de B.
- [x] Migration funciona em banco novo, legado e na reexecução.
- [x] Executar testes focados, suíte backend completa, Ruff e Black check.
- [x] Revisar diff e criar somente o commit deste incremento.

---

## C.3 — Referências externas de pedido

**Status:** ✅ Concluído  
**Dependência:** C.1 concluída.  
**Commit realizado:** `e893668` — `feat(tenant): isolate external order references`

### Implementação

- [x] Adicionar `PedidoExternalRef.store_ref_id` interno, com índice e FK para `stores`.
- [x] Preservar `store_id` textual como ID externo do provedor e substituir a unique por
  `(store_ref_id, provider, store_id, external_order_id)`.
- [x] Fazer backfill de `store_ref_id` a partir de `pedidos.store_ref_id` via `pedido_id`.
- [x] Registrar o model no filtro automático.
- [x] Ajustar `_get_order_ref` e `_upsert_external_ref` em `backend/app/integrations/bling/service.py`
  para derivar e gravar o tenant do pedido.

### Testes e critérios de saída

- [x] Referência da empresa A não aparece para B.
- [x] Import Nuvemshop e envio Bling gravam o tenant correto derivado do pedido.
- [x] Identidades externas continuam funcionando sem alterar o significado de `store_id`.
- [x] Executar testes focados, suíte backend completa, Ruff e Black check.
- [x] Revisar diff e criar somente o commit deste incremento.

---

## C.4 — Auditoria

**Status:** ✅ Concluído  
**Dependência:** C.1 concluída.  
**Commit realizado:** `9b486a1` — `feat(tenant): isolate audit logs`

### Implementação

- [x] Adicionar `AuditLog.store_ref_id` nullable e indexado.
- [x] Fazer backfill dos registros existentes para a empresa `default`.
- [x] Fazer `log_action(...)` gravar tenant de `g.current_store` em request ou da entidade
  auditada quando executado sem request.
- [x] Escopar a leitura da rota administrativa via filtro automático ou filtro explícito, levando
  em conta que `entity_type/entity_id` não são FKs.

### Testes e critérios de saída

- [x] A trilha de auditoria da empresa A não é visível para admin da empresa B.
- [x] Ações de worker com entidade de origem registram o tenant correto.
- [x] Executar testes focados, suíte backend completa, Ruff e Black check.
- [x] Revisar diff e criar somente o commit deste incremento.

---

## D — Filas e workers por empresa

**Status:** ✅ Concluído (rollout pendente)  
**Dependências:** C.1, C.2 e C.3 concluídas.  
**Commit realizado:** `83fc747` — `feat(workers): resolve tenant per outbox row`

O worker não possui `g.current_store`: o tenant deve vir da própria linha da fila e permanecer o
mesmo em poll, retry e reprocessamento.

### Outboxes e migration

- [x] Adicionar `store_ref_id` a `MetaCapiOutbox`, `MetaCapiLeadOutbox`,
  `MarketingConversionOutbox` e `BlingOutbox`.
- [x] Copiar o tenant do pedido ou lead no momento do enqueue, incluindo os helpers Meta,
  marketing e `backend/app/utils/bling_helper.py`.
- [x] Criar migration idempotente que faça backfill pelo pedido/lead referenciado, crie índices/FKs
  e valide nulos/órfãos.
- [x] Garantir que poll, retry e reprocessamento preservem o tenant original da linha.

### Configuração por linha

- [x] Em `backend/meta_capi_worker_entrypoint.py`, resolver
  `runtime_config(row.store_ref_id)` para cada linha ou grupo de tenant.
- [x] Instanciar `MetaConversionsApiService`, GA4/Google Ads e UTMify com a configuração desse
  tenant; nunca selecionar token do lojista apenas por `os.environ`.
- [x] Permitir agrupamento por tenant para eficiência sem compartilhar instâncias/configurações
  entre grupos.
- [x] Fazer o safety-net diário filtrar/agrupar por tenant.

### Bling

- [x] Selecionar credencial com `BlingTokenService.get_credential(store_ref_id)`.
- [x] Remover `BLING_STORE_ID` como seletor operacional no token service, service e helper de
  enqueue; manter somente compatibilidade estritamente necessária fora do fluxo operacional.
- [x] Garantir que outbox e referência externa usem o tenant derivado do pedido.

### Falhas, logs e event IDs

- [x] Isolar falhas: credencial/configuração inválida de A não bloqueia nem altera linha de B.
- [x] Incluir empresa e destino nos logs, com redaction de tokens e segredos.
- [x] Manter event IDs `order_<id>`, pois `id` é PK global; incluir tenant apenas se no futuro o
  identificador do evento passar a ser local, como `numero_pedido`.
- [x] Bloquear novos enqueues para empresa inativa.
- [x] Aplicar a política de produto aprovada às linhas que já estavam pendentes quando a empresa
  foi desativada.

### Testes e critérios de saída

- [x] Um ciclo processa duas empresas com tokens e destinos distintos.
- [x] Falha ou credencial inválida de A não altera a linha de B.
- [x] Empresa inativa não gera novos envios.
- [x] Poll/retry mantém o tenant gravado originalmente.
- [x] Executar testes focados, suíte backend completa, Ruff e Black check.
- [x] Revisar diff e criar somente o commit deste incremento.

---

## F — Hardening fail-closed (multi-store)

**Status:** ✅ Concluído  
**Dependência:** D concluída.  
**Commit realizado:** `99e5945` — `feat(tenant): fail-closed multi-store hardening across domain, jobs and Bling`

Fecha as bordas de compatibilidade restantes das Fases C/D: em multiempresa, entradas sem loja
resolvida falham fechado; no single-store o comportamento legado é preservado.

### Implementação

- [x] Auth/usuários/numeração: usuário sem loja e numeração sem tenant falham fechado em
  multi-store (`auth_context`, `order_number_allocator`, `user_routes`).
- [x] Lead público: `/api/leads` e `/whatsapp-start` respondem 503 em multi-store sem loja
  resolvida; match de token recente escopado à loja, com fallback legado no single-store.
- [x] Escopo automático em lookups por PK: trocar `Query.get(id)` por `filter(id==...).first()`
  para o filtro de tenant se aplicar e IDs de outra loja retornarem 404 (distância, taxa, rota
  otimizada, fonte de pedido).
- [x] Worker de taxa de entrega carrega `store_ref_id` na fila e filtra o pedido pelo tenant (sem
  `g.current_store` no worker).
- [x] Bling por tenant: rotas instanciam `BlingIntegrationService(store_ref_id)`; o service e o
  `token_service` selecionam a credencial por loja.

### Testes e critérios de saída

- [x] Numeração fail-closed: sem tenant em multi-store, erro 4xx em vez de gravação cross-tenant.
- [x] Endpoints/rotas escopados retornam 404 para ID de outra loja.
- [x] Job de taxa por loja grava e filtra pelo tenant correto.
- [x] Lead público retorna 503 em multi-store sem loja resolvida.
- [x] Credencial Bling por tenant no worker; falha de A não afeta B.
- [x] Executar testes focados, suíte backend completa, Ruff e Black check.
- [x] Revisar diff e criar somente o commit deste incremento.

---

## Decisões de produto em aberto

Estas decisões permanecem pendentes até o início do respectivo incremento:

- [x] **C.2 — Fontes iniciais:** não semear fontes para empresa nova; a Nuvemshop cria `Site`
  somente na empresa conectada durante a primeira importação.
- [ ] **C.2/futuro — Lead público:** definir o mapeamento landing page/domínio → empresa; até lá,
  `resolve_public_write_company()` direciona para `default`.
- [x] **D — Empresa inativa:** invalidar/descartar (decisão do usuário, 2026-07-20). Novos enqueues
  são bloqueados e as linhas já pendentes são marcadas como falha permanente (`store_inactive`) no
  worker; não há retomada automática se a empresa voltar.

## Verificação obrigatória por incremento

- [x] Rodar testes focados da entrega.
- [x] Rodar a suíte backend completa com `--basetemp` gravável; usar SQLite local quando Docker não
  estiver disponível.
- [x] Rodar `ruff check` e `black --check` sem reescrita automática durante a verificação.
- [x] Quando houver frontend, rodar `npm run build` e `tsc --noEmit`.
- [x] Revisar o diff e confirmar ausência de segredos, `.env`, `dist` e
  `.claude/settings.local.json`.
- [x] Criar um único commit com a mensagem prevista para o incremento.
- [x] Atualizar a tabela de estado e o registro de execução abaixo.

## Registro de execução

| Incremento | Status final | Commit realizado | Testes/verificações | Desvios aprovados | Data |
|---|---|---|---|---|---|
| C.1 | Concluído | `1bdf5db` | 135 testes direcionados; build Vite aprovado; incluído na suíte completa de 772 testes | PostgreSQL real validado à parte no Gate 0 | 2026-07-20 |
| C.2 | Concluído | `9c6f46d` | 52 testes direcionados; migrations SQLite e reexecução; incluído na suíte completa | Ruff/Black globais mantêm débitos preexistentes | 2026-07-20 |
| C.3 | Concluído | `e893668` | 67 testes direcionados (C.3, Bling e Nuvemshop); incluído na suíte completa | PostgreSQL real validado à parte no Gate 0 | 2026-07-20 |
| C.4 | Concluído | `9b486a1` | 16 testes direcionados; suíte backend completa: 772/772; build Vite aprovado | Black global aponta 62 arquivos preexistentes | 2026-07-20 |
| D | Concluído | `83fc747` | 5 testes direcionados (`test_tenant_workers.py`); suíte backend completa no estado commitado: 777/777; Ruff/Black limpos nos arquivos novos | Débitos Ruff/Black preexistentes fora do escopo; UTMify (síncrono) ficou WIP não commitado | 2026-07-20 |
| F (hardening) | Concluído | `99e5945` | Testes em `test_tenant_auth.py`, `test_tenant_domain_c1.py`, `test_tenant_oauth.py` e `test_bling_service.py` (numeração fail-closed, endpoints/rotas escopados, job de taxa por loja, lead público 503, credencial Bling por tenant); suíte sobe para 786/786 | Credencial Bling por tenant no worker commitada; UTMify síncrono segue WIP fora do escopo; débitos Ruff/Black preexistentes fora do escopo | 2026-07-20 |
| Gate 0 — PostgreSQL | Concluído | `0ab107c` `aabf6c1` `388c773` | `test_order_number_concurrency_pg.py` (2 passed) e `test_domain_isolation_pg_smoke.py` (4 passed) em Postgres real com `FORCE_MULTI_TENANT=1`; `_gate_check_integrity.py` → `GATE OK` sobre 909 pedidos / 10 usuários de produção restaurados | Docker indisponível no dev, mas executado contra Postgres real à parte; backup/restore com dados reais de produção validados | 2026-07-20 |

## Gate de rollout após a implementação

- [x] Quatro commits isolados na ordem C.1 → C.2 → C.3 → C.4.
- [x] Suíte backend completa aprovada: **786/786 testes** em 2026-07-20.
- [x] Build de produção do frontend aprovado: Vite 7.3.0, 14.819 módulos transformados.
- [ ] O `tsc --noEmit` global ainda falha em débitos preexistentes do frontend; o helper e o tipo
  `numero_pedido` não adicionaram erro específico na saída.
- [x] UTF-8 preservado e `.claude/settings.local.json` mantido fora dos commits.
- [x] Novos arquivos e núcleo de tenancy aprovados no Ruff; o Ruff global ainda reporta 25 débitos
  preexistentes fora da Fase C.
- [x] Black aprovado nos arquivos novos; o check global ainda aponta 62 arquivos preexistentes.
- [x] Gate 0 (PostgreSQL real) concluído em 2026-07-20: migrations idempotentes, zero nulos/órfãos,
  concorrência de `numero_pedido` (2 passed) e smoke de isolamento com 2 lojas (4 passed) validados
  contra Postgres real; backup/restore com dados reais de produção (909 pedidos) validado.
- [x] Fase F (hardening fail-closed) concluída em 2026-07-20 (`99e5945`).

**Decisão de rollout:** a implementação das Fases A–D + hardening (F) e o **Gate 0 (PostgreSQL)**
estão concluídos e validados. A ativação em produção (modo multiempresa com 2ª loja) permanece
bloqueada até a execução das Fases 1 e 2 do runbook [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md)
(deploy com 1 loja e verificação de `store_settings`).

## Fora de escopo — Fase F (pendências remanescentes)

- Aplicar `NOT NULL` e constraints finais depois de zerar nulos e órfãos.
- Remover fallback `.env` das credenciais do lojista.
- Cifrar token Nuvemshop.
- Definir rotação de chave e validar backup/restore.
- Adicionar métricas e alertas por tenant.