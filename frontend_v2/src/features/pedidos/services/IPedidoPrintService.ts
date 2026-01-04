export interface IPedidoPrintService {
  print(pedidoId: number): Promise<void>;
}


