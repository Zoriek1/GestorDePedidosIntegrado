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
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import { useLeads, type LeadsFilters, type Lead } from '../../api/endpoints/leads';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';

const SOURCE_OPTIONS = ['', 'facebook', 'google', 'instagram', 'tiktok', 'direto'];

/** Mesmo conjunto que o backend usa como padrão (DEFAULT_KEY_EVENTS) */
const DEFAULT_KEY_EVENTS = 'modal_open,whatsapp_click,site_click';

const EVENT_LABELS: Record<string, string> = {
  modal_open: 'Modal open',
  whatsapp_click: 'WhatsApp Click',
  site_click: 'Site Click',
};

function buildWhatsAppUrl(phone: string): string | null {
  const digits = phone.replace(/\D/g, '');
  if (digits.length < 10) return null;
  const full = digits.length <= 11 ? `55${digits}` : digits;
  return `https://wa.me/${full}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      timeZone: 'America/Sao_Paulo',
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

function formatEventLabel(raw: string | null): string {
  if (!raw) return '—';
  return EVENT_LABELS[raw] ?? raw.replace(/_/g, ' ');
}

function eventFilterToSelectValue(f: LeadsFilters): string {
  if (f.events === DEFAULT_KEY_EVENTS) return 'key';
  if (f.event === 'all') return 'all';
  if (f.event) return f.event;
  return 'key';
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
  const [filters, setFilters] = useState<LeadsFilters>({
    page: 1,
    per_page: 25,
    events: DEFAULT_KEY_EVENTS,
  });
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
          <FormControl size="small" sx={{ minWidth: 170 }}>
            <InputLabel>Evento</InputLabel>
            <Select
              value={eventFilterToSelectValue(filters)}
              label="Evento"
              onChange={(e) => {
                const v = e.target.value;
                setFilters((prev) => {
                  const next: LeadsFilters = { ...prev, page: 1 };
                  if (v === 'key') {
                    delete next.event;
                    next.events = DEFAULT_KEY_EVENTS;
                    return next;
                  }
                  if (v === 'all') {
                    delete next.events;
                    next.event = 'all';
                    return next;
                  }
                  delete next.events;
                  next.event = v;
                  return next;
                });
              }}
            >
              <MenuItem value="key">Principais (modal, WhatsApp, site)</MenuItem>
              <MenuItem value="modal_open">{EVENT_LABELS.modal_open}</MenuItem>
              <MenuItem value="whatsapp_click">{EVENT_LABELS.whatsapp_click}</MenuItem>
              <MenuItem value="site_click">{EVENT_LABELS.site_click}</MenuItem>
              <MenuItem value="all">Todos</MenuItem>
            </Select>
          </FormControl>

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
                  <TableCell>{formatEventLabel(lead.event)}</TableCell>
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
                    <Stack direction="row" spacing={0.5} justifyContent="center">
                      {lead.phone ? (
                        <Tooltip title="Chamar no WhatsApp">
                          <IconButton
                            size="small"
                            color="success"
                            component="a"
                            href={buildWhatsAppUrl(lead.phone) ?? '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <WhatsAppIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      ) : (
                        <Tooltip title="Sem telefone">
                          <span>
                            <IconButton size="small" disabled>
                              <WhatsAppIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                      <Tooltip title="Criar pedido a partir deste lead">
                        <IconButton size="small" color="primary" onClick={() => handleCreateOrder(lead)}>
                          <AddShoppingCartIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Stack>
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
