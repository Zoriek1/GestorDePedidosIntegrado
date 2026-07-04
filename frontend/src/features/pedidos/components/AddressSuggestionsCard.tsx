/**
 * Card de revisão das sugestões de correção de endereço enviadas pelo cliente
 * na página pública de rastreio. Mostra as pendentes com Aplicar/Ignorar.
 *
 * "Aplicar" copia o texto sugerido para o endereço do pedido (server-side);
 * o cliente nunca escreve direto no pedido.
 */
import dayjs from 'dayjs';
import { Paper, Stack, Typography, Button, Chip, Box, Divider } from '@mui/material';
import { EditLocationAlt } from '@mui/icons-material';
import {
  useSugestoesEndereco,
  useResolverSugestaoEndereco,
} from '../../../api/endpoints/pedidos';
import { useToast } from '../../../components/system/useToast';
import { useConfirm } from '../../../components/system/useConfirm';

interface AddressSuggestionsCardProps {
  pedidoId: number;
}

export function AddressSuggestionsCard({ pedidoId }: AddressSuggestionsCardProps) {
  const { data } = useSugestoesEndereco(pedidoId);
  const resolver = useResolverSugestaoEndereco();
  const { success, error: showError } = useToast();
  const confirm = useConfirm();

  const sugestoes = data?.sugestoes ?? [];
  const pendentes = sugestoes.filter((s) => s.status === 'pendente');

  if (pendentes.length === 0) return null;

  const handleResolver = async (
    sugestaoId: number,
    acao: 'aplicar' | 'ignorar',
    texto: string,
  ) => {
    const confirmed = await confirm({
      title: acao === 'aplicar' ? 'Aplicar novo endereço' : 'Ignorar sugestão',
      description:
        acao === 'aplicar'
          ? `O endereço do pedido será substituído por:\n\n"${texto}"`
          : 'A sugestão será marcada como ignorada.',
      confirmText: acao === 'aplicar' ? 'Aplicar' : 'Ignorar',
      confirmColor: acao === 'aplicar' ? 'primary' : 'warning',
    });
    if (!confirmed) return;

    try {
      await resolver.mutateAsync({ sugestaoId, pedidoId, acao });
      success(acao === 'aplicar' ? 'Endereço atualizado' : 'Sugestão ignorada');
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Erro ao resolver sugestão');
    }
  };

  return (
    <Paper
      sx={{
        p: 2.5,
        mb: 2,
        border: '2px solid',
        borderColor: 'warning.main',
        backgroundColor: '#fff8e1',
      }}
    >
      <Stack direction="row" spacing={1} alignItems="center" mb={1}>
        <EditLocationAlt color="warning" />
        <Typography variant="overline" sx={{ letterSpacing: 1.2, fontWeight: 700 }}>
          Correção de endereço sugerida pelo cliente
        </Typography>
        <Chip label={pendentes.length} color="warning" size="small" sx={{ fontWeight: 700 }} />
      </Stack>

      <Stack spacing={2} divider={<Divider flexItem />}>
        {pendentes.map((s) => (
          <Stack key={s.id} spacing={1}>
            {s.endereco_anterior && (
              <Typography variant="caption" color="text.secondary">
                Endereço atual: {s.endereco_anterior}
              </Typography>
            )}
            <Box
              sx={{
                p: 1.5,
                bgcolor: 'background.paper',
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Typography variant="body1" fontWeight={600} sx={{ whiteSpace: 'pre-wrap' }}>
                {s.texto}
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              {s.created_at && (
                <Typography variant="caption" color="text.secondary">
                  Enviado em {dayjs(s.created_at).format('DD/MM/YYYY HH:mm')}
                </Typography>
              )}
              <Box flexGrow={1} />
              <Button
                size="small"
                color="inherit"
                disabled={resolver.isPending}
                onClick={() => handleResolver(s.id, 'ignorar', s.texto)}
              >
                Ignorar
              </Button>
              <Button
                size="small"
                variant="contained"
                color="primary"
                disabled={resolver.isPending}
                onClick={() => handleResolver(s.id, 'aplicar', s.texto)}
              >
                Aplicar ao pedido
              </Button>
            </Stack>
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}

export default AddressSuggestionsCard;
