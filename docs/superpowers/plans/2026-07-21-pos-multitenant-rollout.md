# Plano Pós-Implementação Multi-Tenant

> **Branch:** `multi-tenant` | **Status atual:** Fases A–F concluídas, Gate 0 validado, 786/786 testes
> **Objetivo:** Levar o multi-tenant para produção, ativar a 2ª loja e resolver pendências

---

## Contexto Executivo

Todas as fases de implementação (A–F) estão completas. O próximo passo é operacional: deploy em produção com 1 loja, validação, e então ativação da 2ª loja. Este plano cobre o caminho crítico (Fases 1–2 do rollout) e as melhorias recomendadas antes de ativar múltiplas lojas.

**Sequência:** Fase 1 → Fase 2 → Métricas → Segurança → 2ª Loja → UTMify → Store Mapping → Cleanup

---

## FASE 1: Deploy em Produção com 1 Loja

> `is_multi_store()` permanece `False` (só loja `default` ativa) → sem mudança de comportamento

### Tarefa 1.1 — Backup do banco de produção

**Objetivo:** Garantir rollback seguro antes de qualquer mudança

- [ ] **1.1.1** Conectar ao servidor de produção (Hostinger) e executar backup:
  ```bash
  docker compose exec db pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -F c -f /tmp/backup_pre_multitenant_$(date +%Y%m%d).dump
  docker compose exec db ls -la /tmp/backup_pre_multitenant_*.dump
  ```
- [ ] **1.1.2** Copiar o dump para fora do container e fazer download local:
  ```bash
  docker cp <container_id>:/tmp/backup_pre_multitenant_*.dump ./backups/
  ```
- [ ] **1.1.3** Verificar integridade do restore em ambiente local descartável (repetir processo do Gate 0):
  ```bash
  pg_restore -l backups/backup_pre_multitenant_*.dump | head -20  # confirmar estrutura
  ```

**Critério de saída:** Dump existe, é válido, e está armazenado fora do servidor

---

### Tarefa 1.2 — Deploy do branch multi-tenant

**Objetivo:** Aplicar as mudanças de schema e código em produção

- [ ] **1.2.1** Congelar janela de baixo tráfego (notificar equipe)
- [ ] **1.2.2** No servidor de produção, fazer pull e rebuild:
  ```bash
  cd /path/to/GestorDePedidosIntegrado
  git pull origin multi-tenant
  docker compose build backend capi-worker bling-worker
  ```
- [ ] **1.2.3** Subir os serviços e acompanhar migrations:
  ```bash
  docker compose up -d backend capi-worker bling-worker
  docker compose logs -f backend  # acompanhar cada migration [ADD]/[SUCCESS]/[SKIP]
  ```
- [ ] **1.2.4** Confirmar que o `entrypoint.sh` executou toda a cadeia de migrations sem erros

**Critério de saída:** Backend rodando, todas as migrations aplicadas com sucesso

---

### Tarefa 1.3 — Verificação pós-deploy (smoke tests)

**Objetivo:** Confirmar que o sistema funciona como antes com 1 loja

- [ ] **1.3.1** Rodar checks de integridade no banco de produção:
  ```bash
  docker compose exec backend python scripts/migrations/_gate_check_integrity.py
  # Esperado: GATE OK (zero nulos, zero órfãos, FKs e uniques presentes)
  ```
- [ ] **1.3.2** Confirmar que `is_multi_store()` retorna `False`:
  ```bash
  docker compose exec backend python -c "from app.services.tenancy import is_multi_store; print(is_multi_store())"
  # Esperado: False
  ```
- [ ] **1.3.3** Smoke autenticado manual:
  - Login admin → funciona
  - Listar pedidos → numeração continua normal
  - Criar pedido → `numero_pedido` sequencial correto
  - Lead público/whatsapp-start → resolve loja default
  - Bling/Meta → enfileiram normalmente
- [ ] **1.3.4** Verificar logs dos workers:
  ```bash
  docker compose logs capi-worker --tail=50
  docker compose logs bling-worker --tail=50
  # Nenhum erro novo de tenant
  ```

**Critério de saída:** GATE OK, `is_multi_store() == False`, smoke manual passa, workers sem erros

---

### Tarefa 1.4 — Documentar resultado do deploy

- [ ] **1.4.1** Atualizar `specs/Gestor/10-rollout-fases-0-2.md` marcando Fase 1 como concluída com data
- [ ] **1.4.2** Commit: `docs(specs): Fase 1 deploy concluída - data e notas`

---

## FASE 2: Verificar store_settings da Loja Default

> O import `.env → store_settings` já é automático. Aqui verificamos, não importamos.

### Tarefa 2.1 — Confirmar existência do store_settings

- [ ] **2.1.1** Verificar nos logs do deploy se apareceu:
  ```
  [ADD] store_settings do tenant default importada do ambiente
  ```
  ou `[SKIP]` (já existente)
- [ ] **2.1.2** Consultar o banco diretamente:
  ```sql
  SELECT store_ref_id, created_at FROM store_settings
  WHERE store_ref_id = (SELECT id FROM stores WHERE slug='default');
  # Deve retornar 1 linha
  ```

---

### Tarefa 2.2 — Comparar config sem vazar segredos

- [ ] **2.2.1** Chamar o endpoint de integrações (como admin autenticado):
  ```bash
  curl -H "Authorization: Bearer <token>" http://localhost:5000/api/config/integrations
  ```
- [ ] **2.2.2** Verificar que cada credencial do `.env` aparece como `has_<campo> = true`
- [ ] **2.2.3** Confirmar que campos não-secretos (pixel_id, measurement_id, customer_id, plataforma UTMify, CEP/endereço) batem com o `.env`
- [ ] **2.2.4** Confirmar que nenhum segredo é exposto na resposta (campos mascarados)

---

### Tarefa 2.3 — Confirmar leitura pelo banco (não mais .env)

- [ ] **2.3.1** Verificar que `uses_environment_fallback` retorna `False` para a default:
  ```bash
  docker compose exec backend python -c "
  from app.services.tenancy import uses_environment_fallback
  print(uses_environment_fallback(None))
  "
  # Esperado: False
  ```
- [ ] **2.3.2** Smoke de config: um envio Meta/UTMify usa a config de `store_settings` (verificar log com `store_ref_id`)

---

### Tarefa 2.4 — Documentar resultado

- [ ] **2.4.1** Atualizar `specs/Gestor/10-rollout-fases-0-2.md` marcando Fase 2 como concluída
- [ ] **2.4.2** Commit: `docs(specs): Fase 2 store_settings verificada - data e notas`

---

## FASE 3: Métricas e Alertas por Tenant

> Recomendado antes de ativar a 2ª loja em produção

### Tarefa 3.1 — Instrumentar taxa de erro por tenant

- [ ] **3.1.1** Criar middleware que loga `store_ref_id` em cada request:
  ```python
  # backend/app/middleware/tenant_metrics.py
  import time
  from flask import g, request
  
  def init_tenant_metrics(app):
      @app.before_request
      def start_timer():
          g._request_start = time.time()
      
      @app.after_request
      def log_tenant_metric(response):
          duration = time.time() - getattr(g, '_request_start', time.time())
          store_id = getattr(g, 'tenant_store_id', None)
          app.logger.info(
              'request_completed',
              extra={
                  'store_ref_id': store_id,
                  'method': request.method,
                  'path': request.path,
                  'status': response.status_code,
                  'duration_ms': round(duration * 1000, 2),
              }
          )
          return response
  ```
- [ ] **3.1.2** Registrar o blueprint/middleware em `factory.py`
- [ ] **3.1.3** Testar que logs incluem `store_ref_id`

---

### Tarefa 3.2 — Health endpoint por tenant (admin only)

- [ ] **3.2.1** Criar endpoint `GET /api/admin/tenant-health`:
  ```python
  # backend/app/routes/admin_health.py
  from flask import Blueprint, jsonify
  from app.middleware.auth import require_auth
  from app.models import db, Store, Pedido, MetaCapiOutbox
  
  admin_health_bp = Blueprint('admin_health', __name__)
  
  @admin_health_bp.route('/api/admin/tenant-health', methods=['GET'])
  @require_auth(roles=['admin'])
  def tenant_health():
      stores = db.session.query(Store).filter(Store.active == True).all()
      health = []
      for store in stores:
          pedidos_hoje = db.session.query(Pedido).filter(
              Pedido.store_ref_id == store.id,
              # ... filtro data
          ).count()
          outbox_pendente = db.session.query(MetaCapiOutbox).filter(
              MetaCapiOutbox.store_ref_id == store.id,
              MetaCapiOutbox.status == 'pending'
          ).count()
          health.append({
              'store_id': str(store.id),
              'slug': store.slug,
              'name': store.name,
              'pedidos_hoje': pedidos_hoje,
              'outbox_pendente': outbox_pendente,
          })
      return jsonify({'stores': health})
  ```
- [ ] **3.2.2** Registrar blueprint em `factory.py`
- [ ] **3.2.3** Testar com admin autenticado

---

### Tarefa 3.3 — Configurar alertas (documentação)

- [ ] **3.3.1** Documentar thresholds recomendados:
  - Taxa de erro > 1% por tenant
  - Latência p95 > 2s
  - Zero eventos Meta em 24h para loja ativa
- [ ] **3.3.2** Criar `docs/monitoring.md` com instruções de setup

---

## FASE 4: Revisão de Segurança

> Recomendado antes de ativar a 2ª loja

### Tarefa 4.1 — Timing attack em tenant resolution

- [ ] **4.1.1** Auditar `resolve_tenant()` em `tenancy.py` — confirmar que IDs inválidos não vazam tempo diferente
- [ ] **4.1.2** Se necessário, adicionar constante-time comparison para `store_ref_id`

---

### Tarefa 4.2 — Limpeza de segredos em memória

- [ ] **4.2.1** Após `runtime_config()`, zerar segredos descriptografados:
  ```python
  config = runtime_config(store_ref_id)
  try:
      # usar config
      pass
  finally:
      for key in ['META_CAPI_ACCESS_TOKEN', 'GA4_API_SECRET', 'UTMIFY_API_TOKEN']:
          if key in config:
              config[key] = None
      del config
      import gc; gc.collect()
  ```
- [ ] **4.2.2** Implementar context manager `secure_config()` se aplicável

---

### Tarefa 4.3 — Hardening de cookies/sessão

- [ ] **4.3.1** Auditar configuração de cookies JWT:
  - `SameSite=Strict`
  - `Secure=True` (em produção)
  - `HttpOnly=True`
  - Prefixo `__Host-` se aplicável
- [ ] **4.3.2** Confirmar que JWT nunca é armazenado em `localStorage` (auditar Zustand store)

---

### Tarefa 4.4 — CORS restritivo

- [ ] **4.4.1** Revisar `backend/app/cors.py` — confirmar origens restritas por ambiente
- [ ] **4.4.2** Em produção, CORS deve aceitar apenas domínios conhecidos

---

### Tarefa 4.5 — Rate limiting por tenant

- [ ] **4.5.1** Implementar `MAX_OUTBOX_PER_CYCLE` por `store_ref_id` nos workers:
  ```python
  # No worker, limitar processamento por loja
  MAX_PER_STORE = 100
  
  def process_outbox_cycle():
      for store_id in get_active_stores():
          items = get_pending_items(store_id, limit=MAX_PER_STORE)
          # processar...
  ```
- [ ] **4.5.2** Testar que uma loja em loop não consuma todos os recursos

---

### Tarefa 4.6 — Documentar rotação de chaves

- [ ] **4.6.1** Criar `docs/key-rotation.md` com procedimento de rotação de `SECRET_KEY`
- [ ] **4.6.2** Documentar impacto em segredos AES-GCM existentes

---

## FASE 5: Ativar 2ª Loja em Produção

> Após Fases 1–4 validadas

### Tarefa 5.1 — Criar a 2ª loja

- [ ] **5.1.1** Criar loja no banco:
  ```sql
  INSERT INTO stores (name, slug, active) VALUES ('Loja 2', 'loja-2', true);
  ```
- [ ] **5.1.2** Criar `store_settings` para a loja 2 (via API ou migration)
- [ ] **5.1.3** Criar usuário admin para a loja 2:
  ```bash
  docker compose exec backend flask create-admin --store loja-2
  ```
- [ ] **5.1.4** Ativar modo multi-tenant:
  ```bash
  # No .env de produção
  FORCE_MULTI_TENANT=1
  ```
- [ ] **5.1.5** Reiniciar backend para aplicar flag

---

### Tarefa 5.2 — Smoke pós-ativação

- [ ] **5.2.1** Login como admin loja 1 → vê só dados da loja 1
- [ ] **5.2.2** Login como admin loja 2 → vê só dados da loja 2
- [ ] **5.2.3** ID de pedido da loja 1 → 404 quando acessado pela loja 2
- [ ] **5.2.4** Worker processa ambas as lojas com credenciais distintas
- [ ] **5.2.5** Verificar que `is_multi_store()` retorna `True`

---

### Tarefa 5.3 — Monitoramento pós-ativação

- [ ] **5.3.1** Monitorar métricas por 48h antes de declarar sucesso
- [ ] **5.3.2** Verificar logs de ambas as lojas diariamente
- [ ] **5.3.3** Confirmar que outbox de cada loja usa credenciais corretas

---

## FASE 6: UTMify Síncrono

> Não bloqueia a operação multi-loja, mas é o último canal não coberto pelo outbox

### Tarefa 6.1 — Implementar dispatcher UTMify

- [ ] **6.1.1** Finalizar implementação do dispatcher síncrono em `backend/app/services/integration_validation/`
- [ ] **6.1.2** Integrar com `MarketingConversionOutbox` ou criar fluxo próprio
- [ ] **6.1.3** Testar com 2 lojas e tokens distintos (teste de isolamento)

---

## FASE 7: Landing Page → Store Mapping

> Necessário para leads públicos multi-loja

### Tarefa 7.1 — Definir estratégia de mapeamento

- [ ] **7.1.1** Decidir entre domínio (`loja1.com.br` → store 1) ou path/utm (`?store=loja-2`)
- [ ] **7.1.2** Documentar decisão em `specs/Gestor/`

---

### Tarefa 7.2 — Implementar resolução

- [ ] **7.2.1** Modificar `resolve_public_write_company()` para aceitar o novo mapeamento
- [ ] **7.2.2** Se por domínio: adicionar verificação de `Host` header no middleware
- [ ] **7.2.3** Testar lead público com duas lojas em staging

---

## FASE 8: Cleanup de Débitos Técnicos

> Não bloqueia, mas melhora qualidade do código

### Tarefa 8.1 — Ruff (25 ocorrências)

- [ ] **8.1.1** Rodar `ruff check . --fix` e revisar correções automáticas
- [ ] **8.1.2** Corrigir manualmente o que o autofix não resolver
- [ ] **8.1.3** Commit: `style: fix ruff warnings`

---

### Tarefa 8.2 — Black (62 arquivos)

- [ ] **8.2.1** Rodar `black .` e revisar formatação
- [ ] **8.2.2** Commit: `style: apply black formatting`

---

### Tarefa 8.3 — TypeScript (tsc --noEmit)

- [ ] **8.3.1** Rodar `cd frontend && npx tsc --noEmit` e listar erros
- [ ] **8.3.2** Corrigir erros de tipo progressivamente
- [ ] **8.3.3** Commit: `fix(frontend): resolve TypeScript errors`

---

## Resumo de Prioridades

| Ordem | Fase | Bloqueia 2ª loja? | Esforço estimado |
|---|---|---|---|
| 1 | Fase 1 — Deploy com 1 loja | Sim | 1 dia |
| 2 | Fase 2 — Verificar store_settings | Sim | 2 horas |
| 3 | Fase 3 — Métricas e alertas | Recomendado | 2 dias |
| 4 | Fase 4 — Revisão de segurança | Recomendado | 2 dias |
| 5 | Fase 5 — Ativar 2ª loja | — (objetivo) | 1 dia |
| 6 | Fase 6 — UTMify síncrono | Não | 1 dia |
| 7 | Fase 7 — Store mapping | Sim (leads multi-loja) | 1 dia |
| 8 | Fase 8 — Cleanup débitos | Não | 2-3 dias |

---

## Referências

- Runbook de deploy: `specs/Gestor/10-rollout-fases-0-2.md`
- Estado atual: `specs/Gestor/08-estado-atual-e-proximos-passos.md`
- Roadmap completo: `specs/Gestor/11-proximos-passos.md`
- Specs temáticas: `specs/Gestor/01` a `07`
