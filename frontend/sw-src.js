// Service Worker - Plante Uma Flor PWA
// Gerado com Workbox - Não editar manualmente
// O manifest de precache é injetado automaticamente durante o build

import { precacheAndRoute, cleanupOutdatedCaches, matchPrecache } from 'workbox-precaching';
import { registerRoute, setCatchHandler } from 'workbox-routing';
import { NetworkFirst, StaleWhileRevalidate, CacheFirst, NetworkOnly } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';
import { BackgroundSyncPlugin } from 'workbox-background-sync';
import { clientsClaim } from 'workbox-core';

// Limpar caches antigos na ativação
cleanupOutdatedCaches();

// Precache: injeta manifest automaticamente durante o build
// Ignorar query params de cache-busting (?v=... e ?cache_bust=...)
precacheAndRoute(self.__WB_MANIFEST, {
  ignoreURLParametersMatching: [/^v$/, /^cache_bust$/]
});

// Assumir controle imediatamente após ativação (top-level)
clientsClaim();

// ============================================
// RUNTIME CACHING
// ============================================

// 1. Navegação HTML: NetworkOnly (sempre busca da rede quando online)
// O catch handler (linha 176) faz fallback para index.html quando offline
registerRoute(
  ({ request }) => request.mode === 'navigate',
  new NetworkOnly()
);

// 2. JS/CSS (same-origin): StaleWhileRevalidate com expiração
// Usar url.pathname para ignorar query params de cache-busting
registerRoute(
  ({ request, url }) => {
    return (
      (request.destination === 'script' ||
       request.destination === 'style' ||
       url.pathname.endsWith('.js') ||
       url.pathname.endsWith('.css'))
    ) && url.origin === self.location.origin;
  },
  new StaleWhileRevalidate({
    cacheName: 'js-css-cache',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200]
      }),
      new ExpirationPlugin({
        maxEntries: 50,
        maxAgeSeconds: 7 * 24 * 60 * 60 // 7 dias
      })
    ]
  })
);

// 3. Imagens (same-origin): CacheFirst com expiração
// Usar url.pathname para ignorar query params de cache-busting
registerRoute(
  ({ request, url }) => {
    return (
      request.destination === 'image' ||
      url.pathname.match(/\.(jpg|jpeg|png|gif|webp|svg|ico)$/i)
    ) && url.origin === self.location.origin;
  },
  new CacheFirst({
    cacheName: 'images-cache',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200]
      }),
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 30 * 24 * 60 * 60 // 30 dias
      })
    ]
  })
);

// 4. API GET: NetworkFirst com timeout e TTL curto (5 min)
// Excluir endpoints sensíveis (auth, login, tokens)
registerRoute(
  ({ request, url }) => {
    const isApiGet = url.pathname.startsWith('/api/') && request.method === 'GET';
    const isSensitive = 
      url.pathname.includes('/auth') ||
      url.pathname.includes('/login') ||
      url.pathname.includes('/token') ||
      url.pathname.includes('/logout');
    return isApiGet && !isSensitive && url.origin === self.location.origin;
  },
  new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 3,
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200]
      }),
      new ExpirationPlugin({
        maxEntries: 50,
        maxAgeSeconds: 5 * 60 // 5 minutos (dados podem mudar frequentemente)
      })
    ]
  })
);

// 5. API POST (criar pedido): NetworkOnly + BackgroundSync
const bgSyncPlugin = new BackgroundSyncPlugin('pedidosQueue', {
  maxRetentionTime: 24 * 60 // 24 horas
});

registerRoute(
  ({ request, url }) => {
    return (
      url.pathname === '/api/pedidos' &&
      request.method === 'POST' &&
      url.origin === self.location.origin
    );
  },
  new NetworkOnly({
    plugins: [bgSyncPlugin]
  })
);

// 6. CDNs externas (Tailwind, Font Awesome): StaleWhileRevalidate com expiração curta
registerRoute(
  ({ url }) => {
    return (
      url.origin === 'https://cdn.tailwindcss.com' ||
      url.origin === 'https://cdnjs.cloudflare.com' ||
      url.origin === 'https://fonts.googleapis.com' ||
      url.origin === 'https://fonts.gstatic.com'
    );
  },
  new StaleWhileRevalidate({
    cacheName: 'cdn-cache',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200]
      }),
      new ExpirationPlugin({
        maxEntries: 20,
        maxAgeSeconds: 24 * 60 * 60 // 1 dia
      })
    ]
  })
);

// 7. Endpoints sensíveis: NetworkOnly (nunca cachear)
registerRoute(
  ({ request, url }) => {
    const isSensitive = 
      url.pathname.includes('/auth') ||
      url.pathname.includes('/login') ||
      url.pathname.includes('/token') ||
      url.pathname.includes('/logout') ||
      (url.pathname.startsWith('/api/') && request.method !== 'GET');
    return isSensitive && url.origin === self.location.origin;
  },
  new NetworkOnly()
);

// Catch handler: fallback para navegação offline usando matchPrecache
setCatchHandler(async ({ event }) => {
  if (event.request.mode === 'navigate') {
    const precachedResponse = await matchPrecache('index.html');
    return precachedResponse || Response.error();
  }
  return Response.error();
});

// ============================================
// MESSAGE HANDLERS
// ============================================

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHES') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            // Limpar apenas caches do Workbox (não o precache que é gerenciado automaticamente)
            if (
              cacheName.includes('html-cache') ||
              cacheName.includes('js-css-cache') ||
              cacheName.includes('images-cache') ||
              cacheName.includes('api-cache') ||
              cacheName.includes('cdn-cache')
            ) {
              return caches.delete(cacheName);
            }
          })
        );
      }).then(() => {
        console.log('✅ Caches runtime limpos com sucesso');
        // Enviar confirmação de volta
        if (event.ports && event.ports[0]) {
          event.ports[0].postMessage({ success: true });
        }
      })
    );
  }
});

// ============================================
// INSTALL & ACTIVATE
// ============================================

self.addEventListener('install', (event) => {
  console.log('✅ Service Worker: Instalando (Workbox)...');
  // Não usar skipWaiting() aqui - apenas quando receber mensagem SKIP_WAITING
});

self.addEventListener('activate', (event) => {
  console.log('✅ Service Worker: Ativando (Workbox)...');
  // clientsClaim() já foi chamado no top-level
});
