/**
 * Logger utilitário
 * Remove logs em produção para melhor performance
 */

const isDevelopment = import.meta.env.DEV;

/**
 * Factory para criar logger com prefixo de módulo
 */
export function createLogger(module: string) {
  const prefix = `[${module}]`;
  return {
    log: (...args: unknown[]) => logger.log(prefix, ...args),
    debug: (...args: unknown[]) => logger.debug(prefix, ...args),
    warn: (...args: unknown[]) => logger.warn(prefix, ...args),
    error: (...args: unknown[]) => logger.error(prefix, ...args),
    info: (...args: unknown[]) => logger.info(prefix, ...args),
  };
}

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
