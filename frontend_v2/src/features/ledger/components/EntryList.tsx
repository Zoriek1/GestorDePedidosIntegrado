import {
  Box,
  Typography,
  Divider,
  List,
  ListItem,
  ListItemText,
  Chip,
  Skeleton,
} from '@mui/material';
import { formatBRL } from '../../../lib/format/currency';
import { LedgerEntry } from '../services/ledgerApi';

interface EntryListProps {
  entries: LedgerEntry[];
  loading?: boolean;
}

function groupByWeek(entries: LedgerEntry[]): Map<string, LedgerEntry[]> {
  const map = new Map<string, LedgerEntry[]>();
  for (const e of entries) {
    const key = e.week_ref;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(e);
  }
  return map;
}

function weekLabel(weekRef: string): string {
  if (!weekRef) return '';
  const d = new Date(weekRef + 'T00:00:00');
  const end = new Date(d);
  end.setDate(d.getDate() + 6);
  const fmt = (dt: Date) =>
    dt.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  return `Semana ${fmt(d)} – ${fmt(end)}`;
}

const CATEGORY_LABELS: Record<string, string> = {
  fixo_semanal: 'Salário Semanal',
  fixo_mensal: 'Salário Mensal',
  almoco: 'Vale Almoço',
  transporte: 'Vale Transporte',
  comissao_whatsapp: 'Comissão WhatsApp',
  comissao_site: 'Comissão Site',
  comissao_balcao: 'Comissão Balcão',
  comissao_indicacao: 'Comissão Indicação',
  comissao_lucro: 'Comissão Lucro',
  custom_credit: 'Crédito Avulso',
  pagamento: 'Pagamento',
  adiantamento: 'Adiantamento',
  ajuste_debito: 'Ajuste Débito',
};

function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

function getCreditStatus(entry: LedgerEntry): {
  label: string;
  color: 'success' | 'warning' | 'error' | 'default';
} {
  if (entry.status === 'settled') {
    return { label: 'Quitado', color: 'success' };
  }
  if (!entry.due_date) {
    return { label: 'A receber', color: 'warning' };
  }

  const due = new Date(entry.due_date + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  if (due.getTime() < today.getTime()) {
    return { label: 'Atrasado', color: 'error' };
  }
  if (due.getTime() === today.getTime()) {
    return { label: 'Hoje', color: 'warning' };
  }
  return { label: 'A receber', color: 'default' };
}

function settledInfo(entry: LedgerEntry): string | null {
  if (entry.status !== 'settled' || entry.type !== 'CREDIT') return null;
  const parts: string[] = [];
  if (entry.settled_at) {
    const d = new Date(entry.settled_at);
    parts.push(`Quitado em ${d.toLocaleDateString('pt-BR')}`);
  }
  if (entry.settled_by_id) {
    parts.push(`ref. pagamento #${entry.settled_by_id}`);
  }
  return parts.length ? parts.join(' · ') : null;
}

export function EntryList({ entries, loading }: EntryListProps) {
  if (loading) {
    return (
      <Box>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} variant="rectangular" height={48} sx={{ mb: 1, borderRadius: 1 }} />
        ))}
      </Box>
    );
  }

  if (!entries.length) {
    return (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
        Nenhum lançamento encontrado.
      </Typography>
    );
  }

  const grouped = groupByWeek(entries);

  return (
    <Box>
      {Array.from(grouped.entries()).map(([week, weekEntries]) => {
        const weekTotal = weekEntries.reduce(
          (acc, e) => acc + (e.type === 'CREDIT' ? e.amount : -e.amount),
          0
        );

        return (
          <Box key={week} mb={2}>
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              sx={{ py: 1, px: 0.5 }}
            >
              <Typography variant="subtitle2" color="text.secondary">
                {weekLabel(week)}
              </Typography>
              <Typography
                variant="subtitle2"
                fontWeight={600}
                color={weekTotal >= 0 ? 'success.main' : 'error.main'}
              >
                {weekTotal >= 0 ? '+' : ''}{formatBRL(weekTotal)}
              </Typography>
            </Box>
            <Divider />
            <List dense disablePadding>
              {weekEntries.map((entry) => {
                const creditStatus = getCreditStatus(entry);
                const settled = settledInfo(entry);

                return (
                  <ListItem key={entry.id} disableGutters sx={{ px: 0.5 }}>
                    <ListItemText
                      primary={
                        <Box display="flex" justifyContent="space-between" alignItems="center" gap={1}>
                          <Box display="flex" alignItems="center" gap={0.5} flexWrap="wrap">
                            <Typography variant="body2">
                              {categoryLabel(entry.category)}
                              {entry.pedido_id && (
                                <Typography
                                  component="span"
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{ ml: 0.5 }}
                                >
                                  #{entry.pedido_id}
                                </Typography>
                              )}
                            </Typography>
                            {entry.type === 'CREDIT' && (
                              <Chip
                                size="small"
                                label={creditStatus.label}
                                color={creditStatus.color}
                                variant="filled"
                                sx={{ height: 18, fontSize: '0.65rem' }}
                              />
                            )}
                          </Box>
                          <Chip
                            size="small"
                            label={`${entry.type === 'CREDIT' ? '+' : '-'} ${formatBRL(entry.amount)}`}
                            color={entry.type === 'CREDIT' ? 'success' : 'error'}
                            variant="outlined"
                            sx={{ fontWeight: 600, flexShrink: 0 }}
                          />
                        </Box>
                      }
                      secondary={
                        settled
                          ? settled
                          : entry.due_date
                          ? `${entry.description ? entry.description + ' · ' : ''}Vence ${new Date(entry.due_date + 'T00:00:00').toLocaleDateString('pt-BR')}`
                          : entry.description || undefined
                      }
                    />
                  </ListItem>
                );
              })}
            </List>
          </Box>
        );
      })}
    </Box>
  );
}
