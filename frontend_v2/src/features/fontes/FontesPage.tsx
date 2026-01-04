/**
 * Fontes de Pedido - Listagem simples (paridade mínima com legado)
 */

import { Box, Typography, Paper, List, ListItem, ListItemText, Chip, Stack, Alert } from '@mui/material';
import { useFontesPedido } from '../../api/endpoints/fontes';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';

export default function FontesPage() {
  const { data, isLoading, error } = useFontesPedido(false);

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Fontes de Pedido
      </Typography>

      <Alert severity="info" sx={{ mb: 2 }}>
        Gestão simplificada das fontes de pedido. Edição/criação avançada pode ser adicionada em etapas futuras.
      </Alert>

      <Paper>
        {isLoading ? (
          <Loading variant="skeleton" count={3} />
        ) : error ? (
          <ErrorState message="Erro ao carregar fontes" onRetry={() => window.location.reload()} />
        ) : data?.fontes?.length ? (
          <List>
            {data.fontes.map((fonte) => (
              <ListItem key={fonte.id} divider>
                <ListItemText
                  primary={fonte.nome}
                  secondary={`ID: ${fonte.id}`}
                />
                <Stack direction="row" spacing={1}>
                  <Chip
                    label={fonte.ativo ? 'Ativa' : 'Inativa'}
                    color={fonte.ativo ? 'success' : 'default'}
                    size="small"
                  />
                </Stack>
              </ListItem>
            ))}
          </List>
        ) : (
          <Box p={2}>
            <Typography variant="body2" color="text.secondary">
              Nenhuma fonte cadastrada.
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
}


