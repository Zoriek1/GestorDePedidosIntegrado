# Spec 02 — Backend, criptografia e API de configurações

## Status de implementação

`GET/PUT /api/config/integrations` já operam sobre a loja autenticada (`g.current_store`,
Fase A), com AES-GCM `v1:`, máscara, `has_<campo>`, rejeição de campos desconhecidos
(incl. `store_ref_id` no body) e remoção explícita. A resolução de config por `store_ref_id`
(`runtime_config`) está pronta. Pendente: remover o fallback `.env` das credenciais do lojista
após backfill/auditoria (Fase F).

## Pastas afetadas

- `backend/app/utils/`
- `backend/app/services/`
- `backend/app/routes/`
- `backend/app/schemas/`

## Classificação das variáveis

Antes de mover qualquer valor do `.env`, classificá-lo:

1. Infraestrutura global: banco, `SECRET_KEY`, JWT, URLs internas e flags do deploy. Nunca vai para a tela.
2. Credencial da plataforma: client ID/secret dos aplicativos OAuth Nuvemshop e Bling. Normalmente é compartilhada pelo app SaaS e fica no secret manager.
3. Configuração do lojista: Pixel, tokens, IDs de destino, endereço e credenciais que pertençam à conta da loja. Vai para `store_settings`.
4. Token OAuth instalado: access/refresh tokens Nuvemshop e Bling. Continua nas tabelas próprias, mas ligado à FK interna da loja.

## Criptografia

Criar utilitário único de AES-GCM:

- Chave derivada de `SHA256(SECRET_KEY + purpose)` para compatibilidade inicial.
- Nonce aleatório de 12 bytes.
- Ciphertext versionado com prefixo `v1:`.
- Purpose distinto para Bling e `store_settings`.
- Decrypt aceita texto legado somente durante a migração.
- Erros de chave/ciphertext não podem devolver o segredo em logs ou respostas.

O utilitário deve preservar a capacidade de descriptografar tokens Bling já existentes. Antes de mudar o algoritmo, incluir vetor de compatibilidade nos testes.

Risco: uma única `SECRET_KEY` ainda compartilha domínio criptográfico entre tenants e sua rotação afeta JWT e segredos. Antes do SaaS externo, desenhar master key separada e envelope encryption.

## Contrato da API

Endpoints administrativos sugeridos:

- `GET /api/config/integrations`
- `PUT /api/config/integrations`

Regras:

- Somente `admin` da loja atual.
- A loja vem do contexto autenticado, nunca de `store_ref_id` livre no body.
- GET retorna campos claros e segredos mascarados.
- Para cada segredo, retornar também `has_<campo>`.
- PUT ignora valor mascarado, grava valor novo e permite remoção explícita.
- Campos desconhecidos são rejeitados.
- Validar tipos, tamanho, CEP e JSON de credenciais.
- Respostas e logs não incluem plaintext.
- Atualização é transacional.

## Máscara de segredos

- Formato estável, por exemplo `********1234`.
- A máscara serve apenas à interface; não é um token de autorização.
- Reenviar exatamente um valor iniciado por `****` significa “não alterar”.
- String vazia significa remover somente se o frontend pedir explicitamente; a UI deve alertar sobre isso.
- Nunca usar o valor mascarado como credencial em runtime.

## Resolução de configuração em runtime

Criar uma função única que receba `store_ref_id` e devolva uma visão tipada.

Precedência durante rollout:

1. Se existe `store_settings`, ele é autoritativo inclusive para campos vazios.
2. Se ainda não existe registro para a loja `default`, usar `.env` temporariamente.
3. Para novas lojas, ausência de configuração deve resultar em integração desabilitada, não em herança da loja default.

O fallback não pode ressuscitar um segredo removido da tela. Após backfill e auditoria, remover fallback das credenciais do lojista.

## Importação do `.env`

- Migration cria um snapshot apenas para a loja `default`.
- Não sobrescreve registro existente.
- Não imprime valores secretos.
- É idempotente.
- Valores globais/técnicos não são copiados.

## Critérios de aceite

- Admin lê e atualiza somente sua loja.
- Não-admin recebe 403.
- Segredos no banco começam com `v1:` e não contêm plaintext.
- GET nunca contém plaintext.
- PUT mascarado preserva; PUT novo substitui; remoção explícita apaga.
- Runtime usa DB por loja e fallback apenas nas condições documentadas.
- Testes validam compatibilidade criptográfica do Bling.
