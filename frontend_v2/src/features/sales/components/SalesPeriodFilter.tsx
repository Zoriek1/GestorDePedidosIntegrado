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
}

const QUICK_PERIODS = [
  { label: 'Este mês', months: 0 },
  { label: 'Mês anterior', months: -1 },
  { label: 'Últimos 3 meses', months: -3 },
  { label: 'Últimos 6 meses', months: -6 },
  { label: 'Este ano', months: -12 },
];

export function SalesPeriodFilter({ startDate, endDate, onChange }: SalesPeriodFilterProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [tempStartDate, setTempStartDate] = useState<Dayjs | null>(dayjs(startDate));
  const [tempEndDate, setTempEndDate] = useState<Dayjs | null>(dayjs(endDate));

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
          onClick={() => setDialogOpen(true)}
        >
          Período personalizado
        </Button>
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
    </Box>
  );
}
