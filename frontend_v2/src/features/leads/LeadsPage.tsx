/**
 * Leads UTM - Listagem de cliques da landing page
 */

import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  Stack,
  Chip,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip,
} from '@mui/material';
import CampaignIcon from '@mui/icons-material/Campaign';
import AddShoppingCartIcon from '@mui/icons-material/AddShoppingCart';
import { useLeads, type LeadsFilters, type Lead } from '../../api/endpoints/leads';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';

const SOURCE_OPTIONS = ['', 'facebook', 'google', 'instagram', 'tiktok', 'direto'];

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function sourceColor(source: string | null): 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'default' {
  switch (source) {
    case 'facebook': return 'primary';
    case 'google': return 'success';
    case 'instagram': return 'secondary';
    case 'tiktok': return 'warning';
    default: return 'default';
  }
}

export default function LeadsPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<LeadsFilters>({ page: 1, per_page: 25 });
  const { data, isLoading, error, refetch } = useLeads(filters);

  const handleCreateOrder = useCallback((lead: Lead) => {
    navigate('/pedidos/novo', {
      state: {
        prefillData: {
          telefone_cliente: lead.phone ?? '',
          origem_anuncio: !!lead.fbclid,
          fbclid: lead.fbclid ?? '',
          fbp: lead.fbp ?? '',
        },
      },
    });
  }, [navigate]);

  if (isLoading) return <Loading />;
  if (error) return <ErrorState message="Erro ao carregar leads" onRetry={refetch} />;

  const leads = data?.leads ?? [];
  const total = data?.total ?? 0;

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 3 }}>
        <CampaignIcon color="primary" />
        <Typography variant="h5" fontWeight={600}>
          Leads UTM
        </Typography>
        <Chip label={`${total} cliques`} size="small" />
      </Stack>

      {/* Filtros */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Origem</InputLabel>
            <Select
              value={filters.utm_source ?? ''}
              label="Origem"
              onChange={(e) =>
                setFilters((f) => ({ ...f, utm_source: e.target.value || undefined, page: 1 }))
              }
            >
              <MenuItem value="">Todas</MenuItem>
              {SOURCE_OPTIONS.filter(Boolean).map((s) => (
                <MenuItem key={s} value={s}>{s}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            size="small"
            label="Campanha"
            value={filters.utm_campaign ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, utm_campaign: e.target.value || undefined, page: 1 }))
            }
          />

          <TextField
            size="small"
            label="De"
            type="date"
            slotProps={{ inputLabel: { shrink: true } }}
            value={filters.date_from ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, date_from: e.target.value || undefined, page: 1 }))
            }
          />

          <TextField
            size="small"
            label="Até"
            type="date"
            slotProps={{ inputLabel: { shrink: true } }}
            value={filters.date_to ?? ''}
            onChange={(e) =>
              setFilters((f) => ({ ...f, date_to: e.target.value || undefined, page: 1 }))
            }
          />
        </Stack>
      </Paper>

      {/* Tabela */}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Data</TableCell>
              <TableCell>Evento</TableCell>
              <TableCell>Telefone</TableCell>
              <TableCell>fbclid</TableCell>
              <TableCell>fbp</TableCell>
              <TableCell>Origem</TableCell>
              <TableCell>Campanha</TableCell>
              <TableCell>Conteúdo</TableCell>
              <TableCell>Meio</TableCell>
              <TableCell>IP</TableCell>
              <TableCell align="center">Ação</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {leads.length === 0 ? (
              <TableRow>
                <TableCell colSpan={11} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                    Nenhum lead encontrado
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              leads.map((lead) => (
                <TableRow key={lead.id} hover>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{formatDate(lead.created_at)}</TableCell>
                  <TableCell>{lead.event ?? '—'}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{lead.phone ?? '—'}</TableCell>
                  <TableCell sx={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {lead.fbclid ?? '—'}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {lead.fbp ?? '—'}
                  </TableCell>
                  <TableCell>
                    {lead.utm_source ? (
                      <Chip label={lead.utm_source} size="small" color={sourceColor(lead.utm_source)} />
                    ) : '—'}
                  </TableCell>
                  <TableCell>{lead.utm_campaign ?? '—'}</TableCell>
                  <TableCell>{lead.utm_content ?? '—'}</TableCell>
                  <TableCell>{lead.utm_medium ?? '—'}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.75rem' }}>{lead.ip_address ?? '—'}</TableCell>
                  <TableCell align="center">
                    <Tooltip title="Criar pedido a partir deste lead">
                      <IconButton size="small" color="primary" onClick={() => handleCreateOrder(lead)}>
                        <AddShoppingCartIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        <TablePagination
          component="div"
          count={total}
          page={(filters.page ?? 1) - 1}
          onPageChange={(_e, newPage) => setFilters((f) => ({ ...f, page: newPage + 1 }))}
          rowsPerPage={filters.per_page ?? 25}
          onRowsPerPageChange={(e) =>
            setFilters((f) => ({ ...f, per_page: parseInt(e.target.value, 10), page: 1 }))
          }
          rowsPerPageOptions={[10, 25, 50, 100]}
          labelRowsPerPage="Por página"
          labelDisplayedRows={({ from, to, count }) => `${from}–${to} de ${count}`}
        />
      </TableContainer>
    </Box>
  );
}
