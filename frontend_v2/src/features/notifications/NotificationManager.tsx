/**
 * NotificationManager
 *
 * Componente invisível que:
 * 1. Busca a chave pública VAPID do backend.
 * 2. Pede permissão de notificação ao usuário (se ainda não concedida).
 * 3. Inscreve o Service Worker no Push Manager.
 * 4. Envia a subscription para o backend.
 *
 * Deve ser montado uma vez no AppShell (ou layout principal).
 * Não renderiza nada na UI — toda a lógica é via useEffect.
 */
import { useEffect, useRef } from 'react';
import { createApiRequest } from '../../api/http';
import { useAuth } from '../auth/authStore';
import { createLogger } from '../../lib/logger';

const log = createLogger('Push');

/** Converte base64url para Uint8Array (necessário para applicationServerKey). */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function NotificationManager() {
  const { getAuthHeader } = useAuth();
  const ran = useRef(false);

  useEffect(() => {
    // Só executar uma vez
    if (ran.current) return;
    ran.current = true;

    // Verificações de suporte
    if (!('serviceWorker' in navigator)) return;
    if (!('PushManager' in window)) return;
    if (!('Notification' in window)) return;

    const setup = async () => {
      try {
        // 1. Buscar chave pública VAPID do backend
        const apiRequest = createApiRequest(getAuthHeader);
        const resp = await apiRequest<{ publicKey: string }>(
          '/notifications/vapid-public-key',
        );
        if (!resp.ok || !resp.data?.publicKey) {
          console.warn('[Push] VAPID key não disponível:', resp.message);
          return;
        }
        const vapidPublicKey = resp.data.publicKey;

        // 2. Pedir permissão (se ainda não dada)
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
          console.info('[Push] Permissão de notificação negada pelo usuário.');
          return;
        }

        // 3. Esperar Service Worker estar pronto
        const registration = await navigator.serviceWorker.ready;

        // 4. Verificar se já está inscrito
        const existingSub = await registration.pushManager.getSubscription();
        if (existingSub) {
          // Já inscrito — enviar para o backend (pode ter sido reinstalado)
          await sendSubscriptionToBackend(existingSub, apiRequest);
          return;
        }

        // 5. Inscrever no Push Manager
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
        });

        // 6. Enviar subscription para o backend
        await sendSubscriptionToBackend(subscription, apiRequest);

        console.info('[Push] Inscrição de push registrada com sucesso.');
      } catch (err) {
        console.warn('[Push] Erro ao configurar push notifications:', err);
      }
    };

    setup();
  }, [getAuthHeader]);

  return null; // Componente invisível
}

async function sendSubscriptionToBackend(
  subscription: PushSubscription,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  apiRequest: any,
) {
  const subJSON = subscription.toJSON();
  await apiRequest('/notifications/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      endpoint: subJSON.endpoint,
      keys: {
        p256dh: subJSON.keys?.p256dh,
        auth: subJSON.keys?.auth,
      },
    }),
  });
}
