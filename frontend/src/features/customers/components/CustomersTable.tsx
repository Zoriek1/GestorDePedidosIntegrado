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
  Box,
  Typography,
  Stack,
  useMediaQuery,
  useTheme,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import type { Customer } from '../../../api/endpoints/customers';
import type { CustomerBadge } from '../services/ICustomerInsightsService';

interface CustomersTableProps {
  customers: Customer[];
  badgesMap: Record<number, CustomerBadge[]>;
  onRowClick?: (customer: Customer) => void;
}

export function CustomersTable({ customers, badgesMap, onRowClick }: CustomersTableProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const formatDate = (iso?: string) =>
    iso ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(new Date(iso)) : '—';

  const formatMoney = (value?: number) =>
    value !== undefined ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value) : '—';

  const formatFreq = (total?: number) => (total && total > 0 ? `${total} pedidos` : '—');

  // Mobile: Cards colapsáveis
  if (isMobile) {
    return (
      <Stack spacing={2}>
        {customers.map((c) => (
          <Accordion key={c.id} defaultExpanded={false}>
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              onClick={(e) => {
                if (onRowClick && !(e.target as HTMLElement).closest('.MuiAccordionSummary-expandIconWrapper')) {
                  onRowClick(c);
                }
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', pr: 2 }}>
                <Box>
                  <Typography variant="subtitle1" fontWeight="bold">
                    {c.nome}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
                    {(badgesMap[c.id] || []).map((badge) => (
                      <Chip key={badge.label} label={badge.label} size="small" color={badge.color} variant="outlined" />
                    ))}
                  </Box>
                </Box>
                <Tooltip title="Ver detalhes">
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRowClick?.(c);
                    }}
                  >
                    <VisibilityIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Stack spacing={1}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Último Pedido
                  </Typography>
                  <Typography variant="body2">{formatDate(c.ultimo_pedido)}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Total Gasto (LTV)
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {formatMoney(c.ltv)}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Frequência
                  </Typography>
                  <Typography variant="body2">{formatFreq(c.total_pedidos)}</Typography>
                </Box>
              </Stack>
            </AccordionDetails>
          </Accordion>
        ))}
      </Stack>
    );
  }

  // Desktop: Tabela normal
  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Cliente</TableCell>
            <TableCell>Último Pedido</TableCell>
            <TableCell>Total Gasto (LTV)</TableCell>
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

