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
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import BlockIcon from '@mui/icons-material/Block';
import ScheduleIcon from '@mui/icons-material/Schedule';
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

type SelectionMode = 'simple' | 'interval';

export function TimeSlotDialog({
  open,
  onClose,
  date,
  onSelectSlot,
  currentSlot,
}: TimeSlotDialogProps) {
  const { getAuthHeader } = useAuth();
  const { fetchAvailability, isLoading, availability, error } = useTimeSlotAvailability(getAuthHeader);
  
  // Detectar modo inicial baseado no currentSlot
  const isInterval = currentSlot?.includes(' - ') || false;
  const [selectionMode, setSelectionMode] = useState<SelectionMode>(isInterval ? 'interval' : 'simple');
  
  // Para modo simples: horário único
  // Para modo intervalo: horário inicial e final
  const [selectedSlot, setSelectedSlot] = useState<string | null>(currentSlot || null);
  const [intervalStart, setIntervalStart] = useState<string | null>(null);
  const [intervalEnd, setIntervalEnd] = useState<string | null>(null);

  // Buscar disponibilidade quando abrir ou data mudar
  useEffect(() => {
    if (open && date) {
      fetchAvailability(date);
      
      // Parse currentSlot se for intervalo
      if (currentSlot) {
        if (currentSlot.includes(' - ')) {
          const [start, end] = currentSlot.split(' - ').map(s => s.trim());
          setSelectionMode('interval');
          setIntervalStart(start);
          setIntervalEnd(end);
          setSelectedSlot(null);
        } else {
          setSelectionMode('simple');
          setSelectedSlot(currentSlot);
          setIntervalStart(null);
          setIntervalEnd(null);
        }
      } else {
        // Reset quando não há currentSlot
        setSelectedSlot(null);
        setIntervalStart(null);
        setIntervalEnd(null);
      }
    }
  }, [open, date, fetchAvailability, currentSlot]);

  const handleModeChange = (_event: React.MouseEvent<HTMLElement>, newMode: SelectionMode | null) => {
    if (newMode !== null) {
      setSelectionMode(newMode);
      // Reset seleções ao mudar modo
      setSelectedSlot(null);
      setIntervalStart(null);
      setIntervalEnd(null);
    }
  };

  const handleSelectSlot = (slot: SlotAvailability) => {
    if (slot.status === 'full') return;
    
    if (selectionMode === 'simple') {
      setSelectedSlot(slot.slot);
    } else {
      // Modo intervalo: primeira seleção = início, segunda = fim
      if (!intervalStart) {
        setIntervalStart(slot.slot);
        setIntervalEnd(null);
      } else {
        // Validar que horário final é depois do inicial
        const startMinutes = parseTimeToMinutes(slot.slot);
        const endMinutes = parseTimeToMinutes(intervalStart);
        
        if (startMinutes <= endMinutes) {
          // Se selecionou um horário antes ou igual, resetar e começar de novo
          setIntervalStart(slot.slot);
          setIntervalEnd(null);
        } else {
          setIntervalEnd(slot.slot);
        }
      }
    }
  };

  const parseTimeToMinutes = (time: string): number => {
    const [hours, minutes] = time.split(':').map(Number);
    return hours * 60 + minutes;
  };

  const isSlotSelected = (slot: SlotAvailability): boolean => {
    if (selectionMode === 'simple') {
      return selectedSlot === slot.slot;
    } else {
      return intervalStart === slot.slot || intervalEnd === slot.slot;
    }
  };

  const handleConfirm = () => {
    let finalValue: string | null = null;
    
    if (selectionMode === 'simple') {
      finalValue = selectedSlot;
    } else {
      if (intervalStart && intervalEnd) {
        finalValue = `${intervalStart} - ${intervalEnd}`;
      }
    }
    
    if (finalValue) {
      onSelectSlot(finalValue);
      onClose();
    }
  };

  const getConfirmButtonText = (): string => {
    if (selectionMode === 'simple') {
      return selectedSlot ? `Confirmar ${selectedSlot}` : 'Confirmar';
    } else {
      if (intervalStart && intervalEnd) {
        return `Confirmar ${intervalStart} - ${intervalEnd}`;
      } else if (intervalStart) {
        return `Selecione o horário final (após ${intervalStart})`;
      } else {
        return 'Selecione o horário inicial';
      }
    }
  };

  const canConfirm = (): boolean => {
    if (selectionMode === 'simple') {
      return selectedSlot !== null;
    } else {
      return intervalStart !== null && intervalEnd !== null;
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

        {/* Seletor de modo */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
            Tipo de horário:
          </Typography>
          <ToggleButtonGroup
            value={selectionMode}
            exclusive
            onChange={handleModeChange}
            aria-label="tipo de horário"
            fullWidth
            size="small"
          >
            <ToggleButton value="simple" aria-label="horário específico">
              <ScheduleIcon sx={{ mr: 1, fontSize: 18 }} />
              Horário Específico
            </ToggleButton>
            <ToggleButton value="interval" aria-label="intervalo">
              <AccessTimeIcon sx={{ mr: 1, fontSize: 18 }} />
              Intervalo
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Instrução para modo intervalo */}
        {selectionMode === 'interval' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            {!intervalStart
              ? 'Selecione o horário inicial'
              : !intervalEnd
              ? `Horário inicial: ${intervalStart}. Selecione o horário final (deve ser depois de ${intervalStart})`
              : `Intervalo selecionado: ${intervalStart} - ${intervalEnd}`}
          </Alert>
        )}

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
          <Grid container spacing={2}>
            {availability.slots.map((slot) => (
              <Grid size={{ xs: 4, sm: 3 }} key={slot.slot}>
                <SlotButton
                  slot={slot}
                  isSelected={isSlotSelected(slot)}
                  onClick={() => handleSelectSlot(slot)}
                />
              </Grid>
            ))}
          </Grid>
        )}
      </DialogContent>

      <DialogActions 
        sx={{ 
          px: 3, 
          pb: 2, 
          pt: 2,
          borderTop: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}
      >
        <Button 
          onClick={onClose} 
          variant="outlined"
          sx={{ 
            minWidth: 100,
            color: 'text.primary',
            borderColor: 'divider',
            '&:hover': {
              borderColor: 'primary.main',
              bgcolor: 'action.hover',
            },
          }}
        >
          Cancelar
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          color="primary"
          disabled={!canConfirm()}
          sx={{ 
            minWidth: 140,
            fontWeight: 600,
          }}
        >
          {getConfirmButtonText()}
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
      minHeight: 56, // Garantir tamanho mínimo para touch targets
    };

    if (selected) {
      return {
        ...baseStyles,
        bgcolor: 'primary.main',
        color: 'primary.contrastText',
        border: '2px solid',
        borderColor: 'primary.dark',
        boxShadow: 2,
        '&:hover': {
          bgcolor: 'primary.dark',
          boxShadow: 4,
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

