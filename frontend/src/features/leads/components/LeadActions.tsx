/**
 * Cluster de ações rápidas da linha do lead, dirigido por `ACTIONS_BY_STATUS`.
 *
 * Fonte única usada pelos DOIS renderers (card mobile e tabela desktop), no lugar
 * dos ternários por status que estavam duplicados em LeadsPage.tsx. Espelha o
 * comportamento anterior — só centraliza.
 *
 * Renderiza, nesta ordem:
 *   1. WhatsApp (universal): liga se há telefone; vira "capturar" em qualquer
 *      estado pré-confirmação sem telefone (ação `capture_phone`, via
 *      getEffectiveLeadActions); desabilitado caso contrário.
 *   2. Confirmar / Descartar (em `lead_pendente` COM telefone — sem número o
 *      backend recusa com 422, então esses botões não aparecem).
 *   3. "Não entrou em contato" (em `pendente_whatsapp`).
 *   4. Ver/Criar pedido (universal): ver se há pedido vinculado; desabilitado em
 *      `compra_realizada` sem pedido; senão abre o menu de criação.
 *
 * `situacao` NÃO é renderada aqui — o segmented (SituacaoSegmented) mora na célula de
 * status, ao lado do chip. Ambos leem o mesmo mapa de ações.
 */
import { type MouseEvent } from 'react';
import { IconButton, Stack, Tooltip } from '@mui/material';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import VisibilityIcon from '@mui/icons-material/Visibility';
import AddShoppingCartIcon from '@mui/icons-material/AddShoppingCart';
import CheckIcon from '@mui/icons-material/Check';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import type { Lead } from '../../../api/endpoints/leads';
import { buildWhatsAppUrl, getEffectiveLeadActions } from '../leadGrouping';

interface LeadActionsProps {
  lead: Lead;
  /** `updateLeadStatus.isPending` — desabilita confirmar/descartar/não-contatou. */
  pending: boolean;
  loadingWhatsAppId?: number | null;
  onCapturePhone: (lead: Lead) => void;
  onMarkNoContact: (lead: Lead) => void;
  onConfirm: (lead: Lead) => void;
  onDisqualify: (lead: Lead) => void;
  onViewOrder: (pedidoId: number) => void;
  onCreateOrder: (e: MouseEvent<HTMLElement>, lead: Lead) => void;
}

export function LeadActions({
  lead,
  pending,
  loadingWhatsAppId,
  onCapturePhone,
  onMarkNoContact,
  onConfirm,
  onDisqualify,
  onViewOrder,
  onCreateOrder,
}: LeadActionsProps) {
  // Ações reais consideram o telefone: sem número, `confirm`/`disqualify` somem
  // (dariam 422 no backend) e entra `capture_phone` para destravar o lead.
  const actions = getEffectiveLeadActions(lead);

  return (
    <Stack direction="row" spacing={0.5} alignItems="center" justifyContent="center">
      {/* 1. WhatsApp (universal) — liga, captura ou desabilitado */}
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
      ) : actions.includes('capture_phone') ? (
        <Tooltip title="Capturar telefone do lead">
          <IconButton size="small" color="success" onClick={() => onCapturePhone(lead)}>
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

      {/* 2. Confirmar / Descartar (lead_pendente) */}
      {actions.includes('confirm') ? (
        <Tooltip title="Confirmar lead (positivo CAPI agora)">
          <span>
            <IconButton
              size="small"
              color="success"
              onClick={() => onConfirm(lead)}
              disabled={pending}
              aria-label="Confirmar lead"
            >
              <CheckCircleIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      ) : null}
      {actions.includes('disqualify') ? (
        <Tooltip title="Desqualificar lead">
          <span>
            <IconButton
              size="small"
              color="warning"
              onClick={() => onDisqualify(lead)}
              disabled={pending}
              aria-label="Desqualificar lead"
            >
              <PersonOffIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      ) : null}

      {/* 3. Não entrou em contato (pendente_whatsapp) */}
      {actions.includes('mark_no_contact') ? (
        <Tooltip title="Marcar como não contatou">
          <span>
            <IconButton
              size="small"
              color="default"
              onClick={() => onMarkNoContact(lead)}
              disabled={pending}
              aria-label="Marcar como não contatou"
            >
              <CheckIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      ) : null}

      {/* 4. Ver / Criar pedido (universal) */}
      {lead.pedido_id ? (
        <Tooltip title="Visualizar pedido vinculado">
          <IconButton size="small" color="secondary" onClick={() => onViewOrder(lead.pedido_id!)}>
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
          <IconButton size="small" color="primary" onClick={(e) => onCreateOrder(e, lead)}>
            <AddShoppingCartIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
    </Stack>
  );
}

export default LeadActions;
