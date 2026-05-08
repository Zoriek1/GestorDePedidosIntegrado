import { getApiBaseUrl } from '../../../api/http';
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
    // 1. Busca HTML Gerado pelo Command no Backend
    // Usar fetch direto porque o endpoint retorna 'text/html' e não JSON
    const authHeaders = this.getAuthHeader();
    const headers: Record<string, string> = {
      'Accept': 'text/html',
      ...authHeaders,
    };

    const url = `${getApiBaseUrl()}/pedidos/${pedidoId}/comprovante`;
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

  async printBatch(pedidoIds: number[]): Promise<void> {
    if (pedidoIds.length === 0) {
      throw new Error('Selecione ao menos 1 pedido para imprimir');
    }
    if (pedidoIds.length > 4) {
      throw new Error('Máximo de 4 pedidos por folha');
    }

    const authHeaders = this.getAuthHeader();
    const headers: Record<string, string> = {
      'Accept': 'text/html',
      'Content-Type': 'application/json',
      ...authHeaders,
    };

    const url = `${getApiBaseUrl()}/pedidos/comprovante-lote`;
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ pedido_ids: pedidoIds }),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Erro desconhecido');
      throw new Error(`Erro ${response.status} ao gerar comprovante em lote: ${errorText}`);
    }

    const html = await response.text();

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      throw new Error('Não foi possível abrir a janela de impressão. Verifique o bloqueador de pop-ups.');
    }

    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();

    if (this.marcarImpresso) {
      pedidoIds.forEach((id) => {
        this.marcarImpresso?.(id).catch(() => {});
      });
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
