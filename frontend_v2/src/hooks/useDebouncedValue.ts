/**
 * useDebouncedValue hook
 * Debounces a value with stable reference and cleanup
 */

import { useState, useEffect } from 'react';

/**
 * Debounce a value
 * @param value - Value to debounce
 * @param delayMs - Delay in milliseconds (default: 300)
 * @returns Debounced value
 */
export function useDebouncedValue<T>(value: T, delayMs: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Set up timer
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delayMs);

    // Cleanup timer on unmount or value change
    return () => {
      clearTimeout(timer);
    };
  }, [value, delayMs]);

  return debouncedValue;
}

