import {
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  TableContainer,
  Paper,
  Typography,
} from '@mui/material';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { calcularValorBrutoPedido } from '../utils/valorEfetivo';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';

// Configurar locale pt-br para dayjs
dayjs.locale('pt-br');

interface SalesTableProps {
  vendas: Pedido[];
}

export function SalesTable({ vendas }: SalesTableProps) {
  const formatDate = (iso?: string) => {
    if (!iso) return '—';
    // Formatar data de criação em pt-BR
    return dayjs(iso).format('DD/MM/YYYY');
  };

  const formatMoney = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { 
      style: 'currency', 
      currency: 'BRL' 
    }).format(value);
  };

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Data</TableCell>
            <TableCell>Cliente</TableCell>
            <TableCell>Produto</TableCell>
            <TableCell>Fonte</TableCell>
            <TableCell align="right">Valor Total</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {vendas.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                <Typography variant="body2" color="text.secondary">
                  Nenhuma venda encontrada para este mês
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            vendas.map((venda) => {
              const valorBruto = calcularValorBrutoPedido(venda);
              
              return (
                <TableRow key={venda.id} hover>
                  <TableCell>{formatDate(venda.created_at)}</TableCell>
                  <TableCell>
                    {venda.cliente}
                    {venda.destinatario !== venda.cliente && (
                      <Chip 
                        label={`→ ${venda.destinatario}`} 
                        size="small" 
                        variant="outlined" 
                        sx={{ ml: 1, fontSize: '0.7rem', height: 20 }}
                      />
                    )}
                  </TableCell>
                  <TableCell>{venda.produto}</TableCell>
                  <TableCell>
                    <Chip 
                      label={venda.fonte_pedido_nome || venda.fonte_pedido || 'Sem fonte'} 
                      size="small" 
                      color="primary" 
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontWeight="bold">
                      {formatMoney(valorBruto)}
                    </Typography>
                  </TableCell>
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
