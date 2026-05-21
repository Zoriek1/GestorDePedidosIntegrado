import {
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

interface KeyboardCheatsheetProps {
  open: boolean;
  onClose: () => void;
}

const SHORTCUTS: Array<{ key: string; label: string }> = [
  { key: 'J', label: 'Próxima linha' },
  { key: 'K', label: 'Linha anterior' },
  { key: 'Enter', label: 'Abrir WhatsApp da linha em foco' },
  { key: 'Ctrl+A', label: 'Selecionar página atual' },
  { key: 'Esc', label: 'Limpar seleção e foco' },
  { key: '?', label: 'Mostrar/ocultar esta lista' },
];

function Kbd({ value }: { value: string }) {
  return (
    <Typography
      component="span"
      sx={{
        fontFamily: 'monospace',
        fontSize: '0.85rem',
        px: 0.75,
        py: 0.25,
        borderRadius: '4px',
        border: '1px solid',
        borderColor: 'divider',
        backgroundColor: 'background.default',
      }}
    >
      {value}
    </Typography>
  );
}

export function KeyboardCheatsheet({ open, onClose }: KeyboardCheatsheetProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ pr: 6 }}>
        Atalhos de teclado
        <IconButton
          aria-label="Fechar"
          onClick={onClose}
          sx={{ position: 'absolute', right: 8, top: 8 }}
          size="small"
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Table size="small">
          <TableBody>
            {SHORTCUTS.map((s) => (
              <TableRow key={s.key} sx={{ '&:last-child td': { borderBottom: 0 } }}>
                <TableCell sx={{ width: 1, whiteSpace: 'nowrap', pl: 0 }}>
                  <Stack direction="row" spacing={0.5}>
                    {s.key.split('+').map((part, i) => (
                      <Kbd key={i} value={part} />
                    ))}
                  </Stack>
                </TableCell>
                <TableCell sx={{ pr: 0 }}>
                  <Typography variant="body2">{s.label}</Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </DialogContent>
    </Dialog>
  );
}
