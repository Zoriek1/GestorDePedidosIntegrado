# Integrações Externas

## Meta Conversions API (Purchase + Lead)

Padrão **outbox**: quando um pedido vira `Pago` ou um lead é criado, uma entrada é inserida em `MetaCapiOutbox` / `MetaCapiLeadOutbox`. O serviço `scheduler` ([backend/meta_scheduler_entrypoint.py](../backend/meta_scheduler_entrypoint.py)) roda em loop e flusha pendentes via [services/meta_capi.py](../backend/app/services/meta_capi.py).

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

## UTMify

Atribuição de receita de vendas manuais/WhatsApp. Quando lead vira pedido pago, [services/utmify_api.py](../backend/app/services/utmify_api.py) chama o endpoint da UTMify com payload de order.

```env
UTMIFY_ENABLED=true
UTMIFY_API_TOKEN=
UTMIFY_PLATFORM=WhatsAppManual
UTMIFY_IS_TEST=false
```

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
