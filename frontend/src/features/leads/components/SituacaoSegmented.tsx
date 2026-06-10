/**
 * Segmented single-select da `situacao` do lead confirmado (`whatsapp_iniciado`).
 *
 * 1 clique troca a etiqueta de funil (Em conversa / Orçamento / Sem resposta) — sem
 * disparar evento Meta (situação é etiqueta pura). Em `sem_resposta`, expõe o botão
 * de followup (reativação): registrar contato tira o lead da fila de pendência.
 *
 * Extraído de LeadsPage.tsx para ser reusado pelos dois renderers (card mobile e
 * tabela desktop) via LeadActions, sem duplicar a lógica.
 */
import { Box, Button, ToggleButton, ToggleButtonGroup, Tooltip } from '@mui/material';
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
  if (lead.status !== 'whatsapp_iniciado') return null;
  const current = (lead.situacao ?? 'aguardando_resposta') as Situacao;
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
      <ToggleButtonGroup
        size="small"
        exclusive
        value={current}
        onChange={(_e, val) => {
          if (val) onSet(lead, val as Situacao);
        }}
        sx={{ flexWrap: 'wrap' }}
      >
        {SITUACAO_VALUES.map((s) => (
          <ToggleButton
            key={s}
            value={s}
            color={SITUACAO_CHIP_COLOR[s]}
            disabled={busy}
            sx={{ textTransform: 'none', py: 0.1, px: 1 }}
          >
            {SITUACAO_LABELS[s]}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
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
