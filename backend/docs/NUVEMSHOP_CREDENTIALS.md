# Nuvemshop — Como obter credenciais e configurar

Este guia descreve como criar o app na Nuvemshop, obter credenciais e configurar o backend para a integracao via OAuth + Webhooks.

## 1) Criar o aplicativo no painel de parceiros

1. Acesse o portal de parceiros Nuvemshop/Tiendanube.
2. Va em **Aplicativos > Criar Aplicativo**.
3. Escolha o tipo de distribuicao:
   - **Loja de Aplicativos** (publico) ou
   - **Para seus clientes** (privado).
4. Salve e anote:
   - **App ID**
   - **Client Secret**

Referencia: https://dev.nuvemshop.com.br/docs/applications/authentication

## 2) Configurar URL de redirecionamento (OAuth)

No painel do app, em **Dados Basicos**, defina a URL de redirecionamento (Redirect URL) para:

```
https://SEU_DOMINIO/api/integrations/nuvemshop/oauth/callback
```

Essa URL precisa ser publica e HTTPS.

## 3) Definir permissoes (escopos)

Escopo minimo recomendado:
- `read_orders`
- `write_notifications` (necessario para criar/gerenciar webhooks via API)

Opcional (se quiser mais dados do cliente):
- `read_customers`

Referencia: https://dev.nuvemshop.com.br/docs/developer-tools/nuvemshop-api

## 4) Configurar variaveis de ambiente no backend

No servidor (ou arquivo .env), defina:

```
NUVEMSHOP_APP_ID=SEU_APP_ID
NUVEMSHOP_CLIENT_SECRET=SEU_CLIENT_SECRET
NUVEMSHOP_USER_AGENT=SeuApp (contato@seudominio.com)
NUVEMSHOP_PUBLIC_BASE_URL=https://SEU_DOMINIO
```

Observacao: o `User-Agent` e obrigatorio pela API da Nuvemshop.

## 5) Iniciar o fluxo de instalacao

Com o backend configurado, chame:

```
GET /api/integrations/nuvemshop/install
```

Resposta:
- `authorize_url` com o link de instalacao do app.

Abra esse link, instale o app na loja demo e o OAuth sera finalizado automaticamente.

## 6) Webhooks

No callback OAuth, o backend cria webhooks automaticamente para:
- `order/created`
- `order/paid`
- `order/updated`
- `order/cancelled`

Os webhooks **LGPD** (URLs obrigatorias no painel do app) devem apontar para o mesmo endpoint:
- `store/redact`
- `customers/redact`
- `customers/data_request`

Referencia: https://tiendanube.github.io/api-documentation/resources/webhook

## 7) Processamento de pedidos

Depois de receber webhooks, execute:

```
POST /api/integrations/nuvemshop/process-pending
```

Isso busca os pedidos na API e cria/atualiza registros no sistema.

## 8) Observacoes sobre HuaApps (agendamento)

O horario vem da opcao de entrega (frete), mas a data nao chega na API.
Nesses casos, o pedido e importado com:
- `horario` preenchido
- `dia_entrega` como data do pedido
- marcador de pendencia em `observacoes`

Depois, ajuste manualmente via:

```
POST /api/integrations/nuvemshop/pedidos/<pedido_id>/definir-agendamento
```

## 9) Nuvemshop na VPS (após deploy)

Se o sistema rodava em outro ambiente e você migrou para uma VPS (Docker, domínio público):

1. **Variáveis no `.env` da raiz** (ou no ambiente do backend):
   - `NUVEMSHOP_APP_ID` e `NUVEMSHOP_CLIENT_SECRET` — use os mesmos do app na Nuvemshop.
   - `NUVEMSHOP_USER_AGENT` — ex.: `Gestor Pedidos (contato@seudominio.com)`.
   - **`NUVEMSHOP_PUBLIC_BASE_URL`** — URL pública do backend na VPS, **sem barra no final**  
     Ex.: `https://gestaopedidos.planteumaflor.online`  
     Essa URL é usada para o callback OAuth e para registrar os webhooks na loja.

2. **Redirect URL no painel do app (Nuvemshop)**  
   Em **Dados Básicos**, defina a URL de redirecionamento para:
   ```
   https://SEU_DOMINIO_VPS/api/integrations/nuvemshop/oauth/callback
   ```
   (substitua `SEU_DOMINIO_VPS` pelo mesmo host de `NUVEMSHOP_PUBLIC_BASE_URL`.)

3. **Reconectar a loja**  
   No Gestor de Pedidos (pela interface na VPS), vá em Integrações > Nuvemshop e **instale/conecte de novo** a loja. Isso:
   - Troca o token (OAuth) no servidor da VPS.
   - Recria os webhooks apontando para `NUVEMSHOP_PUBLIC_BASE_URL/api/integrations/nuvemshop/webhooks`.

4. **Se já reconectou e os pedidos não caem**  
   - Confirme que as 4 variáveis estão definidas no container (ex.: `docker compose exec backend env | grep NUVEMSHOP`).
   - Chame **POST /api/integrations/nuvemshop/setup-webhooks** (como admin) para recriar os webhooks com a URL atual.
   - Verifique no painel da Nuvemshop se os webhooks do app estão com a URL da VPS.

Sem `NUVEMSHOP_PUBLIC_BASE_URL` correto na VPS, o callback e os webhooks usam URL errada e a integração (puxar pedidos) deixa de funcionar.

---

## Links de referencia
- OAuth: https://dev.nuvemshop.com.br/docs/applications/authentication
- API intro: https://tiendanube.github.io/api-documentation/intro
- Orders: https://tiendanube.github.io/api-documentation/resources/order
- Webhooks: https://tiendanube.github.io/api-documentation/resources/webhook
