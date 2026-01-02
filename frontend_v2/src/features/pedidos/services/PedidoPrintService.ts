import { createApiRequest } from '../../../api/http';
import { IPedidoPrintService } from './IPedidoPrintService';
import { useAuth } from '../../auth/authStore';
import { useMarcarImpresso } from '../../../api/endpoints/pedidos';

/**
 * Serviço de impressão (Arquitetura Command Pattern)
 * O Frontend atua apenas como "View/Render", buscando o HTML pronto do Backend.
 * Lógica de negócio e template estão no servidor.
 */
export class PedidoPrintService implements IPedidoPrintService {
  private getAuthHeader: () => Record<string, string>;
  private marcarImpresso?: (id: number) => Promise<void>;

  constructor(getAuthHeader: () => Record<string, string>, marcarImpresso?: (id: number) => Promise<void>) {
    this.getAuthHeader = getAuthHeader;
    this.marcarImpresso = marcarImpresso;
  }

  async print(pedidoId: number): Promise<void> {
    const apiRequest = createApiRequest(this.getAuthHeader);
    
    // 1. Busca HTML Gerado pelo Command no Backend
    // O backend retorna 'text/html', então createApiRequest deve retornar a string crua
    const response = await apiRequest<string>(`/pedidos/${pedidoId}/comprovante`);
    
    if (!response.ok) {
        throw new Error(response.message || 'Erro ao gerar comprovante');
    }

    const html = response.data;
    
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
