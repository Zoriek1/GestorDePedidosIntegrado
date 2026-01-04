# Guia Rápido: Atualizar Cloudflare Tunnel

## Localização do Arquivo de Configuração

No Windows, o arquivo geralmente está em:
```
%USERPROFILE%\.cloudflared\config.yml
```

Ou você pode encontrar o caminho executando:
```powershell
cloudflared tunnel list
```

## Configuração Atual (ANTES - Remover)

Se você tiver algo assim, **REMOVA**:

```yaml
ingress:
  - hostname: gestaopedidos.planteumaflor.online
    path: /api/*
    service: http://localhost:5000
  - hostname: gestaopedidos.planteumaflor.online
    service: http://localhost:3000
```

## Configuração Nova (AGORA - Usar)

Substitua por:

```yaml
tunnel: <seu-tunnel-id>
credentials-file: <caminho-para-credenciais>

ingress:
  # Única regra: tudo vai para o servidor Flask/Waitress na porta 5000
  - hostname: gestaopedidos.planteumaflor.online
    service: http://localhost:5000
  
  # Catch-all para requisições não mapeadas
  - service: http_status:404
```

## Passos para Atualizar

1. **Localizar o arquivo de configuração:**
   ```powershell
   # No PowerShell
   $env:USERPROFILE\.cloudflared\config.yml
   ```

2. **Editar o arquivo:**
   - Abra o arquivo `config.yml` em um editor de texto
   - Remova a regra com `path: /api/*`
   - Remova a referência à porta 3000
   - Mantenha apenas a regra apontando para `localhost:5000`

3. **Reiniciar o Cloudflare Tunnel:**
   ```powershell
   # Se estiver rodando como serviço
   cloudflared service stop
   cloudflared service start
   
   # Ou se estiver rodando manualmente, pare e reinicie o processo
   ```

4. **Verificar que está funcionando:**
   ```powershell
   curl https://gestaopedidos.planteumaflor.online/api/health
   ```
   Deve retornar JSON, não HTML.

## Exemplo Completo de Config

```yaml
tunnel: abc123def456
credentials-file: C:\Users\SeuUsuario\.cloudflared\abc123def456.json

ingress:
  - hostname: gestaopedidos.planteumaflor.online
    service: http://localhost:5000
  - service: http_status:404
```

**IMPORTANTE:** Não altere o `tunnel` ID nem o `credentials-file` - apenas modifique a seção `ingress`.
