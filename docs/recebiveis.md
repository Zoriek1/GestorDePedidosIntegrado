# Módulo Recebíveis (Ledger)

Conta corrente double-entry entre vendedor/entregador e a empresa. Tudo vive em [backend/app/models/ledger_entry.py](../backend/app/models/ledger_entry.py), [backend/app/models/user.py](../backend/app/models/user.py), [backend/app/services/ledger_service.py](../backend/app/services/ledger_service.py), [backend/app/services/commission_service.py](../backend/app/services/commission_service.py) e [backend/app/routes/ledger_routes.py](../backend/app/routes/ledger_routes.py).

## Modelo

### `LedgerEntry`

```
id  user_id  type   category               amount   status   ...
1   3        CREDIT comissao_whatsapp      12.00    active
2   3        CREDIT fixo_semanal          200.00    active
3   3        DEBIT  pagamento             212.00    settled
```

Quando um DEBIT é criado para quitar um lote, os CREDITs ativos viram `status='settled'` e ganham `settled_by_id = id_do_debit`.

Campos importantes ([ledger_entry.py:44-131](../backend/app/models/ledger_entry.py#L44)):

| Campo | Função |
|---|---|
| `type` | `CREDIT` (a empresa deve ao vendedor) ou `DEBIT` (vendedor recebeu) |
| `category` | Ver `CREDIT_CATEGORIES` / `DEBIT_CATEGORIES` abaixo |
| `amount` | `Numeric(12,2)`, sempre positivo |
| `status` | `active` ou `settled` |
| `pedido_id` | Para comissões. Índice UNIQUE parcial `WHERE voided=0 AND pedido_id IS NOT NULL` garante uma comissão ativa por pedido. |
| `delivery_pedido_id` | Para taxa de entrega (crédito do entregador). Índice UNIQUE parcial análogo. |
| `week_ref` | Segunda-feira da semana de referência (para fixo/almoço/transporte semanais) |
| `due_date` | Data prevista de pagamento (week_ref + `PayrollConfig.payment_day`) |
| `voided` + `void_reason` | Estorno (edição de pedido, soft delete, regressão de status). Não apaga, marca. |
| `commission_rate` + `commission_source` | Snapshot da config histórica (preserva se a config mudou depois) |

Categorias válidas (linhas 23-41):

- **CREDIT**: `fixo_semanal`, `fixo_mensal`, `almoco`, `transporte`, `comissao_whatsapp`, `comissao_site`, `comissao_balcao`, `comissao_indicacao`, `comissao_lucro`, `custom_credit`, `taxa_entrega`
- **DEBIT**: `pagamento`, `adiantamento`, `ajuste_debito`

### `PayrollConfig` (remuneração fixa)

Por vendedor, N configs (uma por categoria fixa: `fixo_semanal`, `almoco`, `transporte`). `payment_day` (0=Seg ... 6=Dom) define o dia da due_date dos créditos semanais.

### `CommissionConfig` (comissão por fonte)

Por vendedor, N configs — uma por fonte de pedido. **Forma preferencial**: `fonte_pedido_id` (FK → `fontes_pedido`). **Legado**: `source` (string). Lookup em `commission_service.py` tenta FK primeiro, depois cai no source.

`rate` é decimal (0.03 = 3%).

## Fluxos

### 1. Geração automática de comissão

Em [backend/app/repositories/pedido_repository.py](../backend/app/repositories/pedido_repository.py) `atualizar_status`, quando `Pedido.status_pagamento` transita para `Pago`/`Parcial`:

1. [commission_service.generate_commission()](../backend/app/services/commission_service.py) é chamado.
2. Busca `CommissionConfig` ativa do vendedor para a `fonte_pedido_id` (ou source) do pedido.
3. Calcula `(valor - taxa_cartao_valor) * rate`. **Taxa do cartão desconta da base** (e do líquido).
4. Insere CREDIT `comissao_<source>` com `pedido_id`, `commission_rate`/`commission_source` (snapshot), `due_date = get_due_date_for_commission(today, payment_day)`.
5. Idempotente: índice UNIQUE parcial impede duplicação.

Em edição de pedido com regressão de status ou mudança de valor: o CREDIT antigo é marcado `voided=true` e um novo é criado ([order_commission_lifecycle.py](../backend/app/services/order_commission_lifecycle.py)).

### 2. Créditos semanais (fixos)

`POST /api/ledger/generate-weekly` (admin) chama [ledger_service.generate_weekly_credits()](../backend/app/services/ledger_service.py) que, para cada vendedor ativo:

- Insere CREDITs `fixo_semanal`, `almoco`, `transporte` baseados em PayrollConfig.
- `week_ref` = segunda-feira da semana (`get_monday()` em [backend/app/utils/date_utils.py](../backend/app/utils/date_utils.py)).
- Idempotente: índice UNIQUE parcial em `(user_id, week_ref, category)` para essas 3 categorias.

### 3. Crédito de entrega

[delivery_credit_service.py](../backend/app/services/delivery_credit_service.py): quando entregador finaliza entrega (`pedidos/<id>/finalizar-entrega`), insere CREDIT `taxa_entrega` com `delivery_pedido_id`. Idempotente.

### 4. Quitação (settle)

`POST /api/ledger/settle` (vendedor/entregador ou admin):

1. Cria um DEBIT `pagamento` com `status='settled'` e `amount = sum(CREDITs ativos)`.
2. Atualiza todos esses CREDITs: `status='settled'`, `settled_at=now`, `settled_by_id=<id do DEBIT>`.

`POST /api/ledger/entries` aceita também DEBITs `adiantamento`/`ajuste_debito` avulsos.

## Endpoints ([ledger_routes.py](../backend/app/routes/ledger_routes.py))

Todos sob `/api/ledger/`:

| Método | Path | Quem |
|---|---|---|
| GET | `/balance` | self/admin | retorna `{total_credits, overdue_credits, due_today_credits, upcoming_credits, total_debits, balance}` |
| POST | `/settle` | self/admin | quita todos os CREDITs ativos do usuário |
| GET | `/entries` | self/admin | lista entradas (filtros: type, status, date range) |
| POST | `/entries` | admin | cria CREDIT/DEBIT manual |
| DELETE | `/entries/<id>` | admin | apaga entrada (perigoso; só para correção) |
| POST | `/generate-weekly` | admin | gera créditos semanais para todos os vendedores |
| GET | `/periods` | admin | semanas com agregados |
| GET | `/pedidos` | self/admin | pedidos atribuídos ao vendedor com totais |
| GET | `/summary` | admin | overview de todos os vendedores |
| GET | `/pending` | admin | tudo pendente de pagamento |
| POST | `/generate-calendar` | admin | gera due_dates faltantes |
| GET | `/export` | admin | export CSV |

Frontend: [frontend_v2/src/features/ledger/](../frontend_v2/src/features/ledger/) — `LedgerPage.tsx` para admin/vendedor, `EntregadorTodayView.tsx` para entregador.
