/**
 * CEP Lookup Service
 * Serviço para buscar endereço via CEP usando ViaCEP API
 * Implementado com DI (Interface + Classe)
 */

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

  async lookup(cep: string): Promise<CepLookupResult | null> {
    // Remove caracteres não numéricos
    const cleanCep = cep.replace(/\D/g, '');

    // Valida formato
    if (cleanCep.length !== 8) {
      return null;
    }

    try {
      const response = await fetch(`${this.baseUrl}/${cleanCep}/json/`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        console.warn(`[ViaCepLookupService] Erro HTTP: ${response.status}`);
        return null;
      }

      const data: ViaCepResponse = await response.json();

      // ViaCEP retorna { erro: true } quando CEP não existe
      if (data.erro) {
        return null;
      }

      return {
        cep: data.cep,
        rua: data.logradouro || '',
        bairro: data.bairro || '',
        cidade: data.localidade || '',
        uf: data.uf || '',
      };
    } catch (error) {
      console.error('[ViaCepLookupService] Erro ao buscar CEP:', error);
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

