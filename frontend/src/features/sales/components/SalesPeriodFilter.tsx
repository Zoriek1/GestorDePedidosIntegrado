/**
 * Sales Period Filter Component
 * Permite selecionar período (mês/ano ou intervalo de datas)
 */

import { useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs, { Dayjs } from 'dayjs';

export interface SalesPeriodFilterProps {
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
  onChange: (startDate: string, endDate: string) => void;
  compareEnabled?: boolean;
  compareStartDate?: string;
  compareEndDate?: string;
  onCompareToggle?: (enabled: boolean) => void;
  onCompareChange?: (startDate: string, endDate: string) => void;
}

const QUICK_PERIODS = [
  { label: 'Este mês', months: 0 },
  { label: 'Mês anterior', months: -1 },
  { label: 'Últimos 3 meses', months: -3 },
  { label: 'Últimos 6 meses', months: -6 },
  { label: 'Este ano', months: -12 },
];

export function SalesPeriodFilter({
  startDate,
  endDate,
  onChange,
  compareEnabled = false,
  compareStartDate,
  compareEndDate,
  onCompareToggle,
  onCompareChange,
}: SalesPeriodFilterProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [tempStartDate, setTempStartDate] = useState<Dayjs | null>(dayjs(startDate));
  const [tempEndDate, setTempEndDate] = useState<Dayjs | null>(dayjs(endDate));
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);
  const [tempCompareStart, setTempCompareStart] = useState<Dayjs | null>(
    compareStartDate ? dayjs(compareStartDate) : null
  );
  const [tempCompareEnd, setTempCompareEnd] = useState<Dayjs | null>(
    compareEndDate ? dayjs(compareEndDate) : null
  );

  const handleQuickPeriod = (months: number) => {
    const now = dayjs();
    let newStart: Dayjs;
    const newEnd: Dayjs = now.endOf('month');

    if (months === 0) {
      // Este mês
      newStart = now.startOf('month');
    } else if (months === -12) {
      // Este ano
      newStart = now.startOf('year');
    } else {
      // Últimos N meses
      newStart = now.add(months, 'month').startOf('month');
    }

    onChange(newStart.format('YYYY-MM-DD'), newEnd.format('YYYY-MM-DD'));
  };

  const handleCustomDateConfirm = () => {
    if (tempStartDate && tempEndDate) {
      onChange(
        tempStartDate.startOf('day').format('YYYY-MM-DD'),
        tempEndDate.endOf('day').format('YYYY-MM-DD')
      );
      setDialogOpen(false);
    }
  };

  const handleCompareConfirm = () => {
    if (tempCompareStart && tempCompareEnd && onCompareChange) {
      onCompareChange(
        tempCompareStart.startOf('day').format('YYYY-MM-DD'),
        tempCompareEnd.endOf('day').format('YYYY-MM-DD')
      );
      setCompareDialogOpen(false);
      onCompareToggle?.(true);
    }
  };

  return (
    <Box>
      <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
        {QUICK_PERIODS.map((period) => (
          <Button
            key={period.label}
            size="small"
            variant="outlined"
            onClick={() => handleQuickPeriod(period.months)}
          >
            {period.label}
          </Button>
        ))}
        <Button
          size="small"
          variant="contained"
          onClick={() => {
            setTempStartDate(dayjs(startDate));
            setTempEndDate(dayjs(endDate));
            setDialogOpen(true);
          }}
        >
          Período personalizado
        </Button>
        <Button
          size="small"
          variant={compareEnabled ? 'outlined' : 'contained'}
          onClick={() => {
            setTempCompareStart(compareStartDate ? dayjs(compareStartDate) : null);
            setTempCompareEnd(compareEndDate ? dayjs(compareEndDate) : null);
            setCompareDialogOpen(true);
          }}
        >
          {compareEnabled ? 'Editar comparação' : 'Comparar com…'}
        </Button>
        {compareEnabled && (
          <Button
            size="small"
            variant="text"
            onClick={() => onCompareToggle?.(false)}
          >
            Remover comparação
          </Button>
        )}
      </Stack>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Selecionar Período</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <DatePicker
              label="Data inicial"
              value={tempStartDate}
              onChange={(newValue) => setTempStartDate(newValue)}
              slotProps={{ textField: { fullWidth: true } }}
            />
            <DatePicker
              label="Data final"
              value={tempEndDate}
              onChange={(newValue) => setTempEndDate(newValue)}
              slotProps={{ textField: { fullWidth: true } }}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancelar</Button>
          <Button
            onClick={handleCustomDateConfirm}
            variant="contained"
            disabled={!tempStartDate || !tempEndDate}
          >
            Confirmar
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={compareDialogOpen} onClose={() => setCompareDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Selecionar Período de Comparação</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <DatePicker
              label="Data inicial"
              value={tempCompareStart}
              onChange={(newValue) => setTempCompareStart(newValue)}
              slotProps={{ textField: { fullWidth: true } }}
            />
            <DatePicker
              label="Data final"
              value={tempCompareEnd}
              onChange={(newValue) => setTempCompareEnd(newValue)}
              slotProps={{ textField: { fullWidth: true } }}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCompareDialogOpen(false)}>Cancelar</Button>
          <Button
            onClick={handleCompareConfirm}
            variant="contained"
            disabled={!tempCompareStart || !tempCompareEnd}
          >
            Confirmar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
