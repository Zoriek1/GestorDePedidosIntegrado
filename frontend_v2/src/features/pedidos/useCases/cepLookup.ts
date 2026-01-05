/**
 * CEP Lookup Service
 * Serviço para buscar endereço via CEP usando ViaCEP API
 * Implementado com DI (Interface + Classe)
 */

import { logger } from '../../../lib/logger';

// ============================================================================
// Interface (Contrato)
// ============================================================================

export interface CepLookupResult {
  cep: string;
  rua: string;
  bairro: string;
  cidade: string;
  uf: string;
  /** Se true, indica que o CEP não foi encontrado */
  erro?: boolean;
}

export interface ICepLookupService {
  /**
   * Busca endereço pelo CEP
   * @param cep - CEP no formato 00000000 ou 00000-000
   * @returns Dados do endereço ou null se não encontrado
   */
  lookup(cep: string): Promise<CepLookupResult | null>;
}

// ============================================================================
// Implementação ViaCEP
// ============================================================================

interface ViaCepResponse {
  cep: string;
  logradouro: string;
  complemento: string;
  bairro: string;
  localidade: string;
  uf: string;
  ibge: string;
  gia: string;
  ddd: string;
  siafi: string;
  erro?: boolean;
}

export class ViaCepLookupService implements ICepLookupService {
  private readonly baseUrl = 'https://viacep.com.br/ws';
  private readonly timeoutMs = 10000; // 10 segundos

  async lookup(cep: string): Promise<CepLookupResult | null> {
    // Remove caracteres não numéricos
    const cleanCep = cep.replace(/\D/g, '');

    // Valida formato
    if (cleanCep.length !== 8) {
      logger.warn(`[ViaCepLookupService] CEP inválido: ${cep} (limpo: ${cleanCep})`);
      return null;
    }

    const url = `${this.baseUrl}/${cleanCep}/json/`;
    
    try {
      // Criar AbortController para timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Verificar status HTTP
      if (!response.ok) {
        logger.warn(`[ViaCepLookupService] Erro HTTP ${response.status} para CEP ${cleanCep}`);
        return null;
      }

      // Verificar Content-Type
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        logger.warn(`[ViaCepLookupService] Resposta não é JSON para CEP ${cleanCep}. Content-Type: ${contentType}`);
        return null;
      }

      // Parse JSON com tratamento de erro
      let data: ViaCepResponse;
      try {
        data = await response.json();
      } catch (parseError) {
        logger.error(`[ViaCepLookupService] Erro ao parsear JSON para CEP ${cleanCep}:`, parseError);
        return null;
      }

      // Verificar se a resposta é válida
      if (!data || typeof data !== 'object') {
        logger.warn(`[ViaCepLookupService] Resposta inválida para CEP ${cleanCep}:`, data);
        return null;
      }

      // ViaCEP retorna { erro: true } quando CEP não existe
      // IMPORTANTE: Verificar explicitamente se erro é true (não apenas truthy)
      if (data.erro === true) {
        logger.info(`[ViaCepLookupService] CEP ${cleanCep} não encontrado na base do ViaCEP`);
        return null;
      }

      // Validar campos obrigatórios
      if (!data.localidade || !data.uf) {
        logger.warn(`[ViaCepLookupService] Resposta incompleta para CEP ${cleanCep}:`, data);
        return null;
      }

      // Retornar resultado formatado
      const result: CepLookupResult = {
        cep: data.cep || cleanCep,
        rua: data.logradouro || '',
        bairro: data.bairro || '',
        cidade: data.localidade || '',
        uf: data.uf || '',
      };

      logger.debug(`[ViaCepLookupService] CEP ${cleanCep} encontrado:`, result);
      return result;
    } catch (error) {
      // Tratar diferentes tipos de erro
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          logger.error(`[ViaCepLookupService] Timeout ao buscar CEP ${cleanCep}`);
        } else if (error.message.includes('fetch')) {
          logger.error(`[ViaCepLookupService] Erro de rede ao buscar CEP ${cleanCep}:`, error.message);
        } else {
          logger.error(`[ViaCepLookupService] Erro ao buscar CEP ${cleanCep}:`, error.message);
        }
      } else {
        logger.error(`[ViaCepLookupService] Erro desconhecido ao buscar CEP ${cleanCep}:`, error);
      }
      return null;
    }
  }
}

// ============================================================================
// Singleton Instance (para uso direto sem DI container)
// ============================================================================

let defaultInstance: ICepLookupService | null = null;

export function getCepLookupService(): ICepLookupService {
  if (!defaultInstance) {
    defaultInstance = new ViaCepLookupService();
  }
  return defaultInstance;
}

// ============================================================================
// React Hook para uso em componentes
// ============================================================================

import { useState, useCallback } from 'react';

export interface UseCepLookupResult {
  /** Busca endereço pelo CEP */
  lookupCep: (cep: string) => Promise<CepLookupResult | null>;
  /** Indica se a busca está em andamento */
  isLoading: boolean;
  /** Último resultado da busca */
  result: CepLookupResult | null;
  /** Erro da última busca (se houver) */
  error: string | null;
  /** Limpa o resultado e erro */
  reset: () => void;
}

export function useCepLookup(service?: ICepLookupService): UseCepLookupResult {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<CepLookupResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cepService = service || getCepLookupService();

  const lookupCep = useCallback(async (cep: string): Promise<CepLookupResult | null> => {
    const cleanCep = cep.replace(/\D/g, '');
    
    if (cleanCep.length !== 8) {
      setError('CEP deve ter 8 dígitos');
      return null;
    }

    setIsLoading(true);
    setError(null);

    try {
      const lookupResult = await cepService.lookup(cleanCep);
      
      if (lookupResult) {
        setResult(lookupResult);
        setError(null);
        return lookupResult;
      } else {
        setError('CEP não encontrado');
        setResult(null);
        return null;
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao buscar CEP';
      setError(errorMessage);
      setResult(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [cepService]);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    lookupCep,
    isLoading,
    result,
    error,
    reset,
  };
}

