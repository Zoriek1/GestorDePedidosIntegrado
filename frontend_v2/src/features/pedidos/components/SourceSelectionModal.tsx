import React, { useMemo } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Stack,
  Typography,
  Button,
  Box,
  Divider,
} from '@mui/material';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import LanguageIcon from '@mui/icons-material/Language';
import { useFontesPedido } from '../../../api/endpoints/fontes';

interface SourceSelectionModalProps {
  open: boolean;
  onConfirm: (fonteId: number) => void;
}

type FonteMapped = {
  id: number;
  label: string;
  description: string;
  icon: React.ReactNode;
};

const matchFonte = (fontes: Array<{ id: number; nome: string }>, ...keywords: string[]) => {
  const lowerKeywords = keywords.map((k) => k.toLowerCase());
  const found = fontes.find((f) => {
    const name = f.nome.toLowerCase();
    return lowerKeywords.every((k) => name.includes(k));
  });
  return found?.id;
};

export function SourceSelectionModal({ open, onConfirm }: SourceSelectionModalProps) {
  const { data, isLoading } = useFontesPedido(true);
  const fontes = data?.fontes || [];

  // Memoizar fontes para evitar recálculos desnecessários
  const fontesMemo = useMemo(() => fontes, [fontes]);
  
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const mapped: FonteMapped[] = useMemo(() => {
    const whatsappId = matchFonte(fontesMemo, 'whatsapp') ?? matchFonte(fontesMemo, 'zap') ?? matchFonte(fontesMemo, 'caio');
    const catalogoId = matchFonte(fontesMemo, 'catalogo') ?? matchFonte(fontesMemo, 'catálogo');
    const siteId = matchFonte(fontesMemo, 'site');

    return [
      {
        id: whatsappId ?? -1,
        label: 'WhatsApp (Caio)',
        description: 'Atendimento direto via WhatsApp',
        icon: <WhatsAppIcon color="success" />,
      },
      {
        id: catalogoId ?? -1,
        label: 'Catálogo',
        description: 'Pedidos vindos do catálogo digital',
        icon: <MenuBookIcon color="primary" />,
      },
      {
        id: siteId ?? -1,
        label: 'Site',
        description: 'Pedidos recebidos pelo site',
        icon: <LanguageIcon color="info" />,
      },
    ];
  }, [fontesMemo]);

  const handleSelect = (id: number) => {
    if (id === -1) return;
    onConfirm(id);
  };

  const showManualFallback =
    !isLoading &&
    fontes.length > 0 &&
    mapped.some((m) => m.id === -1);

  return (
    <Dialog open={open} disableEscapeKeyDown fullWidth maxWidth="xs">
      <DialogTitle>Selecione a Fonte do Pedido</DialogTitle>
      <DialogContent sx={{ pt: 1 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Esta informação é obrigatória antes de iniciar o cadastro. Após selecionar, ficará somente leitura.
        </Typography>
        <Stack spacing={1.5}>
          {mapped.map((item) => (
            <Button
              key={item.label}
              variant="outlined"
              fullWidth
              disabled={isLoading || item.id === -1}
              onClick={() => handleSelect(item.id)}
              sx={{
                justifyContent: 'flex-start',
                textTransform: 'none',
                p: 2,
                borderRadius: 2,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                {item.icon}
                <Box textAlign="left">
                  <Typography variant="subtitle1" fontWeight="bold">
                    {item.label}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {item.description}
                  </Typography>
                </Box>
              </Box>
            </Button>
          ))}
          {mapped.some((m) => m.id === -1) && (
            <Typography variant="caption" color="text.secondary">
              Fonte não encontrada? Garanta que “WhatsApp”, “Catálogo” ou “Site” existam no cadastro.
            </Typography>
          )}
        </Stack>

        {showManualFallback && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Seleção manual (fallback)
            </Typography>
            <Stack spacing={1}>
              {fontes.map((fonte) => (
                <Button
                  key={fonte.id}
                  variant="text"
                  onClick={() => onConfirm(fonte.id)}
                  sx={{ justifyContent: 'flex-start', textTransform: 'none' }}
                >
                  {fonte.nome}
                </Button>
              ))}
            </Stack>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default SourceSelectionModal;

