/**
 * Diálogo público para o CLIENTE SUGERIR uma correção de endereço.
 *
 * Não altera o pedido — envia a sugestão para /pedidos/track/<token>/sugestao-endereco,
 * que grava como pendente para a equipe revisar. Fetch cru (sem JWT), igual ao PushOptIn.
 */
import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Typography,
  Stack,
  CircularProgress,
  Alert,
} from '@mui/material';
import { getApiBaseUrl } from '../../api/http';

const MAX_LEN = 500;

interface SuggestAddressDialogProps {
  open: boolean;
  onClose: () => void;
  token: string;
  enderecoAtual?: string;
}

export function SuggestAddressDialog({
  open,
  onClose,
  token,
  enderecoAtual,
}: SuggestAddressDialogProps) {
  const [texto, setTexto] = useState('');
  const [busy, setBusy] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const handleClose = () => {
    if (busy) return;
    onClose();
    // Reseta após fechar para reabrir limpo.
    setTimeout(() => {
      setTexto('');
      setEnviado(false);
      setErro(null);
    }, 200);
  };

  const handleSubmit = async () => {
    const valor = texto.trim();
    if (!valor) {
      setErro('Descreva a correção do endereço.');
      return;
    }
    setBusy(true);
    setErro(null);
    try {
      const res = await fetch(
        `${getApiBaseUrl()}/pedidos/track/${encodeURIComponent(token)}/sugestao-endereco`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ texto: valor }),
        },
      );
      if (!res.ok) {
        const json = await res.json().catch(() => null);
        throw new Error(json?.error || 'Não foi possível enviar. Tente novamente.');
      }
      setEnviado(true);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao enviar.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Sugerir correção do endereço</DialogTitle>
      <DialogContent>
        {enviado ? (
          <Alert severity="success" sx={{ mt: 1 }}>
            Sugestão enviada! Nossa equipe vai revisar antes de atualizar o pedido.
          </Alert>
        ) : (
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Sua sugestão será revisada pela equipe — o endereço não é alterado
              automaticamente.
            </Typography>
            {enderecoAtual && (
              <Typography variant="body2">
                Endereço atual: <strong>{enderecoAtual}</strong>
              </Typography>
            )}
            <TextField
              label="Endereço correto / instruções"
              multiline
              minRows={3}
              fullWidth
              autoFocus
              value={texto}
              onChange={(e) => setTexto(e.target.value.slice(0, MAX_LEN))}
              helperText={`${texto.length}/${MAX_LEN}`}
              disabled={busy}
            />
            {erro && <Alert severity="error">{erro}</Alert>}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        {enviado ? (
          <Button onClick={handleClose} variant="contained">
            Fechar
          </Button>
        ) : (
          <>
            <Button onClick={handleClose} disabled={busy} color="inherit">
              Cancelar
            </Button>
            <Button
              onClick={handleSubmit}
              variant="contained"
              disabled={busy || !texto.trim()}
              startIcon={busy ? <CircularProgress size={16} /> : undefined}
            >
              Enviar sugestão
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}

export default SuggestAddressDialog;
