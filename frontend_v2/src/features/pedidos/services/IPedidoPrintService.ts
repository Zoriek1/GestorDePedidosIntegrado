export interface IPedidoPrintService {
  print(pedidoId: number): Promise<void>;
  printBatch(pedidoIds: number[]): Promise<void>;
}
