/**
 * QuickEntryModal - Modal de Entrada Rápida de Pedidos
 * Permite colar texto do cliente e extrair campos automaticamente.
 * Redireciona para o wizard com dados pré-preenchidos.
 */

import React, { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
<<<<<<< HEAD
=======
import { createLogger } from '../../../lib/logger';

const log = createLogger('QuickEntryModal');
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  Typography,
  Button,
  Box,
  TextField,
  Alert,
  Chip,
  Collapse,
  IconButton,
  Tooltip,
  Divider,
} from '@mui/material';
import BoltIcon from '@mui/icons-material/Bolt';
import ContentPasteIcon from '@mui/icons-material/ContentPaste';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CloseIcon from '@mui/icons-material/Close';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import LanguageIcon from '@mui/icons-material/Language';
import { useFontesPedido } from '../../../api/endpoints/fontes';
import { parseQuickEntry, QUICK_ENTRY_TEMPLATE } from '../utils/quickEntryParser';
import { useToast } from '../../../components/system/useToast';

interface QuickEntryModalProps {
  open: boolean;
  onClose: () => void;
}

// Mapeamento de fontes para ícones
const matchFonte = (fontes: Array<{ id: number; nome: string }>, ...keywords: string[]) => {
  const lowerKeywords = keywords.map((k) => k.toLowerCase());
  const found = fontes.find((f) => {
    const name = f.nome.toLowerCase();
    return lowerKeywords.every((k) => name.includes(k));
  });
  return found?.id;
};

export function QuickEntryModal({ open, onClose }: QuickEntryModalProps) {
  const navigate = useNavigate();
  const { success, warning } = useToast();
  const { data, isLoading } = useFontesPedido(true);
  
  const [text, setText] = useState('');
  const [fonteSelecionada, setFonteSelecionada] = useState<number | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  // Memoizar fontes
  const fontes = useMemo(() => data?.fontes || [], [data?.fontes]);
  
  // Fontes mapeadas com ícones
  const fontesButtons = useMemo(() => {
    const whatsappId = matchFonte(fontes, 'whatsapp') ?? matchFonte(fontes, 'zap') ?? matchFonte(fontes, 'caio');
    const catalogoId = matchFonte(fontes, 'catalogo') ?? matchFonte(fontes, 'catálogo');
    const siteId = matchFonte(fontes, 'site');

    return [
      { id: whatsappId ?? -1, label: 'WhatsApp', icon: <WhatsAppIcon fontSize="small" /> },
      { id: catalogoId ?? -1, label: 'Catálogo', icon: <MenuBookIcon fontSize="small" /> },
      { id: siteId ?? -1, label: 'Site', icon: <LanguageIcon fontSize="small" /> },
    ];
  }, [fontes]);
  
  // Handler para colar texto
  const handlePaste = useCallback(async () => {
    try {
      const clipboardText = await navigator.clipboard.readText();
      setText(clipboardText);
    } catch {
<<<<<<< HEAD
      console.warn('Não foi possível acessar a área de transferência');
    }
  }, []);
  
=======
      log.warn('Não foi possível acessar a área de transferência');
    }
  }, []);

>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
  // Handler para copiar template
  const handleCopyTemplate = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(QUICK_ENTRY_TEMPLATE);
      success('Template copiado para a área de transferência!');
    } catch {
<<<<<<< HEAD
      console.warn('Não foi possível copiar para a área de transferência');
=======
      log.warn('Não foi possível copiar para a área de transferência');
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
    }
  }, [success]);
  
  // Handler para processar texto
  const handleProcess = useCallback(() => {
    if (!fonteSelecionada) {
      warning('Selecione uma fonte de pedido primeiro');
      return;
    }
    
    if (!text.trim()) {
      warning('Cole o texto do cliente antes de processar');
      return;
    }
    
    // Processar texto
    const result = parseQuickEntry(text, fonteSelecionada);
    // resultado utilizado para UI / logs futuros
    
    // Navegar para página de criação com dados pré-preenchidos
    navigate('/pedidos/novo', {
      state: {
        prefillData: result.formData,
        quickEntryWarnings: result.warnings,
        orderReset: Date.now(),
      },
    });
    
    // Limpar e fechar
    setText('');
    setFonteSelecionada(null);
    onClose();
    
    // Feedback
    if (result.warnings.length > 0) {
      warning(`${result.extractedFields.length} campos extraídos, ${result.warnings.length} avisos`);
    } else {
      success(`${result.extractedFields.length} campos extraídos com sucesso!`);
    }
  }, [text, fonteSelecionada, navigate, onClose, success, warning]);
  
  // Handler para fechar
  const handleClose = useCallback(() => {
    setText('');
    setFonteSelecionada(null);
    setShowHelp(false);
    onClose();
  }, [onClose]);
  
  // Preview do parse (quando tem texto)
  const preview = useMemo(() => {
    if (!text.trim() || !fonteSelecionada) return null;
    return parseQuickEntry(text, fonteSelecionada);
  }, [text, fonteSelecionada]);
  
  return (
    <Dialog 
      open={open} 
      onClose={handleClose} 
      fullWidth 
      maxWidth="sm"
      PaperProps={{
        sx: { borderRadius: 2 }
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, pb: 1 }}>
        <BoltIcon color="warning" />
        <Typography variant="h6" component="span" sx={{ flexGrow: 1 }}>
          Entrada Rápida de Pedido
        </Typography>
        <IconButton size="small" onClick={handleClose}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      
      <DialogContent sx={{ pt: 1 }}>
        <Stack spacing={2}>
          {/* Seleção de Fonte */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              1. Selecione a fonte do pedido:
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {fontesButtons.map((fonte) => (
                <Chip
                  key={fonte.label}
                  icon={fonte.icon}
                  label={fonte.label}
                  variant={fonteSelecionada === fonte.id ? 'filled' : 'outlined'}
                  color={fonteSelecionada === fonte.id ? 'primary' : 'default'}
                  disabled={isLoading || fonte.id === -1}
                  onClick={() => setFonteSelecionada(fonte.id)}
                  sx={{ cursor: 'pointer' }}
                />
              ))}
              {/* Fallback para outras fontes */}
              {fontes.filter(f => !fontesButtons.some(fb => fb.id === f.id && fb.id !== -1)).map((fonte) => (
                <Chip
                  key={fonte.id}
                  label={fonte.nome}
                  variant={fonteSelecionada === fonte.id ? 'filled' : 'outlined'}
                  color={fonteSelecionada === fonte.id ? 'primary' : 'default'}
                  onClick={() => setFonteSelecionada(fonte.id)}
                  sx={{ cursor: 'pointer' }}
                />
              ))}
            </Stack>
          </Box>
          
          {/* Textarea para texto */}
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="subtitle2">
                2. Cole o texto do cliente:
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                <Tooltip title="Colar da área de transferência">
                  <IconButton size="small" onClick={handlePaste}>
                    <ContentPasteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Ver formato esperado">
                  <IconButton size="small" onClick={() => setShowHelp(!showHelp)}>
                    {showHelp ? <ExpandLessIcon fontSize="small" /> : <HelpOutlineIcon fontSize="small" />}
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
            
            {/* Ajuda com formato */}
            <Collapse in={showHelp}>
              <Alert 
                severity="info" 
                sx={{ mb: 1 }}
                action={
                  <Button size="small" onClick={handleCopyTemplate}>
                    Copiar Template
                  </Button>
                }
              >
                <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                  {QUICK_ENTRY_TEMPLATE}
                </Typography>
              </Alert>
            </Collapse>
            
            <TextField
              multiline
              rows={8}
              fullWidth
              placeholder="Cole aqui o texto do cliente com as informações do pedido..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                }
              }}
            />
          </Box>
          
          {/* Preview dos campos extraídos */}
          {preview && (
            <Box>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Preview dos campos extraídos:
              </Typography>
              
              {/* Campos extraídos com sucesso */}
              {preview.extractedFields.length > 0 && (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
                  {preview.extractedFields.map((field) => (
                    <Chip
                      key={field}
                      label={field}
                      size="small"
                      color="success"
                      icon={<CheckCircleIcon />}
                      variant="outlined"
                    />
                  ))}
                </Box>
              )}
              
              {/* Warnings */}
              {preview.warnings.length > 0 && (
                <Alert severity="warning" sx={{ mt: 1 }}>
                  <Typography variant="body2" fontWeight="bold" sx={{ mb: 0.5 }}>
                    Campos não encontrados/inválidos:
                  </Typography>
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {preview.warnings.map((warn, idx) => (
                      <li key={idx}>
                        <Typography variant="caption">{warn}</Typography>
                      </li>
                    ))}
                  </ul>
                </Alert>
              )}
            </Box>
          )}
        </Stack>
      </DialogContent>
      
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} color="inherit">
          Cancelar
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleProcess}
          disabled={!fonteSelecionada || !text.trim()}
          startIcon={<BoltIcon />}
        >
          Processar e Preencher Formulário
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default QuickEntryModal;
