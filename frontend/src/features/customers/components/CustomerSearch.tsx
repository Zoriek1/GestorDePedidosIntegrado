/**
 * Customer Search Component
 * Controlled input with debounce, focus-safe, virtualized results
 */

import { useRef } from 'react';
import {
  TextField,
  Box,
  List,
  ListItemButton,
  ListItemText,
  Typography,
  Paper,
  CircularProgress,
} from '@mui/material';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useDebouncedValue } from '../../../hooks/useDebouncedValue';
import { useCustomerSearch } from '../../../api/endpoints/customers';
import type { Customer } from '../../../api/endpoints/customers';

interface CustomerSearchProps {
  value: string;
  onChange: (value: string) => void;
  onSelect: (customer: Customer) => void;
  limit?: number;
  placeholder?: string;
}

const ROW_HEIGHT = 56; // Fixed height for virtualized rows
const MAX_DROPDOWN_HEIGHT = 300; // Maximum height of dropdown
const VIRTUALIZATION_THRESHOLD = 50; // Virtualize when > 50 items

export function CustomerSearch({
  value,
  onChange,
  onSelect,
  limit = 10,
  placeholder = 'Buscar cliente…',
}: CustomerSearchProps) {
  const debouncedQuery = useDebouncedValue(value.trim(), 300);
  const parentRef = useRef<HTMLDivElement>(null);

  const {
    data: searchData,
    isLoading,
    isFetching,
  } = useCustomerSearch(debouncedQuery, limit);

  const customers: Customer[] = searchData?.clientes || [];
  const showResults = debouncedQuery.length >= 2 && customers.length > 0;

  // Virtualizer for large lists
  // eslint-disable-next-line react-hooks/incompatible-library
  const virtualizer = useVirtualizer({
    count: customers.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 5,
  });

  const shouldVirtualize = customers.length > VIRTUALIZATION_THRESHOLD;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };

  const handleSelectCustomer = (customer: Customer) => {
    // Propaga seleção e garante que o input reflita o nome escolhido (controlled)
    onChange(customer.nome);
    onSelect(customer);
  };

  const virtualItems = shouldVirtualize ? virtualizer.getVirtualItems() : [];
  const totalHeight = shouldVirtualize
    ? virtualizer.getTotalSize()
    : customers.length * ROW_HEIGHT;
  const displayedHeight = Math.min(totalHeight, MAX_DROPDOWN_HEIGHT);

  return (
    <Box sx={{ position: 'relative', width: '100%' }}>
      <TextField
        fullWidth
        value={value}
        onChange={handleInputChange}
        placeholder={placeholder}
        inputMode="search"
        InputProps={{
          endAdornment: isFetching ? (
            <CircularProgress size={20} />
          ) : undefined,
        }}
        sx={{
          // Keep component stable - don't change key or remount
          '& .MuiOutlinedInput-root': {
            minHeight: '44px', // Touch target
          },
        }}
      />

      {showResults && (
        <Paper
          elevation={3}
          sx={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            zIndex: 1000,
            mt: 0.5,
            maxHeight: `${MAX_DROPDOWN_HEIGHT}px`,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {shouldVirtualize ? (
            <Box
              ref={parentRef}
              sx={{
                height: `${displayedHeight}px`,
                overflow: 'auto',
              }}
            >
              <Box
                sx={{
                  height: `${virtualizer.getTotalSize()}px`,
                  width: '100%',
                  position: 'relative',
                }}
              >
                {virtualItems.map((virtualItem) => {
                  const customer = customers[virtualItem.index];
                  return (
                    <Box
                      key={virtualItem.key}
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: `${virtualItem.size}px`,
                        transform: `translateY(${virtualItem.start}px)`,
                      }}
                    >
                      <ListItemButton
                        onClick={() => handleSelectCustomer(customer)}
                        sx={{
                          height: ROW_HEIGHT,
                          minHeight: '44px', // Touch target
                        }}
                      >
                        <ListItemText
                          primary={customer.nome}
                          secondary={customer.telefone}
                        />
                      </ListItemButton>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          ) : (
            <List
              sx={{
                maxHeight: `${MAX_DROPDOWN_HEIGHT}px`,
                overflow: 'auto',
                py: 0,
              }}
            >
              {customers.map((customer: Customer) => (
                <ListItemButton
                  key={customer.id}
                  onClick={() => handleSelectCustomer(customer)}
                  sx={{
                    minHeight: '44px', // Touch target
                  }}
                >
                  <ListItemText
                    primary={customer.nome}
                    secondary={customer.telefone}
                  />
                </ListItemButton>
              ))}
            </List>
          )}
        </Paper>
      )}

      {debouncedQuery.length >= 2 && !isLoading && !showResults && (
        <Paper
          elevation={3}
          sx={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            zIndex: 1000,
            mt: 0.5,
            p: 2,
          }}
        >
          <Typography variant="body2" color="text.secondary" align="center">
            Nenhum cliente encontrado
          </Typography>
        </Paper>
      )}
    </Box>
  );
}

