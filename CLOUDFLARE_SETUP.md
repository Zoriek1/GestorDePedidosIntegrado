# Configuração do Cloudflare Tunnel

## Problema Identificado

Quando acessando via Cloudflare (`gestaopedidos.planteumaflor.online`), requisições para `/api/pedidos` estão retornando HTML (index.html) ao invés de JSON do backend.

## Causa Raiz

O servidor estático do frontend (`serve` na porta 3000) não possui proxy configurado. Quando uma requisição `/api/pedidos` chega nele, ele não encontra o arquivo e serve o `index.html` como fallback (comportamento padrão de SPA routing).

## Solução: Configuração do Cloudflare Tunnel

O Cloudflare Tunnel deve rotear requisições de forma seletiva:

### Configuração Correta do Ingress

No arquivo de configuração do `cloudflared` (geralmente `config.yml`), você deve ter regras de ingress na seguinte ordem:

```yaml
ingress:
  # 1. Rotas da API devem ir para o backend (porta 5000)
  - hostname: gestaopedidos.planteumaflor.online
    path: /api/*
    service: http://localhost:5000

  # 2. Todas as outras rotas vão para o frontend (porta 3000)
  - hostname: gestaopedidos.planteumaflor.online
    service: http://localhost:3000
```

**IMPORTANTE:** 
- A ordem das regras importa! A regra mais específica (`/api/*`) deve vir ANTES da regra catch-all.
- A documentação Swagger/OpenAPI (`/docs/*`) **NÃO** está exposta via Cloudflare e permanece acessível apenas localmente em `http://localhost:5000/docs/swagger`.

## Verificação

Para verificar se está funcionando corretamente:

1. **Teste direto da API:**
   ```bash
   curl https://gestaopedidos.planteumaflor.online/api/health
   ```
   Deve retornar JSON, não HTML.

2. **Teste no navegador:**
   - Acesse: `https://gestaopedidos.planteumaflor.online/api/health`
   - Deve ver JSON, não a página HTML do frontend.

3. **Teste de autenticação:**
   - Acesse: `https://gestaopedidos.planteumaflor.online/api/pedidos` sem autenticação
   - Deve retornar 401/403 JSON, não HTML
   - O frontend deve detectar e redirecionar para `/login`

## Correções Implementadas no Código

Mesmo com a configuração correta do Cloudflare, implementamos proteções no código:

1. **Detecção de HTML em respostas da API** (`frontend_v2/src/api/http.ts`):
   - Detecta quando recebe HTML ao invés de JSON
   - Retorna erro claro indicando que o endpoint não está acessível

2. **Verificação de tipo robusta** (`frontend_v2/src/features/pedidos/OrdersPage.tsx`):
   - Verifica se `pedidosData` é um objeto antes de usar o operador `in`
   - Previne erros quando recebe HTML como string
   - Adiciona type guards no `visiblePedidos` useMemo

3. **Proteção em TimeSlotAvailability** (`frontend_v2/src/features/pedidos/useCases/timeSlotAvailability.ts`):
   - Verifica se `response.data` é um objeto antes de acessar `.pedidos`
   - Previne erros quando recebe respostas inesperadas

## Próximos Passos

1. Verificar a configuração do Cloudflare Tunnel conforme acima
2. Reiniciar o tunnel após alterações
3. Testar novamente a aplicação via Cloudflare

