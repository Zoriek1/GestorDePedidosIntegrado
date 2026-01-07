import { getCached, setCached } from './cache';

export async function queryFnWithCache<T>(
  queryKey: readonly unknown[],
  networkFn: () => Promise<T>,
  options?: { tag?: string }
): Promise<T> {
  const cacheKey = JSON.stringify(queryKey);
  const tag = options?.tag;
  
  try {
    const result = await networkFn();
    // Write to cache after successful network request
    await setCached(cacheKey, result, tag ?? 'default');
    return result;
  } catch (error) {
    // On network failure, try fresh cache first (never return expired when online)
    const cachedFresh = await getCached<T>(cacheKey, { allowStale: false });
    if (cachedFresh) return cachedFresh.value as T;

    // If offline, allow stale cache only when no fresh cache exists
    if (!navigator.onLine) {
      const cachedStale = await getCached<T>(cacheKey, { allowStale: true });
      if (cachedStale) {
        const value: unknown = cachedStale.value;
        if (value && typeof value === 'object') {
          // Attach non-contract meta for UI indicators (safe: extra field)
          return {
            ...value,
            __offline: {
              stale: cachedStale.stale === true,
              ts: cachedStale.ts,
              tag: cachedStale.tag ?? tag ?? 'default',
            },
          } as T;
        }
        return cachedStale.value as T;
      }
    }
    // No cache available, propagate error
    throw error;
  }
}

