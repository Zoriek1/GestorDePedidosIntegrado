import { IPedidoPrintService } from './IPedidoPrintService';
import { useAuth } from '../../auth/authStore';
import { useMarcarImpresso } from '../../../api/endpoints/pedidos';

/**
 * Serviço de impressão (Arquitetura Command Pattern)
 * O Frontend atua apenas como "View/Render", buscando o HTML pronto do Backend.
 * Lógica de negócio e template estão no servidor.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export class PedidoPrintService implements IPedidoPrintService {
  private getAuthHeader: () => Record<string, string>;
  private marcarImpresso?: (id: number) => Promise<void>;

  constructor(getAuthHeader: () => Record<string, string>, marcarImpresso?: (id: number) => Promise<void>) {
    this.getAuthHeader = getAuthHeader;
    this.marcarImpresso = marcarImpresso;
  }

  async print(pedidoId: number): Promise<void> {
    // 1. Busca HTML Gerado pelo Command no Backend
    // Usar fetch direto porque o endpoint retorna 'text/html' e não JSON
    const authHeaders = this.getAuthHeader();
    const headers: Record<string, string> = {
      'Accept': 'text/html',
      ...authHeaders,
    };
    
    const url = `${BASE_URL}/pedidos/${pedidoId}/comprovante`;
    const response = await fetch(url, { headers });
    
    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Erro desconhecido');
      throw new Error(`Erro ${response.status} ao gerar comprovante: ${errorText}`);
    }

    const html = await response.text();
    
    // 2. Abre janela e injeta HTML
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
        throw new Error('Não foi possível abrir a janela de impressão. Verifique o bloqueador de pop-ups.');
    }

    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();

    // 3. Marca como impresso (Best Effort)
    if (this.marcarImpresso) {
        this.marcarImpresso(pedidoId).catch(() => {});
    }
  }
}

// Factory helper (hook-friendly)
export function usePedidoPrintService() {
  const { getAuthHeader } = useAuth();
  const marcarImpressoHook = useMarcarImpresso();
  
  const marcarImpresso = async (id: number) => {
    await marcarImpressoHook.mutateAsync(id);
  };
  
  return new PedidoPrintService(getAuthHeader, marcarImpresso);
}
