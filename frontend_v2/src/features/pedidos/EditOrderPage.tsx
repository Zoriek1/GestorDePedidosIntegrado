import { useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Breadcrumbs, Link, Container, Paper } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import EditNoteIcon from '@mui/icons-material/EditNote';
import { usePedido, useUpdatePedido, type CreatePedidoPayload } from '../../api/endpoints/pedidos';
import { useToast } from '../../components/system/useToast';
import { Loading } from '../../components/common/Loading';
import { ErrorState } from '../../components/common/ErrorState';
import { CreateOrderWizard } from './CreateOrderWizard';
import { orderToForm } from './useCases/orderToForm';
import { OrderFormProvider } from './contexts/OrderFormContext';

export default function EditOrderPage() {
  const { id } = useParams<{ id: string }>();
  const pedidoId = useMemo(() => Number(id), [id]);
  const navigate = useNavigate();
  const { success, error: showError } = useToast();
  const { data, isLoading, error, refetch } = usePedido(pedidoId);
  const updatePedido = useUpdatePedido();

  const handleSubmit = useCallback(async (payload: Record<string, unknown>) => {
    try {
      await updatePedido.mutateAsync({ id: pedidoId, ...(payload as Partial<CreatePedidoPayload>) });
      success('Pedido atualizado com sucesso!');
      navigate(`/pedidos/${pedidoId}`);
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao atualizar pedido';
      showError(message);
      return false;
    }
  }, [updatePedido, pedidoId, navigate, success, showError]);

  const handleClearError = useCallback(() => {
    // noop
  }, []);

  if (isLoading) return <Loading />;
  if (error) return <ErrorState message={error.message || 'Erro ao carregar pedido'} onRetry={() => refetch()} />;
  if (!data?.pedido) return <ErrorState message="Pedido não encontrado" onRetry={() => refetch()} />;

  const initialData = orderToForm(data.pedido);

  return (
    <OrderFormProvider>
      <Container maxWidth={false} sx={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', py: { xs: 3, md: 6 } }}>
        <Paper
          elevation={4}
          sx={{
            width: '100%',
            maxWidth: 960,
            p: { xs: 2.5, md: 3.5 },
            borderRadius: 2,
            boxShadow: 6,
          }}
        >
          <Breadcrumbs sx={{ mb: 2 }}>
            <Link
              href="/"
              underline="hover"
              color="inherit"
              sx={{ display: 'flex', alignItems: 'center' }}
              onClick={(e) => {
                e.preventDefault();
                navigate('/');
              }}
            >
              <HomeIcon sx={{ mr: 0.5 }} fontSize="small" />
              Início
            </Link>
            <Typography color="text.primary" sx={{ display: 'flex', alignItems: 'center' }}>
              <EditNoteIcon sx={{ mr: 0.5 }} fontSize="small" />
              Editar Pedido #{pedidoId}
            </Typography>
          </Breadcrumbs>

          <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
            Editar Pedido #{pedidoId}
          </Typography>

          <CreateOrderWizard
            onSubmit={handleSubmit}
            isSubmitting={updatePedido.isPending}
            submitError={null}
            onClearError={handleClearError}
            initialData={initialData}
          />
        </Paper>
      </Container>
    </OrderFormProvider>
  );
}


