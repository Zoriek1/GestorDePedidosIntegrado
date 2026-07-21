# Grupo 2: Secure Config + Rate Limiting por Tenant

> **Tarefas:** 4.2 (Limpeza segredos) + 4.5 (Rate limiting workers)

**Goal:** Integrar `secure_runtime_config()` nos workers e garantir isolamento por tenant em todos os serviços.

**Architecture:** Context manager `secure_runtime_config()` zera segredos do dict após uso. Workers iteram por loja com limite por tenant. Nuvemshop ganha `store_ref_id` em `process_pending`.

**Tech Stack:** Flask, SQLAlchemy, contextlib, pytest

## Global Constraints

- Python 3.8+ (target em pyproject.toml)
- SQLite para testes, PostgreSQL para produção
- JWT Bearer auth (não session cookies)
- Multi-tenant via `Store` model com `store_ref_id`

---

## Tarefa 2.1: Integrar `secure_runtime_config` nos workers

**Files:**
- Modify: `app/commands/send_daily_purchases_to_meta_command.py` (line ~154, `process_outbox_cycle`)
- Modify: `app/integrations/bling/service.py` (line ~451, `process_pending`)
- Modify: `app/services/marketing_conversion_dispatcher.py` (line ~31, `process_cycle`)
- Test: `tests/test_secure_config.py`

**Interfaces:**
- Consumes: `secure_runtime_config(store_ref_id) -> Iterator[dict]` de `app/services/secure_config.py`
- Produces: Todos os services que chamam `runtime_config()` devem usar o context manager

- [ ] **Step 1: Auditar todas as chamadas a `runtime_config()`**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\backend"
rg "runtime_config\(" --type py -n
```

- [ ] **Step 2: Substituir em `send_daily_purchases_to_meta_command.py`**

Encontrar onde `runtime_config` é chamado dentro de `process_outbox_cycle` e substituir por `secure_runtime_config`. O dict de config deve ser usado apenas dentro do bloco `with`.

- [ ] **Step 3: Substituir em `bling/service.py`**

O método `process_pending` chama `runtime_config` para obter credenciais. Envolver em `secure_runtime_config`.

- [ ] **Step 4: Substituir em `marketing_conversion_dispatcher.py`**

O dispatcher chama `runtime_config(getattr(row, "store_ref_id", None))` em `_send()`. Envolver cada chamada.

- [ ] **Step 5: Rodar testes existentes**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\backend"
python -m pytest tests/test_secure_config.py tests/test_tenant_workers.py -v
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(security): integrate secure_runtime_config in all worker paths"
```

---

## Tarefa 2.2: Nuvemshop `process_pending` com `store_ref_id`

**Files:**
- Modify: `app/models/nuvemshop_webhook_delivery.py` — adicionar coluna `store_ref_id`
- Modify: `app/integrations/nuvemshop/service.py:97-116` — adicionar parâmetro
- Create: `scripts/migrations/add_store_ref_to_nuvemshop_delivery.py`
- Create: `tests/test_nuvemshop_tenant.py`

**Interfaces:**
- Produces: `process_pending(limit, store_ref_id=None) -> Tuple[int, int]`

- [ ] **Step 1: Adicionar coluna `store_ref_id` no model**

```python
# app/models/nuvemshop_webhook_delivery.py
# Adicionar após store_id:
store_ref_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=True, index=True)
```

- [ ] **Step 2: Criar migration script**

```python
# scripts/migrations/add_store_ref_to_nuvemshop_delivery.py
"""Backfill store_ref_id from NuvemshopStore mapping."""
def migrate():
    from app import db
    from app.models.nuvemshop_webhook_delivery import NuvemshopWebhookDelivery
    from app.models.nuvemshop_store import NuvemshopStore
    from sqlalchemy import text

    # Adicionar coluna se não existe
    engine = db.engine
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE nuvemshop_webhook_delivery ADD COLUMN store_ref_id INTEGER REFERENCES stores(id)"))
            conn.commit()
        except Exception:
            pass  # coluna já existe

    # Backfill: relacionar via NuvemshopStore
    mappings = NuvemshopStore.query.all()
    for ns in mappings:
        NuvemshopWebhookDelivery.query.filter_by(store_id=ns.store_id).update({"store_ref_id": ns.store_ref_id})
    db.session.commit()
```

- [ ] **Step 3: Modificar `process_pending`**

```python
# app/integrations/nuvemshop/service.py
def process_pending(self, limit: int = 50, store_ref_id: int | None = None) -> Tuple[int, int]:
    query = NuvemshopWebhookDelivery.query.filter_by(status="pending")
    if store_ref_id is not None:
        query = query.filter_by(store_ref_id=store_ref_id)
    deliveries = query.order_by(NuvemshopWebhookDelivery.received_at.asc()).limit(limit).all()
    # ... resto mantido
```

- [ ] **Step 4: Criar testes**

```python
# tests/test_nuvemshop_tenant.py
"""Testes para isolamento por tenant no Nuvemshop."""
import pytest
from app import db
from app.models.store import Store
from app.models.nuvemshop_webhook_delivery import NuvemshopWebhookDelivery

@pytest.fixture
def app():
    from flask import Flask
    import app.models
    flask_app = Flask(__name__)
    flask_app.config.update({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test",
        "TESTING": True,
    })
    db.init_app(flask_app)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

def test_process_pending_filters_by_store(app):
    with app.app_context():
        store_a = Store(name="A", slug="a", active=True)
        store_b = Store(name="B", slug="b", active=True)
        db.session.add_all([store_a, store_b])
        db.session.commit()

        for i in range(3):
            db.session.add(NuvemshopWebhookDelivery(
                store_id="ext-a", store_ref_id=store_a.id,
                event="order/created", resource_id=str(i), status="pending"
            ))
        for i in range(3, 6):
            db.session.add(NuvemshopWebhookDelivery(
                store_id="ext-b", store_ref_id=store_b.id,
                event="order/created", resource_id=str(i), status="pending"
            ))
        db.session.commit()

        from app.integrations.nuvemshop.service import NuvemshopService
        # Mock client to avoid real API calls
        # ... assert per-store filtering
```

- [ ] **Step 5: Rodar testes**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\backend"
python -m pytest tests/test_nuvemshop_tenant.py -v
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(nuvemshop): add store_ref_id to webhook delivery + tenant filtering"
```

---

## Tarefa 2.3: Rate limiting por tenant (opcional)

**Files:**
- Modify: `app/middleware.py:587-642`

**Depende de:** Decisão se rate limit por IP é suficiente.

- [ ] **Step 1: Avaliar necessidade**
  - Se o app é multi-tenant mas com poucos usuários por tenant, IP-based é suficiente
  - Se um tenant pode ter muitos IPs (CDN/móvel), considerar bucket por store_ref_id

- [ ] **Step 2 (se necessário): Adicionar bucket composto**

```python
# app/middleware.py, dentro de rate_limit()
ip = _get_client_ip()
store_id = getattr(g, "tenant_store_id", None) or "global"
key = f"{ip}:{store_id}"
```

- [ ] **Step 3: Testar e commitar**
