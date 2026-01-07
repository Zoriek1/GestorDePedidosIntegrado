import Dexie, { Table } from 'dexie';

export interface CacheEntry {
  key: string;
  value: unknown;
  ts: number;
  tag?: string;
}

export type OutboxStatus = 'PENDING' | 'PROCESSING' | 'FAILED' | 'DONE';

export interface OutboxEntry {
  id?: number;
  type: 'create_order' | 'update_order';
  payload: Record<string, unknown>;
  createdAt: number;
  attempts: number;
  lastError?: string;
  lastStatus?: number;
  status: OutboxStatus;
  blocked?: boolean;
  clientTimestamp?: number;
}

class OfflineDB extends Dexie {
  cache!: Table<CacheEntry>;
  outbox!: Table<OutboxEntry>;

  constructor() {
    super('puf_offline');
    this.version(1).stores({
      cache: 'key, ts',
      outbox: '++id, type, createdAt, attempts',
    });

    // Phase 1.3.1 hardening: tag-aware cache + outbox status/blocked tracking
    this.version(2)
      .stores({
        cache: 'key, ts, tag',
        outbox: '++id, status, createdAt, type, attempts, blocked',
      })
      .upgrade(async (tx) => {
        // Backfill defaults for existing records (best-effort)
        const cacheTable = tx.table('cache');
        await cacheTable.toCollection().modify((entry: CacheEntry) => {
          if (entry.tag === undefined) entry.tag = 'default';
          if (typeof entry.ts !== 'number') entry.ts = Date.now();
        });

        const outboxTable = tx.table('outbox');
        await outboxTable.toCollection().modify((entry: OutboxEntry) => {
          if (!entry.status) entry.status = 'PENDING';
          if (typeof entry.attempts !== 'number') entry.attempts = 0;
          if (entry.blocked === undefined) entry.blocked = false;
        });
      });
  }
}

export const db = new OfflineDB();

