/**
 * TimeSlotDialog - Modal de Seleção de Horário
 * Grid de horários com estados visuais: livre, alerta, lotado
 */

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  CircularProgress,
  Grid,
  Chip,
  Alert,
} from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import BlockIcon from '@mui/icons-material/Block';
import dayjs from 'dayjs';
import { useAuth } from '../../auth/authStore';
import {
  useTimeSlotAvailability,
  SlotAvailability,
  SlotStatus,
} from '../useCases/timeSlotAvailability';

// ============================================================================
// Props Interface
// ============================================================================

interface TimeSlotDialogProps {
  /** Se o dialog está aberto */
  open: boolean;
  /** Callback para fechar o dialog */
  onClose: () => void;
  /** Data selecionada (YYYY-MM-DD) */
  date: string;
  /** Callback ao selecionar um horário */
  onSelectSlot: (slot: string) => void;
  /** Horário atualmente selecionado (para destacar) */
  currentSlot?: string;
}

// ============================================================================
// Componente
// ============================================================================

export function TimeSlotDialog({
  open,
  onClose,
  date,
  onSelectSlot,
  currentSlot,
}: TimeSlotDialogProps) {
  const { getAuthHeader } = useAuth();
  const { fetchAvailability, isLoading, availability, error } = useTimeSlotAvailability(getAuthHeader);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(currentSlot || null);

  // Buscar disponibilidade quando abrir ou data mudar
  useEffect(() => {
    if (open && date) {
      fetchAvailability(date);
      setSelectedSlot(currentSlot || null);
    }
  }, [open, date, fetchAvailability, currentSlot]);

  const handleSelectSlot = (slot: SlotAvailability) => {
    if (slot.status === 'full') return;
    setSelectedSlot(slot.slot);
  };

  const handleConfirm = () => {
    if (selectedSlot) {
      onSelectSlot(selectedSlot);
      onClose();
    }
  };

  const formattedDate = dayjs(date).format('DD/MM/YYYY (dddd)');

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 },
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <AccessTimeIcon color="primary" />
        Selecionar Horário
      </DialogTitle>

      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Data: <strong>{formattedDate}</strong>
        </Typography>

        {/* Legenda */}
        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <Chip
            icon={<CheckCircleIcon />}
            label="Disponível"
            color="success"
            variant="outlined"
            size="small"
          />
          <Chip
            icon={<WarningIcon />}
            label="Quase lotado"
            color="warning"
            variant="outlined"
            size="small"
          />
          <Chip
            icon={<BlockIcon />}
            label="Lotado"
            color="error"
            variant="outlined"
            size="small"
          />
        </Box>

        {/* Loading */}
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Erro */}
        {error && !isLoading && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {error}. Exibindo disponibilidade estimada.
          </Alert>
        )}

        {/* Grid de horários */}
        {!isLoading && availability && (
          <Grid container spacing={1}>
            {availability.slots.map((slot) => (
              <Grid size={{ xs: 4, sm: 3 }} key={slot.slot}>
                <SlotButton
                  slot={slot}
                  isSelected={selectedSlot === slot.slot}
                  onClick={() => handleSelectSlot(slot)}
                />
              </Grid>
            ))}
          </Grid>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} color="inherit">
          Cancelar
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          disabled={!selectedSlot}
        >
          Confirmar {selectedSlot || ''}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// ============================================================================
// Sub-componentes
// ============================================================================

interface SlotButtonProps {
  slot: SlotAvailability;
  isSelected: boolean;
  onClick: () => void;
}

function SlotButton({ slot, isSelected, onClick }: SlotButtonProps) {
  const getButtonStyles = (status: SlotStatus, selected: boolean) => {
    const baseStyles = {
      width: '100%',
      py: 1.5,
      borderRadius: 2,
      fontWeight: selected ? 'bold' : 'normal',
      transition: 'all 0.2s ease',
    };

    if (selected) {
      return {
        ...baseStyles,
        bgcolor: 'primary.main',
        color: 'primary.contrastText',
        border: '2px solid',
        borderColor: 'primary.dark',
        '&:hover': {
          bgcolor: 'primary.dark',
        },
      };
    }

    switch (status) {
      case 'available':
        return {
          ...baseStyles,
          bgcolor: 'success.light',
          color: 'success.contrastText',
          border: '1px solid',
          borderColor: 'success.main',
          '&:hover': {
            bgcolor: 'success.main',
            transform: 'scale(1.02)',
          },
        };
      case 'warning':
        return {
          ...baseStyles,
          bgcolor: 'warning.light',
          color: 'warning.contrastText',
          border: '1px solid',
          borderColor: 'warning.main',
          '&:hover': {
            bgcolor: 'warning.main',
            transform: 'scale(1.02)',
          },
        };
      case 'full':
        return {
          ...baseStyles,
          bgcolor: 'grey.200',
          color: 'grey.500',
          border: '1px solid',
          borderColor: 'grey.300',
          cursor: 'not-allowed',
          opacity: 0.6,
        };
      default:
        return baseStyles;
    }
  };

  const getIcon = (status: SlotStatus) => {
    switch (status) {
      case 'available':
        return <CheckCircleIcon fontSize="small" />;
      case 'warning':
        return <WarningIcon fontSize="small" />;
      case 'full':
        return <BlockIcon fontSize="small" />;
      default:
        return null;
    }
  };

  return (
    <Box
      component="button"
      type="button"
      onClick={slot.status !== 'full' ? onClick : undefined}
      sx={getButtonStyles(slot.status, isSelected)}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
        {getIcon(slot.status)}
        <Typography variant="body2" component="span">
          {slot.slot}
        </Typography>
      </Box>
      <Typography variant="caption" display="block" sx={{ opacity: 0.8 }}>
        {slot.count}/{slot.maxCount}
      </Typography>
    </Box>
  );
}

export default TimeSlotDialog;

