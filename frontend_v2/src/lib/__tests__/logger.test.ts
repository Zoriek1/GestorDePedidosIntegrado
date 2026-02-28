import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createLogger, logger } from '../logger';

describe('createLogger', () => {
  beforeEach(() => {
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'info').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('inclui o nome do módulo como prefixo', () => {
    const log = createLogger('TestModule');
    log.error('mensagem de erro');
    expect(console.error).toHaveBeenCalledWith('[TestModule]', 'mensagem de erro');
  });

  it('sempre emite erros (inclusive em produção)', () => {
    const log = createLogger('Prod');
    log.error('erro crítico');
    expect(console.error).toHaveBeenCalledTimes(1);
  });

  it('exporta logger genérico da aplicação', () => {
    expect(logger).toBeDefined();
    expect(typeof logger.error).toBe('function');
    expect(typeof logger.warn).toBe('function');
    expect(typeof logger.log).toBe('function');
  });
});
