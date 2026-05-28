/**
 * Leads UTM - Listagem de cliques da landing page
 */

import { Fragment, useState, useCallback, useEffect, useMemo, useRef, type MouseEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
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
  DialogContentText,
  DialogActions,
  Button,
  Menu,
  FormControlLabel,
  Checkbox,
  Card,
  CardContent,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  useMediaQuery,
  useTheme,
  type Theme,
} from '@mui/material';
import CampaignIcon from '@mui/icons-material/Campaign';
import AddShoppingCartIcon from '@mui/icons-material/AddShoppingCart';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import VisibilityIcon from '@mui/icons-material/Visibility';
import CheckIcon from '@mui/icons-material/Check';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ScheduleIcon from '@mui/icons-material/Schedule';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import PhoneDisabledIcon from '@mui/icons-material/PhoneDisabled';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import KeyboardIcon from '@mui/icons-material/Keyboard';
import BoltIcon from '@mui/icons-material/Bolt';
import EditCalendarIcon from '@mui/icons-material/EditCalendar';
import {
  useLeads,
  useLeadsStats,
  useBulkUpdateLeadStatus,
  useBulkDisqualifyLeads,
  useUpdateLeadPhone,
  useUpdateLeadStatus,
  type LeadsFilters,
  type LeadsPeriod,
  type Lead,
} from '../../api/endpoints/leads';
import { KeyboardCheatsheet } from './KeyboardCheatsheet';
import { QuickEntryModal } from '../pedidos/components/QuickEntryModal';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs, { type Dayjs } from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../components/system/useToast';

const SOURCE_OPTIONS = ['', 'facebook', 'google', 'instagram', 'tiktok', 'direto'];

dayjs.extend(utc);
dayjs.extend(timezone);

const TZ_BR = 'America/Sao_Paulo';

const EVENT_LABELS: Record<string, string> = {
  whatsapp_click: 'WhatsApp Click',
  site_click: 'Site Click',
};

// Labels visíveis na UI. As chaves internas no DB continuam as mesmas
// (`pendente_whatsapp`, `whatsapp_iniciado`, `descarte`). Ver docs/integrations.md
// "Funil de leads Meta CAPI" para o mapeamento label ↔ chave ↔ evento Meta.
const LEAD_STATUS_LABELS: Record<string, string> = {
  pendente_whatsapp: 'P. Whatsapp (Contact)',
  whatsapp_iniciado: 'Lead Confirmado',
  compra_realizada: 'Compra realizada',
  nao_entrou_em_contato: 'Não entrou em contato',
  descarte: 'Lead Desqualificado',
};

const FILTERS_STORAGE_KEY = 'leads:filters:v1';

const DEFAULT_FILTERS: LeadsFilters = {
  page: 1,
  per_page: 25,
  event: 'whatsapp_click',
  period: 'today',
  hidden: 'exclude',
};

/** Valor do ToggleButtonGroup de período (inclui o modo UI-only "day"). */
type PeriodUiValue = LeadsPeriod | 'day';

type AgeBucket = 'fresh' | 'warm' | 'cold';

/**
 * Decide se o badge de idade deve aparecer pra este lead.
 *
 * Casos de uso:
 *  - `pendente_whatsapp`: saber há quanto tempo o lead aguarda primeira resposta.
 *  - `whatsapp_iniciado` SEM followup: saber quando dar followup.
 *
 * Demais status (compra_realizada, nao_entrou_em_contato, descarte, ou
 * whatsapp_iniciado já com followup) não precisam — o tempo decorrido vira
 * ruído visual (vermelho permanente que não muda nada).
 */
function shouldShowAge(lead: Pick<Lead, 'status' | 'followup_feito_em'>): boolean {
  if (lead.status === 'pendente_whatsapp') return true;
  if (lead.status === 'whatsapp_iniciado' && !lead.followup_feito_em) return true;
  return false;
}

/**
 * SLA visual: ≤15min verde, ≤30min âmbar, >30min vermelho.
 * Só aplica quando shouldShowAge(lead) é true.
 */
function getLeadAgeBucket(createdAt: string | null): AgeBucket {
  if (!createdAt) return 'fresh';
  const normalized = createdAt.trim().replace(' ', 'T');
  const d = isoStringHasOffset(normalized)
    ? dayjs(normalized)
    : dayjs.utc(normalized);
  if (!d.isValid()) return 'fresh';
  const minutes = dayjs().diff(d, 'minute');
  if (minutes <= 15) return 'fresh';
  if (minutes <= 30) return 'warm';
  return 'cold';
}

function formatLeadAge(createdAt: string | null): string {
  if (!createdAt) return '—';
  const normalized = createdAt.trim().replace(' ', 'T');
  const d = isoStringHasOffset(normalized)
    ? dayjs(normalized)
    : dayjs.utc(normalized);
  if (!d.isValid()) return '—';
  const now = dayjs();
  const minutes = now.diff(d, 'minute');
  if (minutes < 60) return `${Math.max(0, minutes)}m`;
  const hours = now.diff(d, 'hour');
  if (hours < 24) return `${hours}h`;
  const days = now.diff(d, 'day');
  return `${days}d`;
}

type LeadGroup = 'confirmados' | 'pendentes' | 'descartados';

function getLeadGroup(status: string | null): LeadGroup {
  if (status === 'whatsapp_iniciado' || status === 'compra_realizada') return 'confirmados';
  if (status === 'nao_entrou_em_contato' || status === 'descarte') return 'descartados';
  return 'pendentes';
}

const GROUP_ORDER: readonly LeadGroup[] = ['confirmados', 'pendentes', 'descartados'] as const;

const GROUP_LABELS: Record<LeadGroup, string> = {
  confirmados: 'Confirmados',
  pendentes: 'Pendentes / Sem resposta',
  descartados: 'Descartados',
};

function loadPersistedFilters(): LeadsFilters {
  if (typeof window === 'undefined') return DEFAULT_FILTERS;
  try {
    const raw = window.localStorage.getItem(FILTERS_STORAGE_KEY);
    if (!raw) return DEFAULT_FILTERS;
    const parsed = JSON.parse(raw) as Partial<LeadsFilters> | null;
    if (!parsed || typeof parsed !== 'object') return DEFAULT_FILTERS;
    return { ...DEFAULT_FILTERS, ...parsed, page: 1 };
  } catch {
    return DEFAULT_FILTERS;
  }
}

function persistFilters(filters: LeadsFilters): void {
  if (typeof window === 'undefined') return;
  try {
    const { page: _ignored, ...rest } = filters;
    window.localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(rest));
  } catch {
    /* ignore */
  }
}

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

function leadStatusColor(status: string | null): 'warning' | 'info' | 'success' | 'error' | 'default' {
  switch (status) {
    case 'pendente_whatsapp':
      return 'warning';
    case 'whatsapp_iniciado':
      return 'info';
    case 'compra_realizada':
      return 'success';
    case 'descarte':
      return 'error';
    default:
      return 'default';
  }
}

function leadStatusLabel(status: string | null): string {
  if (!status) return '—';
  return LEAD_STATUS_LABELS[status] ?? status;
}

function displayAdSet(name: string | null | undefined): string {
  if (name === 'LAL | 6km | ADV+') return 'OPEN | 6km | ADV+';
  return name ?? '—';
}

function canEditLeadPhone(lead: Lead): boolean {
  return lead.status === 'pendente_whatsapp' || lead.status === 'nao_entrou_em_contato';
}

function ageBorderColor(lead: Pick<Lead, 'created_at' | 'status' | 'followup_feito_em'>, theme: Theme): string {
  if (!shouldShowAge(lead)) return theme.palette.divider;
  const bucket = getLeadAgeBucket(lead.created_at);
  if (bucket === 'fresh') return theme.palette.success.light;
  if (bucket === 'warm') return theme.palette.warning.light;
  return theme.palette.error.main;
}

const AGE_BUCKET_META: Record<AgeBucket, { Icon: typeof CheckCircleIcon; color: 'success' | 'warning' | 'error' }> = {
  fresh: { Icon: CheckCircleIcon, color: 'success' },
  warm: { Icon: ScheduleIcon, color: 'warning' },
  cold: { Icon: ReportProblemIcon, color: 'error' },
};

function AgeChip({ lead }: { lead: Pick<Lead, 'created_at' | 'status' | 'followup_feito_em'> }) {
  const theme = useTheme();
  if (!shouldShowAge(lead)) return null;
  const bucket = getLeadAgeBucket(lead.created_at);
  const { Icon, color } = AGE_BUCKET_META[bucket];
  // Saturação reduzida: usa `light` exceto no caso crítico (>30min)
  const bg = bucket === 'cold' ? theme.palette.error.main : theme.palette[color].light;
  const fg = bucket === 'cold' ? theme.palette.error.contrastText : theme.palette[color].contrastText;
  return (
    <Chip
      size="small"
      icon={<Icon sx={{ color: `${fg} !important`, fontSize: '0.95rem' }} />}
      label={formatLeadAge(lead.created_at)}
      sx={{
        height: 22,
        borderRadius: '4px',
        backgroundColor: bg,
        color: fg,
        fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
        '& .MuiChip-label': { px: 0.75 },
      }}
    />
  );
}

export default function LeadsPage() {
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { success, error: showError } = useToast();
  const [filters, setFilters] = useState<LeadsFilters>(loadPersistedFilters);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [manualPhone, setManualPhone] = useState('');
  const [respondeuPrimeiraMensagem, setRespondeuPrimeiraMensagem] = useState(false);
  const [statusMenuAnchor, setStatusMenuAnchor] = useState<null | HTMLElement>(null);
  const [statusMenuLead, setStatusMenuLead] = useState<Lead | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => new Set());
  const [confirmBulkNoContact, setConfirmBulkNoContact] = useState(false);
  const [bulkDisqualifyOpen, setBulkDisqualifyOpen] = useState(false);
  const [phoneEdits, setPhoneEdits] = useState<Record<number, string>>({});
  const [focusedId, setFocusedId] = useState<number | null>(null);
  const [cheatsheetOpen, setCheatsheetOpen] = useState(false);
  const [loadingWhatsAppId, setLoadingWhatsAppId] = useState<number | null>(null);
  const [descartadosOpen, setDescartadosOpen] = useState(false);
  const [dayPickerOpen, setDayPickerOpen] = useState(false);
  const [createModeAnchor, setCreateModeAnchor] = useState<HTMLElement | null>(null);
  const [createModeLead, setCreateModeLead] = useState<Lead | null>(null);
  const [quickEntryOpen, setQuickEntryOpen] = useState(false);
  const [, forceTick] = useState(0);
  const lastSelectedIndexRef = useRef<number | null>(null);
  const rowRefs = useRef<Map<number, HTMLElement>>(new Map());
  const { data, isLoading, error, refetch } = useLeads(filters);
  // 2ª query lazy: só busca leads ocultos (descarte + nao_entrou_em_contato)
  // quando o accordion está aberto. Per_page alto para evitar paginação separada.
  const hiddenFilters = useMemo<LeadsFilters>(
    () => ({ ...filters, hidden: 'only', page: 1, per_page: 200 }),
    [filters],
  );
  const { data: hiddenData, isLoading: hiddenLoading } = useLeads(
    hiddenFilters,
    { enabled: descartadosOpen },
  );
  const { data: statsData } = useLeadsStats();
  const updateLeadPhone = useUpdateLeadPhone();
  const updateLeadStatus = useUpdateLeadStatus();
  const bulkUpdateStatus = useBulkUpdateLeadStatus();
  const bulkDisqualifyLeads = useBulkDisqualifyLeads();
  useEffect(() => {
    persistFilters(filters);
  }, [filters]);

  const setPeriod = useCallback((period: LeadsPeriod) => {
    setFilters((prev) => {
      const next: LeadsFilters = { ...prev, period, page: 1 };
      if (period !== 'custom') {
        delete next.date_from;
        delete next.date_to;
      }
      return next;
    });
  }, []);

  const handleViewOrder = useCallback((pedidoId: number) => {
    navigate(`/pedidos/${pedidoId}`);
  }, [navigate]);

  const handleCreateOrder = useCallback((lead: Lead) => {
    navigate('/pedidos/novo', {
      state: {
        prefillData: {
          telefone_cliente: lead.phone || undefined,
          codigo_whatsapp: lead.token_rastreio || undefined,
          origem_anuncio: !!lead.fbclid,
          fbclid: lead.fbclid || undefined,
          fbp: lead.fbp || undefined,
        },
      },
    });
  }, [navigate]);

  const openCreateModeMenu = useCallback(
    (event: MouseEvent<HTMLElement>, lead: Lead) => {
      event.stopPropagation();
      setCreateModeAnchor(event.currentTarget);
      setCreateModeLead(lead);
    },
    [],
  );

  const handleOpenPhoneDialog = useCallback((lead: Lead) => {
    setEditingLead(lead);
    setManualPhone(lead.phone ?? '');
    setRespondeuPrimeiraMensagem(false);
  }, []);

  const handleClosePhoneDialog = useCallback(() => {
    setEditingLead(null);
    setManualPhone('');
    setRespondeuPrimeiraMensagem(false);
  }, []);

  const handleSavePhone = useCallback(async () => {
    if (!editingLead) return;

    if (!respondeuPrimeiraMensagem) {
      showError('Confirme que o cliente respondeu a primeira mensagem');
      return;
    }

    const digits = manualPhone.replace(/\D/g, '');
    if (digits.length < 10) {
      showError('Informe um telefone válido com DDD');
      return;
    }

    try {
      await updateLeadPhone.mutateAsync(
        editingLead.token_rastreio
          ? { token_rastreio: editingLead.token_rastreio, phone: manualPhone }
          : { id: editingLead.id, phone: manualPhone },
      );
      success('Telefone do lead atualizado');
      handleClosePhoneDialog();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao atualizar telefone';
      showError(message);
    }
  }, [editingLead, handleClosePhoneDialog, manualPhone, respondeuPrimeiraMensagem, showError, success, updateLeadPhone]);

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
      await updateLeadStatus.mutateAsync(
        statusMenuLead.token_rastreio
          ? { token_rastreio: statusMenuLead.token_rastreio, status: 'nao_entrou_em_contato' }
          : { id: statusMenuLead.id, status: 'nao_entrou_em_contato' },
      );
      success('Lead marcado como não entrou em contato');
      handleCloseStatusMenu();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao atualizar status';
      showError(message);
    }
  }, [handleCloseStatusMenu, showError, statusMenuLead, success, updateLeadStatus]);

  const handleQuickMarkNoContact = useCallback(
    async (lead: Lead) => {
      try {
        await updateLeadStatus.mutateAsync({ id: lead.id, status: 'nao_entrou_em_contato' });
        success('Lead marcado como não entrou em contato');
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Erro ao atualizar status';
        showError(message);
      }
    },
    [showError, success, updateLeadStatus],
  );

  const total = data?.total ?? 0;
  // Quantos leads ocultos existem na janela atual — usado no header do accordion
  // sem precisar do fetch da 2ª query.
  const hiddenCount = data?.hidden_count ?? 0;

  const sortLeadsByPhoneThenRecent = useCallback((arr: Lead[]) => {
    arr.sort((a, b) => {
      const hasA = a.phone ? 0 : 1;
      const hasB = b.phone ? 0 : 1;
      if (hasA !== hasB) return hasA - hasB;
      const ta = a.created_at ?? '';
      const tb = b.created_at ?? '';
      if (ta === tb) return 0;
      return ta < tb ? 1 : -1;
    });
  }, []);

  const hiddenLeads = useMemo(() => {
    const src = [...(hiddenData?.leads ?? [])];
    sortLeadsByPhoneThenRecent(src);
    return src;
  }, [hiddenData?.leads, sortLeadsByPhoneThenRecent]);

  // Agrupamento: Confirmados + Pendentes vêm da query principal (hidden=exclude).
  // Descartados vêm da 2ª query (hidden=only) e são populados aqui só quando
  // o accordion já está aberto / dados carregados — mas a key existe sempre
  // para manter a API do GROUP_ORDER consistente.
  const groupedLeads = useMemo(() => {
    const src = data?.leads ?? [];
    const groups: Record<LeadGroup, Lead[]> = {
      confirmados: [],
      pendentes: [],
      descartados: hiddenLeads,
    };
    for (const lead of src) {
      const g = getLeadGroup(lead.status);
      if (g === 'descartados') continue; // defensivo: backend já filtra
      groups[g].push(lead);
    }
    sortLeadsByPhoneThenRecent(groups.confirmados);
    sortLeadsByPhoneThenRecent(groups.pendentes);
    return groups;
  }, [data?.leads, hiddenLeads, sortLeadsByPhoneThenRecent]);

  // Achata para navegação por teclado (J/K) e shift+click. Inclui descartados
  // apenas quando o accordion está aberto (e a 2ª query carregou).
  const orderedLeads = useMemo(() => {
    return [
      ...groupedLeads.confirmados,
      ...groupedLeads.pendentes,
      ...(descartadosOpen ? groupedLeads.descartados : []),
    ];
  }, [groupedLeads, descartadosOpen]);

  // Todos os leads conhecidos (úteis + ocultos já carregados) para ações em lote.
  const allLeads = useMemo(
    () => [...groupedLeads.confirmados, ...groupedLeads.pendentes, ...groupedLeads.descartados],
    [groupedLeads],
  );

  const pageIds = useMemo(() => orderedLeads.map((l) => l.id), [orderedLeads]);
  const allSelectedOnPage = pageIds.length > 0 && pageIds.every((id) => selectedIds.has(id));
  const someSelectedOnPage = pageIds.some((id) => selectedIds.has(id));

  const togglePageSelection = useCallback(() => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allSelectedOnPage) {
        for (const id of pageIds) next.delete(id);
      } else {
        for (const id of pageIds) next.add(id);
      }
      return next;
    });
    lastSelectedIndexRef.current = null;
  }, [allSelectedOnPage, pageIds]);

  const toggleLeadSelection = useCallback(
    (leadId: number, index: number, shiftKey: boolean) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        const lastIdx = lastSelectedIndexRef.current;
        if (shiftKey && lastIdx !== null && lastIdx !== index) {
          const [start, end] = lastIdx < index ? [lastIdx, index] : [index, lastIdx];
          const shouldSelect = !next.has(leadId);
          for (let i = start; i <= end; i++) {
            const id = pageIds[i];
            if (id === undefined) continue;
            if (shouldSelect) next.add(id);
            else next.delete(id);
          }
        } else if (next.has(leadId)) {
          next.delete(leadId);
        } else {
          next.add(leadId);
        }
        return next;
      });
      lastSelectedIndexRef.current = index;
    },
    [pageIds],
  );

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
    lastSelectedIndexRef.current = null;
  }, []);

  const handleConfirmBulkNoContact = useCallback(async () => {
    if (selectedIds.size === 0) {
      setConfirmBulkNoContact(false);
      return;
    }
    const ids = Array.from(selectedIds);
    try {
      const res = await bulkUpdateStatus.mutateAsync({ ids, status: 'nao_entrou_em_contato' });
      const updated = res?.updated ?? 0;
      const skipped = res?.skipped ?? 0;
      if (updated === 0 && skipped > 0) {
        showError(
          `Nenhum lead atualizado: ${skipped} ignorado${skipped === 1 ? '' : 's'} ` +
            'por transição não permitida.',
        );
      } else {
        success(
          `${updated} lead${updated === 1 ? '' : 's'} marcado${updated === 1 ? '' : 's'} como não contatou` +
            (skipped ? ` (${skipped} ignorado${skipped === 1 ? '' : 's'})` : ''),
        );
      }
      clearSelection();
      setConfirmBulkNoContact(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro na ação em lote';
      showError(message);
    }
  }, [bulkUpdateStatus, clearSelection, selectedIds, showError, success]);

  const openBulkDisqualify = useCallback(() => {
    // Prefill phoneEdits com phones atuais dos selecionados.
    // Usa allLeads (não orderedLeads) para incluir descartados/ocultos que
    // possam ter sido selecionados antes do accordion ser fechado.
    const edits: Record<number, string> = {};
    for (const lead of allLeads) {
      if (selectedIds.has(lead.id)) {
        edits[lead.id] = lead.phone ?? '';
      }
    }
    setPhoneEdits(edits);
    setBulkDisqualifyOpen(true);
  }, [allLeads, selectedIds]);

  const handleConfirmBulkDisqualify = useCallback(async () => {
    const eligibleLeads = allLeads.filter(
      (l) => selectedIds.has(l.id) && l.status !== 'whatsapp_iniciado' && l.status !== 'compra_realizada',
    );
    if (eligibleLeads.length === 0) {
      setBulkDisqualifyOpen(false);
      return;
    }
    const updates = eligibleLeads.map((lead) => {
      const phone = (phoneEdits[lead.id] ?? '').trim();
      return phone ? { id: lead.id, phone } : { id: lead.id };
    });
    try {
      const res = await bulkDisqualifyLeads.mutateAsync({ updates });
      const updated = res?.updated ?? 0;
      const skipped = res?.skipped ?? 0;
      // Conta também os leads que filtramos antes (whatsapp_iniciado / compra_realizada)
      // — eles "foram pulados" do ponto de vista do operador.
      const skippedClient = selectedIds.size - eligibleLeads.length;
      const totalSkipped = skipped + skippedClient;
      if (updated === 0) {
        showError(
          `Nenhum lead desqualificado${totalSkipped ? ` (${totalSkipped} ignorado${totalSkipped === 1 ? '' : 's'})` : ''}.`,
        );
      } else {
        success(
          `${updated} lead${updated === 1 ? '' : 's'} desqualificado${updated === 1 ? '' : 's'}` +
            (totalSkipped ? ` (${totalSkipped} ignorado${totalSkipped === 1 ? '' : 's'})` : ''),
        );
      }
      clearSelection();
      setPhoneEdits({});
      setBulkDisqualifyOpen(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao desqualificar leads';
      showError(message);
    }
  }, [
    bulkDisqualifyLeads,
    clearSelection,
    allLeads,
    phoneEdits,
    selectedIds,
    showError,
    success,
  ]);

  // Recalc da idade SLA a cada 30s sem reload — força re-render para chip de cor mudar.
  useEffect(() => {
    const t = window.setInterval(() => forceTick((n) => (n + 1) % 1_000_000), 30_000);
    return () => window.clearInterval(t);
  }, []);

  // Atalhos de teclado (desktop apenas):
  //   Ctrl+A: selecionar página · Esc: limpar foco/seleção
  //   J/K: navegar · Enter: abrir WhatsApp do focado · ?: cheatsheet
  useEffect(() => {
    if (isMobile) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      const isTypingInField =
        tag === 'input' || tag === 'textarea' || target?.isContentEditable;

      if ((e.ctrlKey || e.metaKey) && (e.key === 'a' || e.key === 'A')) {
        if (isTypingInField) return;
        if (pageIds.length === 0) return;
        e.preventDefault();
        setSelectedIds(new Set(pageIds));
        return;
      }

      if (e.key === 'Escape') {
        if (selectedIds.size > 0) clearSelection();
        if (focusedId !== null) setFocusedId(null);
        return;
      }

      if (isTypingInField) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        e.preventDefault();
        setCheatsheetOpen((open) => !open);
        return;
      }

      if (orderedLeads.length === 0) return;

      if (e.key === 'j' || e.key === 'J') {
        e.preventDefault();
        const currentIdx = focusedId !== null
          ? orderedLeads.findIndex((l) => l.id === focusedId)
          : -1;
        const nextIdx = Math.min(currentIdx + 1, orderedLeads.length - 1);
        const next = orderedLeads[nextIdx];
        if (next) {
          setFocusedId(next.id);
          rowRefs.current.get(next.id)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
        return;
      }

      if (e.key === 'k' || e.key === 'K') {
        e.preventDefault();
        const currentIdx = focusedId !== null
          ? orderedLeads.findIndex((l) => l.id === focusedId)
          : orderedLeads.length;
        const prevIdx = Math.max(currentIdx - 1, 0);
        const prev = orderedLeads[prevIdx];
        if (prev) {
          setFocusedId(prev.id);
          rowRefs.current.get(prev.id)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
        return;
      }

      if (e.key === 'Enter' && focusedId !== null) {
        const lead = orderedLeads.find((l) => l.id === focusedId);
        if (!lead?.phone) return;
        const url = buildWhatsAppUrl(lead.phone);
        if (!url) return;
        e.preventDefault();
        setLoadingWhatsAppId(lead.id);
        window.setTimeout(() => {
          setLoadingWhatsAppId(null);
          window.open(url, '_blank', 'noopener,noreferrer');
        }, 200);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [clearSelection, isMobile, pageIds, selectedIds.size, orderedLeads, focusedId]);

  if (isLoading) return <Loading />;
  if (error) return <ErrorState message="Erro ao carregar leads" onRetry={refetch} />;

  const today = statsData?.today;
  const last14d = statsData?.last_14d;
  const period: LeadsPeriod = filters.period ?? 'custom';
  // Modo "Dia" é UI-only: mapeia para period=custom com date_from === date_to.
  const isDayMode =
    period === 'custom' &&
    !!filters.date_from &&
    filters.date_from === filters.date_to;
  const periodUiValue: PeriodUiValue = isDayMode ? 'day' : period;
  const selectedDayLabel =
    isDayMode && filters.date_from ? dayjs(filters.date_from).format('DD/MM') : null;

  return (
    <Box sx={{ p: { xs: 2, md: 3 }, pb: selectedIds.size > 0 ? 12 : { xs: 2, md: 3 } }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        spacing={{ xs: 1, sm: 2 }}
        sx={{ mb: 3 }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <CampaignIcon color="primary" />
          <Typography variant="h5" fontWeight={600}>
            Leads UTM
          </Typography>
        </Stack>
        {statsData ? (
          <Stack spacing={0.25} sx={{ ml: { sm: 2 } }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Hoje:</strong> {today?.pendentes ?? 0} pendentes · {today?.confirmados ?? 0}{' '}
              confirmados · {today?.compras ?? 0} compras
            </Typography>
            <Typography variant="body2" color="text.secondary">
              <strong>14 dias:</strong> {last14d?.pendentes ?? 0} pendentes ·{' '}
              {last14d?.confirmados ?? 0} confirmados · {last14d?.compras ?? 0} compras
            </Typography>
          </Stack>
        ) : (
          <Chip label={`${total} cliques`} size="small" />
        )}
      </Stack>

      {/* Filtros */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack spacing={1.5}>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1.5}
            alignItems={{ xs: 'stretch', sm: 'center' }}
            flexWrap="wrap"
          >
            <ToggleButtonGroup
              value={periodUiValue}
              exclusive
              size="small"
              onChange={(_e, v: PeriodUiValue | null) => {
                if (!v) return;
                if (v === 'day') {
                  setDayPickerOpen(true);
                  return;
                }
                setPeriod(v);
              }}
            >
              <ToggleButton value="today">Hoje</ToggleButton>
              <ToggleButton value="14d">14 dias</ToggleButton>
              <ToggleButton value="all">Tudo</ToggleButton>
              <ToggleButton value="day">
                {selectedDayLabel ? `Dia (${selectedDayLabel})` : 'Dia'}
              </ToggleButton>
              <ToggleButton value="custom">Personalizado</ToggleButton>
            </ToggleButtonGroup>
            {isDayMode ? (
              <Tooltip title="Trocar dia">
                <IconButton size="small" onClick={() => setDayPickerOpen(true)}>
                  <EditCalendarIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            ) : null}

            <Box sx={{ flexGrow: 1 }} />

            {!isMobile ? (
              <Tooltip title="Atalhos de teclado (?)">
                <IconButton size="small" onClick={() => setCheatsheetOpen(true)}>
                  <KeyboardIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            ) : null}
          </Stack>

          {period === 'custom' && !isDayMode ? (
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
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
          ) : null}

          <Accordion disableGutters elevation={0} sx={{ '&:before': { display: 'none' } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 0 }}>
              <Typography variant="body2" color="text.secondary">
                Filtros +
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ px: 0 }}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} flexWrap="wrap">
                <FormControl size="small" sx={{ minWidth: 160 }}>
                  <InputLabel>Evento</InputLabel>
                  <Select
                    value={filters.event ?? 'whatsapp_click'}
                    label="Evento"
                    onChange={(e) => {
                      const v = e.target.value;
                      setFilters((prev) => {
                        const next: LeadsFilters = { ...prev, page: 1 };
                        delete next.events;
                        next.event = v;
                        return next;
                      });
                    }}
                  >
                    <MenuItem value="whatsapp_click">{EVENT_LABELS.whatsapp_click}</MenuItem>
                    <MenuItem value="site_click">{EVENT_LABELS.site_click}</MenuItem>
                    <MenuItem value="all">Todos</MenuItem>
                  </Select>
                </FormControl>

                <FormControl size="small" sx={{ minWidth: 190 }}>
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={filters.status ?? ''}
                    label="Status"
                    onChange={(e) =>
                      setFilters((f) => ({ ...f, status: e.target.value || undefined, page: 1 }))
                    }
                  >
                    <MenuItem value="">Todos</MenuItem>
                    <MenuItem value="pendente_whatsapp">P. Whatsapp (Contact)</MenuItem>
                    <MenuItem value="whatsapp_iniciado">Lead Confirmado</MenuItem>
                    <MenuItem value="compra_realizada">Compra realizada</MenuItem>
                    <MenuItem value="nao_entrou_em_contato">Não entrou em contato</MenuItem>
                    <MenuItem value="descarte">Lead Desqualificado</MenuItem>
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
                  label="Código (token)"
                  placeholder="ex.: A3F9B7K20K"
                  value={filters.token_rastreio ?? ''}
                  onChange={(e) =>
                    setFilters((f) => ({
                      ...f,
                      token_rastreio: e.target.value.trim() || undefined,
                      page: 1,
                    }))
                  }
                  sx={{ minWidth: 160 }}
                />
              </Stack>
            </AccordionDetails>
          </Accordion>
        </Stack>
      </Paper>

      {/* Cards (mobile) */}
      {isMobile ? (
        <Box>
          {allLeads.length === 0 && hiddenCount === 0 ? (
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Nenhum lead encontrado
              </Typography>
            </Paper>
          ) : (
            <Stack spacing={1.5}>
              {GROUP_ORDER.map((groupName) => {
                const list = groupedLeads[groupName];
                const isDescartados = groupName === 'descartados';
                // Descartados aparecem se há ocultos na janela (mesmo sem fetch ainda).
                if (isDescartados ? hiddenCount === 0 : list.length === 0) return null;
                const renderCard = (lead: Lead) => {
                  const index = orderedLeads.findIndex((l) => l.id === lead.id);
                  const isSelected = selectedIds.has(lead.id);
                  const noPhonePending = !lead.phone && lead.status === 'pendente_whatsapp';
                  const longPressTimer = { current: null as null | number };
                  const beginLongPress = () => {
                    longPressTimer.current = window.setTimeout(() => {
                      toggleLeadSelection(lead.id, index, false);
                    }, 450);
                  };
                  const cancelLongPress = () => {
                    if (longPressTimer.current !== null) {
                      window.clearTimeout(longPressTimer.current);
                      longPressTimer.current = null;
                    }
                  };
                  return (
                    <Card
                      key={lead.id}
                      variant="outlined"
                      onTouchStart={beginLongPress}
                      onTouchEnd={cancelLongPress}
                      onTouchMove={cancelLongPress}
                      onTouchCancel={cancelLongPress}
                      sx={{
                        borderRadius: '4px',
                        borderLeftWidth: '3px',
                        borderLeftColor: ageBorderColor(lead, theme),
                        backgroundColor: isSelected
                          ? theme.palette.action.selected
                          : noPhonePending
                            ? theme.palette.action.hover
                            : undefined,
                      }}
                    >
                  <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                    {/* Linha 1: Checkbox + Status (ação principal) + ações */}
                    <Stack
                      direction="row"
                      spacing={1}
                      alignItems="center"
                      justifyContent="space-between"
                      sx={{ mb: 1 }}
                    >
                      <Checkbox
                        size="medium"
                        checked={isSelected}
                        onChange={() => toggleLeadSelection(lead.id, index, false)}
                        sx={{ p: 0.5, mr: -0.5 }}
                        inputProps={{ 'aria-label': `Selecionar lead ${lead.id}` }}
                      />
                      {canEditLeadPhone(lead) ? (
                        <Stack direction="row" spacing={0.5} alignItems="center" sx={{ flexGrow: 1, minWidth: 0 }}>
                          <Chip
                            size="medium"
                            color={leadStatusColor(lead.status)}
                            label={leadStatusLabel(lead.status)}
                            variant="filled"
                            clickable
                            onClick={() => handleOpenPhoneDialog(lead)}
                            sx={{ fontWeight: 600, borderRadius: '4px' }}
                          />
                          {lead.status === 'pendente_whatsapp' ? (
                            <IconButton
                              size="small"
                              aria-label="Ações do status"
                              onClick={(e) => handleOpenStatusMenu(e, lead)}
                            >
                              <MoreVertIcon fontSize="small" />
                            </IconButton>
                          ) : null}
                        </Stack>
                      ) : (
                        <Chip
                          size="medium"
                          color={leadStatusColor(lead.status)}
                          label={leadStatusLabel(lead.status)}
                          variant={lead.status ? 'filled' : 'outlined'}
                          sx={{ fontWeight: 600, borderRadius: '4px' }}
                        />
                      )}
                      <Stack direction="row" spacing={0.5} alignItems="center" sx={{ ml: 'auto' }}>
                        <AgeChip lead={lead} />
                        {lead.phone ? (
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
                        ) : (
                          <IconButton size="small" disabled>
                            <WhatsAppIcon fontSize="small" />
                          </IconButton>
                        )}
                        {lead.pedido_id ? (
                          <IconButton
                            size="small"
                            color="secondary"
                            onClick={() => handleViewOrder(lead.pedido_id!)}
                          >
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
                        ) : lead.status === 'compra_realizada' ? (
                          <IconButton size="small" disabled>
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
                        ) : (
                          <IconButton size="small" color="primary" onClick={(e) => openCreateModeMenu(e, lead)}>
                            <AddShoppingCartIcon fontSize="small" />
                          </IconButton>
                        )}
                      </Stack>
                    </Stack>

                    {/* Linha 2: telefone + valor */}
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: 'wrap' }}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {lead.phone ?? 'Sem telefone'}
                      </Typography>
                      {lead.valor_pedido ? (
                        <Chip
                          size="small"
                          label={lead.valor_pedido}
                          color="success"
                          variant="outlined"
                          sx={{ borderRadius: '4px' }}
                        />
                      ) : null}
                    </Stack>

                    <Divider sx={{ my: 1 }} />

                    {/* Linha 3: metadados secundários */}
                    <Stack spacing={0.5}>
                      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(lead.created_at)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">·</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatEventLabel(lead.event)}
                        </Typography>
                        {lead.token_rastreio ? (
                          <>
                            <Typography variant="caption" color="text.secondary">·</Typography>
                            <Typography
                              variant="caption"
                              sx={{ fontFamily: 'monospace' }}
                              color="text.secondary"
                            >
                              {lead.token_rastreio}
                            </Typography>
                          </>
                        ) : null}
                      </Stack>
                      <Stack direction="row" spacing={0.5} alignItems="center" flexWrap="wrap">
                        {lead.utm_source ? (
                          <Chip label={lead.utm_source} size="small" color={sourceColor(lead.utm_source)} sx={{ borderRadius: '4px' }} />
                        ) : null}
                        {lead.utm_campaign ? (
                          <Typography variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>
                            {lead.utm_campaign}
                          </Typography>
                        ) : null}
                        {lead.utm_term ? (
                          <Typography variant="caption" color="text.secondary">
                            · {displayAdSet(lead.utm_term)}
                          </Typography>
                        ) : null}
                      </Stack>
                    </Stack>
                      </CardContent>
                    </Card>
                  );
                };

                const header = (
                  <Box
                    sx={{
                      px: 0.5,
                      pt: 1,
                      pb: 0.5,
                      borderTop: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ fontWeight: 500 }}
                    >
                      {GROUP_LABELS[groupName]} ({list.length})
                    </Typography>
                  </Box>
                );

                if (isDescartados) {
                  return (
                    <Accordion
                      key={groupName}
                      expanded={descartadosOpen}
                      onChange={(_e, exp) => setDescartadosOpen(exp)}
                      disableGutters
                      elevation={0}
                      sx={{
                        '&:before': { display: 'none' },
                        borderTop: '1px solid',
                        borderColor: 'divider',
                      }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 0.5 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                          {GROUP_LABELS[groupName]} ({hiddenCount})
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails sx={{ px: 0 }}>
                        {hiddenLoading && list.length === 0 ? (
                          <Box sx={{ py: 2 }}><Loading /></Box>
                        ) : (
                          <Stack spacing={1.5}>{list.map(renderCard)}</Stack>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  );
                }
                return (
                  <Fragment key={groupName}>
                    {header}
                    {list.map(renderCard)}
                  </Fragment>
                );
              })}
            </Stack>
          )}

          <Paper sx={{ mt: 1.5 }}>
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
          </Paper>
        </Box>
      ) : (
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  size="small"
                  indeterminate={someSelectedOnPage && !allSelectedOnPage}
                  checked={allSelectedOnPage}
                  onChange={togglePageSelection}
                  inputProps={{ 'aria-label': 'Selecionar todos da página' }}
                />
              </TableCell>
              <TableCell align="center">Ação</TableCell>
              <TableCell>Data (BRT)</TableCell>
              <TableCell>Idade</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Telefone</TableCell>
              <TableCell>Valor Pedido</TableCell>
              <TableCell>Código WhatsApp</TableCell>
              <TableCell>Token válido</TableCell>
              <TableCell>Evento</TableCell>
              <TableCell>Origem</TableCell>
              <TableCell>Campanha</TableCell>
              <TableCell>Grupo de Anúncio</TableCell>
              <TableCell>Conteúdo</TableCell>
              <TableCell>Meio</TableCell>
            </TableRow>
          </TableHead>
          {allLeads.length === 0 && hiddenCount === 0 ? (
            <TableBody>
              <TableRow>
                <TableCell colSpan={15} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 4 }}>
                    Nenhum lead encontrado
                  </Typography>
                </TableCell>
              </TableRow>
            </TableBody>
          ) : null}
          {GROUP_ORDER.map((groupName) => {
            const list = groupedLeads[groupName];
            const isDescartados = groupName === 'descartados';
            if (isDescartados ? hiddenCount === 0 : list.length === 0) return null;
            const collapsed = isDescartados && !descartadosOpen;
            const headerCount = isDescartados ? hiddenCount : list.length;
            return (
              <TableBody key={groupName}>
                <TableRow
                  sx={{
                    backgroundColor: isDescartados ? 'transparent' : theme.palette.background.default,
                  }}
                >
                  <TableCell
                    colSpan={15}
                    sx={{
                      borderTop: `1px solid ${theme.palette.divider}`,
                      borderBottom: 0,
                      py: 0.5,
                      cursor: isDescartados ? 'pointer' : 'default',
                    }}
                    onClick={() => {
                      if (isDescartados) setDescartadosOpen((v) => !v);
                    }}
                  >
                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      {isDescartados ? (
                        <ExpandMoreIcon
                          fontSize="small"
                          sx={{
                            color: 'text.secondary',
                            transform: descartadosOpen ? 'rotate(180deg)' : 'rotate(0)',
                            transition: 'transform 150ms',
                          }}
                        />
                      ) : null}
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
                        {GROUP_LABELS[groupName]} ({headerCount})
                      </Typography>
                    </Stack>
                  </TableCell>
                </TableRow>
                {collapsed ? null : isDescartados && hiddenLoading && list.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={15} align="center">
                      <Box sx={{ py: 2 }}><Loading /></Box>
                    </TableCell>
                  </TableRow>
                ) : (
                  list.map((lead) => {
                      const index = orderedLeads.findIndex((l) => l.id === lead.id);
                      const isSelected = selectedIds.has(lead.id);
                      const noPhonePending = !lead.phone && lead.status === 'pendente_whatsapp';
                      const isFocused = focusedId === lead.id;
                      return (
                <TableRow
                  key={lead.id}
                  ref={(el: HTMLTableRowElement | null) => {
                    if (el) rowRefs.current.set(lead.id, el);
                    else rowRefs.current.delete(lead.id);
                  }}
                  hover
                  selected={isSelected}
                  onClick={() => setFocusedId(lead.id)}
                  sx={{
                    borderLeft: isFocused
                      ? `3px solid ${theme.palette.primary.main}`
                      : `3px solid ${ageBorderColor(lead, theme)}`,
                    backgroundColor: noPhonePending && !isSelected ? theme.palette.action.hover : undefined,
                    '& > td': { borderRadius: 0 },
                  }}
                >
                  <TableCell padding="checkbox">
                    <Checkbox
                      size="small"
                      checked={isSelected}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleLeadSelection(lead.id, index, (e as unknown as MouseEvent).shiftKey);
                      }}
                      inputProps={{ 'aria-label': `Selecionar lead ${lead.id}` }}
                    />
                  </TableCell>
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
                            disabled={loadingWhatsAppId === lead.id}
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
                      {lead.pedido_id ? (
                        <Tooltip title="Visualizar pedido vinculado">
                          <IconButton
                            size="small"
                            color="secondary"
                            onClick={() => handleViewOrder(lead.pedido_id!)}
                          >
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      ) : lead.status === 'compra_realizada' ? (
                        <Tooltip title="Compra realizada — pedido não localizado">
                          <span>
                            <IconButton size="small" disabled>
                              <VisibilityIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      ) : (
                        <Tooltip title="Criar pedido a partir deste lead">
                          <IconButton size="small" color="primary" onClick={(e) => openCreateModeMenu(e, lead)}>
                            <AddShoppingCartIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {lead.status === 'pendente_whatsapp' ? (
                        <Tooltip title="Marcar como não contatou">
                          <IconButton
                            size="small"
                            color="default"
                            onClick={() => handleQuickMarkNoContact(lead)}
                            disabled={updateLeadStatus.isPending}
                          >
                            <CheckIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      ) : null}
                    </Stack>
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{formatDate(lead.created_at)}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    <AgeChip lead={lead} />
                  </TableCell>
                  <TableCell>
                    {canEditLeadPhone(lead) ? (
                      <Stack direction="row" spacing={0.5} alignItems="center">
                        <Tooltip title="Clique para informar o número correto">
                          <Chip
                            size="small"
                            color={leadStatusColor(lead.status)}
                            label={leadStatusLabel(lead.status)}
                            variant="filled"
                            clickable
                            onClick={() => handleOpenPhoneDialog(lead)}
                            sx={{ borderRadius: '4px' }}
                          />
                        </Tooltip>
                        {lead.status === 'pendente_whatsapp' ? (
                          <Tooltip title="Outras ações">
                            <IconButton
                              size="small"
                              aria-label="Ações do status"
                              onClick={(e) => handleOpenStatusMenu(e, lead)}
                            >
                              <MoreVertIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        ) : null}
                      </Stack>
                    ) : (
                      <Stack direction="row" spacing={0.5} alignItems="center">
                        <Chip
                          size="small"
                          color={leadStatusColor(lead.status)}
                          label={leadStatusLabel(lead.status)}
                          variant={lead.status ? 'filled' : 'outlined'}
                          sx={{ borderRadius: '4px' }}
                        />
                      </Stack>
                    )}
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{lead.phone ?? '—'}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {lead.valor_pedido ? (
                      <Chip
                        size="small"
                        label={lead.valor_pedido}
                        color="success"
                        variant="outlined"
                        sx={{ borderRadius: '4px' }}
                      />
                    ) : '—'}
                  </TableCell>
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
                        sx={{ borderRadius: '4px' }}
                      />
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell>{formatEventLabel(lead.event)}</TableCell>
                  <TableCell>
                    {lead.utm_source ? (
                      <Chip
                        label={lead.utm_source}
                        size="small"
                        color={sourceColor(lead.utm_source)}
                        sx={{ borderRadius: '4px' }}
                      />
                    ) : '—'}
                  </TableCell>
                  <TableCell>{lead.utm_campaign ?? '—'}</TableCell>
                  <TableCell>{displayAdSet(lead.utm_term)}</TableCell>
                  <TableCell>{lead.utm_content ?? '—'}</TableCell>
                  <TableCell>{lead.utm_medium ?? '—'}</TableCell>
                </TableRow>
                      );
                    })
                )}
              </TableBody>
            );
          })}
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
      )}

      <Dialog open={!!editingLead} onClose={handleClosePhoneDialog} fullWidth maxWidth="xs">
        <DialogTitle>Atualizar WhatsApp do lead</DialogTitle>
        <DialogContent>
          <FormControlLabel
            sx={{ mt: 0.5, mb: 0.5 }}
            control={
              <Checkbox
                checked={respondeuPrimeiraMensagem}
                onChange={(e) => setRespondeuPrimeiraMensagem(e.target.checked)}
              />
            }
            label="Respondeu primeira mensagem?"
          />
          <TextField
            margin="dense"
            label="Telefone/WhatsApp"
            placeholder="(62) 99999-0000"
            fullWidth
            disabled={!respondeuPrimeiraMensagem}
            helperText={
              respondeuPrimeiraMensagem
                ? undefined
                : 'Marque a confirmação acima para liberar o campo'
            }
            value={manualPhone}
            onChange={(e) => setManualPhone(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClosePhoneDialog} disabled={updateLeadPhone.isPending}>Cancelar</Button>
          <Button
            onClick={handleSavePhone}
            variant="contained"
            disabled={updateLeadPhone.isPending || !respondeuPrimeiraMensagem}
          >
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

      <Dialog
        open={confirmBulkNoContact}
        onClose={() => setConfirmBulkNoContact(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Marcar como não contatou?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {selectedIds.size} lead{selectedIds.size === 1 ? '' : 's'} serão atualizados. Leads sem
            transição válida serão ignorados.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmBulkNoContact(false)}
            disabled={bulkUpdateStatus.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={() => void handleConfirmBulkNoContact()}
            color="primary"
            variant="contained"
            disabled={bulkUpdateStatus.isPending}
          >
            Confirmar
          </Button>
        </DialogActions>
      </Dialog>

      <BulkDisqualifyDialog
        open={bulkDisqualifyOpen}
        onClose={() => setBulkDisqualifyOpen(false)}
        selectedLeads={allLeads.filter((l) => selectedIds.has(l.id))}
        phoneEdits={phoneEdits}
        onPhoneChange={(id, phone) => setPhoneEdits((prev) => ({ ...prev, [id]: phone }))}
        onConfirm={() => void handleConfirmBulkDisqualify()}
        pending={bulkDisqualifyLeads.isPending}
      />

      {selectedIds.size > 0 ? (
        <Paper
          elevation={6}
          sx={{
            position: 'fixed',
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: (t) => t.zIndex.appBar + 1,
            px: { xs: 1.5, sm: 2 },
            py: 1.25,
            paddingBottom: 'calc(10px + env(safe-area-inset-bottom))',
            borderRadius: 0,
            borderTop: 1,
            borderColor: 'divider',
          }}
        >
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1.25}
            alignItems={{ xs: 'stretch', sm: 'center' }}
            justifyContent="space-between"
          >
            <Typography
              variant="body2"
              sx={{ fontWeight: 600, textAlign: { xs: 'center', sm: 'left' } }}
            >
              {selectedIds.size} lead{selectedIds.size === 1 ? '' : 's'} selecionado
              {selectedIds.size === 1 ? '' : 's'}
            </Typography>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1}
              sx={{ width: { xs: '100%', sm: 'auto' } }}
            >
              <Button
                size="medium"
                variant="contained"
                color="error"
                startIcon={<PersonOffIcon />}
                onClick={openBulkDisqualify}
                disabled={bulkUpdateStatus.isPending || bulkDisqualifyLeads.isPending}
                fullWidth={isMobile}
                sx={{
                  borderRadius: '4px',
                  minHeight: 44,
                  textTransform: 'none',
                  fontWeight: 600,
                }}
              >
                Desqualificar
              </Button>
              <Button
                size="medium"
                variant="outlined"
                startIcon={<PhoneDisabledIcon />}
                onClick={() => setConfirmBulkNoContact(true)}
                disabled={bulkUpdateStatus.isPending || bulkDisqualifyLeads.isPending}
                fullWidth={isMobile}
                sx={{
                  borderRadius: '4px',
                  minHeight: 44,
                  textTransform: 'none',
                }}
              >
                Não contatou
              </Button>
              <Button
                size="medium"
                onClick={clearSelection}
                disabled={bulkUpdateStatus.isPending || bulkDisqualifyLeads.isPending}
                fullWidth={isMobile}
                sx={{ borderRadius: '4px', minHeight: 44, textTransform: 'none' }}
              >
                Limpar
              </Button>
            </Stack>
          </Stack>
        </Paper>
      ) : null}

      <KeyboardCheatsheet
        open={cheatsheetOpen}
        onClose={() => setCheatsheetOpen(false)}
      />

      {dayPickerOpen ? (
        <DayPickerDialog
          initialDate={filters.date_from ? dayjs(filters.date_from) : dayjs()}
          onClose={() => setDayPickerOpen(false)}
          onConfirm={(d) => {
            const iso = d.format('YYYY-MM-DD');
            setFilters((f) => ({
              ...f,
              period: 'custom',
              date_from: iso,
              date_to: iso,
              page: 1,
            }));
            setDayPickerOpen(false);
          }}
        />
      ) : null}

      <QuickEntryModal
        open={quickEntryOpen}
        lead={createModeLead}
        onClose={() => {
          setQuickEntryOpen(false);
          setCreateModeLead(null);
        }}
      />

      <Menu
        anchorEl={createModeAnchor}
        open={Boolean(createModeAnchor)}
        onClose={() => {
          setCreateModeAnchor(null);
          setCreateModeLead(null);
        }}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <MenuItem
          onClick={() => {
            setCreateModeAnchor(null);
            setQuickEntryOpen(true);
          }}
        >
          <BoltIcon fontSize="small" sx={{ mr: 1, color: 'warning.main' }} />
          Preenchimento rápido
        </MenuItem>
        <MenuItem
          onClick={() => {
            const lead = createModeLead;
            setCreateModeAnchor(null);
            setCreateModeLead(null);
            if (lead) handleCreateOrder(lead);
          }}
        >
          <AddShoppingCartIcon fontSize="small" sx={{ mr: 1 }} />
          Preenchimento normal
        </MenuItem>
      </Menu>

    </Box>
  );
}

interface BulkDisqualifyDialogProps {
  open: boolean;
  onClose: () => void;
  selectedLeads: Lead[];
  phoneEdits: Record<number, string>;
  onPhoneChange: (id: number, phone: string) => void;
  onConfirm: () => void;
  pending: boolean;
}

function isLeadConfirmedTerminal(status: string | null): boolean {
  return status === 'whatsapp_iniciado' || status === 'compra_realizada';
}

function isPhoneValidOrEmpty(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) return true;
  const digits = trimmed.replace(/\D/g, '');
  return digits.length >= 10;
}

function BulkDisqualifyDialog({
  open,
  onClose,
  selectedLeads,
  phoneEdits,
  onPhoneChange,
  onConfirm,
  pending,
}: BulkDisqualifyDialogProps) {
  const eligible = selectedLeads.filter((l) => !isLeadConfirmedTerminal(l.status));
  const skippedCount = selectedLeads.length - eligible.length;
  const hasInvalidPhone = eligible.some(
    (l) => !isPhoneValidOrEmpty(phoneEdits[l.id] ?? ''),
  );
  const canConfirm = !pending && eligible.length > 0 && !hasInvalidPhone;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Desqualificar leads selecionados ({selectedLeads.length})</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          Esta ação dispara o evento <strong>LeadDisqualified</strong> para a Meta. Para melhorar o
          match, preencha o telefone se conhecer.
        </DialogContentText>
        {skippedCount > 0 ? (
          <DialogContentText sx={{ mb: 2, color: 'warning.main' }}>
            ⚠ {skippedCount} lead{skippedCount === 1 ? '' : 's'} em &quot;Lead Confirmado&quot; ser
            {skippedCount === 1 ? 'á' : 'ão'} ignorado{skippedCount === 1 ? '' : 's'} (terminal).
          </DialogContentText>
        ) : null}
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Status</TableCell>
                <TableCell>Token</TableCell>
                <TableCell sx={{ minWidth: 180 }}>Número</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {selectedLeads.map((lead) => {
                const isSkipped = isLeadConfirmedTerminal(lead.status);
                const phoneValue = phoneEdits[lead.id] ?? '';
                const phoneError = !isPhoneValidOrEmpty(phoneValue);
                return (
                  <TableRow key={lead.id} sx={{ opacity: isSkipped ? 0.5 : 1 }}>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} alignItems="center">
                        <Chip
                          size="small"
                          color={leadStatusColor(lead.status)}
                          label={leadStatusLabel(lead.status)}
                          variant={lead.status ? 'filled' : 'outlined'}
                        />
                        {isSkipped ? (
                          <Tooltip title="Ignorado: já está em Lead Confirmado (terminal)">
                            <Typography variant="caption" sx={{ ml: 0.5 }}>⊘</Typography>
                          </Tooltip>
                        ) : null}
                      </Stack>
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                      {lead.token_rastreio ?? '—'}
                    </TableCell>
                    <TableCell>
                      {isSkipped ? (
                        <Typography variant="body2" color="text.secondary">—</Typography>
                      ) : (
                        <TextField
                          size="small"
                          fullWidth
                          placeholder="(62) 99999-0000"
                          value={phoneValue}
                          onChange={(e) => onPhoneChange(lead.id, e.target.value)}
                          error={phoneError}
                          helperText={phoneError ? 'Telefone inválido' : undefined}
                          disabled={pending}
                        />
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={pending}>
          Cancelar
        </Button>
        <Button
          onClick={onConfirm}
          color="error"
          variant="contained"
          disabled={!canConfirm}
        >
          Alterar
        </Button>
      </DialogActions>
    </Dialog>
  );
}

interface DayPickerDialogProps {
  initialDate: Dayjs;
  onClose: () => void;
  onConfirm: (date: Dayjs) => void;
}

/**
 * Renderizar apenas quando aberto (`{open ? <DayPickerDialog/> : null}`).
 * Sem `open` prop interno — o estado `value` é inicializado uma única vez,
 * no mount, a partir de `initialDate`.
 */
function DayPickerDialog({ initialDate, onClose, onConfirm }: DayPickerDialogProps) {
  const [value, setValue] = useState<Dayjs | null>(initialDate);

  return (
    <Dialog open onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Escolha o dia</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          <DatePicker
            value={value}
            onChange={(d) => setValue(d)}
            slotProps={{ textField: { fullWidth: true } }}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancelar</Button>
        <Button
          variant="contained"
          disabled={!value || !value.isValid()}
          onClick={() => value && onConfirm(value)}
        >
          Aplicar
        </Button>
      </DialogActions>
    </Dialog>
  );
}
