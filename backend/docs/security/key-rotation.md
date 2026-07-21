# Key Rotation

Procedimentos de rotação de chaves e segredos da aplicação.

## Mapeamento de Chaves

| Chave | Escopo | Onde está | Impacto da rotação |
|-------|--------|-----------|-------------------|
| `SECRET_KEY` | Global | env var | Invalida todos tokens JWT + dados encriptados |
| `JWT_SECRET_KEY` | Global | env var (fallback: SECRET_KEY) | Invalida todos tokens JWT |
| `META_CAPI_ACCESS_TOKEN` | Per-loja | StoreSetting encriptado (AES-GCM) | Perde envio Meta CAPI até reconfigurar |
| `GA4_API_SECRET` | Per-loja | StoreSetting encriptado (AES-GCM) | Perde tracking GA4 até reconfigurar |
| `UTMIFY_API_TOKEN` | Per-loja | StoreSetting encriptado (AES-GCM) | Perde UTMify até reconfigurar |
| `BLING_CLIENT_SECRET` | Global | env var | Perde Bling OAuth até reconfigurar |
| `NUVEMSHOP_CLIENT_SECRET` | Global | env var | Perde Nuvemshop OAuth até reconfigurar |

## Processo de Rotação

### SECRET_KEY (crítico — afeta tudo)

**Impacto:** Rotação invalida todos os tokens JWT ativos e torna inacessíveis dados encriptados com a chave anterior.

**Procedimento:**

1. Gerar nova chave:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. Manter chave antiga em `SECRET_KEY_OLD` para suporte a dual-key
3. Atualizar `SECRET_KEY` no ambiente e reiniciar a aplicação
4. Usuários precisam fazer login novamente (tokens JWT invalidados)

**Dual-key approach (recomendado):**

Para evitar perda de dados encriptados, implementar suporte a duas chaves simultaneamente:

- `SECRET_KEY` — chave atual (usada para novas encriptações)
- `SECRET_KEY_OLD` — chave anterior (usada apenas para desencriptar dados legados)

O módulo `app/utils/crypto.py` derivada a chave via `SHA-256(SECRET_KEY + purpose)`. Para suportar dual-key, modificar `decrypt_secret()` para tentar `SECRET_KEY_OLD` quando `SECRET_KEY` falha.

### JWT_SECRET_KEY

**Procedimento:**

1. Definir `JWT_SECRET_KEY` separadamente de `SECRET_KEY` (evitar dependência implícita)
2. Atualizar env var e reiniciar
3. Todos os tokens JWT são invalidados — usuários fazem login novamente

### Chaves per-loja (Meta CAPI, GA4, UTMify)

**Procedimento:**

1. Acessar painel admin → Configurações da Loja → Integrações
2. Inserir nova chave no campo correspondente
3. Chave antiga é automaticamente substituída ao salvar
4. Sem impacto em dados existentes (afeta apenas chamadas HTTP de API)

**Nota:** Estes segredos são persistidos encriptados via AES-GCM (`app/utils/crypto.py`) com prefixo `v1:`.

### Chaves OAuth (Bling, Nuvemshop)

**Procedimento:**

1. Renovar token via fluxo OAuth existente no painel admin
2. Atualizar env var do client secret se necessário
3. Reiniciar o worker para aplicar nova configuração

### Google API Keys

**Procedimento:**

1. Gerar nova chave no Google Cloud Console
2. Atualizar env vars (`GOOGLE_MAPS_API_KEY`, `GOOGLE_DATAMANAGER_CREDENTIALS_JSON`)
3. Desativar chave antiga no console após validar a nova

## Checklist de Rotação

- [ ] Gerar nova chave com `secrets.token_hex(32)`
- [ ] Atualizar variável de ambiente
- [ ] Manter chave antiga em `SECRET_KEY_OLD` se aplicável
- [ ] Reiniciar aplicação
- [ ] Testar login (JWT)
- [ ] Testar operações com dados encriptados
- [ ] Verificar integrações externas
- [ ] Remover `SECRET_KEY_OLD` após migração completa (opcional)
