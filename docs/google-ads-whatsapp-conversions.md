# Google Ads -> WhatsApp -> Compra

Este fluxo costura o clique no botão do tema Nuvemshop ao lead e ao pedido manual do
Gestor. Ele não cria GTM Server e não altera a LandingPage.

## Fluxo implementado

1. O tema preserva por 90 dias o último toque pago e captura `gclid`, `gbraid`,
   `wbraid`, UTMs, Meta cookies, GA4 client/session, página, produto e posição do CTA.
2. O clique gera um token válido e acrescenta à conversa:
   `(código de atendimento: ABCD1234XY)`.
3. O navegador publica `whatsapp_click` no `dataLayer`, dispara Pixel `Contact`, envia
   o lead com `sendBeacon` e abre o WhatsApp sem aguardar a API.
4. O Evolution associa o telefone ao token. Ao criar o pedido com esse código, o lead
   muda para `compra_realizada`.
5. Pedidos com valor válido geram, de forma idempotente:
   - Meta CAPI `Purchase` no outbox já existente;
   - GA4 Measurement Protocol `whatsapp_purchase`;
   - Google Ads Data Manager offline Purchase.

O identificador comum é `GESTOR-WA-{pedido.id}`. Pedidos Nuvemshop e pedidos sem lead
de `whatsapp_click` ligado por token não entram no novo outbox.

## Configuração

Aplicar a migration (o entrypoint Docker já a executa):

```bash
cd backend
python scripts/migrations/add_whatsapp_marketing_tracking.py
```

Criar um API Secret na mesma Data Stream GA4 usada pelo GTM web da loja e configurar:

```dotenv
MARKETING_DISPATCH_ENABLED=false
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
GA4_API_SECRET=secret-do-measurement-protocol
GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY=true
```

No Google Ads, criar `Compra GoogleAds WhatsApp` como Purchase, origem **Import from
clicks**, contagem **Every**, valor dinâmico e BRL. Manter a ação secundária durante a
homologação. Habilitar a Data Manager API no projeto Cloud e conceder à credencial o
acesso necessário à conta Ads.

```dotenv
GOOGLE_DATAMANAGER_ENABLED=true
GOOGLE_DATAMANAGER_VALIDATE_ONLY=true
GOOGLE_CLOUD_PROJECT_ID=meu-projeto
GOOGLE_ADS_CUSTOMER_ID=1234567890
GOOGLE_ADS_CONVERSION_ACTION_ID=987654321
GOOGLE_DATAMANAGER_CREDENTIALS_JSON={...service account...}
```

O worker existente `meta_capi_worker_entrypoint.py` processa Meta, GA4 e Google Ads de
forma independente. Requisições Google em `validateOnly` terminam imediatamente como
`sent/validated_only`, porque não oferecem diagnóstico posterior por `requestId`.
Envios reais passam por `submitted`: a primeira consulta ocorre após 30 minutos e as
seguintes usam backoff persistente até 60 minutos, com prazo total de 24 horas.

Nunca registrar o conteúdo das credenciais. A Meta usa bearer token fora da URL e seus
erros são sanitizados antes de chegar ao worker. O outbox do Google armazena apenas telefone
normalizado e já transformado em SHA-256; GA4 não recebe telefone, nome ou endereço.

## GTM web da loja

No contêiner GTM já instalado em `www.planteumaflor.com`, criar um acionador Custom
Event com nome `whatsapp_click`. Os campos disponíveis no `dataLayer` incluem:

- `event_id`, `token_rastreio`;
- `gclid`, `gbraid`, `wbraid`;
- `utm_source`, `utm_campaign`;
- `page_location`, `product_id`, `cta_location`.

O GTM da LandingPage não precisa ser alterado. Não importar `whatsapp_purchase` do GA4
como conversão primária no Google Ads; a fonte primária é apenas a ação offline acima.

## Operação e homologação

- `GET /api/admin/marketing-conversions`: contagens e últimas entradas do outbox.
- `POST /api/admin/marketing-conversions/retry`: reenvia falhas; aceita `ids`, `destino`
  e `force=true` para reenviar uma entrada validada.
- `Configurações > Marketing`: mostra configuração, últimos envios e executa diagnósticos
  independentes sem criar pedido, lead, outbox real ou lançamento no Bling.
- Meta: o diagnóstico exige um código de **Test Events**, usado apenas na requisição.
- GA4: usar `GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY=true` para validar o payload. Eventos
  enviados a `/debug/mp/collect` não aparecem nos relatórios; para confirmar a coleta é
  necessário desligar a flag e conferir `whatsapp_purchase` no Tempo real.
- Google Ads: o diagnóstico sempre usa `validateOnly=true`, independentemente da flag de
  produção, e considera HTTP 2xx com `requestId` uma validação concluída.
- Tema: publicar primeiro no preview FTP e validar clique, texto, `dataLayer`, Pixel e
  lead antes de promover.

Depois da homologação, esvaziar `META_TEST_EVENT_CODE`, rotacionar qualquer token exposto,
desligar os dois `VALIDATE_ONLY`, manter a conversão Ads como secundária por um período de
observação e só então promovê-la para primária. O código não
declara consentimento concedido quando o estado é desconhecido e, pela decisão de
negócio atual, não bloqueia o envio pelo banner de cookies.

Configuração final de produção:

```dotenv
MARKETING_DISPATCH_ENABLED=true
GA4_MEASUREMENT_PROTOCOL_VALIDATE_ONLY=false
GOOGLE_DATAMANAGER_ENABLED=true
GOOGLE_DATAMANAGER_VALIDATE_ONLY=false
META_TEST_EVENT_CODE=
```

Os IDs, o API Secret, o projeto Cloud e o JSON da service account permanecem iguais aos
validados na homologação. O teste final de atribuição ainda deve partir de um clique real
do Google Ads; identificadores de clique sintéticos validam a integração, mas não comprovam
atribuição.

Referências oficiais: [GA4 Measurement Protocol](https://developers.google.com/analytics/devguides/collection/protocol/ga4)
e [Data Manager API: send events](https://developers.google.com/data-manager/api/devguides/events/send-events).
