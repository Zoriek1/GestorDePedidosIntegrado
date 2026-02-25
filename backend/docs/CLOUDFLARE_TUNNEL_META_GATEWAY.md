# Configuração do Cloudflare Tunnel para Meta Gateway

## Configuração Atual

O Cloudflare Tunnel está configurado com uma rota catch-all (`*`) que envia todas as requisições para `localhost:5000` (backend). Isso significa que as rotas do Meta Gateway (`/capig/` e `/meta-gateway/`) já estão sendo enviadas corretamente para o backend.

```yaml
ingress:
  - hostname: gestaopedidos.planteumaflor.online
    path: *
    service: http://localhost:5000
```

## Problema Identificado

Quando o usuário está **logado no aplicativo**, o React Router intercepta as rotas `/capig/` e `/meta-gateway/` e tenta processá-las como rotas do SPA, causando erro 404 do React Router.

## Solução Implementada

Foram feitas duas correções:

### 1. Backend (`backend/app/errors.py`)
- O error handler 404 agora retorna JSON para rotas do backend (`/api/`, `/docs/`, `/capig/`, `/meta-gateway/`)
- Apenas rotas do frontend recebem `index.html` para SPA routing

### 2. Frontend (`frontend_v2/src/app/router.tsx`)
- Adicionadas rotas catch-all no React Router para `/capig/*` e `/meta-gateway/*`
- Essas rotas retornam um componente vazio (`null`), permitindo que o backend processe

## Verificação

Após as correções, teste acessando:
- `https://gestaopedidos.planteumaflor.online/capig/autoconfig` - deve retornar JSON do backend
- `https://gestaopedidos.planteumaflor.online/meta-gateway/370300471997593/events` - deve retornar resposta do backend

**Importante:** Teste tanto **logado** quanto **deslogado** para garantir que funciona em ambos os casos.

## Se Ainda Houver Problemas

Se o Cloudflare Tunnel estiver configurado com múltiplas rotas, certifique-se de que as rotas do Meta Gateway venham **ANTES** do catch-all:

```yaml
ingress:
  # API vai para o backend (porta 5000)
  - hostname: gestaopedidos.planteumaflor.online
    path: /api/*
    service: http://localhost:5000

  # Meta Gateway - autoconfig
  - hostname: gestaopedidos.planteumaflor.online
    path: /capig/*
    service: http://localhost:5000

  # Meta Gateway - eventos
  - hostname: gestaopedidos.planteumaflor.online
    path: /meta-gateway/*
    service: http://localhost:5000

  # Tudo mais vai para o frontend (porta 3000) ou backend (porta 5000)
  - hostname: gestaopedidos.planteumaflor.online
    service: http://localhost:5000
```

**A ordem das regras importa!** Regras mais específicas devem vir **ANTES** do catch-all.
