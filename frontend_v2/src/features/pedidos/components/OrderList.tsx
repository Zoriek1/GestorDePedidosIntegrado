/**
 * Order List component
 */

import { useState, useMemo } from 'react';
import { Grid, Box, Typography, Paper, Collapse, IconButton } from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';
import type { Pedido } from '../../../api/endpoints/pedidos';
import { OrderCard } from './OrderCard';
import { groupOrdersByDate } from '../utils/dateGrouping';
import { useUsers } from '../../users/services/userApi';
import { useAuth } from '../../auth/authStore';

interface OrderListProps {
  pedidos: Pedido[];
  onOrderClick?: (pedido: Pedido) => void;
  selectionMode?: boolean;
  selectedIds?: Set<number>;
  onToggleSelect?: (pedido: Pedido) => void;
}

export function OrderList({ pedidos, onOrderClick, selectionMode = false, selectedIds, onToggleSelect }: OrderListProps) {
  const { getUserRole, getUser } = useAuth();
  const userRole = getUserRole();
  const currentUser = getUser();
  const { data: users } = useUsers(userRole === 'admin');

  const sellerNameById = useMemo<Record<number, string>>(() => {
    const map: Record<number, string> = {};
    (users || []).forEach((user) => {
      map[user.id] = user.name;
    });
    if (currentUser?.id && currentUser?.name) {
      map[currentUser.id] = currentUser.name;
    }
    return map;
  }, [users, currentUser]);

  // Filtrar pedidos deletados (segurança extra)
  const pedidosValidos = pedidos.filter(p => !p.deleted_at);
  
  // Agrupar pedidos por data
  const grupos = useMemo(() => groupOrdersByDate(pedidosValidos), [pedidosValidos]);
  
  // Estado para controlar quais grupos estão expandidos
  // Por padrão, apenas "HOJE" está expandido
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => {
    const initialGroups = groupOrdersByDate(pedidosValidos);
    const hojeGroup = initialGroups.find((g) => g.label === 'HOJE');
    return hojeGroup ? new Set(['HOJE']) : new Set();
  });

  const toggleGroup = (label: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  };

  if (pedidosValidos.length === 0) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="200px"
        p={3}
      >
        <Typography variant="body1" color="text.secondary">
          Nenhum pedido encontrado
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {grupos.map((grupo) => {
        const isExpanded = expandedGroups.has(grupo.label);
        
        return (
          <Box key={grupo.label} sx={{ mb: 3 }}>
            {/* Card/Header do grupo - clicável */}
            <Paper
              elevation={isExpanded ? 3 : 1}
              onClick={() => toggleGroup(grupo.label)}
              sx={{
                p: 2,
                mb: isExpanded ? 2 : 1,
                backgroundColor: isExpanded ? 'primary.main' : 'action.hover',
                color: isExpanded ? 'primary.contrastText' : 'text.primary',
                cursor: 'pointer',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  backgroundColor: isExpanded ? 'primary.dark' : 'action.selected',
                  elevation: 4,
                  transform: 'translateY(-1px)',
                },
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderLeft: isExpanded ? '4px solid' : '4px solid transparent',
                borderColor: isExpanded ? 'primary.contrastText' : 'transparent',
              }}
            >
              <Box sx={{ flex: 1 }}>
                <Typography 
                  variant="h6" 
                  component="h2" 
                  fontWeight="bold"
                  sx={{ 
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                  }}
                >
                  {grupo.label}
                  {!isExpanded && (
                    <Typography 
                      component="span" 
                      variant="caption" 
                      sx={{ 
                        opacity: 0.8,
                        fontWeight: 'normal',
                        ml: 0.5,
                        color: 'inherit',
                      }}
                    >
                      ({grupo.pedidos.length})
                    </Typography>
                  )}
                </Typography>
                {isExpanded && (
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      opacity: 0.9, 
                      mt: 0.5,
                      color: 'inherit',
                    }}
                  >
                    {grupo.pedidos.length} pedido{grupo.pedidos.length !== 1 ? 's' : ''}
                  </Typography>
                )}
              </Box>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleGroup(grupo.label);
                }}
                sx={{
                  color: isExpanded ? 'primary.contrastText' : 'text.secondary',
                  '&:hover': {
                    backgroundColor: isExpanded ? 'rgba(255, 255, 255, 0.1)' : 'action.hover',
                  },
                }}
              >
                {isExpanded ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            </Paper>

            {/* Grid de pedidos do grupo - colapsável */}
            <Collapse in={isExpanded} timeout="auto">
              <Grid container spacing={2}>
                {grupo.pedidos.map((pedido) => (
                  <Grid size={{ xs: 12, sm: 6, md: 4 }} key={pedido.id}>
                    <OrderCard
                      pedido={pedido}
                      sellerNameById={sellerNameById}
                      onClick={onOrderClick ? () => onOrderClick(pedido) : undefined}
                      selectable={selectionMode}
                      selected={selectedIds ? selectedIds.has(pedido.id) : false}
                      onToggleSelect={onToggleSelect}
                    />
                  </Grid>
                ))}
              </Grid>
            </Collapse>
          </Box>
        );
      })}
    </Box>
  );
}

