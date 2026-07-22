# Spec 03 — Frontend da tela de Integrações

## Pastas afetadas

- `frontend/src/features/config/`
- `frontend/src/api/`

`frontend/src/features/integrations/` foi **esvaziada** na consolidação de 2026-07-22: `AssignVendorModal` migrou para `features/config/components/` e as três páginas dedicadas foram removidas.

## Experiência desejada

A página de Configurações tem uma **única** aba “Integrações”, exclusiva para administradores, que centraliza todas as configurações pertencentes à loja.

> **Revisão 2026-07-22 (commit `181350c`).** O desenho original previa manter as telas OAuth de Nuvemshop e Bling como fluxos próprios, em abas separadas (`integrations`, `bling`, `marketing`). Na prática eram quatro abas para o que é conceitualmente uma coisa só — credenciais por canal — e o usuário pediu a consolidação. As páginas dedicadas foram **removidas**; a funcionalidade que só existia nelas foi migrada para modais antes da remoção.

Layout: uma grade de cards, um por canal. Cada card mostra o estado da integração, um ícone de engrenagem que abre a configuração, e um botão “Testar” quando o canal admite validação por campo.

Canais (ver `frontend/src/features/config/constants.ts`):

1. Identificação da loja atual, somente leitura, no cabeçalho da grade.
2. Meta CAPI — `testable: true`.
3. GA4 e Google Ads/Data Manager — `testable: false`; só um envio real de payload confirma a credencial, então o teste destes dois vive no diagnóstico de marketing.
4. UTMify — `testable: true`.
5. Dados operacionais da loja — `testable: true`.
6. Nuvemshop e Bling — cards OAuth com status Conectado/Não conectado, Conectar/Reconectar/Desconectar e Testar.

### Configuração avançada (modais)

Aberta pela engrenagem do card, montada **sob demanda** — cada modal dispara queries próprias que não devem rodar só por abrir a aba:

- `BlingAdvancedModal` — mapeamento financeiro (forma de pagamento → portador e categoria) e sincronização de cadastros.
- `NuvemshopAdvancedModal` — vendedor padrão, recriar webhooks, reprocessar webhooks pendentes, backfill de vendedor.
- `MarketingDiagnosticsModal` — diagnóstico por destino e visão do outbox, aberto por um botão no cabeçalho da grade. É o **único** caminho de teste de GA4 e Google Ads.

A fila de “pendências de agendamento” da antiga NuvemshopPage foi removida por decisão do usuário (nunca utilizada — os pedidos chegam ao painel de qualquer forma). Os endpoints correspondentes continuam no backend.

`/integracoes/nuvemshop` e `/integracoes/bling` redirecionam para `/configuracoes`; os callbacks OAuth apontam para lá e a grade lê `?nuvemshop=connected` / `?bling=connected` para o toast de sucesso.

## Comportamento dos segredos

- Campos secretos usam `type=password` quando possível.
- Ao carregar, exibem apenas a máscara recebida.
- Salvar sem editar mantém o segredo.
- Apagar deve exigir intenção clara; preferir botão “Remover credencial” com confirmação a depender apenas de campo vazio.
- Após salvar, substituir o valor digitado pela nova máscara retornada pelo backend.
- Nunca persistir segredos em localStorage, Zustand, logs ou cache offline Dexie.
- React Query pode manter somente o payload mascarado.

## Validação e feedback

- CEP validado/formado como `00000-000`.
- JSON de credenciais validado antes do envio, sem formatar ou mostrar dados depois de salvo.
- Indicar `Configurado`, `Incompleto` ou `Desativado` por integração.
- Botão salvar desabilitado durante request.
- Erros do backend são mostrados sem revelar detalhes criptográficos.
- Alertar que alterações afetam novos envios; não reprocessar filas automaticamente.

## Organização de código

- Tipos e client em `features/config/services/` ou endpoint dedicado.
- Hook React Query com query key que inclua a loja quando houver troca de tenant.
- Form separado em componente próprio.
- Evitar índices numéricos frágeis para tabs; preferir IDs estáveis. Após a consolidação resta uma aba de integrações — a regra vale para as demais abas de Configurações.
- Validação client-side com Zod antes do PATCH, por canal (`features/config/schemas.ts`).
- Usar componentes e versão do MUI já adotados pelo projeto.

## Controle de acesso

- A aba não aparece para não-admin.
- A proteção real continua no backend; ocultar a aba não é autorização.
- Ao trocar de loja numa futura sessão de suporte, invalidar imediatamente o cache anterior.

## Critérios de aceite

- Build Vite passa.
- Admin carrega, edita e salva configurações.
- Segredos nunca aparecem em texto puro no Network após GET.
- Reenvio da máscara não altera ciphertext.
- Remoção exige ação clara e resulta em `has_<campo> = false`.
- Testes de componente cobrem loading, erro, máscara, salvar e remover.
