import { createTheme } from '@mui/material/styles';

export const SEMANTIC = {
  success: '#16a34a',
  warning: '#f59e0b',
  error: '#dc2626',
  info: '#2563eb',
  purple: '#7c3aed',
  sky: '#0ea5e9',
  iconBgBlue: '#e0f2fe',
  iconBgGray: '#f3f4f6',
  iconBgYellow: '#fef9c3',
  iconBgGreen: '#dcfce7',
  iconBgPurple: '#ede9fe',
  iconBgRed: '#fee2e2',
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

export const theme = createTheme({
  palette: {
    primary: { main: '#143d28', light: '#1f5234', dark: '#0a2818', contrastText: '#f5f1e8' },
    secondary: { main: '#d4af7a', light: '#e0c397', dark: '#b8945f', contrastText: '#143d28' },
    background: {
      default: '#f7f5ef',
      paper: '#ffffff',
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
    body1: { color: '#1f2937' },
    body2: { color: '#4b5563' },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 10px 30px -12px rgba(0,0,0,0.18)',
          borderRadius: 12,
          border: '1px solid #e5e7eb',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 10px 30px -12px rgba(0,0,0,0.20)',
          borderRadius: 12,
          border: '1px solid #e5e7eb',
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
