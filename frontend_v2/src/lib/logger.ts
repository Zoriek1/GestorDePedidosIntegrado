/**
<<<<<<< HEAD
 * Logger utilitário
 * Remove logs em produção para melhor performance
 */

const isDevelopment = import.meta.env.DEV;

/**
 * Logger condicional - apenas em desenvolvimento
 */
export const logger = {
  log: (...args: unknown[]) => {
    if (isDevelopment) {
      console.log(...args);
    }
  },
  debug: (...args: unknown[]) => {
    if (isDevelopment) {
      console.debug(...args);
    }
  },
  warn: (...args: unknown[]) => {
    if (isDevelopment) {
      console.warn(...args);
    }
  },
  error: (...args: unknown[]) => {
    // Erros sempre são logados, mesmo em produção
    console.error(...args);
  },
  info: (...args: unknown[]) => {
    if (isDevelopment) {
      console.info(...args);
    }
  },
};
=======
 * Logger utilitário com suporte a prefixos de módulo.
 * Em produção (import.meta.env.PROD), apenas erros são emitidos.
 */

const isDev = import.meta.env.DEV;

interface Logger {
  debug: (...args: unknown[]) => void;
  log: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  /** Erros são sempre emitidos, inclusive em produção. */
  error: (...args: unknown[]) => void;
}

/**
 * Cria um logger com prefixo de módulo.
 *
 * @example
 * const log = createLogger('OrderWizard');
 * log.debug('step changed', step); // [OrderWizard] step changed 2
 */
export function createLogger(module: string): Logger {
  const prefix = `[${module}]`;
  return {
    debug: (...args) => { if (isDev) console.debug(prefix, ...args); },
    log: (...args) => { if (isDev) console.log(prefix, ...args); },
    info: (...args) => { if (isDev) console.info(prefix, ...args); },
    warn: (...args) => { if (isDev) console.warn(prefix, ...args); },
    error: (...args) => console.error(prefix, ...args),
  };
}

/** Logger genérico da aplicação (sem prefixo de módulo). */
export const logger = createLogger('app');
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
