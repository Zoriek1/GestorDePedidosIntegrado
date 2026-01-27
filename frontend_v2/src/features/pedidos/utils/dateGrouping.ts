import type { Pedido } from '../../../api/endpoints/pedidos';

export interface DateGroup {
  label: string;
  pedidos: Pedido[];
}

/**
 * Agrupa pedidos por faixas de data para exibição visual no painel
 * Grupos: HOJE, AMANHÃ, ESTA SEMANA, ESTE MÊS, MÊS QUE VEM, ATRASADOS
 */
export function groupOrdersByDate(pedidos: Pedido[]): DateGroup[] {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  
  const amanha = new Date(hoje);
  amanha.setDate(amanha.getDate() + 1);
  
  const fimSemana = new Date(hoje);
  fimSemana.setDate(fimSemana.getDate() + 7);
  
  const fimMes = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
  fimMes.setHours(23, 59, 59, 999);
  
  const inicioProximoMes = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 1);
  inicioProximoMes.setHours(0, 0, 0, 0);
  
  const fimProximoMes = new Date(hoje.getFullYear(), hoje.getMonth() + 2, 0);
  fimProximoMes.setHours(23, 59, 59, 999);
  
  const grupos: DateGroup[] = [
    { label: 'ATRASADOS', pedidos: [] },
    { label: 'HOJE', pedidos: [] },
    { label: 'AMANHÃ', pedidos: [] },
    { label: 'ESTA SEMANA', pedidos: [] },
    { label: 'ESTE MÊS', pedidos: [] },
    { label: 'MÊS QUE VEM', pedidos: [] },
  ];
  
  // Filtrar pedidos deletados (segurança extra)
  const pedidosValidos = pedidos.filter(p => !p.deleted_at);
  
  for (const pedido of pedidosValidos) {
    const dataEntrega = new Date(pedido.dia_entrega + 'T00:00:00');
    dataEntrega.setHours(0, 0, 0, 0);
    
    if (dataEntrega < hoje) {
      grupos[0].pedidos.push(pedido); // ATRASADOS
    } else if (dataEntrega.getTime() === hoje.getTime()) {
      grupos[1].pedidos.push(pedido); // HOJE
    } else if (dataEntrega.getTime() === amanha.getTime()) {
      grupos[2].pedidos.push(pedido); // AMANHÃ
    } else if (dataEntrega <= fimSemana) {
      grupos[3].pedidos.push(pedido); // ESTA SEMANA
    } else if (dataEntrega <= fimMes) {
      grupos[4].pedidos.push(pedido); // ESTE MÊS
    } else if (dataEntrega >= inicioProximoMes && dataEntrega <= fimProximoMes) {
      grupos[5].pedidos.push(pedido); // MÊS QUE VEM
    } else {
      // Pedidos muito futuros (mais de 2 meses) - adicionar ao último grupo
      grupos[5].pedidos.push(pedido);
    }
  }
  
  // Ordenar pedidos dentro de cada grupo por dia_entrega e horario
  for (const grupo of grupos) {
    grupo.pedidos.sort((a, b) => {
      const dataA = new Date(a.dia_entrega + 'T00:00:00');
      const dataB = new Date(b.dia_entrega + 'T00:00:00');
      if (dataA.getTime() !== dataB.getTime()) {
        return dataA.getTime() - dataB.getTime();
      }
      // Se mesma data, ordenar por horário
      return (a.horario || '').localeCompare(b.horario || '');
    });
  }
  
  // Retornar apenas grupos que têm pedidos
  return grupos.filter(grupo => grupo.pedidos.length > 0);
}
