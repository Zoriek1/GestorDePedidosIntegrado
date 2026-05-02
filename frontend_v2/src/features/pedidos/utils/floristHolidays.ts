import type { Dayjs } from 'dayjs';

export type HolidayTier = 'peak' | 'high' | 'normal';

export interface FloristHoliday {
  name: string;
  tier: HolidayTier;
  color: string;
}

const TIER_COLORS: Record<HolidayTier, string> = {
  peak: '#d81b60',
  high: '#e65100',
  normal: '#7b1fa2',
};

function nthSundayOfMonth(year: number, month: number, n: number): { d: number; m: number } {
  const first = new Date(Date.UTC(year, month, 1));
  const offset = (7 - first.getUTCDay()) % 7;
  return { d: 1 + offset + (n - 1) * 7, m: month };
}

// Meeus/Jones/Butcher
function easterSunday(year: number): { d: number; m: number } {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return { d: day, m: month - 1 };
}

export function getFloristHoliday(date: Dayjs): FloristHoliday | null {
  const day = date.date();
  const month = date.month();
  const year = date.year();

  const fixed: Array<[number, number, string, HolidayTier]> = [
    [0, 1, 'Ano Novo', 'normal'],
    [1, 14, "Dia dos Namorados (Valentine's)", 'normal'],
    [2, 8, 'Dia Internacional da Mulher', 'high'],
    [4, 12, 'Dia dos Namorados', 'peak'],
    [6, 26, 'Dia dos Avós', 'normal'],
    [8, 30, 'Dia das Secretárias', 'normal'],
    [9, 15, 'Dia dos Professores', 'normal'],
    [10, 2, 'Finados', 'high'],
    [11, 25, 'Natal', 'high'],
  ];

  for (const [m, d, name, tier] of fixed) {
    if (month === m && day === d) {
      return { name, tier, color: TIER_COLORS[tier] };
    }
  }

  if (month === 4) {
    const maes = nthSundayOfMonth(year, 4, 2);
    if (day === maes.d) {
      return { name: 'Dia das Mães', tier: 'peak', color: TIER_COLORS.peak };
    }
  }

  if (month === 7) {
    const pais = nthSundayOfMonth(year, 7, 2);
    if (day === pais.d) {
      return { name: 'Dia dos Pais', tier: 'peak', color: TIER_COLORS.peak };
    }
  }

  const easter = easterSunday(year);
  if (month === easter.m && day === easter.d) {
    return { name: 'Páscoa', tier: 'normal', color: TIER_COLORS.normal };
  }

  return null;
}
