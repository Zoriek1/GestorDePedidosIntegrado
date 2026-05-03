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

  const tint = `${holiday.color}1f`;
  const tintHover = `${holiday.color}33`;

  return (
    <PickersDay
      {...props}
      title={holiday.name}
      sx={{
        ...(selected
          ? {
              backgroundColor: holiday.color,
              color: '#fff',
              fontWeight: 700,
              '&.Mui-selected': {
                backgroundColor: holiday.color,
                '&:hover, &:focus': { backgroundColor: holiday.color },
              },
            }
          : {
              backgroundColor: tint,
              color: holiday.color,
              fontWeight: 700,
              '&:hover': { backgroundColor: tintHover },
            }),
      }}
    />
  );
}

const POPUP_SX = {
  '& .MuiDateCalendar-root': {
    width: 360,
    maxHeight: 380,
  },
  '& .MuiPickersCalendarHeader-root': {
    paddingLeft: '12px',
    paddingRight: '8px',
  },
  '& .MuiDayCalendar-header, & .MuiDayCalendar-weekContainer': {
    justifyContent: 'space-around',
  },
  '& .MuiDayCalendar-weekDayLabel': {
    width: 40,
    height: 32,
    margin: 0,
    fontSize: 12,
    fontWeight: 600,
  },
  '& .MuiPickersDay-root': {
    width: 40,
    height: 40,
    margin: 0,
    fontSize: 14,
  },
  '& .MuiPickersSlideTransition-root': {
    minHeight: 260,
  },
};

export function FloristDatePicker(props: DatePickerProps) {
  const { slots, slotProps, dayOfWeekFormatter: customFormatter, ...rest } = props;
  const userPaperSx = (slotProps?.desktopPaper as { sx?: object } | undefined)?.sx;
  const userMobilePaperSx = (slotProps?.mobilePaper as { sx?: object } | undefined)?.sx;

  return (
    <DatePicker
      {...rest}
      dayOfWeekFormatter={customFormatter ?? dayOfWeekFormatter}
      slots={{
        day: HolidayDay,
        ...(slots || {}),
      }}
      slotProps={{
        ...(slotProps || {}),
        desktopPaper: {
          ...(slotProps?.desktopPaper || {}),
          sx: { ...POPUP_SX, ...(userPaperSx || {}) },
        },
        mobilePaper: {
          ...(slotProps?.mobilePaper || {}),
          sx: { ...POPUP_SX, ...(userMobilePaperSx || {}) },
        },
      }}
    />
  );
}

export default FloristDatePicker;
