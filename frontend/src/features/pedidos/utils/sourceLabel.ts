export interface SourceLabelInput {
  sourceName?: string;
  legacySource?: string;
  vendedorId?: number;
  vendedorName?: string;
  emptyLabel?: string;
}

function isWhatsAppSource(source: string): boolean {
  return source.trim().toLowerCase().startsWith('whatsapp');
}

export function formatOrderSourceLabel(input: SourceLabelInput): string {
  const emptyLabel = input.emptyLabel || 'Sem fonte';
  const baseSource = (input.sourceName || input.legacySource || emptyLabel).trim();
  if (!baseSource) return emptyLabel;

  if (!isWhatsAppSource(baseSource) || !input.vendedorId) {
    return baseSource;
  }

  const sellerName = (input.vendedorName || 'Vendedor').trim();
  return `WhatsApp: (${sellerName || 'Vendedor'})`;
}
