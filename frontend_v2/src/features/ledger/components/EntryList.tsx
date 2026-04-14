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

// Agrupa entries por week_ref
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

function categoryLabel(category: string): string {
  const labels: Record<string, string> = {
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
  return labels[category] ?? category;
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
              {weekEntries.map((entry) => (
                <ListItem key={entry.id} disableGutters sx={{ px: 0.5 }}>
                  <ListItemText
                    primary={
                      <Box display="flex" justifyContent="space-between" alignItems="center">
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
                        <Chip
                          size="small"
                          label={`${entry.type === 'CREDIT' ? '+' : '-'} ${formatBRL(entry.amount)}`}
                          color={entry.type === 'CREDIT' ? 'success' : 'error'}
                          variant="outlined"
                          sx={{ fontWeight: 600 }}
                        />
                      </Box>
                    }
                    secondary={entry.description || undefined}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        );
      })}
    </Box>
  );
}
