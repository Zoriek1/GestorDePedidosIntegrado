# Brief do Grupo 2: Limpeza de Segredos (4.2) + Rate Limiting por Tenant (4.5)

## Tarefa 4.2 — Limpeza de segredos em memória

**Contexto:** `runtime_config()` em `backend/app/services/integration_settings_service.py:259` retorna um dict com segredos descriptografados (`META_CAPI_ACCESS_TOKEN`, `GA4_API_SECRET`, `UTMIFY_API_TOKEN`). Esses valores ficam em memória até o GC coletar.

**O que fazer:**
- Criar um context manager `secure_runtime_config(store_ref_id)` que:
  1. Chama `runtime_config(store_ref_id)` internamente
  2. Faz `yield` do config
  3. No `finally`: zera os segredos no dict com `None`, faz `del config`, e chama `gc.collect()`
- Colocar em um novo arquivo `backend/app/services/secure_config.py`
- Keys a zerar: `META_CAPI_ACCESS_TOKEN`, `GA4_API_SECRET`, `UTMIFY_API_TOKEN`

**Exemplo de uso:**
```python
with secure_runtime_config(store_ref_id) as cfg:
    token = cfg["META_CAPI_ACCESS_TOKEN"]
    # usar token
# após o with, token foi zerado da memória
```

**Importante:** `runtime_config()` está em `backend/app/services/integration_settings_service.py`. Importe de lá.

## Tarefa 4.5 — Rate limiting por tenant nos workers

**Contexto:** Atualmente os workers têm um limite global de processamento:
- Meta CAPI worker: `process_outbox_cycle(limit=50)` (linha 78 de `meta_capi_worker_entrypoint.py`)
- Bling worker: `process_pending(limit=limit)` onde `limit = BLING_WORKER_LIMIT` (padrão 20)
- Nuvemshop worker: `process_pending(limit=50)` em `backend/app/integrations/nuvemshop/service.py`

O problema: uma loja com muitas pendências pode consumir todo o limite, atrasando as outras lojas.

**O que fazer:**
1. No **Bling worker** (`backend/bling_worker_entrypoint.py`): adicionar processamento limitado por `store_ref_id`:
   - Usar `BlingIntegrationService().process_pending(limit=limit_per_store, store_ref_id=X)` para cada loja ativa em vez de uma chamada global
   - Se `BlingIntegrationService().process_pending()` já aceita `store_ref_id`, basta mudar a chamada. Se não, adicionar suporte.
   
2. No **Nuvemshop service** (`backend/app/integrations/nuvemshop/service.py`): verificar se `process_pending` já processa por loja. Se não, adicionar suporte.

3. Será que a implementação atual do `SendDailyPurchasesToMetaCommand().process_outbox_cycle()` já processa por loja? Verifique o código. Se sim, está ok. Se não, adicione.

**Arquivos que serão criados/modificados:**
- Criar: `backend/app/services/secure_config.py`
- Modificar (se necessário): `backend/bling_worker_entrypoint.py`
- Modificar (se necessário): `backend/app/integrations/bling/service.py`
- Modificar (se necessário): `backend/app/integrations/nuvemshop/service.py`
- Modificar (se necessário): `backend/app/commands/send_daily_purchases_to_meta_command.py`
- Testes em `backend/tests/`

**Importante:** Antes de modificar os workers, verifique se `process_pending`/`process_outbox_cycle` já processa por loja. O spec 11 diz que isso já pode estar implementado. Se estiver, apenas documente e pule as mudanças.