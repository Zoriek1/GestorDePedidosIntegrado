/**
 * Fontes de Pedido - CRUD completo
 */

import { useState } from 'react';
import { Box, Typography, Paper, List, ListItem, ListItemText, Chip, Stack, IconButton, Button, Tooltip } from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import { useFontesPedido, useCreateFonte, useUpdateFonte, useDeleteFonte, type FontePedido } from '../../api/endpoints/fontes';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { FonteDialog } from './components/FonteDialog';
import { useConfirm } from '../../components/system/useConfirm';

export default function FontesPage() {
  const { data, isLoading, error, refetch } = useFontesPedido(false);
  const createFonte = useCreateFonte();
  const updateFonte = useUpdateFonte();
  const deleteFonte = useDeleteFonte();
  const confirm = useConfirm();
  
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedFonte, setSelectedFonte] = useState<FontePedido | null>(null);

  const handleCreate = () => {
    setSelectedFonte(null);
    setDialogOpen(true);
  };

  const handleEdit = (fonte: FontePedido) => {
    setSelectedFonte(fonte);
    setDialogOpen(true);
  };

  const handleDelete = async (fonte: FontePedido) => {
    const confirmed = await confirm({
      title: 'Deletar fonte',
      description: `Tem certeza que deseja deletar a fonte "${fonte.nome}"? Esta ação não pode ser desfeita.`,
      confirmColor: 'error',
      confirmText: 'Deletar',
    });
    
    if (confirmed) {
      await deleteFonte.mutateAsync(fonte.id);
    }
  };

  const handleDialogSubmit = async (data: import('../../api/endpoints/fontes').CreateFontePayload | import('../../api/endpoints/fontes').UpdateFontePayload) => {
    if (selectedFonte) {
      await updateFonte.mutateAsync({ id: selectedFonte.id, payload: data as import('../../api/endpoints/fontes').UpdateFontePayload });
    } else {
      await createFonte.mutateAsync(data as import('../../api/endpoints/fontes').CreateFontePayload);
    }
    setDialogOpen(false);
    setSelectedFonte(null);
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4" component="h1">
          Fontes de Pedido
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleCreate}
        >
          Nova Fonte
        </Button>
      </Stack>

      <Paper>
        {isLoading ? (
          <Loading variant="skeleton" count={3} />
        ) : error ? (
          <ErrorState message="Erro ao carregar fontes" onRetry={() => refetch()} />
        ) : data?.fontes?.length ? (
          <List>
            {data.fontes.map((fonte) => (
              <ListItem 
                key={fonte.id} 
                divider
                secondaryAction={
                  <Stack direction="row" spacing={1}>
                    <Chip
                      label={fonte.ativo ? 'Ativa' : 'Inativa'}
                      color={fonte.ativo ? 'success' : 'default'}
                      size="small"
                    />
                    <Tooltip title="Editar">
                      <IconButton
                        edge="end"
                        onClick={() => handleEdit(fonte)}
                        size="small"
                      >
                        <Edit fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Deletar">
                      <IconButton
                        edge="end"
                        onClick={() => handleDelete(fonte)}
                        size="small"
                        color="error"
                      >
                        <Delete fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                }
              >
                <ListItemText
                  primary={fonte.nome}
                  secondary={`ID: ${fonte.id}`}
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Box p={2}>
            <Typography variant="body2" color="text.secondary">
              Nenhuma fonte cadastrada. Clique em "Nova Fonte" para criar uma.
            </Typography>
          </Box>
        )}
      </Paper>

      <FonteDialog
        open={dialogOpen}
        fonte={selectedFonte}
        onClose={() => {
          setDialogOpen(false);
          setSelectedFonte(null);
        }}
        onSubmit={handleDialogSubmit}
        isLoading={createFonte.isPending || updateFonte.isPending}
      />
    </Box>
  );
}


