/**
 * Hook para aplicar animações do animate.css quando componente monta
 * 
 * Uso:
 * const animationClass = useAnimateOnMount('fadeIn');
 * return <div className={animationClass}>...</div>
 */

import { useState, useEffect } from 'react';

const prefersReducedMotion = typeof window !== 'undefined'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function useAnimateOnMount(
  animation: string = 'fadeIn',
  delay: number = 0
): string {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    if (delay > 0) {
      const timer = setTimeout(() => setIsMounted(true), delay);
      return () => clearTimeout(timer);
    } else {
      // Usar setTimeout para evitar setState síncrono em effect
      const timer = setTimeout(() => setIsMounted(true), 0);
      return () => clearTimeout(timer);
    }
  }, [delay]);

  if (prefersReducedMotion) return '';

  if (!isMounted) {
    return '';
  }

  return `animate__animated animate__${animation}`;
}
