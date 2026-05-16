import React, { useEffect, useState, useCallback } from 'react';
import { flush, getQueue } from './outbox';
import { cleanupCache } from './cache';
import { useAuth } from '../../features/auth/authStore';
import { useToast } from '../../components/system/useToast';
import { OfflineContext } from './OfflineContext';

const CACHE_CLEANUP_LAST_RUN_KEY = 'puf_offline_cache_cleanup_last';
const ONE_DAY_MS = 24 * 60 * 60 * 1000;

export function OfflineProvider({ children }: { children: React.ReactNode }) {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [outboxCount, setOutboxCount] = useState(0);
  const { getAuthHeader } = useAuth();
  const { info, success, error } = useToast();

  const updateOutboxCount = useCallback(async () => {
    const queue = await getQueue();
    setOutboxCount(queue.length);
  }, []);

  const handleFlush = useCallback(async () => {
    if (!isOnline) return;
    
    const result = await flush(getAuthHeader);
    await updateOutboxCount();
    
    if (result.success > 0) {
      success(`${result.success} item(ns) sincronizado(s)`);
    }

    const diagnosticsEnabled =
      import.meta.env.DEV || import.meta.env.VITE_ENABLE_OFFLINE_DIAGNOSTICS === 'true';

    if (result.blockedAuth > 0) {
      error('Sessão inválida, faça login para sincronizar');
      return;
    }

    if (result.blockedValidation > 0) {
      error(
        diagnosticsEnabled
          ? 'Alguns itens falharam e precisam de atenção. Veja detalhes em Diagnósticos Offline.'
          : 'Alguns itens falharam e precisam de atenção.'
      );
      return;
    }

    if (result.failed > 0) {
      error(`${result.failed} item(ns) falharam ao sincronizar`);
    }
  }, [isOnline, getAuthHeader, updateOutboxCount, success, error]);

  useEffect(() => {
    // Usar setTimeout para evitar setState síncrono em effect
    const timeoutId = setTimeout(() => {
      setIsOnline(navigator.onLine);
      updateOutboxCount();
    }, 0);

    // Cache cleanup on startup and best-effort once per day
    (async () => {
      try {
        const lastRunRaw = localStorage.getItem(CACHE_CLEANUP_LAST_RUN_KEY);
        const lastRun = lastRunRaw ? Number(lastRunRaw) : 0;
        const now = Date.now();

        if (!lastRun || Number.isNaN(lastRun) || now - lastRun > ONE_DAY_MS) {
          await cleanupCache();
          localStorage.setItem(CACHE_CLEANUP_LAST_RUN_KEY, String(now));
        }
      } catch {
        // Best-effort: ignore storage/IndexedDB errors
      }
    })();

    const handleOnline = () => {
      setIsOnline(true);
      // Call handleFlush asynchronously to avoid setState in effect
      setTimeout(() => {
        handleFlush().catch(() => {
          // Silently handle errors (already logged in handleFlush)
        });
      }, 0);
    };

    const handleOffline = () => {
      setIsOnline(false);
      info('Você está offline');
    };

    const handleOutboxChanged = () => {
      // Update count when queue changes
      setTimeout(() => {
        updateOutboxCount().catch(() => {
          // Silently handle errors
        });
      }, 0);
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        updateOutboxCount().catch(() => {
          // Silently handle errors
        });
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('puf_outbox_changed', handleOutboxChanged as EventListener);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Call handleFlush asynchronously to avoid setState in effect
    if (navigator.onLine) {
      setTimeout(() => {
        handleFlush().catch(() => {
          // Silently handle errors (already logged in handleFlush)
        });
      }, 0);
    }

    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('puf_outbox_changed', handleOutboxChanged as EventListener);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [handleFlush, updateOutboxCount, info]);

  return (
    <OfflineContext.Provider value={{ isOnline, outboxCount, flush: handleFlush }}>
      {children}
    </OfflineContext.Provider>
  );
}

