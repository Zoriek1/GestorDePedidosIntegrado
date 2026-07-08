# API — Comissões por vendedor (para dashboard externo)

Endpoint de leitura que devolve as comissões **agregadas por vendedor** num período, em JSON.
Pensado para você puxar os dados e montar o dashboard por fora.

## Autenticação

Requer um JWT de **admin** no header. Para obter:

```bash
curl -s -X POST https://gestaopedidos.planteumaflor.online/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"SEU_EMAIL_ADMIN","password":"SUA_SENHA"}' | jq -r .access_token
```

O token expira em `JWT_EXPIRATION_HOURS` (padrão 24h). Para automação contínua, faça login de novo
quando expirar (ou peça pra aumentar a validade / criar um token de leitura dedicado).

## Requisição

```
GET /api/ledger/commissions
Authorization: Bearer <token_admin>
```

### Parâmetros (query string)

| Param | Valores | Default | Descrição |
|-------|---------|---------|-----------|
| `from` | `YYYY-MM-DD` | — | Início do período (inclusive). Opcional. |
| `to` | `YYYY-MM-DD` | — | Fim do período (inclusive). Opcional. |
| `date_basis` | `entrega` \| `vencimento` \| `competencia` | `entrega` | Qual data define o período: `entrega` = `pedido.dia_entrega`; `vencimento` = `due_date` (quando a comissão vence); `competencia` = `week_ref` (segunda-feira da semana). |
| `user_id` | int | — | Restringe a um único vendedor. Opcional. |
| `detail` | `true` \| `false` | `false` | Se `true`, inclui a lista de pedidos (`items`) dentro de cada vendedor. |

### Exemplos

```bash
BASE=https://gestaopedidos.planteumaflor.online
TOKEN=<token_admin>

# Comissões de maio/2026 (por data de entrega), todos os vendedores:
curl -s "$BASE/api/ledger/commissions?from=2026-05-01&to=2026-05-31" \
  -H "Authorization: Bearer $TOKEN" | jq

# Com detalhamento dos pedidos:
curl -s "$BASE/api/ledger/commissions?from=2026-05-01&to=2026-05-31&detail=true" \
  -H "Authorization: Bearer $TOKEN" | jq

# Só uma vendedora, agrupando pelo vencimento da comissão:
curl -s "$BASE/api/ledger/commissions?from=2026-05-01&to=2026-05-31&date_basis=vencimento&user_id=3" \
  -H "Authorization: Bearer $TOKEN" | jq
```

## Resposta (JSON)

```json
{
  "success": true,
  "from": "2026-05-01",
  "to": "2026-05-31",
  "date_basis": "entrega",
  "totals": {
    "total_commission": 110.0,
    "paid_commission": 20.0,
    "pending_commission": 90.0,
    "orders_count": 4,
    "vendedores_count": 2
  },
  "vendedores": [
    {
      "user_id": 3,
      "name": "Vendedora A",
      "email": "a@loja.com",
      "total_commission": 100.0,
      "paid_commission": 20.0,
      "pending_commission": 80.0,
      "orders_count": 3,
      "by_source": [
        { "source": "whatsapp", "total": 50.0, "orders_count": 2 },
        { "source": "site", "total": 50.0, "orders_count": 1 }
      ],
      "items": [
        {
          "entry_id": 10,
          "pedido_id": 55,
          "cliente": "Fulano",
          "dia_entrega": "2026-05-11",
          "week_ref": "2026-05-04",
          "due_date": "2026-05-09",
          "commission_amount": 30.0,
          "commission_rate_pct": 3.0,
          "source": "whatsapp",
          "category": "comissao_whatsapp",
          "status": "active",
          "settled_at": null
        }
      ]
    }
  ]
}
```

Notas:
- `paid_commission` = comissões já quitadas (`status = settled`); `pending_commission` = ainda em aberto (`active`).
- `items` só aparece com `detail=true`.
- `vendedores` vem ordenado por `total_commission` desc.
- Considera apenas comissões de vendedor (categorias `comissao_*`); taxas de entrega de entregador não entram.
- Valores monetários em reais (float, 2 casas).
```
