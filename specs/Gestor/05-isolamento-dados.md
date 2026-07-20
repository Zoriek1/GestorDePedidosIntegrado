# Spec 05 — Isolamento dos dados de negócio

## Status de implementação

**Fases C e D concluídas no código.** C.1 (pedidos e leads), C.2 (clientes, endereços e fontes), C.3
(referências externas), C.4 (auditoria) e D (outboxes/workers) foram entregues na branch
`multi-tenant`. O **Gate 0 (PostgreSQL)** também foi concluído: migrations em Postgres real,
teste de concorrência de `numero_pedido`, smoke de isolamento com 2 lojas e backup/restore
com dados reais de produção. A ativação multi-tenant em produção permanece condicionada ao
deploy das Fases 1–2 (runbook em [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md)) e ao
hardening da Fase F. O checklist, os commits, testes e gates de rollout estão em
[09-blueprint-fases-c-d.md](09-blueprint-fases-c-d.md).

## Pastas afetadas

- `backend/app/models/`
- `backend/app/repositories/`
- `backend/app/services/`
- `backend/app/routes/`

## Princípio

Adicionar uma FK não isola dados. O isolamento só existe quando todas as leituras, escritas, updates, deletes, agregações e exports aplicam o tenant correto.

## Decisões permanentes da Fase C

- Modelo compartilhado: tabelas comuns com `store_ref_id`; não criar tabela ou schema por empresa.
- Leitura segura por padrão: um listener SQLAlchemy em `backend/app/services/tenant_scope.py` injeta o
  escopo da empresa nos SELECTs dos models registrados.
- Em contexto multiempresa, o filtro é estrito: `store_ref_id == g.current_store.id`.
- Com uma única empresa ativa, a leitura aceita a empresa atual ou `store_ref_id IS NULL` para
  tolerar dados legados durante a transição.
- `is_multi_store()` governa somente essas bordas de compatibilidade; não desliga o isolamento.
- Workers e outros fluxos sem request não recebem escopo implícito. Eles resolvem o tenant pela
  entidade ou linha de fila que originou a operação.
- O opt-out `execution_options(include_all_tenants=True)` é explícito e reservado a operações
  administrativas ou de migration auditadas.
- `store_ref_id` permanece nullable até o hardening da Fase F.

## Receita por entidade

1. Adicionar `store_ref_id` ao model e ao índice, com FK `ON DELETE RESTRICT` e nullable durante
   o rollout; não expor o tenant nos serializers públicos.
2. Criar migration idempotente: resolver a empresa pelo `slug='default'`, fazer backfill direto
   ou pela entidade-pai, criar índices/uniques, criar FK física somente no PostgreSQL e validar
   nulos e órfãos.
3. Registrar o model no filtro automático de tenant.
4. Carimbar `store_ref_id` em toda escrita a partir da origem confiável: request autenticada,
   instalação/credencial da integração, entidade-pai ou helper explícito de escrita pública.
5. Converter unicidades pertencentes à empresa para uniques compostas
   `(store_ref_id, <campo>)`.
6. Testar duas empresas com dados sobrepostos, incluindo get/list/stats/export/bulk e acesso por
   ID da outra empresa retornando 404.

## Inventário obrigatório

Classificar cada tabela:

- Global da plataforma.
- Própria de uma loja.
- Filha de entidade escopada, com ou sem FK redundante.
- Catálogo compartilhável, se houver.

No mínimo revisar pedidos, leads, clientes, endereços, fontes, rotas, entregas, recebíveis, usuários, payroll, comissões, notificações, auditoria, integrações e exports.

## Repositories

- Em requests autenticadas, o filtro automático aplica o tenant a queries por ID, relacionamentos,
  listas, stats, buscas, paginação e agregações.
- Bulk update/delete deve permanecer escopado no SQL; testar explicitamente, pois não pode depender
  de filtragem posterior em memória.
- APIs internas executadas sem request recebem `store_ref_id` obrigatório ou derivam o tenant da
  entidade-raiz; nunca assumem a empresa `default` silenciosamente em modo multiempresa.
- Uma busca por ID conhecido da outra empresa deve retornar `None` e virar 404 na rota.
- Unique constraints passam a incluir tenant quando a unicidade é local à loja.

Exemplo de invariável:

`PedidoRepository.get_by_id(pedido_id)` dentro de request nunca enxerga um pedido fora do escopo
injetado; o equivalente usado por worker recebe ou deriva `store_ref_id` explicitamente.

## Escritas

- Pedidos manuais usam a loja do usuário autenticado.
- Pedidos Nuvemshop usam a loja da instalação que recebeu o webhook.
- Pedidos Bling/importados usam a credencial selecionada.
- Entidades derivadas copiam tenant da entidade raiz, nunca do request se já existe raiz.
- O servidor ignora `store_ref_id` enviado pelo cliente comum.

Leads públicos, atualmente sem login, usam `resolve_public_write_company()` e ficam na empresa
`default` até existir mapeamento aprovado de landing page/domínio para empresa.

## Numeração de pedidos

- `Pedido.id` continua sendo a PK global e interna.
- O identificador exibido passa a ser `numero_pedido`, sequencial por empresa; o nome evita conflito
  com `Pedido.numero`, que já representa o número do endereço.
- O backfill inicial usa `numero_pedido = id`, preservando os números da empresa existente.
- A constraint é unique composta `(store_ref_id, numero_pedido)`.
- A geração usa `max(numero_pedido)` da empresa + 1, com unique e retry após `IntegrityError` para
  tratar concorrência.
- O frontend exibe `numero_pedido` com fallback temporário para `id`.

## Relações e consistência

Uma FK simples não impede relacionar pedido da loja A a cliente da loja B. Para relações críticas:

- Validar tenant na service.
- Considerar constraints compostas quando justificadas.
- Incluir testes de tentativa cross-tenant.

## Ordem de isolamento

1. C.1: `pedidos` e `leads`, filtro automático e numeração por empresa.
2. C.2: `clientes`, `enderecos_clientes` e `fontes_pedido`; telefone/nome passam a ter unicidade
   local à empresa e endereços copiam o tenant do cliente.
3. C.3: `pedido_external_refs`; manter o `store_id` textual externo e adicionar o
   `store_ref_id` interno derivado do pedido.
4. C.4: `audit_log`; gravar e filtrar a empresa mesmo sem FK para a entidade auditada.

## Cache e offline

- React Query keys incluem tenant.
- Zustand limpa dados ao logout/troca de loja.
- Dexie separa registros por tenant e limpa dados inacessíveis.
- Service worker não pode devolver payload autenticado de outra sessão.

## Exports, métricas e logs

- CSVs, dashboards, stats e relatórios filtram tenant.
- Logs estruturados incluem `store_ref_id`, mas nunca segredos.
- Auditoria registra tenant da ação.
- Endpoints debug não podem atravessar tenants.

## Critérios de aceite

- Suite cria duas lojas com dados sobrepostos e prova isolamento em CRUD, stats, busca, export e processamento.
- IDs conhecidos da outra loja não retornam o objeto.
- Uniques locais permitem mesmo valor em lojas diferentes.
- Nenhuma repository per-tenant possui query pública sem argumento/contexto de loja.
