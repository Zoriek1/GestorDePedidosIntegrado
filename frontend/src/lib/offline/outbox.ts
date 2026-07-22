import { db, OutboxEntry, OutboxStatus } from './db';
import { createApiRequest } from '../../api/http';
import type { ApiResponse } from '../../api/http';

const MAX_ATTEMPTS = 3;
let flushInProgress = false;

function notifyOutboxChanged() {
  try {
    window.dispatchEvent(new CustomEvent('puf_outbox_changed'));
  } catch {
    // noop
  }
}

export async function enqueue(type: OutboxEntry['type'], payload: unknown, storeId?: string): Promise<number> {
  // Ensure payload is an object for spread
  const payloadObj = typeof payload === 'object' && payload !== null 
    ? payload as Record<string, unknown>
    : { data: payload };
  
  const entry: OutboxEntry = {
    type,
    payload: { ...payloadObj, clientTimestamp: Date.now(), _storeId: storeId },
    createdAt: Date.now(),
    attempts: 0,
    status: 'PENDING',
    blocked: false,
  };
  const id = await db.outbox.add(entry);
  notifyOutboxChanged();
  return id as number;
}

export async function getQueue(storeId?: string): Promise<OutboxEntry[]> {
  const all = await db.outbox.orderBy('createdAt').toArray();
  if (!storeId) return all;
  return all.filter(e => (e.payload as Record<string, unknown>)._storeId === storeId);
}

export interface OutboxStats {
  total: number;
  byStatus: Record<OutboxStatus, number>;
  blocked: number;
}

export async function getOutboxStats(): Promise<OutboxStats> {
  const items = await getQueue();
  const byStatus: Record<OutboxStatus, number> = {
    PENDING: 0,
    PROCESSING: 0,
    FAILED: 0,
    DONE: 0,
  };
  let blocked = 0;

  for (const item of items) {
    const status = (item.status ?? 'PENDING') as OutboxStatus;
    byStatus[status] = (byStatus[status] ?? 0) + 1;
    if (item.blocked) blocked++;
  }

  return { total: items.length, byStatus, blocked };
}

export interface FlushResult {
  success: number;
  failed: number;
  blockedAuth: number;
  blockedValidation: number;
  skippedBlocked: number;
  skippedNotPending: number;
}

export async function flush(
  getAuthHeader: () => Record<string, string>
): Promise<FlushResult> {
  if (flushInProgress) {
    const result = {
      success: 0,
      failed: 0,
      blockedAuth: 0,
      blockedValidation: 0,
      skippedBlocked: 0,
      skippedNotPending: 0,
    };
    return result;
  }
  flushInProgress = true;

  try {
    if (!navigator.onLine) {
      const result = {
        success: 0,
        failed: 0,
        blockedAuth: 0,
        blockedValidation: 0,
        skippedBlocked: 0,
        skippedNotPending: 0,
      };
      return result;
    }

  // Reset any stuck PROCESSING items from previous runs (best-effort)
  try {
    await db.outbox.where('status').equals('PROCESSING').modify({ status: 'PENDING' });
  } catch {
    // ignore
  }

  const queue = await getQueue();
  const existingBlockedAuth = queue.filter(
    (i) =>
      ((i.status ?? 'PENDING') as OutboxStatus) === 'FAILED' &&
      i.blocked === true &&
      (i.lastStatus === 401 || i.lastStatus === 403)
  ).length;
  const existingBlockedValidation = queue.filter(
    (i) =>
      ((i.status ?? 'PENDING') as OutboxStatus) === 'FAILED' &&
      i.blocked === true &&
      typeof i.lastStatus === 'number' &&
      i.lastStatus >= 400 &&
      i.lastStatus < 500 &&
      i.lastStatus !== 401 &&
      i.lastStatus !== 403
  ).length;

  // If we already have auth-blocked items, do NOT process anything until re-login.
  if (existingBlockedAuth > 0) {
      const result = {
      success: 0,
      failed: 0,
      blockedAuth: existingBlockedAuth,
      blockedValidation: existingBlockedValidation,
      skippedBlocked: 0,
      skippedNotPending: queue.length,
    };
      return result;
  }

  const apiRequest = createApiRequest(getAuthHeader);
  let success = 0;
  let failed = 0;
  let blockedAuth = existingBlockedAuth;
  let blockedValidation = existingBlockedValidation;
  let skippedBlocked = 0;
  let skippedNotPending = 0;

  for (const item of queue) {
    const status: OutboxStatus = (item.status ?? 'PENDING') as OutboxStatus;
    const blocked = item.blocked === true;

    // Only auto-process PENDING items that are not blocked
    if (status !== 'PENDING') {
      skippedNotPending++;
      continue;
    }
    if (blocked) {
      skippedBlocked++;
      continue;
    }
    if (item.attempts >= MAX_ATTEMPTS) {
      await db.outbox.update(item.id!, {
        status: 'FAILED',
        blocked: false,
        lastError: item.lastError ?? 'Máximo de tentativas atingido',
      });
      failed++;
      continue;
    }

    try {
      // Mark as processing to avoid duplicate flush attempts
      await db.outbox.update(item.id!, { status: 'PROCESSING' });

      let response: ApiResponse;
      
      if (item.type === 'create_order') {
        response = await apiRequest('/pedidos', {
          method: 'POST',
          body: JSON.stringify(item.payload),
          headers: { 'Content-Type': 'application/json' }
        });
      } else if (item.type === 'update_order') {
        const { id, ...payload } = item.payload;
        if (typeof id !== 'number' && typeof id !== 'string') {
          throw new Error('Payload must contain id for update_order');
        }
        response = await apiRequest(`/pedidos/${id}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
          headers: { 'Content-Type': 'application/json' }
        });
      } else {
        await db.outbox.update(item.id!, {
          status: 'FAILED',
          blocked: true,
          lastError: `Tipo de outbox desconhecido: ${String(item.type)}`,
        });
        failed++;
        continue;
      }

      if (response.ok) {
        // Success: mark DONE and remove (no history in v1)
        await db.outbox.delete(item.id!);
        success++;
      } else {
        const statusCode = response.status;
        const nextAttempts = item.attempts + 1;

        // Auth failures: block until user logs in again
        if (statusCode === 401 || statusCode === 403) {
          await db.outbox.update(item.id!, {
            status: 'FAILED',
            blocked: true,
            attempts: nextAttempts,
            lastError: response.message,
            lastStatus: statusCode,
          });
          blockedAuth++;
          failed++;
          continue;
        }

        // Other 4xx: mark FAILED + blocked (do NOT delete)
        if (statusCode && statusCode >= 400 && statusCode < 500) {
          await db.outbox.update(item.id!, {
            status: 'FAILED',
            blocked: true,
            attempts: nextAttempts,
            lastError: response.message,
            lastStatus: statusCode,
          });
          blockedValidation++;
          failed++;
          continue;
        }

        // 5xx or unknown: retry (up to MAX_ATTEMPTS), then mark FAILED (not blocked)
        const shouldFail = nextAttempts >= MAX_ATTEMPTS;
        await db.outbox.update(item.id!, {
          status: shouldFail ? 'FAILED' : 'PENDING',
          blocked: false,
          attempts: nextAttempts,
          lastError: response.message,
          lastStatus: statusCode,
        });
        failed++;
      }
    } catch (error) {
      const nextAttempts = item.attempts + 1;
      const shouldFail = nextAttempts >= MAX_ATTEMPTS;
      await db.outbox.update(item.id!, {
        status: shouldFail ? 'FAILED' : 'PENDING',
        blocked: false,
        attempts: nextAttempts,
        lastError: error instanceof Error ? error.message : 'Unknown error',
        lastStatus: undefined,
      });
      failed++;
    }
  }

  const result = {
    success,
    failed,
    blockedAuth,
    blockedValidation,
    skippedBlocked,
    skippedNotPending,
  };
  return result;
  } finally {
    flushInProgress = false;
    notifyOutboxChanged();
  }
}

export async function clearOutbox(): Promise<void> {
  await db.outbox.clear();
  notifyOutboxChanged();
}

export async function removeOutboxItem(id: number): Promise<void> {
  await db.outbox.delete(id);
  notifyOutboxChanged();
}

export async function retryOutboxItem(id: number): Promise<void> {
  await db.outbox.update(id, {
    status: 'PENDING',
    blocked: false,
    lastError: undefined,
    lastStatus: undefined,
    attempts: 0,
  });
  notifyOutboxChanged();
}

