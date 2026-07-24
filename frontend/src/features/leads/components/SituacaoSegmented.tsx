import { Box, Button, ToggleButton, ToggleButtonGroup, Tooltip, Select, MenuItem, useMediaQuery, useTheme } from '@mui/material';
import type { Lead } from '../../../api/endpoints/leads';
import { SITUACAO_VALUES, SITUACAO_LABELS, SITUACAO_CHIP_COLOR, type Situacao } from '../leadGrouping';

export function SituacaoSegmented({
  lead,
  busy,
  onSet,
  onFollowup,
}: {
  lead: Lead;
  busy: boolean;
  onSet: (lead: Lead, situacao: Situacao) => void;
  onFollowup: (lead: Lead) => void;
}) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  if (lead.status !== 'whatsapp_iniciado') return null;
  const current = (lead.situacao ?? 'aguardando_resposta') as Situacao;

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
      {isMobile ? (
        <Select
          size="small"
          value={current}
          onChange={(e) => onSet(lead, e.target.value as Situacao)}
          disabled={busy}
          sx={{ minWidth: 140, fontSize: '0.813rem' }}
        >
          {SITUACAO_VALUES.map((s) => (
            <MenuItem key={s} value={s}>
              {SITUACAO_LABELS[s]}
            </MenuItem>
          ))}
        </Select>
      ) : (
        <ToggleButtonGroup
          size="small"
          exclusive
          value={current}
          onChange={(_e, val) => {
            if (val) onSet(lead, val as Situacao);
          }}
          sx={{ flexShrink: 0 }}
        >
          {SITUACAO_VALUES.map((s) => (
            <ToggleButton
              key={s}
              value={s}
              color={SITUACAO_CHIP_COLOR[s]}
              disabled={busy}
              sx={{ textTransform: 'none', py: 0.1, px: 1, whiteSpace: 'nowrap' }}
            >
              {SITUACAO_LABELS[s]}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      )}
      {current === 'sem_resposta' ? (
        <Tooltip title={lead.followup_feito_em ? 'Followup já registrado — registrar novo contato' : 'Registrar contato (followup)'}>
          <span>
            <Button
              size="small"
              variant={lead.followup_feito_em ? 'text' : 'outlined'}
              onClick={() => onFollowup(lead)}
              disabled={busy}
              sx={{ textTransform: 'none', py: 0.1, px: 1, minWidth: 0 }}
            >
              {lead.followup_feito_em ? 'Contato ✓' : 'Registrei contato'}
            </Button>
          </span>
        </Tooltip>
      ) : null}
    </Box>
  );
}

export default SituacaoSegmented;
