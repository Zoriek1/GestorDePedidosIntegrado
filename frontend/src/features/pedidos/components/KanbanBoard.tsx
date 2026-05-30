/**
 * Visão Kanban dos pedidos por status.
 *
 * Colunas espelham o fluxo operacional (Agendado → Em produção → Pronto → Em rota →
 * Concluído). Arrastar um card chama a mutation existente `useUpdatePedidoStatus`, com
 * atualização otimista + rollback em caso de erro. Reaproveita o `OrderCard`.
 */
import { useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Box, Paper, Typography, Stack, Chip, CircularProgress } from '@mui/material';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  useDroppable,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import type { Pedido, PedidosFilters } from '../../../api/endpoints/pedidos';
import { usePedidos, useUpdatePedidoStatus } from '../../../api/endpoints/pedidos';
import { useUsers } from '../../users/services/userApi';
import { useAuth } from '../../auth/authStore';
import { useToast } from '../../../components/system/useToast';
import { OrderCard } from './OrderCard';

interface ColumnDef {
  id: string;
  label: string;
  statuses: string[];
}

// "Pronto" reúne os dois sabores (entrega/retirada); o status concreto é resolvido no drop.
const COLUMNS: ColumnDef[] = [
  { id: 'agendado', label: 'Agendado', statuses: ['agendado'] },
  { id: 'em_producao', label: 'Em produção', statuses: ['em_producao'] },
  { id: 'pronto', label: 'Pronto', statuses: ['pronto_entrega', 'pronto_retirada'] },
  { id: 'em_rota', label: 'Em rota', statuses: ['em_rota'] },
  { id: 'concluido', label: 'Concluído', statuses: ['concluido'] },
];

const ENTREGADOR_COLUMN_IDS = ['agendado', 'em_rota'];

function isRetirada(p: Pedido): boolean {
  return (p.tipo_pedido || '').toLowerCase().includes('retirada');
}

function columnOf(status: string): string | undefined {
  return COLUMNS.find((c) => c.statuses.includes(status))?.id;
}

/** Status concreto ao soltar um pedido numa coluna. `null` = transição inválida. */
function targetStatus(columnId: string, p: Pedido): string | null {
  switch (columnId) {
    case 'agendado':
      return 'agendado';
    case 'em_producao':
      return 'em_producao';
    case 'pronto':
      return isRetirada(p) ? 'pronto_retirada' : 'pronto_entrega';
    case 'em_rota':
      return isRetirada(p) ? null : 'em_rota'; // retirada não vai para rota
    case 'concluido':
      return 'concluido';
    default:
      return null;
  }
}

function DraggableCard({
  pedido,
  sellerNameById,
}: {
  pedido: Pedido;
  sellerNameById: Record<number, string>;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: pedido.id,
  });
  return (
    <Box
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      style={{
        transform: transform ? `translate(${transform.x}px, ${transform.y}px)` : undefined,
        opacity: isDragging ? 0.4 : 1,
        touchAction: 'manipulation',
        cursor: 'grab',
      }}
      sx={{ mb: 2 }}
    >
      <OrderCard pedido={pedido} sellerNameById={sellerNameById} />
    </Box>
  );
}

function Column({
  col,
  pedidos,
  sellerNameById,
}: {
  col: ColumnDef;
  pedidos: Pedido[];
  sellerNameById: Record<number, string>;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: col.id });
  return (
    <Paper
      ref={setNodeRef}
      sx={{
        p: 1.5,
        width: 320,
        minWidth: 320,
        flexShrink: 0,
        bgcolor: isOver ? 'primary.50' : 'background.default',
        border: '1px solid',
        borderColor: isOver ? 'primary.main' : 'divider',
        maxHeight: 'calc(100vh - 280px)',
        overflowY: 'auto',
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
        <Typography variant="subtitle2" fontWeight={700}>
          {col.label}
        </Typography>
        <Chip size="small" label={pedidos.length} />
      </Stack>
      {pedidos.map((p) => (
        <DraggableCard key={p.id} pedido={p} sellerNameById={sellerNameById} />
      ))}
      {pedidos.length === 0 && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', py: 2 }}>
          Sem pedidos
        </Typography>
      )}
    </Paper>
  );
}

interface KanbanBoardProps {
  filters?: Pick<PedidosFilters, 'search' | 'data_inicio' | 'data_fim'>;
}

export function KanbanBoard({ filters }: KanbanBoardProps) {
  const { getUserRole, getUser } = useAuth();
  const role = getUserRole();
  const currentUser = getUser();
  const { success, error: showError } = useToast();
  const updateStatus = useUpdatePedidoStatus();
  const queryClient = useQueryClient();

  const { data, isLoading } = usePedidos({
    ...filters,
    per_page: 200,
    sort_by: 'dia_entrega',
    sort_order: 'asc',
  });
  const { data: users } = useUsers(role === 'admin');

  const sellerNameById = useMemo<Record<number, string>>(() => {
    const map: Record<number, string> = {};
    (users || []).forEach((u) => {
      map[u.id] = u.name;
    });
    if (currentUser?.id && currentUser?.name) map[currentUser.id] = currentUser.name;
    return map;
  }, [users, currentUser]);

  const [activeId, setActiveId] = useState<number | null>(null);

  const pedidos = useMemo<Pedido[]>(() => {
    if (data && typeof data === 'object' && 'pedidos' in data && Array.isArray(data.pedidos)) {
      return (data.pedidos as Pedido[]).filter((p) => !p.deleted_at);
    }
    return [];
  }, [data]);

  // Update otimista direto no cache do React Query (padrão idiomático): o card muda
  // de coluna na hora; a invalidação do onSuccess traz a verdade do servidor depois.
  const applyStatusToCache = (id: number, status: string) => {
    queryClient.setQueriesData<unknown>({ queryKey: ['pedidos'] }, (old) => {
      if (
        !old ||
        typeof old !== 'object' ||
        !('pedidos' in old) ||
        !Array.isArray((old as { pedidos: unknown }).pedidos)
      ) {
        return old;
      }
      const typed = old as { pedidos: Pedido[] };
      return {
        ...typed,
        pedidos: typed.pedidos.map((p) => (p.id === id ? { ...p, status } : p)),
      };
    });
  };

  const visibleColumns = useMemo(
    () =>
      role === 'entregador'
        ? COLUMNS.filter((c) => ENTREGADOR_COLUMN_IDS.includes(c.id))
        : COLUMNS,
    [role],
  );

  const byColumn = useMemo(() => {
    const map: Record<string, Pedido[]> = {};
    visibleColumns.forEach((c) => {
      map[c.id] = [];
    });
    pedidos.forEach((p) => {
      const c = columnOf(p.status);
      if (c && map[c]) map[c].push(p);
    });
    return map;
  }, [pedidos, visibleColumns]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const activePedido = activeId != null ? pedidos.find((p) => p.id === activeId) ?? null : null;

  const handleDragStart = (e: DragStartEvent) => setActiveId(Number(e.active.id));

  const handleDragEnd = async (e: DragEndEvent) => {
    setActiveId(null);
    const { active, over } = e;
    if (!over) return;
    const id = Number(active.id);
    const columnId = String(over.id);
    const pedido = pedidos.find((p) => p.id === id);
    if (!pedido || columnOf(pedido.status) === columnId) return;

    const target = targetStatus(columnId, pedido);
    if (!target) {
      showError('Pedido de retirada não vai para rota de entrega');
      return;
    }

    const prevStatus = pedido.status;
    applyStatusToCache(id, target);
    try {
      await updateStatus.mutateAsync({ id, status: target });
      success('Status atualizado');
    } catch {
      applyStatusToCache(id, prevStatus); // rollback
      showError('Erro ao atualizar status');
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" py={6}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <Box sx={{ display: 'flex', gap: 2, overflowX: 'auto', pb: 2 }}>
        {visibleColumns.map((col) => (
          <Column
            key={col.id}
            col={col}
            pedidos={byColumn[col.id] || []}
            sellerNameById={sellerNameById}
          />
        ))}
      </Box>
      <DragOverlay>
        {activePedido ? (
          <Box sx={{ width: 300 }}>
            <OrderCard pedido={activePedido} sellerNameById={sellerNameById} />
          </Box>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

export default KanbanBoard;
