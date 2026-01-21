# Meta Conversions API (CAPI) - Arquitetura Outbox

## Visao Geral

Este documento descreve a arquitetura de envio de eventos de compra (Purchase) para a Meta Conversions API, utilizando o padrao Outbox para garantir entrega confiavel.

## Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Pedido       │───>│   Outbox        │───>│  Meta CAPI      │
│  (status=Pago)  │    │ (pending/sent)  │    │  Gateway/API    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
        │  Hook: create_outbox │  Command: send_batch │
        │  if_purchase()       │  every hour          │
        ▼                      ▼                      ▼
   Criacao do          Persistencia          Envio HTTP
   evento              segura                com retry
```

## Componentes

### 1. MetaCapiOutbox (Model)
Arquivo: `backend/app/models/meta_capi_outbox.py`

Armazena eventos pendentes com:
- `order_id`: Referencia ao pedido
- `event_id`: ID unico do evento (formato: `order_<id>`)
- `payload_json`: Payload serializado (sem PII em claro, apenas hashes)
- `status`: pending | sent | failed
- `error_type`: retryable | permanent
- `attempts`: Contagem de tentativas

### 2. MetaCapiOutboxRepository
Arquivo: `backend/app/repositories/meta_capi_outbox_repository.py`

Operacoes:
- `create_from_pedido()`: Cria outbox com deduplicacao
- `get_pending()`: Busca pendentes para envio
- `get_failed_retryable()`: Busca failed com retry < 3
- `mark_sent()`: Marca como enviado com fbtrace_id
- `mark_failed()`: Marca como falhou com classificacao

### 3. MetaConversionsApiService
Arquivo: `backend/app/services/meta_capi.py`

Responsabilidades:
- Normalizacao de dados (telefone BR E.164, nomes, etc.)
- Hashing SHA-256 conforme especificacao Meta
- Validacao de fbc/fbp
- Sanitizacao de payloads (remocao de campos invalidos)
- Envio HTTP para Meta (direto ou via Gateway)
- Classificacao de erros (retryable vs permanent)

### 4. SendDailyPurchasesToMetaCommand
Arquivo: `backend/app/commands/send_daily_purchases_to_meta_command.py`

Fluxo:
1. Safety Net: Busca pedidos pagos do dia e cria outbox faltantes
2. Processa pendentes em lotes de 50
3. Processa failed retryable com attempts < 3
4. Marca como sent ou failed conforme resposta

## Configuracao (.env)

```env
# Credenciais obrigatorias
META_PIXEL_ID=123456789
META_CAPI_ACCESS_TOKEN=EAAxxxxxxxx

# Versao da API (padrao: v21.0)
META_CAPI_API_VERSION=v21.0

# Codigo de teste (apenas dev/homologacao)
META_TEST_EVENT_CODE=TEST12345

# Gateway (opcional - usar dominio proprio)
META_CAPI_USE_GATEWAY=true
META_CAPI_GATEWAY_DOMAIN=gestaopedidos.planteumaflor.online

# Debug detalhado (apenas dev)
META_CAPI_DEBUG=false
```

## Gateway vs API Direta

### Gateway Proprio (Recomendado)
Quando `META_CAPI_USE_GATEWAY=true`:
- Eventos vao para `https://{seu-dominio}/meta-gateway/{pixel_id}/events`
- Seu backend faz proxy para `graph.facebook.com`
- Vantagem: URL first-party melhora rastreamento

### API Direta
Quando `META_CAPI_USE_GATEWAY=false`:
- Eventos vao diretamente para `https://graph.facebook.com/{version}/{pixel_id}/events`
- Mais simples, menos infra

**Nota:** O "Conversions API Gateway" oficial da Meta (`mv-prod-1...`) e um produto separado (hospedado no GCP). Nossa implementacao e um "proxy simples" que funciona equivalente para envio de eventos.

## Scripts de Operacao

### Envio Manual
```powershell
cd backend
python scripts/meta/send_daily_purchases_to_meta.py
```

### Diagnostico
```powershell
python scripts/meta/diagnosticar_gateway.py
```

### Recriar Outboxes (apos correcoes)
```powershell
python scripts/meta/recriar_outboxes.py
```

### Verificar Failed
```powershell
python scripts/meta/verificar_outbox_failed.py
```

## Tratamento de Erros

### Erros Retryable (tentam novamente)
- HTTP 429 (Rate Limit)
- HTTP 5xx (Server Error)
- Timeout de conexao

### Erros Permanent (nao tentam)
- HTTP 401 (Token invalido)
- HTTP 403 (Sem permissao)
- HTTP 400 com "validation" ou "invalid"

## Testes

```powershell
cd backend
pytest tests/test_meta_capi.py -v
```

Cobertura:
- Normalizacao de dados (telefone, nome, cidade)
- Hashing e deduplicacao
- Sanitizacao de payloads (event_time, fbc/fbp)
- Classificacao de erros
- Operacoes de outbox (create, mark_sent, mark_failed)

## Troubleshooting

### Erro "Invalid parameter" (subcode 2804016)
Campos invalidos em `custom_data`. Verificar se:
- Campos de localizacao (city, state, zip_code) estao em `user_data` como hash
- `event_time` esta em segundos (nao milissegundos) e dentro de 7 dias

### Erro "Timestamp no futuro" (subcode 2804004)
O `event_time` esta no futuro. O sistema normaliza automaticamente para `now()`.

### Erro "Resource not found" ao acessar URL do Gateway
Normal. O endpoint `/meta-gateway/{pixel_id}/events` e uma API, nao uma pagina web.
Use GET para verificar status ou POST para enviar eventos.
