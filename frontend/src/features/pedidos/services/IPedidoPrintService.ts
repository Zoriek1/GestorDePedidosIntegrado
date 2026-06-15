/** Moldura de impressão em lote: pedidos por folha A4. */
export type PrintLayout = 1 | 2 | 4;

export interface IPedidoPrintService {
  print(pedidoId: number): Promise<void>;
  printBatch(pedidoIds: number[], layout?: PrintLayout): Promise<void>;
}
