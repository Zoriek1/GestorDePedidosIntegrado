# Grupo 5: Key Rotation Doc + UTMify

> **Tarefas:** 4.6 (Key rotation) + 6.1 (UTMify)

**Goal:** Documentar processo de rotação de chaves e verificar completude da integração UTMify.

**Architecture:** Chaves são gerenciadas via env vars. Secrets em banco são encriptados com AES-GCM. UTMify é síncrono (sem outbox).

**Tech Stack:** cryptography (AES-GCM), UTMify API

## Global Constraints

- SECRET_KEY deriva key para AES-GCM via SHA-256
- Secrets por loja em StoreSetting (encriptados)
- UTMify API token mínimo 16 caracteres

---

## Tarefa 5.1: Documentar rotação de chaves

**Files:**
- Create: `docs/security/key-rotation.md`

- [ ] **Step 1: Mapear todas as chaves**

| Chave | Escopo | Onde está | Impacto da rotação |
|-------|--------|-----------|-------------------|
| `SECRET_KEY` | Global | env var | Invalida todos tokens JWT + dados encriptados |
| `JWT_SECRET_KEY` | Global | env var (fallback: SECRET_KEY) | Invalida todos tokens JWT |
| `META_CAPI_ACCESS_TOKEN` | Per-loja | StoreSetting encriptado | Perde envio Meta CAPI até reconfigurar |
| `GA4_API_SECRET` | Per-loja | StoreSetting encriptado | Perde tracking GA4 até reconfigurar |
| `UTMIFY_API_TOKEN` | Per-loja | StoreSetting encriptado | Perde UTMify até reconfigurar |
| `BLING_CLIENT_SECRET` | Global | env var | Perde Bling OAuth até reconfigurar |
| `NUVEMSHOP_CLIENT_SECRET` | Global | env var | Perde Nuvemshop OAuth até reconfigurar |

- [ ] **Step 2: Documentar processo de rotação**

```markdown
# Key Rotation

## Processo manual de rotação

### SECRET_KEY (crítico — afeta tudo)

1. Manter chave antiga em `SECRET_KEY_OLD`
2. Gerar nova chave: `python -c "import secrets; print(secrets.token_hex(32))"`
3. Atualizar `SECRET_KEY` no env
4. **ATENÇÃO:** Dados encriptados com chave antiga ficam inacessíveis
   - Opção A: Re-encriptar todos os dados antes de rotacionar
   - Opção B: Suportar dual-key (decrypt com old, encrypt com new)
5. Usuários precisam fazer login novamente (tokens JWT invalidados)

### Chaves per-loja (Meta, GA4, UTMify)

1. Configurar nova chave no painel admin (StoreSetting)
2. Chave antiga é automaticamente substituída
3. Sem impacto em dados existentes (somente API calls)

### Chaves OAuth (Bling, Nuvemshop)

1. Renovar token via fluxo OAuth existente
2. Atualizar env var e reiniciar worker
```

- [ ] **Step 3: Commit**

```bash
git add docs/security/key-rotation.md
git commit -m "docs(security): key rotation procedures for all secrets"
```

---

## Tarefa 5.2: UTMify — avaliar resiliência

**Files:**
- Review: `app/services/utmify_api.py`
- Review: `app/utils/utmify_helper.py`

- [ ] **Step 1: Avaliar timeout**

```python
# app/services/utmify_api.py — post_utmify_order()
# Timeout: UTMIFY_TIMEOUT_SECONDS (default 5s)
# Adequado para API externa
```

- [ ] **Step 2: Avaliar se precisa de outbox**

| Critério | Meta CAPI | GA4/Google Ads | UTMify |
|----------|-----------|----------------|--------|
| Volume | Alto | Médio | Baixo |
| Crítico para negócio | Sim | Parcial | Não |
| Custo de perda | Alto | Médio | Baixo |
| Justifica outbox | Sim | Sim | **Não** |

**Decisão:** UTMify síncrono com timeout é aceitável. Volume baixo, custo de perda baixo.

- [ ] **Step 3: Documentar decisão**

Adicionar seção em `docs/security/security-alerts.md`:

```markdown
### UTMify síncrono
- Chamada HTTP direta durante request (sem outbox)
- Timeout: 5s (configurável via UTMIFY_TIMEOUT_SECONDS)
- Decisão: Síncrono aceitável — volume baixo, custo de perda baixo
- Se volume crescer: considerar MigrationConversionOutbox
```

- [ ] **Step 4: Commit**

```bash
git add docs/security/security-alerts.md
git commit -m "docs(security): UTMify resilience assessment - synchronous acceptable"
```
