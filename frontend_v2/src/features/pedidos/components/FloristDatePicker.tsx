import { Tooltip } from '@mui/material';
import { DatePicker, DatePickerProps } from '@mui/x-date-pickers/DatePicker';
import { PickersDay, PickersDayProps } from '@mui/x-date-pickers/PickersDay';
import type { Dayjs } from 'dayjs';
import { getFloristHoliday } from '../utils/floristHolidays';

const WEEKDAY_LABELS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

function dayOfWeekFormatter(date: Dayjs): string {
  return WEEKDAY_LABELS[date.day()];
}

function HolidayDay(props: PickersDayProps) {
  const { day, outsideCurrentMonth, selected } = props;
  const holiday = outsideCurrentMonth ? null : getFloristHoliday(day as Dayjs);

  if (!holiday) {
    return <PickersDay {...props} />;
  }

  return (
    <Tooltip title={holiday.name} arrow placement="top">
      <PickersDay
        {...props}
        sx={{
          ...(props.sx || {}),
          ...(selected
            ? {
                backgroundColor: holiday.color,
                color: '#fff',
                '&:hover': { backgroundColor: holiday.color },
                '&.Mui-selected': {
                  backgroundColor: holiday.color,
                  '&:hover': { backgroundColor: holiday.color },
                  '&:focus': { backgroundColor: holiday.color },
                },
              }
            : {
                border: `2px solid ${holiday.color}`,
                color: holiday.color,
                fontWeight: 600,
              }),
        }}
      />
    </Tooltip>
  );
}

export function FloristDatePicker(props: DatePickerProps) {
  const { slots, slotProps, dayOfWeekFormatter: customFormatter, ...rest } = props;

  return (
    <DatePicker
      {...rest}
      dayOfWeekFormatter={customFormatter ?? dayOfWeekFormatter}
      slots={{
        day: HolidayDay,
        ...(slots || {}),
      }}
      slotProps={slotProps}
    />
  );
}

export default FloristDatePicker;
