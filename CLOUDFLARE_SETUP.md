# Configuração do Cloudflare Tunnel

## Arquitetura Atual (v3.0 - Simplificada)

O servidor Flask/Waitress na porta 5000 serve tanto a API (`/api/*`) quanto o frontend estático (`/*`). 
Não é mais necessário ter dois servidores separados (backend na 5000 + frontend na 3000).

## Configuração do Cloudflare Tunnel

### Configuração Simplificada do Ingress

No arquivo de configuração do `cloudflared` (geralmente `~/.cloudflared/config.yml` ou `%USERPROFILE%\.cloudflared\config.yml` no Windows), configure:

```yaml
tunnel: <seu-tunnel-id>
credentials-file: <caminho-para-credenciais>

ingress:
  # Única regra: tudo vai para o servidor Flask/Waitress na porta 5000
  - hostname: gestaopedidos.planteumaflor.online
    service: http://localhost:5000
  
  # Catch-all para requisições não mapeadas (opcional, mas recomendado)
  - service: http_status:404
```

**IMPORTANTE:** 
- **NÃO** é mais necessário rotear `/api/*` separadamente - o Flask já faz isso internamente
- **NÃO** é mais necessário ter servidor na porta 3000 - o Flask serve o frontend diretamente
- A documentação Swagger/OpenAPI (`/docs/*`) **NÃO** está exposta via Cloudflare e permanece acessível apenas localmente em `http://localhost:5000/docs/swagger`

## Migração da Configuração Antiga

Se você estava usando a configuração antiga com duas portas:

**ANTES (configuração antiga - REMOVER):**
```yaml
ingress:
  - hostname: gestaopedidos.planteumaflor.online
    path: /api/*
    service: http://localhost:5000
  - hostname: gestaopedidos.planteumaflor.online
    service: http://localhost:3000
```

**AGORA (configuração simplificada - USAR):**
```yaml
ingress:
  - hostname: gestaopedidos.planteumaflor.online
    service: http://localhost:5000
  - service: http_status:404
```

## Passos para Atualizar

1. **Editar configuração do Cloudflare Tunnel:**
   - Localizar arquivo de config (geralmente `~/.cloudflared/config.yml`)
   - Remover regra separada para `/api/*`
   - Remover referência à porta 3000
   - Manter apenas regra apontando para `localhost:5000`

2. **Parar servidor na porta 3000 (se estiver rodando):**
   - Não é mais necessário iniciar `serve` ou `vite preview` na porta 3000
   - O Flask/Waitress na porta 5000 serve tudo

3. **Reiniciar Cloudflare Tunnel:**
   ```bash
   cloudflared tunnel restart <tunnel-name>
   # ou simplesmente reiniciar o serviço/processo
   ```

4. **Verificar que backend está rodando:**
   - Backend deve estar rodando com Waitress na porta 5000
   - Use: `iniciar_producao_completo.bat` (já atualizado)

## Verificação

Para verificar se está funcionando corretamente:

1. **Teste direto da API:**
   ```bash
   curl https://gestaopedidos.planteumaflor.online/api/health
   ```
   Deve retornar JSON, não HTML.

2. **Teste do frontend:**
   - Acesse: `https://gestaopedidos.planteumaflor.online/`
   - Deve carregar o frontend React (HTML)
   - Deep links devem funcionar: `https://gestaopedidos.planteumaflor.online/pedidos`

3. **Teste de autenticação:**
   - Acesse: `https://gestaopedidos.planteumaflor.online/api/pedidos` sem autenticação
   - Deve retornar 401/403 JSON, não HTML
   - O frontend deve detectar e redirecionar para `/login`

4. **Verificar headers de segurança:**
   - Abrir DevTools → Network
   - Verificar que respostas incluem headers:
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: SAMEORIGIN`
     - `Content-Security-Policy: ...`
     - `Referrer-Policy: strict-origin-when-cross-origin`

## Benefícios da Nova Arquitetura

1. **Simplicidade**: Um único servidor (porta 5000) ao invés de dois
2. **Segurança**: Headers de segurança aplicados consistentemente
3. **Manutenção**: Menos pontos de falha, mais fácil de gerenciar
4. **Performance**: Waitress é servidor WSGI robusto para produção
5. **CORS**: Configurado para aceitar requisições do Cloudflare Tunnel

