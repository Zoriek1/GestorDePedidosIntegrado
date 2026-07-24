import { createTheme } from '@mui/material/styles';

export const SEMANTIC = {
  success: '#16a34a',
  warning: '#f59e0b',
  error: '#dc2626',
  info: '#2563eb',
  purple: '#7c3aed',
  sky: '#0ea5e9',
  iconBgBlue: { light: '#e0f2fe', dark: '#1e3a5f' },
  iconBgGray: { light: '#f3f4f6', dark: '#2a2a2a' },
  iconBgYellow: { light: '#fef9c3', dark: '#3d3520' },
  iconBgGreen: { light: '#dcfce7', dark: '#143d28' },
  iconBgPurple: { light: '#ede9fe', dark: '#2d1f5e' },
  iconBgRed: { light: '#fee2e2', dark: '#5c1a1a' },
} as const;

export const BRAND = {
  green: '#143d28',
  greenMuted: '#0a2818',
  gold: '#d4af7a',
  goldMuted: 'rgba(212, 175, 122, 0.5)',
  goldBorder: 'rgba(212, 175, 122, 0.18)',
  textNeutral: '#d4d4cc',
  textBright: '#f5f1e8',
  onlineBg: 'rgba(151, 196, 89, 0.12)',
  onlineText: '#b3d77a',
  onlineDot: '#97c459',
  offlineBg: 'rgba(255, 255, 255, 0.08)',
} as const;

export const THEME_MODE_KEY = 'puf-theme-mode';

export type ThemeMode = 'light' | 'dark' | 'system';

export function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function getStoredThemeMode(): ThemeMode {
  if (typeof window === 'undefined') return 'system';
  try {
    const stored = localStorage.getItem(THEME_MODE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  } catch { /* ignore */ }
  return 'system';
}

export function resolveThemeMode(mode: ThemeMode): 'light' | 'dark' {
  return mode === 'system' ? getSystemTheme() : mode;
}

export function createAppTheme(_mode: 'light' | 'dark') {
  return createTheme({
    cssVariables: true,
    colorSchemes: {
      light: {
        palette: {
          primary: { main: '#143d28', light: '#1f5234', dark: '#0a2818', contrastText: '#f5f1e8' },
          secondary: { main: '#d4af7a', light: '#e0c397', dark: '#b8945f', contrastText: '#143d28' },
          background: { default: '#f7f5ef', paper: '#ffffff' },
          text: { primary: '#1f2937', secondary: '#4b5563' },
          divider: '#e5e7eb',
        },
      },
      dark: {
        palette: {
          primary: { main: '#2d8a56', light: '#3aad6e', dark: '#1a5c3a', contrastText: '#ffffff' },
          secondary: { main: '#d4af7a', light: '#e0c397', dark: '#b8945f', contrastText: '#0a0a0a' },
          background: { default: '#121212', paper: '#1e1e1e' },
          text: { primary: '#e5e5e5', secondary: '#a3a3a3' },
          divider: '#2e2e2e',
          error: { main: '#f87171' },
          warning: { main: '#fbbf24' },
          success: { main: '#4ade80' },
          info: { main: '#60a5fa' },
        },
      },
    },
    shape: {
      borderRadius: 10,
    },
    typography: {
      fontFamily: '"Jost", "Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      h1: { fontWeight: 700, fontFamily: '"Fraunces", Georgia, serif' },
      h2: { fontWeight: 700, fontFamily: '"Fraunces", Georgia, serif' },
      h3: { fontWeight: 700, fontFamily: '"Fraunces", Georgia, serif' },
      h4: { fontWeight: 700, fontFamily: '"Fraunces", Georgia, serif' },
      h5: { fontWeight: 700, fontFamily: '"Fraunces", Georgia, serif' },
      h6: { fontFamily: '"Jost", "Inter", sans-serif', fontWeight: 600 },
    },
    components: {
      MuiPaper: {
        styleOverrides: {
          root: {
            borderRadius: 12,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 12,
          },
        },
      },
      MuiContainer: {
        styleOverrides: {
          root: {
            paddingLeft: '1rem',
            paddingRight: '1rem',
          },
        },
      },
      MuiTypography: {
        styleOverrides: {
          h6: { fontWeight: 700 },
          subtitle1: { fontWeight: 600 },
        },
      },
    },
  });
}

export const theme = createAppTheme('light');
