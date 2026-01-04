# Progressive Web App (PWA)

Este documento descreve a implementação PWA, Service Worker, offline support e instalação.

## Visão Geral

O sistema é um **Progressive Web App (PWA)** completo, permitindo instalação como app nativo e funcionalidade offline completa.

## Service Worker

O projeto utiliza **Workbox** (via `vite-plugin-pwa`) para gerenciamento do Service Worker.

### Configuração

Configurado em `vite.config.ts`:

```typescript
import { VitePWA } from 'vite-plugin-pwa'

VitePWA({
  registerType: 'autoUpdate',
  // ...
  workbox: {
    runtimeCaching: [
      // Estratégias de cache
    ]
  }
})
```

### Estratégias de Cache

- **Fonts/Images**: CacheFirst (cache primeiro)
- **API Health**: NetworkFirst (rede primeiro, com timeout)
- **API Pedidos/Stats**: NetworkFirst com cache de 24h
- **Outras APIs**: NetworkOnly (sempre busca da rede)

### Atualização Automática

O Service Worker é atualizado automaticamente quando nova versão é detectada (`registerType: 'autoUpdate'`).

## Manifest

O manifest PWA está configurado em `vite.config.ts`:

```typescript
manifest: {
  name: 'Plante Uma Flor - Gestão de Pedidos',
  short_name: 'Plante Uma Flor',
  description: 'Sistema de gestão de pedidos',
  theme_color: '#047857',
  background_color: '#ffffff',
  display: 'standalone',
  start_url: '/',
  icons: [
    {
      src: 'pwa-192x192.png',
      sizes: '192x192',
      type: 'image/png'
    },
    {
      src: 'pwa-512x512.png',
      sizes: '512x512',
      type: 'image/png'
    }
  ]
}
```

**Arquivo gerado**: `dist/manifest.webmanifest`

## Offline Support

### IndexedDB (Dexie)

O projeto utiliza **Dexie** como wrapper para IndexedDB:

- **Cache**: Dados da API são cacheados localmente
- **Outbox**: Operações offline são enfileiradas para sincronização

**Localização**: `src/lib/offline/`

### Outbox Pattern

Operações realizadas offline são armazenadas no Outbox (IndexedDB) e sincronizadas quando a conexão é restaurada.

**Fluxo**:
1. Usuário faz ação offline (ex: criar pedido)
2. Operação é adicionada ao Outbox
3. Quando online, sincronização automática
4. Outbox é limpo após sucesso

### Cache de Dados

Dados da API são cacheados localmente para acesso offline:

- **Pedidos**: Cache de pedidos para visualização offline
- **Clientes**: Cache de clientes
- **Stats**: Cache de estatísticas

## Instalação

### Desktop (Chrome/Edge)

1. Acesse o site
2. Clique no ícone de instalação na barra de endereços
3. Ou: Menu → "Instalar Plante Uma Flor"

### Mobile (Android)

1. Acesse o site no Chrome
2. Menu → "Adicionar à tela inicial"
3. Ou: Prompt de instalação automático

### iOS (Safari)

1. Acesse o site no Safari
2. Compartilhar → "Adicionar à Tela de Início"

## Funcionalidades Offline

### Disponível Offline

- ✅ Visualização de pedidos cacheados
- ✅ Visualização de clientes cacheados
- ✅ Criação de pedidos (salvos no Outbox)
- ✅ Edição de pedidos (salvos no Outbox)
- ✅ Navegação entre páginas

### Sincronização

Quando a conexão é restaurada:

- Operações do Outbox são sincronizadas automaticamente
- Cache é atualizado com dados mais recentes
- Notificação visual de sincronização (se implementado)

## Diagnósticos Offline

Página de diagnósticos disponível em desenvolvimento:

- **Rota**: `/offline-diagnostics`
- **Acesso**: Apenas em desenvolvimento ou com `VITE_ENABLE_OFFLINE_DIAGNOSTICS=true`
- **Funcionalidades**: Status do Service Worker, IndexedDB, Outbox, etc

## Troubleshooting

### Service Worker não atualiza

- Limpe cache do navegador
- Desregistre Service Worker manualmente (DevTools → Application → Service Workers)
- Recarregue a página com Ctrl+Shift+R (hard reload)

### Offline não funciona

- Verifique se Service Worker está registrado (DevTools → Application → Service Workers)
- Verifique IndexedDB (DevTools → Application → IndexedDB)
- Verifique console para erros

### Instalação não aparece

- Verifique se HTTPS está habilitado (requerido para PWA)
- Verifique se manifest está correto
- Verifique se Service Worker está registrado

---

**Última atualização**: 2026-01-04  
**Ver também**: [DATA_PATTERNS.md](DATA_PATTERNS.md), [PRODUCTION.md](PRODUCTION.md)
