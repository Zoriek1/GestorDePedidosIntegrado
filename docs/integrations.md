# Integrações Externas

## Meta Conversions API (Purchase + Lead)

Padrão **outbox assíncrono**: quando um pedido é criado ou um lead avança no funil, uma entrada é inserida em `MetaCapiOutbox` / `MetaCapiLeadOutbox` — o request **apenas enfileira e retorna** (não bloqueia esperando a Meta). O serviço `capi-worker` ([backend/meta_capi_worker_entrypoint.py](../backend/meta_capi_worker_entrypoint.py)) faz polling do outbox a cada `META_CAPI_WORKER_INTERVAL_SECONDS` (default 5s) e flusha pendentes + failed-retryable via [services/meta_capi.py](../backend/app/services/meta_capi.py). Falhas retryable respeitam um backoff (`META_CAPI_RETRY_BACKOFF_SECONDS`, default 300s) antes de retentar, com teto de 3 tentativas. O mesmo worker ainda roda o safety-net diário (23:00) e o payroll (06:00).

**Gateway (opcional)**: `/capig/*` e `/meta-gateway/<pixel_id>/events` em [routes/meta_gateway.py](../backend/app/routes/meta_gateway.py). Quando `META_CAPI_USE_GATEWAY=true`, eventos do Pixel também vão para nosso endpoint, agregando server-side. Requer domínio público (Cloudflare Tunnel).

Pedido captura `fbc` (Click ID, vem do `?fbclid=...`) e `fbp` (cookie `_fbp`) no frontend e os envia ao backend ([pedido.py:195-196](../backend/app/models/pedido.py#L195)) para melhorar match quality.

Variáveis:
```env
META_PIXEL_ID=
META_CAPI_ACCESS_TOKEN=
META_CAPI_API_VERSION=v21.0
META_TEST_EVENT_CODE=         # só em ambiente de teste
META_CAPI_USE_GATEWAY=false
META_CAPI_GATEWAY_DOMAIN=gestaopedidos.planteumaflor.online
```

Endpoints diagnóstico (admin): `GET /api/pedidos/meta-outbox/stats`, `POST /api/pedidos/meta-outbox/reset-failed`, `POST /api/pedidos/meta-outbox/criar-faltantes`.

## Nuvemshop

OAuth + webhooks. Fluxo:

1. Loja instala o app via `GET /api/integrations/nuvemshop/install` → redireciona para autorização Nuvemshop.
2. Callback `GET /api/integrations/nuvemshop/oauth/callback` salva `NuvemshopStore` (store_id + access_token).
3. `POST /api/integrations/nuvemshop/setup-webhooks` registra os webhooks `order/paid`, etc. na Nuvemshop.
4. Webhooks chegam em `POST /api/integrations/nuvemshop/webhooks` — ACK imediato (status 200) e processamento em background ([integrations/nuvemshop/service.py](../backend/app/integrations/nuvemshop/service.py)).
5. Cria/atualiza Pedido com `plataforma='Nuvemshop'`, captura ids externos em `PedidoExternalRef`.
6. Webhook delivery log em `NuvemshopWebhookDelivery`.

Pedido importado fica pendente de **agendamento manual** (data/horário não vêm da loja) — vendedor define via `POST /api/integrations/nuvemshop/pedidos/<id>/definir-agendamento`. Atribuição de vendedor: `POST /api/integrations/nuvemshop/atribuir-vendedor`.

Variáveis:
```env
NUVEMSHOP_APP_ID=
NUVEMSHOP_CLIENT_SECRET=
NUVEMSHOP_USER_AGENT=Gestor Pedidos (contato@seudominio.com)   # OBRIGATÓRIO pela Nuvemshop
NUVEMSHOP_PUBLIC_BASE_URL=https://gestaopedidos.planteumaflor.online
```

## Acompanhamento público do pedido

Página pública (sem login) onde o cliente acompanha o status do pedido: `/acompanhar/<token>`.

- O `token` é assinado com HMAC + timestamp via `itsdangerous` ([services/track_token.py](../backend/app/services/track_token.py)) — derivado do `id`, **não** enumerável e **não** forjável sem a `SECRET_KEY`. Sem coluna/migration nova.
- Endpoint read-only `GET /api/pedidos/track/<token>` ([routes/pedidos.py](../backend/app/routes/pedidos.py)) devolve só campos públicos via `Pedido.to_public_dict()` (whitelist: status amigável, 1º nome do destinatário, produto, data/janela). **Nunca** telefone, endereço, cartinha, valores ou `fbc`/`fbp`. 404 genérico para token inválido/expirado ou pedido oculto/deletado.
- O link é gerado na criação do pedido (retornado em `track_url`) e oferecido para envio ao remetente via WhatsApp na tela de Novo Pedido.

```env
PUBLIC_BASE_URL=https://gestaopedidos.planteumaflor.online   # base do link; cai em NUVEMSHOP_PUBLIC_BASE_URL se vazio
TRACK_TOKEN_MAX_AGE_DAYS=60                                   # validade do token (default 60); expirado → 404
```

> Revogar todos os links de uma vez: trocar o sufixo de `_SALT` (`pedido-track-v1` → `v2`) em [track_token.py](../backend/app/services/track_token.py).

## UTMify

Atribuição de receita de vendas manuais/WhatsApp. Quando lead vira pedido pago, [services/utmify_api.py](../backend/app/services/utmify_api.py) chama o endpoint da UTMify com payload de order.

```env
UTMIFY_ENABLED=true
UTMIFY_API_TOKEN=
UTMIFY_PLATFORM=WhatsAppManual
UTMIFY_IS_TEST=false
```

## Evolution API (WhatsApp → lead pendente)

A Evolution API roda como serviço próprio no [docker-compose.yml](../docker-compose.yml), separado do Gestor:

- `evolution-api`: API REST/WhatsApp.
- `evolution-db`: Postgres próprio da Evolution.
- `evolution-redis`: Redis próprio para cache/sessão.

Variáveis principais:

```env
EVOLUTION_IMAGE=atendai/evolution-api:latest
EVOLUTION_PORT=8080
EVOLUTION_SERVER_URL=https://evolution.planteumaflor.online
EVOLUTION_AUTHENTICATION_API_KEY=
EVOLUTION_INSTANCE_NAME=plante-uma-flor
EVOLUTION_POSTGRES_PASSWORD=
EVOLUTION_WEBHOOK_GLOBAL_URL=http://backend:5000/api/leads/whatsapp-start
```

Fluxo operacional:

1. Subir a stack: `docker compose up -d evolution-db evolution-redis evolution-api`.
2. Criar a instância WhatsApp:

```bash
curl -X POST http://localhost:8080/instance/create \
  -H "Content-Type: application/json" \
  -H "apikey: $EVOLUTION_AUTHENTICATION_API_KEY" \
  -d '{
    "instanceName": "plante-uma-flor",
    "integration": "WHATSAPP-BAILEYS",
    "qrcode": true
  }'
```

3. Obter o QR Code:

```bash
curl http://localhost:8080/instance/connect/plante-uma-flor \
  -H "apikey: $EVOLUTION_AUTHENTICATION_API_KEY"
```

4. Se preferir webhook por instância em vez de global:

```bash
curl -X POST http://localhost:8080/webhook/instance/plante-uma-flor \
  -H "Content-Type: application/json" \
  -H "apikey: $EVOLUTION_AUTHENTICATION_API_KEY" \
  -d '{
    "enabled": true,
    "url": "https://gestaopedidos.planteumaflor.online/api/leads/whatsapp-start",
    "webhook_by_events": false,
    "webhook_base64": false,
    "events": ["MESSAGES_UPSERT"]
  }'
```

O endpoint do Gestor lê `data.message.conversation`, compara com os últimos 5 `token_rastreio` válidos e salva o telefone vindo de `data.key.remoteJid`; quando `remoteJid` vier com `@lid`, tenta `remoteJidAlt` e `senderPn`. Só então muda o lead para `lead_pendente`.

## Google (Maps + Drive + Sheets)

**Geocoding**: [services/google_geocoding.py](../backend/app/services/google_geocoding.py) usa Google Maps Geocoding API. Fallback: ViaCEP (`GET /api/cep/<cep>`). 

**Roteamento**: [services/google_routes.py](../backend/app/services/google_routes.py) usa Routes API para cálculo de distância. Em produção, [services/graphhopper.py](../backend/app/services/graphhopper.py) é o principal (mais barato); Google é fallback.

**Drive**: backups encriptados subidos pelos scripts em [backend/scripts/backup/](../backend/scripts/backup/).

**Sheets**: export de vendas e leads via [backend/scripts/export/](../backend/scripts/export/).

Todos usam o mesmo Service Account: arquivo apontado por `GOOGLE_APPLICATION_CREDENTIALS` (default no container: `/app/backend/user/config/google_credentials.json`). Pode ser injetado via env `GOOGLE_CREDENTIALS_JSON` (JSON inteiro) — o `_setup_google_credentials` em [factory.py:139](../backend/app/factory.py#L139) escreve o arquivo a partir do env se ele não existir.

```env
GOOGLE_MAPS_API_KEY=
GOOGLE_APPLICATION_CREDENTIALS=/app/backend/user/config/google_credentials.json
# OU injetar JSON inline:
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
GDRIVE_BACKUP_FOLDER_ID=
```

## GraphHopper / OpenRouteService

Cálculo de distância e otimização de rota. Usado em `services/graphhopper.py` e `services/google_routes.py` (que faz fallback).

```env
GRAPHHOPPER_API_KEY=
OPENROUTE_API_KEY=
```

## Push Notifications (VAPID)

[routes/notifications.py](../backend/app/routes/notifications.py) — `GET /api/notifications/vapid-public-key` para o frontend assinar, `POST /api/notifications/subscribe` para registrar `PushSubscription`. Envio via [services/notification_service.py](../backend/app/services/notification_service.py).

```env
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_CLAIMS_EMAIL=mailto:contato@planteumaflor.com.br
```

Gerar par de chaves: `pywebpush` → `vapid --gen`.

## Funil de leads Meta CAPI (Contact → Lead → LeadDisqualified)

Funil de 3 eventos enviados pra Meta Conversions API conforme o lead evolui de clique no botão WhatsApp até desfecho (compra, sem resposta ou desqualificação). Toda essa lógica vive em [routes/leads.py](../backend/app/routes/leads.py), [services/meta_capi.py](../backend/app/services/meta_capi.py), [repositories/meta_capi_lead_outbox_repository.py](../backend/app/repositories/meta_capi_lead_outbox_repository.py). Toggle global: `META_CAPI_LEAD_FUNNEL_ENABLED=true`.

### Timeline

```
T0  POST /api/leads (event=whatsapp_click)
    │  Lead criado, status="pendente_whatsapp"
    │  meta_event_id_contact obrigatório no payload (vem do Pixel)
    └→ [META] Contact event — sem value/currency, user_data sem phone (lead ainda não mandou msg)

T1  POST /api/leads/whatsapp-start (Evolution recebe mensagem com um token recente)
    │  salva phone a partir de remoteJid/remoteJidAlt/senderPn
    │  status muda para "lead_pendente"
    └→ [META] nada (operador ainda precisa confirmar o lead)

T1.5 PATCH /api/leads/<id>/phone (operador registra telefone)
    │  ou PATCH /api/leads/<id>/status com "whatsapp_iniciado" após triagem
    │  status confirmado em "whatsapp_iniciado"
    │  meta_event_id_lead gerado
    └→ [META] Lead event — sem value/currency, user_data.ph com hash do telefone

T2  PATCH /api/leads/bulk/disqualify (operador marca via modal em lote)
    │  Transição válida: pendente_whatsapp ou nao_entrou_em_contato → descarte
    │  whatsapp_iniciado NÃO é elegível (terminal)
    │  Operador pode preencher phone no modal — gravado silencioso (sem disparar Lead)
    └→ [META] LeadDisqualified event — sem value/currency, user_data.ph se houver phone

T3 (alt) Compra realizada (via fluxo de pedido — order_commission_lifecycle)
    └→ [META] Purchase event (outbox separado: MetaCapiOutbox)
```

Disparos em T0/T1.5/T2 **enfileiram** no outbox (`MetaCapiLeadOutbox`) e o request retorna na hora; o envio é **assíncrono** pelo `capi-worker` (polling), que também retenta failed-retryable respeitando o backoff. O `SendDailyPurchasesToMetaCommand` segue como safety-net diário.

### Mapeamento chave ↔ label ↔ evento

| Chave no DB (`leads.status`) | Label na UI | Evento Meta disparado |
|---|---|---|
| `pendente_whatsapp` | P. Whatsapp (Contact) | `Contact` (em T0) |
| `lead_pendente` | Lead (Pendente) | — (aguardando confirmação do operador) |
| `whatsapp_iniciado` | Lead Confirmado | `Lead` (em T1.5, ao adicionar phone) |
| `nao_entrou_em_contato` | Não entrou em contato | — (nenhum) |
| `descarte` | **Lead Desqualificado** | `LeadDisqualified` (em T2) |
| `compra_realizada` | Compra realizada | `Purchase` (outbox separado) |

### ⚠️ Chave interna no DB vs. label na UI

A chave salva em `leads.status` continua sendo `descarte`. A label "Lead Desqualificado" é puramente visual — exibida pelo map `LEAD_STATUS_LABELS` em [frontend/src/features/leads/LeadsPage.tsx](../frontend/src/features/leads/LeadsPage.tsx). Consultas SQL diretas retornam `descarte`:

```sql
SELECT id, status FROM leads WHERE status = 'descarte';
```

Mesma coisa para `whatsapp_iniciado` ↔ "Lead Confirmado" e `pendente_whatsapp` ↔ "P. Whatsapp (Contact)". Toda mutação de status via API (`PATCH /api/leads/.../status`, `PATCH /api/leads/bulk/disqualify`) usa as chaves internas no body, nunca os labels.

### Por que Lead Confirmado é terminal

Uma vez que o evento `Lead` foi enviado pra Meta (em T1.5), a campanha começa a otimizar para perfis parecidos com aquele lead. Se 24h depois operador percebe que o lead era spam e quer desqualificar, o `LeadDisqualified` é uma correção, mas não desfaz horas de otimização.

Por isso `whatsapp_iniciado` (Lead Confirmado) é **terminal para mutações manuais** — só `compra_realizada` pode acontecer depois, via fluxo automático de pedido. O backend bloqueia: `ALLOWED_STATUS_TRANSITIONS` em [routes/leads.py:41](../backend/app/routes/leads.py#L41) não tem chave `whatsapp_iniciado`, e os endpoints `/bulk/status` + `/bulk/disqualify` pulam silenciosamente leads nesse status. A UI do modal de desqualificação sinaliza visualmente (`⊘`) que esses leads serão ignorados.

### Por que o modal de desqualificação pede telefone

`LeadDisqualified` na Meta usa `user_data.ph` (hash SHA-256 do telefone E.164) para construir uma Custom Audience confiável de exclusão. Sem telefone, o sinal cai pra `fbp` + `fbclid` + `ip_address` + `client_user_agent` — Match Quality (EMQ) menor, audiência menos precisa.

O modal `PATCH /api/leads/bulk/disqualify` é a chance do operador (que conhece o cliente por outro canal — Instagram DM, recomendação, CRM externo) enriquecer o sinal. O endpoint atualiza `lead.phone` **silenciosamente** (sem disparar evento `Lead`!) e em seguida cria o outbox row para `LeadDisqualified`, que lê `lead.phone` fresco do DB e inclui o hash em `user_data.ph`.

### Por que Contact, Lead e LeadDisqualified não enviam `value`/`currency`

Nenhum dos três eventos de funil envia `value`/`currency` em `custom_data` (só `lead_id`). São sinais **qualitativos** — o valor é a presença do evento + os dados de matching em `user_data` (`ph`/`fbc`/`fbp`), não um preço.

A Meta sinalizava preço de baixa qualidade nesses eventos: o **Contact** divergia do Pixel da LP (que parou de enviar preço), e o **Lead** mandava preço **por ad set** (via `utm_content`) — flagado como "todos o mesmo preço". O antigo mapa de valor por ad set (`META_CAPI_VALUE_MAP_ENABLED` + `meta_capi_value_resolver` + `config/meta_capi_value_map.json`) foi **removido**. O único evento com preço real continua sendo o `Purchase` (compra de verdade no checkout).

Como usar no Ads Manager:
1. Events Manager → Custom Audiences → criar audiência "Pessoas que dispararam LeadDisqualified nos últimos 90 dias"
2. Em cada conjunto de anúncios ativo → seção Audience → **Exclude** essa audiência
3. Meta passa a evitar mostrar anúncio para lookalikes dos desqualificados

Em 2-3 semanas, a métrica "% de leads desqualificados" deve cair se a exclusão estiver pegando.
