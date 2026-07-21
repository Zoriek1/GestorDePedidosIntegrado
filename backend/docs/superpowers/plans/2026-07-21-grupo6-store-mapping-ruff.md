# Grupo 6: Store Mapping + Ruff

> **Tarefas:** 7.2 (Store mapping) + 8.1 (Ruff)

**Goal:** Documentar mapeamento de lojas e rodar Ruff no codebase.

**Architecture:** Store → StoreSetting → runtime_config → workers. Ruff para linting Python.

**Tech Stack:** SQLAlchemy, Ruff

## Global Constraints

- Ruff config em pyproject.toml: E/W/F/I/B/C4, ignore E501/B008
- Target Python 3.8
- Black compat (line-length 100)

---

## Tarefa 6.1: Documentar store mapping

**Files:**
- Create: `docs/architecture/store-mapping.md`

- [ ] **Step 1: Criar documentação**

```markdown
# Store Mapping — Arquitetura Multi-Tenant

## Modelo Store

```python
class Store(db.Model):
    __tablename__ = "stores"
    id         = Column(Integer, primary_key=True)
    name       = Column(String(120), nullable=False)
    slug       = Column(String(60), nullable=False, unique=True, index=True)
    active     = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, onupdate=...)
```

- `id`: Chave interna usada como `store_ref_id` em todas as tabelas
- `slug`: Identificador legível, usado em URLs e OAuth state
- `active`: Flag para desativar tenant sem deletar dados

## Fluxo de config por loja

```
Store (id, slug, active)
  ↓ 1:1
StoreSetting (meta_pixel_id, utmify_enabled, ...)
  ↓ get_secret() / atributo direto
runtime_config(store_ref_id) → dict com todas as configs
  ↓ usado por
Workers (Meta CAPI, Bling, Nuvemshop) e Services
```

## Resolução de fallback

```python
def runtime_config(store_ref_id):
    store = db.session.get(Store, store_ref_id)
    settings = get_settings(store.id)
    if not settings:
        if store.slug == "default":
            return _environment_runtime_config()  # fallback env vars
        return _disabled_runtime_config()  # desabilitado
    return { "META_CAPI_ACCESS_TOKEN": settings.get_secret("meta_capi_access_token"), ... }
```

1. Busca StoreSetting pela loja
2. Se não existe e é loja default → fallback para env vars
3. Se não existe e é outra loja → desabilitado
4. Se existe → retorna config do banco (com secrets decriptados)

## Tabelas com store_ref_id

| Tabela | Coluna | FK |
|--------|--------|-----|
| `meta_capi_outbox` | `store_ref_id` | `stores.id` |
| `meta_capi_lead_outbox` | `store_ref_id` | `stores.id` |
| `bling_outbox` | `store_ref_id` | `stores.id` |
| `marketing_conversion_outbox` | `store_ref_id` | `stores.id` |
| `nuvemshop_webhook_delivery` | `store_ref_id` | `stores.id` |
| `store_settings` | `store_ref_id` | `stores.id` |

## Workers — iteração por loja

```python
# Padrão em todos os workers:
active_stores = Store.query.filter_by(active=True).all()
per_store_limit = max(1, total_limit // max(len(active_stores), 1))
for store in active_stores:
    service.process(limit=per_store_limit, store_ref_id=store.id)
```

Empresa inativa: linhas pendentes são invalidadas (`status="failed", error="store_inactive"`).
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture/store-mapping.md
git commit -m "docs(architecture): multi-tenant store mapping documentation"
```

---

## Tarefa 6.2: Rodar Ruff e corrigir issues

**Files:**
- Modify: múltiplos arquivos conforme output do Ruff

- [ ] **Step 1: Rodar Ruff para ver issues**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\backend"
ruff check .
```

- [ ] **Step 2: Auto-fix**

```bash
ruff check --fix .
```

- [ ] **Step 3: Revisar fixes restantes**

```bash
ruff check .
```

Corrigir manualmente se necessário.

- [ ] **Step 4: Confirmar zero issues**

```bash
ruff check .
```

Esperado: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "style: ruff check --fix cleanup"
```
