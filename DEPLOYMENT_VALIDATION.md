# Guia de Validação de Deployment

Este documento lista os passos para validar que o deployment está funcionando corretamente após as mudanças implementadas.

## Pré-requisitos

- [ ] Build do frontend executado (`npm run build` em `frontend_v2/`)
- [ ] Backend rodando com Waitress na porta 5000
- [ ] Cloudflare Tunnel configurado e rodando
- [ ] Variáveis de ambiente configuradas (`.env` no backend)

## Validações Locais (Antes do Cloudflare)

### 1. Health Check da API

```bash
curl http://localhost:5000/api/health
```

**Esperado:**
```json
{
  "success": true,
  "status": "healthy",
  "message": "API funcionando normalmente"
}
```

### 2. Frontend sendo servido

```bash
curl http://localhost:5000/
```

**Esperado:** HTML do `index.html` do frontend

### 3. Deep Link (SPA Routing)

```bash
curl http://localhost:5000/pedidos
```

**Esperado:** Mesmo HTML do `index.html` (não 404)

### 4. Headers de Segurança

```bash
curl -I http://localhost:5000/
```

**Esperado:** Headers presentes:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: ...`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### 5. Assets com Cache

```bash
curl -I http://localhost:5000/assets/index-*.js
```

**Esperado:** 
- `Cache-Control: public, max-age=31536000, immutable`

### 6. Index.html sem Cache

```bash
curl -I http://localhost:5000/
```

**Esperado:**
- `Cache-Control: no-cache, no-store, must-revalidate`

## Validações via Cloudflare (Produção)

### 1. Health Check da API

```bash
curl https://gestaopedidos.planteumaflor.online/api/health
```

**Esperado:** JSON com `"status": "healthy"` (não HTML)

### 2. Frontend sendo servido

Acesse no navegador: `https://gestaopedidos.planteumaflor.online/`

**Esperado:** 
- Página carrega corretamente
- Sem erros no console do navegador
- Service Worker registrado (verificar DevTools → Application → Service Workers)

### 3. Deep Links funcionam

Acesse no navegador: `https://gestaopedidos.planteumaflor.online/pedidos`

**Esperado:**
- Página carrega (não 404)
- React Router funciona corretamente
- Navegação entre rotas funciona

### 4. API Calls do Frontend

Abra DevTools → Network e:
- Faça login (se necessário)
- Navegue pela aplicação
- Crie/edite um pedido

**Esperado:**
- Requisições para `/api/*` retornam JSON (não HTML)
- Status codes corretos (200, 401, 403, etc)
- Sem erros CORS no console

### 5. Headers de Segurança (via Cloudflare)

Abra DevTools → Network → Selecione qualquer requisição → Headers → Response Headers

**Esperado:** Headers de segurança presentes (mesmos do teste local)

### 6. CORS Headers

Faça uma requisição para a API e verifique Response Headers:

**Esperado:**
- `Access-Control-Allow-Origin: https://gestaopedidos.planteumaflor.online`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization`

## Checklist de Validação Completo

### Backend
- [ ] Waitress rodando na porta 5000
- [ ] Porta 3000 NÃO está em uso
- [ ] `/api/health` retorna JSON
- [ ] `/api/pedidos` requer autenticação (retorna 401/403 sem auth)
- [ ] Logs não mostram erros

### Frontend
- [ ] `/` serve `index.html`
- [ ] `/pedidos` serve `index.html` (deep link funciona)
- [ ] Assets em `/assets/*` são servidos corretamente
- [ ] Service Worker funciona (PWA)

### Segurança
- [ ] Headers de segurança presentes em todas as respostas
- [ ] CORS configurado corretamente (aceita origem do Cloudflare)
- [ ] CSP não bloqueia recursos necessários
- [ ] Source maps NÃO estão sendo servidos em produção

### Cloudflare Tunnel
- [ ] Config aponta apenas para `localhost:5000`
- [ ] Não há regra separada para `/api/*`
- [ ] Tunnel está rodando e conectado

### Performance
- [ ] Assets com hash têm cache longo (immutable)
- [ ] `index.html` e `sw.js` não têm cache
- [ ] Tempo de resposta da API < 500ms (para requisições simples)

## Problemas Comuns e Soluções

### Problema: API retorna HTML ao invés de JSON

**Causa:** Cloudflare Tunnel ainda configurado com regra separada para `/api/*` ou roteamento incorreto

**Solução:** 
1. Verificar config do Cloudflare Tunnel
2. Remover regra separada `/api/*`
3. Manter apenas regra apontando para `localhost:5000`
4. Reiniciar tunnel

### Problema: CORS errors no navegador

**Causa:** Origem do Cloudflare não está na lista de origens permitidas

**Solução:**
1. Verificar `backend/app/cors.py`
2. Confirmar que `https://gestaopedidos.planteumaflor.online` está na lista
3. Reiniciar backend

### Problema: Deep links retornam 404

**Causa:** Flask não está servindo `index.html` para rotas não-API

**Solução:**
1. Verificar `backend/app/static.py`
2. Confirmar que catch-all route está registrada
3. Verificar ordem de registro (static routes devem ser últimos)

### Problema: Headers de segurança não aparecem

**Causa:** Função `add_security_headers()` não está sendo chamada

**Solução:**
1. Verificar `backend/app/static.py`
2. Confirmar que `add_security_headers(response)` é chamada antes de retornar

## Próximos Passos Após Validação

1. Monitorar logs por 24h
2. Verificar performance (tempo de resposta)
3. Testar em diferentes dispositivos/browsers
4. Verificar que backups continuam funcionando
5. Documentar processo de restart/update
