import { useState } from 'react';
import { Box, Stack, TextField, useMediaQuery, useTheme, Dialog, DialogTitle, DialogContent } from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { StatusTabs } from './StatusTabs';
import { DateQuickFilters } from './DateQuickFilters';
import { Dayjs } from 'dayjs';

export interface OrdersFilterToolbarProps {
  search: string;
  status: string;
  onSearchChange: (value: string) => void;
  onStatusChange: (status: string) => void;
  onDateRangeChange: (start?: string, end?: string) => void;
}

export function OrdersFilterToolbar({
  search,
  status,
  onSearchChange,
  onStatusChange,
  onDateRangeChange,
}: OrdersFilterToolbarProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerValue, setPickerValue] = useState<Dayjs | null>(null);

  const handleDateChange = (date: Dayjs | null) => {
    setPickerValue(date);
    if (date) {
      const iso = date.format('YYYY-MM-DD');
      onDateRangeChange(iso, iso);
    } else {
      onDateRangeChange(undefined, undefined);
    }
  };

  return (
    <Box component={Stack} spacing={2}>
      <TextField
        fullWidth
        label="Buscar pedidos"
        placeholder="Cliente, destinatário, produto..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        size="small"
      />

      <DateQuickFilters
        onDateRangeChange={onDateRangeChange}
        onOpenDatePicker={() => setPickerOpen(true)}
      />

      <StatusTabs value={status || ''} onChange={onStatusChange} />

      <Dialog open={pickerOpen} onClose={() => setPickerOpen(false)} fullScreen={isMobile}>
        <DialogTitle>Selecionar data</DialogTitle>
        <DialogContent>
          <DatePicker
            value={pickerValue}
            onChange={(v) => handleDateChange(v)}
            slotProps={{ textField: { fullWidth: true } }}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
}


