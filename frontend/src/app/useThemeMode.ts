import { useContext } from 'react';
import { ThemeContext } from './ThemeContext';

export function useThemeMode() {
  return useContext(ThemeContext);
}
