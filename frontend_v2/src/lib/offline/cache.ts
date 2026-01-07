import { db } from './db';

export const MAX_CACHE_ENTRIES = 200;

const TTL_MS_BY_TAG: Record<string, number> = {
  health: 5 * 60 * 1000, // 5 minutes
  stats: 60 * 60 * 1000, // 1 hour
  pedidos: 24 * 60 * 60 * 1000, // 24 hours
  default: 24 * 60 * 60 * 1000, // 24 hours
};

function getTtlMs(tag?: string): number {
  if (!tag) return TTL_MS_BY_TAG.default;
  return TTL_MS_BY_TAG[tag] ?? TTL_MS_BY_TAG.default;
}

export type CacheTag = keyof typeof TTL_MS_BY_TAG | (string & {});

export interface GetCachedOptions {
  allowStale?: boolean;
}

export interface CachedResult<T = unknown> {
  value: T;
  ts: number;
  tag?: string;
  stale?: boolean;
}

export async function getCached<T = unknown>(
  key: string,
  options: GetCachedOptions = {}
): Promise<CachedResult<T> | null> {
  const entry = await db.cache.get(key);
  if (!entry) return null;

  const ttlMs = getTtlMs(entry.tag);
  const expired = Date.now() - entry.ts > ttlMs;

  if (expired && !options.allowStale) return null;

  return {
    value: entry.value as T,
    ts: entry.ts,
    tag: entry.tag,
    stale: expired ? true : undefined,
  };
}

export async function setCached(key: string, value: unknown, tag: CacheTag = 'default'): Promise<void> {
  await db.cache.put({ key, value, ts: Date.now(), tag });
}

export async function clearCache(): Promise<void> {
  await db.cache.clear();
}

export async function getAllCacheKeys(): Promise<string[]> {
  return db.cache.toCollection().keys() as Promise<string[]>;
}

export interface CacheStats {
  total: number;
  byTag: Record<string, number>;
  oldestTs: number | null;
  newestTs: number | null;
}

export async function getCacheStats(): Promise<CacheStats> {
  const entries = await db.cache.toArray();
  const byTag: Record<string, number> = {};
  let oldestTs: number | null = null;
  let newestTs: number | null = null;

  for (const e of entries) {
    const tag = e.tag ?? 'default';
    byTag[tag] = (byTag[tag] ?? 0) + 1;
    if (oldestTs === null || e.ts < oldestTs) oldestTs = e.ts;
    if (newestTs === null || e.ts > newestTs) newestTs = e.ts;
  }

  return { total: entries.length, byTag, oldestTs, newestTs };
}

export interface CleanupCacheResult {
  removedExpired: number;
  removedOverflow: number;
  totalAfter: number;
}

export async function cleanupCache(): Promise<CleanupCacheResult> {
  const now = Date.now();
  const entries = await db.cache.toArray();

  const expiredKeys: string[] = [];
  for (const e of entries) {
    const ttlMs = getTtlMs(e.tag);
    if (now - e.ts > ttlMs) {
      expiredKeys.push(e.key);
    }
  }

  if (expiredKeys.length > 0) {
    await db.cache.bulkDelete(expiredKeys);
  }

  // Cap by oldest timestamp (LRU-ish)
  const countAfterExpiry = await db.cache.count();
  const overflow = Math.max(0, countAfterExpiry - MAX_CACHE_ENTRIES);

  let removedOverflow = 0;
  if (overflow > 0) {
    const keysToDelete = await db.cache.orderBy('ts').limit(overflow).primaryKeys();
    await db.cache.bulkDelete(keysToDelete as string[]);
    removedOverflow = keysToDelete.length;
  }

  const totalAfter = await db.cache.count();

  return {
    removedExpired: expiredKeys.length,
    removedOverflow,
    totalAfter,
  };
}

