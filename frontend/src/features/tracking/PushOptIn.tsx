/**
 * Opt-in de notificações para o CLIENTE, na tela pública de acompanhamento.
 *
 * Reaproveita a infra de Web Push (VAPID) que o app já tem, mas vincula a inscrição
 * ao pedido (rotas públicas /notifications/track/<token>/(un)subscribe), para que o
 * cliente receba apenas os avisos de status do SEU pedido. Tudo via fetch cru (sem JWT).
 */
import { useCallback, useEffect, useState } from 'react';
import { Button, Stack, Typography, CircularProgress } from '@mui/material';
import { NotificationsActive, NotificationsOff } from '@mui/icons-material';
import { getApiBaseUrl } from '../../api/http';

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

const isPushSupported = () =>
  typeof navigator !== 'undefined' &&
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window;

interface PushOptInProps {
  token: string;
}

export function PushOptIn({ token }: PushOptInProps) {
  const [supported] = useState(isPushSupported);
  const [enabled, setEnabled] = useState(false);
  const [denied, setDenied] = useState(false);
  const [busy, setBusy] = useState(false);

  // Estado de opt-in por pedido (o navegador tem 1 subscription por dispositivo;
  // a flag por token reflete a escolha do cliente para ESTE pedido).
  const storageKey = `puf_track_sub_${token}`;

  useEffect(() => {
    if (!supported) return;
    setDenied(Notification.permission === 'denied');
    setEnabled(
      Notification.permission === 'granted' && localStorage.getItem(storageKey) === '1',
    );
  }, [supported, storageKey]);

  const enable = useCallback(async () => {
    setBusy(true);
    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        setDenied(permission === 'denied');
        return;
      }
      const base = getApiBaseUrl();
      const keyRes = await fetch(`${base}/notifications/vapid-public-key`, {
        headers: { Accept: 'application/json' },
      });
      const keyJson = await keyRes.json();
      const vapid: string | undefined = keyJson?.publicKey;
      if (!vapid) throw new Error('VAPID indisponível');

      const reg = await navigator.serviceWorker.ready;
      let sub = await reg.pushManager.getSubscription();
      if (!sub) {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapid),
        });
      }
      const j = sub.toJSON();
      const res = await fetch(
        `${base}/notifications/track/${encodeURIComponent(token)}/subscribe`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            endpoint: j.endpoint,
            keys: { p256dh: j.keys?.p256dh, auth: j.keys?.auth },
          }),
        },
      );
      if (!res.ok) throw new Error('Falha ao inscrever');
      localStorage.setItem(storageKey, '1');
      setEnabled(true);
    } catch {
      // Opt-in é best-effort; falha silenciosa não atrapalha o acompanhamento.
    } finally {
      setBusy(false);
    }
  }, [token, storageKey]);

  const disable = useCallback(async () => {
    setBusy(true);
    try {
      const base = getApiBaseUrl();
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      const endpoint = sub?.endpoint;
      if (endpoint) {
        await fetch(`${base}/notifications/track/${encodeURIComponent(token)}/unsubscribe`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ endpoint }),
        });
      }
      localStorage.removeItem(storageKey);
      setEnabled(false);
    } catch {
      // silencioso
    } finally {
      setBusy(false);
    }
  }, [token, storageKey]);

  if (!supported) return null;

  return (
    <Stack spacing={0.5} alignItems="center">
      {enabled ? (
        <Button
          onClick={disable}
          disabled={busy}
          size="small"
          variant="text"
          color="secondary"
          startIcon={busy ? <CircularProgress size={16} /> : <NotificationsOff />}
        >
          Desativar avisos deste pedido
        </Button>
      ) : (
        <Button
          onClick={enable}
          disabled={busy || denied}
          size="small"
          variant="outlined"
          color="primary"
          startIcon={busy ? <CircularProgress size={16} /> : <NotificationsActive />}
        >
          Avisar quando meu pedido andar
        </Button>
      )}
      {denied && (
        <Typography variant="caption" color="text.secondary" textAlign="center">
          Notificações bloqueadas no navegador deste dispositivo.
        </Typography>
      )}
    </Stack>
  );
}

export default PushOptIn;
