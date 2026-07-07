# Auditoria de Segurança — Backend (julho/2026)

- **Escopo:** `GestorDePedidosIntegrado/backend` (API Flask). App em produção em
  `https://gestaopedidos.planteumaflor.online`.
- **Data:** 2026-07-07
- **Método:** revisão manual de código (rotas, decorators de auth, config, middleware,
  webhooks, tokens). Sem varredura ativa contra produção com dados reais.

## Sumário executivo

O backend usa **autenticação seletiva**: não há auth global — cada rota precisa declarar o
próprio decorator (`factory.py` chama `setup_security_middleware(..., enable_auth=False)`).
Esse modelo deixou **rotas sensíveis sem proteção**, publicamente acessíveis na internet.

Duas falhas eram **críticas**: qualquer pessoa, sem login, podia (1) baixar os dados pessoais de
todos os clientes iterando IDs sequenciais de pedido (comprovantes) e (2) criar/editar/apagar
endereços de clientes. Ambas com implicação de LGPD.

O núcleo de segurança, porém, está bem feito (senhas com bcrypt, HMAC de webhook, token de
rastreio assinado, sem SQL injection, sem segredos commitados) — ver [Pontos corretos](#pontos-corretos).

### Tabela de findings

| ID | Severidade | Endpoint / Local | Problema | Status |
|----|------------|------------------|----------|--------|
| [V-01](#v-01) | 🔴 Crítica | `GET /api/pedidos/<id>/comprovante`, `POST /api/pedidos/comprovante-lote` | Sem auth → dump de PII por IDOR sequencial | ✅ Corrigido |
| [V-02](#v-02) | 🔴 Crítica | `POST/PUT/DELETE /api/clientes/.../enderecos` | Sem auth → escrita/exclusão de endereços (IDOR) | ✅ Corrigido |
| [V-03](#v-03) | 🟠 Média | `GET /api/stats` | Sem auth → vazamento de métricas do negócio | ✅ Corrigido |
| [V-04](#v-04) | 🟠 Média | `/api/pedidos/<id>/distancia`, `/api/pedidos/calcular-distancias`, `/api/pedidos/<id>/calcular-taxa` | Sem auth → abuso da API paga Google + vaza endereço + grava no banco | ✅ Corrigido |
| [V-05](#v-05) | 🟠 Média | `_get_client_ip` (rate limit) | Confia em `X-Forwarded-For` forjável → bypass de rate limit e brute-force no login | ✅ Corrigido |
| [V-06](#v-06) | 🟠 Média | `POST /api/meta-gateway/<pixel_id>/events` | Sem auth → injeção de eventos no Meta CAPI com o token do servidor | ✅ Mitigado |
| [V-07](#v-07) | 🟡 Baixa | Vários endpoints | Vazam `str(e)` ao cliente (info disclosure) | 🟨 Parcial |
| [V-08](#v-08) | 🟡 Baixa | JWT / `/api/auth/logout` | Sem revogação; troca de senha não invalida tokens ativos | ⬜ Aberto |
| [V-09](#v-09) | 🟡 Baixa | Rate limit em memória | Por-processo, reseta no restart; não escala entre workers | ⬜ Aberto |
| [V-10](#v-10) | 🟡 Baixa | authZ interna | Qualquer cargo autenticado edita qualquer registro; sem escopo de propriedade | ⬜ Aberto (decisão) |

---

## Findings

### V-01
**Comprovantes de pedido públicos (vazamento de PII por IDOR)** — 🔴 Crítica

- **Local:** `app/routes/pedidos.py` — `obter_comprovante` e `obter_comprovante_lote`.
- **Descrição:** os endpoints não tinham decorator de autenticação. O comprovante
  (`app/commands/gerar_comprovante_command.py`) monta um HTML com **nome do cliente, telefone,
  destinatário, endereço completo, mensagem do cartão, valor e forma de pagamento**. O `id` é um
  inteiro sequencial (`#1`, `#2`, …).
- **Impacto:** qualquer pessoa na internet podia iterar os IDs e baixar a base inteira de clientes
  (dados pessoais + endereços). Violação de LGPD.
- **PoC:** `curl https://.../api/pedidos/1/comprovante` (e 2, 3, …) retornava o HTML com PII.
- **Correção:** adicionado `@requires_edit_auth` a ambos os endpoints. O `PedidoPrintService` do
  frontend já envia o `Authorization: Bearer` via `fetch`, então a impressão continua funcionando.
- **Status:** ✅ Corrigido. Verificado: sem token → 401; com token válido → 200/404.

### V-02
**CRUD de endereços de clientes sem autenticação** — 🔴 Crítica

- **Local:** `app/routes/clientes.py` — `adicionar_endereco_cliente`, `atualizar_endereco`,
  `deletar_endereco`, `marcar_endereco_principal`.
- **Descrição:** o `GET` de endereços exigia role, mas as operações de escrita ficaram abertas.
- **Impacto:** qualquer pessoa podia adicionar, alterar ou apagar endereços de qualquer cliente
  (IDOR + escrita não autenticada) — ex.: trocar o endereço de entrega de pedidos.
- **PoC:** `curl -X POST https://.../api/clientes/1/enderecos -d '{...}'` sem credenciais.
- **Correção:** adicionado `@requires_any_role("admin", "atendente", "vendedor")` nas quatro rotas
  (mesmo decorator do `GET`). Não há chamador no frontend → sem risco de regressão.
- **Status:** ✅ Corrigido. Verificado: sem token → 401.

### V-03
**`GET /api/stats` público** — 🟠 Média

- **Local:** `app/routes/core.py` — `obter_estatisticas`.
- **Impacto:** estatísticas do negócio (volume/faturamento) expostas sem login.
- **Correção:** adicionado `@requires_edit_auth`. O hook `useStats` do frontend já envia o token.
- **Status:** ✅ Corrigido. Verificado: sem token → 401; com token → 200.

### V-04
**Endpoints de distância/taxa sem auth** — 🟠 Média

- **Local:** `app/routes/core.py` — `calcular_distancia_pedido_endpoint`,
  `calcular_distancias_lote`, `calcular_taxa_pedido`.
- **Impacto:** consomem a API paga do Google Maps por pedido; sem auth, permitem abuso e estouro da
  fatura do Google (DoS financeiro), vazam o endereço do pedido e gravam no banco.
- **Correção:** adicionado `@requires_edit_auth` nos três. O `pedidos.ts` do frontend já envia o token.
- **Status:** ✅ Corrigido. Verificado: sem token → 401.

### V-05
**Rate limit contornável via `X-Forwarded-For` forjado** — 🟠 Média

- **Local:** `app/middleware.py` — `_get_client_ip`.
- **Descrição:** atrás do Cloudflare/Docker o `remote_addr` é uma rede privada, então o código
  confiava no primeiro elemento de `X-Forwarded-For`, que o cliente controla (a Cloudflare apenas
  *anexa* o IP real depois). Variando esse header a cada request, dava para zerar o bucket do rate
  limit — inclusive no `/api/auth/login`, que não tinha throttle dedicado nem lockout.
- **Impacto:** bypass do rate limit global e brute-force de senha no login.
- **Correção:**
  - `_get_client_ip` passou a priorizar `CF-Connecting-IP` (a Cloudflare define e sobrescreve —
    não é forjável), depois `X-Real-IP`; `X-Forwarded-For[0]` só como último fallback.
  - Adicionado `@rate_limit(max_per_minute=10, max_per_hour=100)` ao `/api/auth/login`.
- **Status:** ✅ Corrigido.

### V-06
**Injeção de eventos no Meta CAPI** — 🟠 Média

- **Local:** `app/routes/meta_gateway.py` — `meta_gateway_events`.
- **Descrição:** endpoint sem auth; o `pixel_id` é público (fica no frontend). Terceiros podiam
  enviar eventos falsos que o servidor repassa à Meta usando o `META_CAPI_ACCESS_TOKEN`.
- **Impacto:** poluição das métricas/otimização de anúncios; possível consumo/abuso do token.
- **Correção (mitigação — não eliminação, pois o endpoint é chamado do navegador):**
  - Rejeita (`403`) quando há `Origin`/`Referer` de navegador que não bate com `META_CAPI_GATEWAY_DOMAIN`
    (bloqueia JS de sites terceiros); chamadas server-to-server sem `Origin` seguem permitidas.
  - `@rate_limit(max_per_minute=120, max_per_hour=2000)` por IP.
  - Valida que `data` é lista não vazia e limita a `MAX_GATEWAY_EVENTS = 100` por request.
- **Status:** ✅ Mitigado. Observação: autenticação forte é inviável para um gateway de pixel público.

### V-07
**Vazamento de `str(e)` nas respostas de erro** — 🟡 Baixa

- **Local:** ~128 ocorrências em `app/routes/*.py` retornando `"detalhes": str(e)` /
  `f"Erro ...: {str(e)}"`.
- **Impacto:** exceções expostas ao cliente podem revelar estrutura interna (tabelas, paths, libs).
- **Correção aplicada:** padronizado o `app/routes/auth.py` (superfície **pré-autenticação**, a de
  maior risco — login/me/change_password/check) para logar a exceção no servidor
  (`logger.exception`) e devolver mensagem genérica.
- **Pendente (follow-up):** sweep nos demais arquivos de rota (agora todos atrás de auth, risco
  menor). Trocar `"detalhes": str(e)` por mensagem genérica + log. Garantir `DEBUG=False` em prod
  (já é o default de `ProductionConfig`).
- **Status:** 🟨 Parcial.

### V-08
**JWT sem revogação** — 🟡 Baixa — ⬜ Aberto (follow-up)

- **Local:** `app/services/auth_service.py`, `app/routes/auth.py` (`logout` é só client-side; a troca
  de senha não invalida tokens já emitidos).
- **Impacto:** token roubado vale até expirar (`JWT_EXPIRATION_HOURS`, default 24h), mesmo após
  trocar a senha.
- **Correção recomendada:**
  1. Adicionar coluna `password_changed_at` ao model `User` (via `_ensure_runtime_columns` em
     `app/extensions.py`, entrada `("users", "password_changed_at", "datetime")`).
  2. Incluir `iat` no payload em `generate_token`.
  3. Em `require_auth`/`decode_token`, buscar o usuário e rejeitar tokens com `iat < password_changed_at`.
  - Trade-off: adiciona um lookup de usuário por request autenticado (aceitável para a escala atual).
- **Motivo do adiamento:** altera o hot-path de autenticação e exige migração de schema — merece um
  PR próprio e revisado, fora do hotfix de segurança.

### V-09
**Rate limit em memória** — 🟡 Baixa — ⬜ Aberto (follow-up)

- **Local:** `app/middleware.py` — dict global `request_counts`.
- **Impacto:** é por-processo (com múltiplos workers Gunicorn, o limite real é N× maior) e reseta a
  cada restart. Enfraquece a proteção anti-abuso.
- **Correção recomendada:** migrar para `flask-limiter` com backend Redis (adicionar serviço Redis ao
  `docker-compose.yml` e a dependência). Escala entre workers e persiste.
- **Motivo do adiamento:** mudança de infraestrutura (novo serviço + dependência) que afeta o deploy.

### V-10
**authZ interna sem escopo de propriedade** — 🟡 Baixa — ⬜ Aberto (decisão de produto)

- **Local:** `app/middleware.py` (`PERMISSIONS` define `edit_own`/`delete_own`), mas rotas como
  `atualizar_pedido`/`deletar_pedido`/`atualizar_cliente` não verificam se o registro pertence ao
  vendedor logado.
- **Impacto:** qualquer cargo autenticado edita/deleta qualquer registro (não é escalonamento para
  fora, mas viola menor-privilégio entre usuários internos).
- **Correção recomendada:** aplicar escopo de propriedade quando o cargo não for `admin`.
- **Motivo do adiamento:** muda o comportamento atual do fluxo de trabalho — **requer confirmação**
  de que esse isolamento entre vendedores é desejado antes de implementar.

---

## Pontos corretos

Itens já bem implementados — documentados para evitar regressão:

- **Senhas:** hash bcrypt com rounds configuráveis (`app/services/auth_service.py`).
- **Webhook Nuvemshop:** HMAC-SHA256 validado com `hmac.compare_digest` antes de processar
  (`app/integrations/nuvemshop/verifier.py`, `app/routes/nuvemshop.py`).
- **Token de rastreio público:** assinado com HMAC truncado + `compare_digest`, resposta 404 genérica
  para não revelar IDs (`app/services/track_token.py`).
- **Sem SQL injection:** acesso via ORM SQLAlchemy; o único SQL cru (`text()` em `extensions.py`) usa
  constantes internas de migração, não input do usuário.
- **Segredos:** `.env` no `.gitignore`, nenhum segredo commitado; `SECRET_KEY` obrigatória no boot
  (`factory.py` falha rápido se ausente).
- **Endpoints de debug:** só registrados com `ENABLE_DEBUG_ENDPOINTS=true` (default off).
- **CORS:** allowlist explícita, reflete `Origin` só se estiver na lista (`app/cors.py`).

---

## Verificação das correções

Smoke test via `Flask test_client` (app real, sqlite em memória):

- **Sem token:** as 11 rotas de V-01..V-04 retornam **401**; `/api/health` (controle) retorna **200**.
- **Com JWT admin válido:** `/api/stats` → 200; comprovante/endereço de ID inexistente → 404
  (passou da autenticação e chegou no handler).

Verificação recomendada em ambiente completo (via docker na VPS):

```bash
docker compose exec backend pytest        # se/quando houver suíte
# checagem manual (devem exigir auth):
curl -i https://.../api/pedidos/1/comprovante   # 401
curl -i https://.../api/stats                    # 401
# e com Authorization: Bearer <token> → 200
```

Regressão de UI (logado): imprimir 1 comprovante e um lote, abrir o dashboard (`/stats`) e
criar/editar um pedido que dispare cálculo de distância/taxa — tudo deve continuar funcionando
(o frontend já envia o token).
