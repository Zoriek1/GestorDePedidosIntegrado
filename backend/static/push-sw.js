/**
 * Push Notification handler for the Service Worker.
 *
 * This file is loaded by the Workbox-generated SW via `importScripts`.
 * It listens for `push` and `notificationclick` events.
 */

/* eslint-disable no-restricted-globals */

// --- Push Event ---
self.addEventListener('push', (event) => {
  if (!event.data) return;

  let payload;
  try {
    payload = event.data.json();
  } catch {
    payload = { title: 'Nova Notificação', body: event.data.text() };
  }

  const title = payload.title || 'Plante Uma Flor';
  const options = {
    body: payload.body || '',
    icon: payload.icon || '/pwa-192x192.png',
    badge: '/pwa-192x192.png',
    // Permitir som do sistema (padrão é false; explícito para garantir)
    silent: false,
    // vibrate para dispositivos móveis
    vibrate: [200, 100, 200],
    // URL para abrir ao clicar
    data: {
      url: payload.url || '/',
    },
    // Tag para evitar duplicatas
    tag: 'puf-new-order',
    // Renotify: vibrar mesmo se já houver notificação com a mesma tag
    renotify: true,
    // Requerer interação: não fechar automaticamente
    requireInteraction: false,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// --- Notification Click ---
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const targetUrl = (event.notification.data && event.notification.data.url) || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // Se já existe uma janela aberta, focar nela
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      // Caso contrário, abrir uma nova
      return self.clients.openWindow(targetUrl);
    })
  );
});
