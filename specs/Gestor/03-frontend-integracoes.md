# Spec 03 — Frontend da tela de Integrações

## Pastas afetadas

- `frontend/src/features/config/`
- `frontend/src/features/integrations/`
- `frontend/src/api/`

## Experiência desejada

A página de Configurações terá uma área “Integrações” exclusiva para administradores. Ela centraliza configurações pertencentes à loja e mantém as telas OAuth de Nuvemshop e Bling como fluxos próprios de conexão/status.

Seções:

1. Identificação da loja atual, somente leitura.
2. Meta CAPI.
3. GA4 e Google Ads/Data Manager.
4. UTMify.
5. Dados operacionais da loja.
6. Links/status de Nuvemshop e Bling.

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
- Evitar índices numéricos frágeis para tabs; preferir IDs estáveis como `integrations`, `bling` e `marketing`.
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
