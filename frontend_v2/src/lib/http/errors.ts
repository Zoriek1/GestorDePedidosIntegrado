/**
 * HTTP Error handling utilities
 * Unified error message mapping for API errors
 */

import type { ApiError } from '../../api/http';

/**
 * Get user-friendly error message from error
 * @param err - Error object (ApiError or generic Error)
 * @returns User-friendly error message in Portuguese
 */
export function getErrorMessage(err: unknown): string {
  // Check if it's an ApiError from our API client
  if (err && typeof err === 'object' && 'code' in err) {
    const apiError = err as ApiError;

    switch (apiError.code) {
      case 'TIMEOUT':
        return 'Tempo de espera esgotado. Tente novamente.';
      case 'OFFLINE':
        return 'Sem conexão. Verifique sua internet.';
      case 'NETWORK_ERROR':
        return 'Erro de conexão. Verifique sua internet e se o servidor está rodando.';
      case 'HTTP_401':
        return 'Não autorizado. Por favor, faça login novamente.';
      case 'HTTP_403':
        return 'Acesso negado.';
      case 'HTTP_404':
        return 'Recurso não encontrado.';
      case 'HTTP_500':
      case 'HTTP_502':
      case 'HTTP_503':
      case 'HTTP_504':
        return 'Erro no servidor. Tente novamente mais tarde.';
      default:
        // Check if it's a 5xx error
        if (apiError.status && apiError.status >= 500 && apiError.status < 600) {
          return 'Erro no servidor. Tente novamente mais tarde.';
        }
        // Use message from API if available
        if (apiError.message) {
          return apiError.message;
        }
    }
  }

  // Generic Error object
  if (err instanceof Error) {
    return err.message || 'Erro desconhecido';
  }

  // Fallback
  return 'Erro desconhecido';
}

/**
 * Get error details if available
 * @param err - Error object
 * @returns Error details string or undefined
 */
export function getErrorDetails(err: unknown): string | undefined {
  if (err && typeof err === 'object' && 'details' in err) {
    const apiError = err as ApiError;
    if (apiError.details) {
      if (typeof apiError.details === 'string') {
        return apiError.details;
      }
      if (typeof apiError.details === 'object') {
        try {
          return JSON.stringify(apiError.details);
        } catch {
          return undefined;
        }
      }
    }
  }

  return undefined;
}

