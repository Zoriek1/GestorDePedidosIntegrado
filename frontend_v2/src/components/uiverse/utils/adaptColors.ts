/**
 * Utilitário para adaptar cores do código Uiverse para variáveis CSS do tema
 * 
 * Uso: Substituir manualmente no CSS, mas este arquivo serve como referência
 */

export const THEME_COLORS = {
  // Cores principais
  primary: 'var(--color-primary)', // #047857
  primaryHover: 'var(--color-primary-hover)', // #059669
  primaryLight: 'var(--color-primary-light)', // #10b981
  secondary: 'var(--color-secondary)', // #2563eb
  
  // Superfícies
  surface: 'var(--color-surface)', // #ffffff
  surfaceAlt: 'var(--color-surface-alt)', // #f9fafb
  
  // Bordas
  border: 'var(--color-border)', // #e5e7eb
  
  // Texto
  text: 'var(--color-text)', // #111827
  textSecondary: 'var(--color-text-secondary)', // #4b5563
  
  // Neutros
  neutral50: 'var(--color-neutral-50)', // #f9fafb
  neutral100: 'var(--color-neutral-100)', // #f3f4f6
  neutral200: 'var(--color-neutral-200)', // #e5e7eb
  neutral300: 'var(--color-neutral-300)', // #d1d5db
  neutral600: 'var(--color-neutral-600)', // #4b5563
  neutral900: 'var(--color-neutral-900)', // #111827
} as const;

/**
 * Mapeamento comum de cores do Uiverse para tema
 * Use como referência ao adaptar CSS
 */
export const COLOR_MAPPING: Record<string, string> = {
  // Preto/Branco padrão → Tema
  '#000': THEME_COLORS.text,
  '#000000': THEME_COLORS.text,
  '#fff': THEME_COLORS.surface,
  '#ffffff': THEME_COLORS.surface,
  'black': THEME_COLORS.text,
  'white': THEME_COLORS.surface,
  
  // Cinzas → Neutros do tema
  '#333': THEME_COLORS.neutral600,
  '#666': THEME_COLORS.neutral600,
  '#999': THEME_COLORS.neutral300,
  '#ccc': THEME_COLORS.neutral200,
  '#eee': THEME_COLORS.neutral100,
  '#f5f5f5': THEME_COLORS.neutral50,
  
  // Azuis/Verdes genéricos → Primary
  '#007bff': THEME_COLORS.primary,
  '#0066cc': THEME_COLORS.primary,
  '#28a745': THEME_COLORS.primaryLight,
  'blue': THEME_COLORS.secondary,
  'green': THEME_COLORS.primary,
};

/**
 * Função helper para substituir cores em strings CSS
 * (Use como referência, adaptação manual é mais segura)
 */
export function adaptColorInCSS(cssString: string): string {
  let adapted = cssString;
  
  Object.entries(COLOR_MAPPING).forEach(([original, theme]) => {
    // Substituir cores exatas
    adapted = adapted.replace(new RegExp(original, 'gi'), theme);
  });
  
  return adapted;
}
