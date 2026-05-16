/**
 * Currency formatting utilities
 * Unified BRL currency formatting
 */

/**
 * Format value as Brazilian Real (BRL)
 * @param value - Number or string to format
 * @returns Formatted string like "R$ 1.234,56"
 */
export function formatBRL(value: number | string): string {
  let numValue: number | undefined;

  if (typeof value === 'string') {
    // Tentar interpretar string BR (ex: "R$ 1.234,56")
    const cleaned = value.replace(/[^\d,.-]/g, '');
    if (cleaned.includes(',')) {
      numValue = parseFloat(cleaned.replace(/\./g, '').replace(',', '.'));
    } else {
      numValue = parseFloat(cleaned);
    }
  } else {
    numValue = value;
  }

  if (numValue === undefined || Number.isNaN(numValue)) {
    return 'R$ 0,00';
  }

  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(numValue);
}

