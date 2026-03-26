/**
 * Leads UTM - Listagem de cliques da landing page
 */

import { useState, useCallback, type MouseEvent } from 'react';
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Menu,
} from '@mui/material';
import CampaignIcon from '@mui/icons-material/Campaign';
import AddShoppingCartIcon from '@mui/icons-material/AddShoppingCart';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import {
  useLeads,
  useUpdateLeadPhone,
  useUpdateLeadStatus,
  type LeadsFilters,
  type Lead,
} from '../../api/endpoints/leads';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../components/system/useToast';

const SOURCE_OPTIONS = ['', 'facebook', 'google', 'instagram', 'tiktok', 'direto'];

dayjs.extend(utc);
dayjs.extend(timezone);

const TZ_BR = 'America/Sao_Paulo';

/** Mesmo conjunto que o backend usa como padrão (DEFAULT_KEY_EVENTS) */
const DEFAULT_KEY_EVENTS = 'modal_open,whatsapp_click,site_click';

const EVENT_LABELS: Record<string, string> = {
  modal_open: 'Modal open',
  whatsapp_click: 'WhatsApp Click',
  site_click: 'Site Click',
};

const LEAD_STATUS_LABELS: Record<string, string> = {
  pendente_whatsapp: 'Pendente WhatsApp',
  whatsapp_iniciado: 'WhatsApp iniciado',
  compra_realizada: 'Compra realizada',
  nao_entrou_em_contato: 'Não entrou em contato',
};

function buildWhatsAppUrl(phone: string): string | null {
  const digits = phone.replace(/\D/g, '');
  if (digits.length < 10) return null;
  const full = digits.length <= 11 ? `55${digits}` : digits;
  return `https://wa.me/${full}`;
}

/** ISO com fuso → instante absoluto. Sem fuso: Postgres/SQLAlchemy costuma devolver UTC naive — não tratar como BRT. */
function isoStringHasOffset(iso: string): boolean {
  return /(Z|[+-]\d{2}:?\d{2})$/i.test(iso.trim());
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    const normalized = iso.trim().replace(' ', 'T');
    const d = isoStringHasOffset(normalized)
      ? dayjs(normalized).tz(TZ_BR)
      : dayjs.utc(normalized).tz(TZ_BR);
    if (!d.isValid()) return iso;
    return d.format('DD/MM/YY[,] HH:mm');
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

function tokenValidColor(valid: boolean | null): 'success' | 'error' | 'default' {
  if (valid === true) return 'success';
  if (valid === false) return 'error';
  return 'default';
}

function tokenValidLabel(valid: boolean | null): string {
  if (valid === true) return 'Válido';
  if (valid === false) return 'Inválido';
  return '—';
}

function shouldShowTokenFields(lead: Lead): boolean {
  return lead.event === 'whatsapp_click' || !!lead.token_rastreio;
}

function leadStatusColor(status: string | null): 'warning' | 'info' | 'success' | 'default' {
  switch (status) {
    case 'pendente_whatsapp':
      return 'warning';
    case 'whatsapp_iniciado':
      return 'info';
    case 'compra_realizada':
      return 'success';
    default:
      return 'default';
  }
}

function leadStatusLabel(status: string | null): string {
  if (!status) return '—';
  return LEAD_STATUS_LABELS[status] ?? status;
}

export default function LeadsPage() {
  const navigate = useNavigate();
  const { success, error: showError } = useToast();
  const [filters, setFilters] = useState<LeadsFilters>({
    page: 1,
    per_page: 25,
    events: DEFAULT_KEY_EVENTS,
  });
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [manualPhone, setManualPhone] = useState('');
  const [statusMenuAnchor, setStatusMenuAnchor] = useState<null | HTMLElement>(null);
  const [statusMenuLead, setStatusMenuLead] = useState<Lead | null>(null);
  const { data, isLoading, error, refetch } = useLeads(filters);
  const updateLeadPhone = useUpdateLeadPhone();
  const updateLeadStatus = useUpdateLeadStatus();

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

  const handleOpenPhoneDialog = useCallback((lead: Lead) => {
    setEditingLead(lead);
    setManualPhone(lead.phone ?? '');
  }, []);

  const handleClosePhoneDialog = useCallback(() => {
    setEditingLead(null);
    setManualPhone('');
  }, []);

  const handleSavePhone = useCallback(async () => {
    if (!editingLead) return;

    const digits = manualPhone.replace(/\D/g, '');
    if (digits.length < 10) {
      showError('Informe um telefone válido com DDD');
      return;
    }

    try {
      await updateLeadPhone.mutateAsync({ id: editingLead.id, phone: manualPhone });
      success('Telefone do lead atualizado');
      handleClosePhoneDialog();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao atualizar telefone';
      showError(message);
    }
  }, [editingLead, handleClosePhoneDialog, manualPhone, showError, success, updateLeadPhone]);

  const handleOpenStatusMenu = useCallback((event: MouseEvent<HTMLElement>, lead: Lead) => {
    event.stopPropagation();
    setStatusMenuAnchor(event.currentTarget);
    setStatusMenuLead(lead);
  }, []);

  const handleCloseStatusMenu = useCallback(() => {
    setStatusMenuAnchor(null);
    setStatusMenuLead(null);
  }, []);

  const handleMarkNoContact = useCallback(async () => {
    if (!statusMenuLead) return;
    try {
      await updateLeadStatus.mutateAsync({ id: statusMenuLead.id, status: 'nao_entrou_em_contato' });
      success('Lead marcado como não entrou em contato');
      handleCloseStatusMenu();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao atualizar status';
      showError(message);
    }
  }, [handleCloseStatusMenu, showError, statusMenuLead, success, updateLeadStatus]);

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
              <TableCell align="center">Ação</TableCell>
              <TableCell>Data (BRT)</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Telefone</TableCell>
              <TableCell>Código WhatsApp</TableCell>
              <TableCell>Token válido</TableCell>
              <TableCell>Evento</TableCell>
              <TableCell>fbclid</TableCell>
              <TableCell>fbp</TableCell>
              <TableCell>Origem</TableCell>
              <TableCell>Campanha</TableCell>
              <TableCell>Conteúdo</TableCell>
              <TableCell>Meio</TableCell>
              <TableCell>IP</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {leads.length === 0 ? (
              <TableRow>
                <TableCell colSpan={14} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                    Nenhum lead encontrado
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              leads.map((lead) => (
                <TableRow key={lead.id} hover>
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
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{formatDate(lead.created_at)}</TableCell>
                  <TableCell>
                    {lead.status === 'pendente_whatsapp' ? (
                      <Stack direction="row" spacing={0.5} alignItems="center">
                        <Tooltip title="Clique para informar o número correto">
                          <Chip
                            size="small"
                            color="warning"
                            label={leadStatusLabel(lead.status)}
                            variant="filled"
                            clickable
                            onClick={() => handleOpenPhoneDialog(lead)}
                          />
                        </Tooltip>
                        <Tooltip title="Outras ações">
                          <IconButton
                            size="small"
                            aria-label="Ações do status"
                            onClick={(e) => handleOpenStatusMenu(e, lead)}
                          >
                            <MoreVertIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    ) : (
                      <Chip
                        size="small"
                        color={leadStatusColor(lead.status)}
                        label={leadStatusLabel(lead.status)}
                        variant={lead.status ? 'filled' : 'outlined'}
                      />
                    )}
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{lead.phone ?? '—'}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap', fontFamily: 'monospace' }}>
                    {lead.token_rastreio ?? '—'}
                  </TableCell>
                  <TableCell>
                    {shouldShowTokenFields(lead) ? (
                      <Chip
                        size="small"
                        color={tokenValidColor(lead.token_valido)}
                        label={tokenValidLabel(lead.token_valido)}
                        variant={lead.token_valido === null ? 'outlined' : 'filled'}
                      />
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell>{formatEventLabel(lead.event)}</TableCell>
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

      <Dialog open={!!editingLead} onClose={handleClosePhoneDialog} fullWidth maxWidth="xs">
        <DialogTitle>Atualizar WhatsApp do lead</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Telefone/WhatsApp"
            placeholder="(62) 99999-0000"
            fullWidth
            value={manualPhone}
            onChange={(e) => setManualPhone(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClosePhoneDialog} disabled={updateLeadPhone.isPending}>Cancelar</Button>
          <Button onClick={handleSavePhone} variant="contained" disabled={updateLeadPhone.isPending}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>

      <Menu
        anchorEl={statusMenuAnchor}
        open={Boolean(statusMenuAnchor)}
        onClose={handleCloseStatusMenu}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <MenuItem
          onClick={() => {
            void handleMarkNoContact();
          }}
          disabled={updateLeadStatus.isPending}
        >
          Não entrou em contato
        </MenuItem>
      </Menu>
    </Box>
  );
}
