/**
 * Offline Diagnostics Page
 * Shows cache status, Workbox cache counts and outbox queue for troubleshooting
 */

import {
  Box,
  Typography,
  Paper,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  Stack,
  Tooltip,
  Divider,
} from '@mui/material';
import { useOffline } from '../../lib/offline/OfflineProvider';
import { clearOutbox, getOutboxStats, getQueue, removeOutboxItem, retryOutboxItem } from '../../lib/offline/outbox';
import { clearCache, getAllCacheKeys, getCacheStats, getCached, MAX_CACHE_ENTRIES } from '../../lib/offline/cache';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useConfirm } from '../../components/system/useConfirm';
import { useToast } from '../../components/system/useToast';
import { formatDateTimeBR } from '../../lib/format/date';
import type { OutboxEntry, OutboxStatus } from '../../lib/offline/db';

const DIAGNOSTICS_ENABLED =
  import.meta.env.DEV || import.meta.env.VITE_ENABLE_OFFLINE_DIAGNOSTICS === 'true';

const WORKBOX_CACHES = [
  { cacheName: 'health-cache', label: 'api-health' },
  { cacheName: 'pedidos-cache', label: 'api-pedidos' },
  { cacheName: 'stats-cache', label: 'api-stats' },
  { cacheName: 'images-cache', label: 'images' },
];

async function getWorkboxCacheCounts(): Promise<Record<string, number> | null> {
  if (typeof caches === 'undefined') return null;
  try {
    const existing = await caches.keys();
    const result: Record<string, number> = {};

    for (const { cacheName } of WORKBOX_CACHES) {
      if (!existing.includes(cacheName)) {
        result[cacheName] = 0;
        continue;
      }
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      result[cacheName] = keys.length;
    }

    return result;
  } catch {
    return null;
  }
}

async function getStorageEstimate(): Promise<{ usage: number; quota: number } | null> {
  try {
    if (!('storage' in navigator) || !('estimate' in navigator.storage)) return null;
    const estimate = await navigator.storage.estimate();
    if (typeof estimate.usage !== 'number' || typeof estimate.quota !== 'number') return null;
    return { usage: estimate.usage, quota: estimate.quota };
  } catch {
    return null;
  }
}

function formatBytes(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function statusColor(status: OutboxStatus): 'default' | 'warning' | 'success' | 'error' {
  switch (status) {
    case 'PENDING':
      return 'warning';
    case 'PROCESSING':
      return 'warning';
    case 'DONE':
      return 'success';
    case 'FAILED':
      return 'error';
    default:
      return 'default';
  }
}

export default function OfflineDiagnostics() {
  const { isOnline, outboxCount, flush: flushFromProvider } = useOffline();
  const confirm = useConfirm();
  const { success, error, info } = useToast();
  const queryClient = useQueryClient();

  // Extra safety: even if route gating fails, hide diagnostics in prod unless flag is enabled
  if (!DIAGNOSTICS_ENABLED) {
    return (
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Diagnósticos Offline
        </Typography>
        <Alert severity="warning">
          Diagnósticos offline desabilitados. Defina <code>VITE_ENABLE_OFFLINE_DIAGNOSTICS=true</code> para habilitar.
        </Alert>
      </Box>
    );
  }

  const { data: queue, refetch: refetchQueue } = useQuery({
    queryKey: ['outbox-queue'],
    queryFn: getQueue,
    refetchInterval: 2000,
  });

  const { data: outboxStats } = useQuery({
    queryKey: ['outbox-stats'],
    queryFn: getOutboxStats,
    refetchInterval: 2000,
  });

  const { data: cacheKeys } = useQuery({
    queryKey: ['cache-keys'],
    queryFn: getAllCacheKeys,
  });

  const { data: dexieCacheStats } = useQuery({
    queryKey: ['dexie-cache-stats'],
    queryFn: getCacheStats,
  });

  const { data: workboxCounts } = useQuery({
    queryKey: ['workbox-cache-counts'],
    queryFn: getWorkboxCacheCounts,
    staleTime: 10000,
    refetchInterval: 10000,
  });

  const { data: storageEstimate } = useQuery({
    queryKey: ['storage-estimate'],
    queryFn: getStorageEstimate,
    staleTime: 10000,
    refetchInterval: 10000,
  });

  const authBlockedCount =
    queue?.filter((i) => i.status === 'FAILED' && i.blocked && (i.lastStatus === 401 || i.lastStatus === 403)).length ??
    0;
  const validationBlockedCount =
    queue?.filter(
      (i) =>
        i.status === 'FAILED' &&
        i.blocked &&
        typeof i.lastStatus === 'number' &&
        i.lastStatus >= 400 &&
        i.lastStatus < 500 &&
        i.lastStatus !== 401 &&
        i.lastStatus !== 403
    ).length ?? 0;

  const handleForceSync = async () => {
    if (!isOnline) return;
    if (authBlockedCount > 0) {
      error('Sessão inválida, faça login para sincronizar');
      return;
    }

    try {
      await flushFromProvider();
      await refetchQueue();
    } catch {
      error('Erro ao sincronizar');
    }
  };

  const handleClearCache = async () => {
    const confirmed = await confirm({
      title: 'Limpar Cache',
      description: 'Tem certeza que deseja limpar todo o cache? Isso pode afetar a experiência offline.',
      confirmText: 'Limpar',
      cancelText: 'Cancelar',
      confirmColor: 'warning',
    });

    if (confirmed) {
      try {
        await clearCache();
        queryClient.invalidateQueries({ queryKey: ['cache-keys'] });
        queryClient.invalidateQueries({ queryKey: ['dexie-cache-stats'] });
        success('Cache limpo com sucesso');
      } catch {
        error('Erro ao limpar cache');
      }
    }
  };

  const handleClearOutbox = async () => {
    const confirmed = await confirm({
      title: 'Limpar Outbox',
      description: 'Tem certeza que deseja limpar toda a fila de sincronização? Itens pendentes serão perdidos.',
      confirmText: 'Limpar',
      cancelText: 'Cancelar',
      confirmColor: 'error',
    });

    if (confirmed) {
      try {
        await clearOutbox();
        await refetchQueue();
        queryClient.invalidateQueries({ queryKey: ['outbox-stats'] });
        success('Outbox limpo com sucesso');
      } catch {
        error('Erro ao limpar outbox');
      }
    }
  };

  const handleRemoveItem = async (id: number) => {
    const confirmed = await confirm({
      title: 'Remover Item',
      description: 'Tem certeza que deseja remover este item da fila?',
      confirmText: 'Remover',
      cancelText: 'Cancelar',
      confirmColor: 'error',
    });

    if (confirmed) {
      try {
        await removeOutboxItem(id);
        await refetchQueue();
        queryClient.invalidateQueries({ queryKey: ['outbox-stats'] });
        success('Item removido');
      } catch {
        error('Erro ao remover item');
      }
    }
  };

  const handleRetryItem = async (item: OutboxEntry) => {
    if (!isOnline) {
      info('Você está offline');
      return;
    }
    if (!item.id) return;

    // Auth-blocked: require re-login (do not allow retry)
    if (item.blocked && (item.lastStatus === 401 || item.lastStatus === 403)) {
      error('Sessão inválida, faça login para sincronizar');
      return;
    }

    // Validation-blocked: require explicit confirmation
    if (item.blocked) {
      const confirmed = await confirm({
        title: 'Reprocessar item com falha',
        description: 'Este item falhou com erro de validação. Deseja tentar novamente mesmo assim?',
        confirmText: 'Tentar novamente',
        cancelText: 'Cancelar',
        confirmColor: 'warning',
      });
      if (!confirmed) return;
    }

    try {
      await retryOutboxItem(item.id);
      await refetchQueue();
      await flushFromProvider();
      await refetchQueue();
      queryClient.invalidateQueries({ queryKey: ['outbox-stats'] });
      success('Item marcado para retry');
    } catch {
      error('Erro ao reprocessar item');
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Diagnósticos Offline
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Esta página mostra o status do cache e da fila de sincronização offline.
      </Alert>

      {/* Status */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Status
        </Typography>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
          <Chip label={isOnline ? 'Online' : 'Offline'} color={isOnline ? 'success' : 'default'} />
          <Chip label={`Outbox: ${outboxCount} item(ns)`} color={outboxCount > 0 ? 'warning' : 'default'} />
          <Chip label={`Dexie Cache: ${dexieCacheStats?.total ?? 0} entrada(s)`} color="default" />
          <Chip
            label={`Cap cache: ${MAX_CACHE_ENTRIES}`}
            color="default"
            variant="outlined"
          />
        </Stack>

        {(authBlockedCount > 0 || validationBlockedCount > 0) && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {authBlockedCount > 0
              ? 'Há itens bloqueados por autenticação (401/403). Faça login novamente para sincronizar.'
              : 'Há itens bloqueados por validação (4xx). Use Retry por item para tentar novamente.'}
          </Alert>
        )}

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <Button variant="contained" onClick={handleForceSync} disabled={!isOnline || outboxCount === 0}>
            Forçar Sincronização
          </Button>
          <Button variant="outlined" color="warning" onClick={handleClearCache}>
            Limpar Cache
          </Button>
          <Button variant="outlined" color="error" onClick={handleClearOutbox} disabled={outboxCount === 0}>
            Limpar Outbox
          </Button>
        </Stack>

        <Divider sx={{ my: 2 }} />

        {/* Storage estimate */}
        <Typography variant="subtitle2" gutterBottom>
          Storage
        </Typography>
        {storageEstimate ? (
          <Typography variant="body2" color="text.secondary">
            Uso: {formatBytes(storageEstimate.usage)} / Cota: {formatBytes(storageEstimate.quota)}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Storage estimate: N/A
          </Typography>
        )}
      </Paper>

      {/* Workbox caches */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Workbox Cache Storage
        </Typography>
        {workboxCounts ? (
          <Stack spacing={1}>
            {WORKBOX_CACHES.map((c) => (
              <Typography key={c.cacheName} variant="body2" color="text.secondary">
                {c.label}: {workboxCounts[c.cacheName] ?? 0} entrada(s)
              </Typography>
            ))}
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            CacheStorage API: N/A
          </Typography>
        )}
      </Paper>

      {/* Outbox Queue */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Outbox
        </Typography>

        {outboxStats && (
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }}>
            <Chip label={`PENDING: ${outboxStats.byStatus.PENDING}`} size="small" color="warning" />
            <Chip label={`FAILED: ${outboxStats.byStatus.FAILED}`} size="small" color="error" />
            <Chip label={`PROCESSING: ${outboxStats.byStatus.PROCESSING}`} size="small" color="warning" variant="outlined" />
            <Chip label={`Blocked: ${outboxStats.blocked}`} size="small" variant="outlined" />
          </Stack>
        )}

        {queue && queue.length > 0 ? (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Tipo</TableCell>
                  <TableCell>Criado em</TableCell>
                  <TableCell>Tentativas</TableCell>
                  <TableCell>HTTP</TableCell>
                  <TableCell>Último Erro</TableCell>
                  <TableCell align="right">Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {queue.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.id}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip label={item.status ?? 'PENDING'} size="small" color={statusColor((item.status ?? 'PENDING') as OutboxStatus)} />
                        {item.blocked && (
                          <Tooltip title="Bloqueado (não será processado automaticamente)">
                            <Chip label="blocked" size="small" variant="outlined" />
                          </Tooltip>
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Chip label={item.type} size="small" />
                    </TableCell>
                    <TableCell>{formatDateTimeBR(new Date(item.createdAt))}</TableCell>
                    <TableCell>{item.attempts}</TableCell>
                    <TableCell>{item.lastStatus ?? '-'}</TableCell>
                    <TableCell>
                      {item.lastError ? (
                        <Typography variant="body2" color="error" sx={{ maxWidth: 320 }}>
                          {item.lastError}
                        </Typography>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        {item.status === 'FAILED' && (
                          <Tooltip
                            title={
                              item.blocked && (item.lastStatus === 401 || item.lastStatus === 403)
                                ? 'Bloqueado por autenticação (faça login novamente)'
                                : ''
                            }
                          >
                            <span>
                              <Button
                                size="small"
                                onClick={() => handleRetryItem(item)}
                                disabled={!isOnline || (item.blocked && (item.lastStatus === 401 || item.lastStatus === 403))}
                              >
                                Retry
                              </Button>
                            </span>
                          </Tooltip>
                        )}
                        <Button
                          size="small"
                          color="error"
                          onClick={() => item.id && handleRemoveItem(item.id)}
                        >
                          Remover
                        </Button>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Nenhum item na fila
          </Typography>
        )}
      </Paper>

      {/* Dexie Cache Entries */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Dexie Cache
        </Typography>

        {dexieCacheStats && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Por tag:{' '}
              {Object.entries(dexieCacheStats.byTag)
                .map(([tag, count]) => `${tag}=${count}`)
                .join(', ') || 'N/A'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Oldest: {dexieCacheStats.oldestTs ? formatDateTimeBR(new Date(dexieCacheStats.oldestTs)) : 'N/A'} | Newest:{' '}
              {dexieCacheStats.newestTs ? formatDateTimeBR(new Date(dexieCacheStats.newestTs)) : 'N/A'}
            </Typography>
          </Box>
        )}

        {cacheKeys && cacheKeys.length > 0 ? (
          <Box>
            {cacheKeys.map((key) => (
              <CacheEntryRow key={key} cacheKey={key} />
            ))}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Nenhuma entrada no cache
          </Typography>
        )}
      </Paper>
    </Box>
  );
}

function CacheEntryRow({ cacheKey }: { cacheKey: string }) {
  const { data: cached } = useQuery({
    queryKey: ['cache-entry', cacheKey],
    queryFn: async () => {
      const entry = await getCached(cacheKey, { allowStale: true });
      return entry;
    },
  });

  return (
    <Box sx={{ mb: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
      <Typography variant="body2" fontWeight="bold" sx={{ wordBreak: 'break-all' }}>
        {cacheKey}
      </Typography>
      {cached ? (
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
          <Chip label={cached.tag ?? 'default'} size="small" variant="outlined" />
          {cached.stale && <Chip label="stale" size="small" color="warning" />}
          <Typography variant="body2" color="text.secondary">
            Atualizado: {formatDateTimeBR(new Date(cached.ts))}
          </Typography>
        </Stack>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Não encontrado (pode ter expirado e sido limpo)
        </Typography>
      )}
    </Box>
  );
}

