/**
 * Test Offline Page
 * Dev-only page to test offline mutation flow
 */

import { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  TextField,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip
} from '@mui/material';
import { useCreatePedido, useUpdatePedido } from '../../api/endpoints/pedidos';
import { useOffline } from '../../lib/offline/OfflineProvider';
import { getQueue, removeOutboxItem } from '../../lib/offline/outbox';
import type { OutboxEntry } from '../../lib/offline/db';
import { useQuery } from '@tanstack/react-query';
import { formatDateTimeBR } from '../../lib/format/date';

export default function TestOfflinePage() {
  const [orderId, setOrderId] = useState<string>('');
  const { isOnline, outboxCount, flush } = useOffline();
  const createMutation = useCreatePedido();
  const updateMutation = useUpdatePedido();

  const { data: queue } = useQuery({
    queryKey: ['outbox-queue'],
    queryFn: getQueue,
    refetchInterval: 2000
  });

  const handleTestCreate = async () => {
    try {
      await createMutation.mutateAsync({
        cliente: 'Cliente Teste',
        telefone_cliente: '(62) 99999-9999',
        destinatario: 'Destinatário Teste',
        tipo_pedido: 'Entrega',
        produto: 'Buquê de Rosas',
        dia_entrega: new Date().toISOString().split('T')[0],
        horario: '14:00',
        quantidade: 1
      });
    } catch {
      // Error is expected when offline (OFFLINE_ENQUEUED)
    }
  };

  const handleTestUpdate = async () => {
    if (!orderId) {
      alert('Digite um ID de pedido');
      return;
    }
    try {
      await updateMutation.mutateAsync({
        id: parseInt(orderId),
        produto: 'Buquê Atualizado - ' + new Date().toLocaleTimeString()
      });
    } catch {
      // Error is expected when offline (OFFLINE_ENQUEUED)
    }
  };

  const handleRemoveItem = async (id: number) => {
    await removeOutboxItem(id);
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Teste Offline
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Esta página é para testes de funcionalidade offline. Desative a internet para testar o outbox.
      </Alert>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Status
        </Typography>
        <Chip
          label={isOnline ? 'Online' : 'Offline'}
          color={isOnline ? 'success' : 'default'}
          sx={{ mr: 2 }}
        />
        <Chip
          label={`Outbox: ${outboxCount} item(ns)`}
          color={outboxCount > 0 ? 'warning' : 'default'}
        />
        <Button
          variant="contained"
          onClick={flush}
          disabled={!isOnline || outboxCount === 0}
          sx={{ ml: 2 }}
        >
          Forçar Sincronização
        </Button>
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Testar Mutations
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <Button
            variant="contained"
            onClick={handleTestCreate}
            disabled={createMutation.isPending}
          >
            Criar Pedido (Teste)
          </Button>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField
              label="ID do Pedido"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              size="small"
              type="number"
            />
            <Button
              variant="contained"
              onClick={handleTestUpdate}
              disabled={updateMutation.isPending || !orderId}
            >
              Atualizar Pedido
            </Button>
          </Box>
        </Box>
        {createMutation.isError && (
          <Alert severity={createMutation.error?.message === 'OFFLINE_ENQUEUED' ? 'info' : 'error'} sx={{ mt: 2 }}>
            {createMutation.error?.message === 'OFFLINE_ENQUEUED' 
              ? 'Pedido enfileirado para sincronização offline'
              : createMutation.error?.message}
          </Alert>
        )}
        {updateMutation.isError && (
          <Alert severity={updateMutation.error?.message === 'OFFLINE_ENQUEUED' ? 'info' : 'error'} sx={{ mt: 2 }}>
            {updateMutation.error?.message === 'OFFLINE_ENQUEUED'
              ? 'Atualização enfileirada para sincronização offline'
              : updateMutation.error?.message}
          </Alert>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Fila de Outbox
        </Typography>
        {queue && queue.length > 0 ? (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Tipo</TableCell>
                  <TableCell>Criado em</TableCell>
                  <TableCell>Tentativas</TableCell>
                  <TableCell>Último Erro</TableCell>
                  <TableCell>Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {queue.map((item: OutboxEntry) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.id}</TableCell>
                    <TableCell>
                      <Chip label={item.type} size="small" />
                    </TableCell>
                    <TableCell>
                      {formatDateTimeBR(new Date(item.createdAt))}
                    </TableCell>
                    <TableCell>{item.attempts}</TableCell>
                    <TableCell>
                      {item.lastError ? (
                        <Typography variant="body2" color="error">
                          {item.lastError}
                        </Typography>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => item.id && handleRemoveItem(item.id)}
                      >
                        Remover
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Nenhum item na fila
          </Typography>
        )}
      </Paper>
    </Box>
  );
}

