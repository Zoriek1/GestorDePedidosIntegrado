import { Stack, Button, IconButton, Tooltip } from '@mui/material';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import dayjs from 'dayjs';

export interface DateQuickFiltersProps {
  onDateRangeChange: (start?: string, end?: string) => void;
  onOpenDatePicker: () => void;
}

export function DateQuickFilters({ onDateRangeChange, onOpenDatePicker }: DateQuickFiltersProps) {
  const today = dayjs().format('YYYY-MM-DD');
  const tomorrow = dayjs().add(1, 'day').format('YYYY-MM-DD');

  return (
    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
      <Button variant="contained" size="small" onClick={() => onDateRangeChange(undefined, undefined)}>
        Todos
      </Button>
      <Button variant="outlined" size="small" onClick={() => onDateRangeChange(today, today)}>
        Hoje
      </Button>
      <Button variant="outlined" size="small" onClick={() => onDateRangeChange(tomorrow, tomorrow)}>
        Amanhã
      </Button>
      <Tooltip title="Escolher data">
        <IconButton size="small" onClick={onOpenDatePicker}>
          <CalendarMonthIcon />
        </IconButton>
      </Tooltip>
    </Stack>
  );
}


