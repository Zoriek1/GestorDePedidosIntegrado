import {
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  IconButton,
  Tooltip,
  TableContainer,
  Paper,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import type { Customer } from '../../../api/endpoints/customers';
import type { CustomerBadge } from '../services/ICustomerInsightsService';

interface CustomersTableProps {
  customers: Customer[];
  badgesMap: Record<number, CustomerBadge[]>;
  onRowClick?: (customer: Customer) => void;
}

export function CustomersTable({ customers, badgesMap, onRowClick }: CustomersTableProps) {
  const formatDate = (iso?: string) =>
    iso ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(new Date(iso)) : '—';

  const formatMoney = (value?: number) =>
    value !== undefined ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value) : '—';

  const formatFreq = (total?: number) => (total && total > 0 ? `${total} pedidos` : '—');

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Cliente</TableCell>
            <TableCell>Último Pedido</TableCell>
            <TableCell>total Gasto (LTV)</TableCell>
            <TableCell>Frequência</TableCell>
            <TableCell align="right">Ações</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {customers.map((c) => (
            <TableRow
              key={c.id}
              hover
              sx={{ cursor: onRowClick ? 'pointer' : 'default' }}
              onClick={() => onRowClick?.(c)}
            >
              <TableCell>
                {c.nome}
                <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                  {(badgesMap[c.id] || []).map((badge) => (
                    <Chip key={badge.label} label={badge.label} size="small" color={badge.color} variant="outlined" />
                  ))}
                </div>
              </TableCell>
              <TableCell>{formatDate(c.ultimo_pedido)}</TableCell>
              <TableCell>{formatMoney(c.ltv)}</TableCell>
              <TableCell>{formatFreq(c.total_pedidos)}</TableCell>
              <TableCell align="right">
                <Tooltip title="Ver detalhes">
                  <IconButton size="small" onClick={(e) => { e.stopPropagation(); onRowClick?.(c); }}>
                    <VisibilityIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

