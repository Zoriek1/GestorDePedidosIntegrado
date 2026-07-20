# Spec 07 — Segurança, testes, rollout e operação

## Segredos

- Nunca commitar `.env`, chaves ou valores reais em fixtures.
- GET retorna máscara; logs e exceptions aplicam redaction.
- Backups contêm ciphertext e devem ser protegidos como dados sensíveis.
- Definir processo de rotação antes de produção SaaS.
- Avaliar master key dedicada fora de `SECRET_KEY` e versionamento de chave.

## Matriz mínima de testes

### Unitários

- Criptografia round-trip, purpose incorreto e ciphertext inválido.
- Máscara e update seguro.
- Validação de payload.
- Resolução de config DB/fallback.

### Migrations

- Banco novo.
- Banco legado.
- Reexecução.
- Execução parcial.
- Nulos, órfãos e múltiplas integrações legadas.
- PostgreSQL real para FKs/constraints.
- SQLite para fallback de desenvolvimento.

### API

- Admin da loja A lê/escreve A.
- Admin da loja B lê/escreve B.
- Não-admin recebe 403.
- Tentativa de enviar tenant alheio é ignorada/rejeitada.
- Respostas nunca contêm segredo.

### Domínio

- CRUD, buscas, stats, exports e bulk actions com duas lojas.
- IDs sobrepostos ou conhecidos não vazam.
- Cache/offline é limpo ao trocar sessão.

### Workers

- Duas lojas no mesmo ciclo.
- Credenciais e destinos distintos.
- Falha isolada.
- Retry e poll mantêm tenant original.

## Rollout

1. Backup e inventário de dados existentes.
2. Deploy de schema aditivo e seed default.
3. Verificar contagens, nulos, órfãos, índices e FKs.
4. Deploy de dual-read/fallback.
5. Importar `.env` para `store_settings` e comparar configurações sem logar segredos.
6. Deploy de dual-write/tenant em novas linhas.
7. Backfill de entidades históricas.
8. Ativar segunda loja apenas em staging.
9. Executar testes de isolamento e workers.
10. Remover fallback por integração gradualmente.
11. Aplicar `NOT NULL` e uniques compostas finais.

## Observabilidade

- Métricas de linhas sem tenant e órfãs.
- Contagem de jobs por tenant/status.
- Erros de decrypt sem payload sensível.
- Alertas para fallback `.env` ainda utilizado.
- Auditoria de alterações de credenciais com usuário, loja, horário e nomes dos campos; nunca valores.

## Rollback

- Schema aditivo permanece.
- Voltar aplicação para versão anterior apenas enquanto compatível com colunas extras.
- Não apagar `stores` ou `store_settings` como rollback automático.
- Se nova configuração causar falhas, reativar fallback por feature flag específica, não misturar tenants.

## Gates para produção multi-tenant

- Zero linhas per-tenant sem FK após backfill.
- Zero queries per-tenant públicas sem escopo comprovado.
- Testes de isolamento verdes em PostgreSQL.
- Nuvemshop token cifrado.
- Workers testados com duas lojas.
- Processo de chave/rotação documentado.
- Backup e restore testados.
- Revisão de segurança concluída.

## Estado atual de verificação

- **Fases A, B, C, D, Gate 0 e hardening fail-closed (Fase F parcial) concluídos** no branch `multi-tenant`.
  O commit `99e5945` fechou as bordas de compatibilidade (numeração, PK lookups, lead público,
  taxa de entrega e Bling por tenant) em multi-store.
- O build Vite de produção passou (Vite 7.3.0, 14.819 módulos transformados).
- Ruff e Black passaram nos arquivos novos (débitos preexistentes: 25 Ruff, 62 Black fora do escopo).
- A suíte backend completa: **786/786 testes aprovados** (vs. 726 da fundação).
  - C.1: 135 testes direcionados.
  - C.2: 52 testes direcionados.
  - C.3: 67 testes direcionados (C.3, Bling e Nuvemshop).
  - C.4: 16 testes direcionados.
  - D (workers): 5 testes direcionados (`test_tenant_workers.py`).
  - Smoke PostgreSQL: 4 testes (`test_domain_isolation_pg_smoke.py`).
  - Concorrência numero_pedido: 2 testes (`test_order_number_concurrency_pg.py`).
  - Hardening fail-closed: testes em `test_tenant_auth.py`, `test_tenant_domain_c1.py`,
    `test_tenant_oauth.py` e `test_bling_service.py`.
- **Gate 0 (PostgreSQL) aprovado:**
  - Migrações idempotentes em Postgres real com dados de produção (backup/restore de 909 pedidos).
  - Zero nulos/órfãos nas tabelas per-tenant; FKs e uniques compostas validadas.
  - Teste de concorrência de `numero_pedido` verde (sem duplicado, sem furo).
  - Smoke de isolamento com 2 lojas via API real — 4 passed.
- `tsc --noEmit` global ainda falha em débitos preexistentes do frontend.
- O estado detalhado e a sequência de continuação estão em [08-estado-atual-e-proximos-passos.md](08-estado-atual-e-proximos-passos.md). O runbook de rollout está em [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).