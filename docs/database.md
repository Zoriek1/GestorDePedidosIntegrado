# Banco de Dados

## Stack

- **Produção e dev (Docker)**: PostgreSQL 16 Alpine — serviço `db` em [docker-compose.yml](../docker-compose.yml). Volume persistente em `pg_data`.
- **Conexão**: variável `DATABASE_URL`. Default em compose: `postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@db:5432/<POSTGRES_DB>`.
- **Fallback** (rodando `python main.py` localmente sem Docker): SQLite em `~/var/lib/database/database.db` ([backend/app/config.py:49-52](../backend/app/config.py#L49-L52)). Usado também por testes unitários em memória.

PRAGMAs WAL e FK enforcement só são aplicados quando o dialeto é SQLite ([backend/app/extensions.py](../backend/app/extensions.py)).

## Models principais ([backend/app/models/](../backend/app/models/))

| Model | Tabela | Notas |
|---|---|---|
| `Pedido` | `pedidos` | Núcleo. Campos do wizard de 4 steps + soft delete (`deleted_at`) + `vendedor_id`/`entregador_id` + `paid_at` imutável + `fbc`/`fbp` (Meta Pixel) + frete dividido em operacional vs cobrado do cliente. |
| `Cliente` + `EnderecoCliente` | `clientes`, `enderecos_cliente` | CRM. Cliente tem múltiplos endereços; um marcado como principal. |
| `User`, `PayrollConfig`, `CommissionConfig` | `users`, `payroll_config`, `commission_config` | Roles: `admin`, `vendedor`, `atendente`, `entregador`, `viewer`. `PayrollConfig.payment_day` (0-6) controla due_date dos créditos semanais. `CommissionConfig.fonte_pedido_id` (FK) é a forma preferencial; `source` (string) é legado. |
| `LedgerEntry` | `ledger_entry` | Recebíveis double-entry. Ver [recebiveis.md](recebiveis.md). |
| `Lead` + `LeadTouchpoint` | `leads`, `lead_touchpoints` | Funil de captação. Pedido pode referenciar Lead. |
| `FontePedido`, `PedidoFonte` | `fontes_pedido`, `pedido_fontes` | Origens (WhatsApp, Site, etc.). `Pedido.fonte_pedido_id` é a FK ativa; `Pedido.fonte_pedido` (string) é legado. |
| `MetaCapiOutbox` + `MetaCapiLeadOutbox` | `meta_capi_outbox`, `meta_capi_lead_outbox` | Outbox pattern para envio assíncrono ao Meta (Purchase / Lead). |
| `NuvemshopStore` + `NuvemshopWebhookDelivery` | `nuvemshop_stores`, `nuvemshop_webhook_deliveries` | OAuth tokens por loja + log de webhooks processados. |
| `RotaOtimizada` | `rotas_otimizadas` | Snapshot de rota gerada (GraphHopper/OpenRouteService). |
| `PedidoExternalRef`, `PedidoManualOverride` | — | Refs externas (id Nuvemshop, etc.) e overrides manuais de taxa/agendamento. |
| `AuditLog`, `PushSubscription` | — | Auditoria + VAPID Push. |

## Conversões críticas

- **Dinheiro em pedido**: `Pedido.valor` é `String` (formato BR `"R$ 250,00"`). Use `parse_brl_money()` em [backend/app/utils/money.py](../backend/app/utils/money.py).
- **Dinheiro em ledger**: `LedgerEntry.amount` é `Numeric(12,2)`, sempre positivo. Serialize com `float(entry.amount)`.
- **Timestamps**: `datetime_now_brazil()` (TZ `America/Sao_Paulo`) — definido em [models/pedido.py:20](../backend/app/models/pedido.py#L20) e duplicado em [models/ledger_entry.py:18](../backend/app/models/ledger_entry.py#L18) e [models/user.py:18](../backend/app/models/user.py#L18).

## Migrations

Não usamos Alphabet/Alembic/Flask-Migrate. Migrations são scripts Python custom em [backend/scripts/migrations/](../backend/scripts/migrations/), cada um idempotente:

```python
from app import create_app, db

def column_exists(table, col):
    from sqlalchemy import inspect
    return col in [c["name"] for c in inspect(db.engine).get_columns(table)]

if __name__ == "__main__":
    with create_app().app_context():
        if not column_exists("pedidos", "novo_campo"):
            db.session.execute(db.text("ALTER TABLE pedidos ADD COLUMN novo_campo TEXT"))
            db.session.commit()
```

Como rodar em Docker:

```bash
docker compose exec backend python scripts/migrations/<arquivo>.py
```

[backend/entrypoint.sh](../backend/entrypoint.sh) roda automaticamente os scripts críticos no boot do container.

Schema é também criado via `db.create_all()` em [backend/app/extensions.py](../backend/app/extensions.py) — útil em ambientes vazios (testes, primeira subida).
