/**
 * Orders Sorting Component
 * Permite ordenar pedidos por diferentes campos
 */

import { FormControl, InputLabel, Select, MenuItem, SelectChangeEvent, Box } from '@mui/material';
import { ArrowUpward, ArrowDownward } from '@mui/icons-material';

export interface OrdersSortingProps {
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onChange: (sortBy: string, sortOrder: 'asc' | 'desc') => void;
}

const SORT_OPTIONS = [
  { value: 'dia_entrega', label: 'Data de Entrega' },
  { value: 'valor', label: 'Valor' },
  { value: 'cliente', label: 'Nome do Cliente' },
  { value: 'created_at', label: 'Data de Criação' },
];

export function OrdersSorting({ sortBy, sortOrder, onChange }: OrdersSortingProps) {
  const handleSortByChange = (event: SelectChangeEvent<string>) => {
    onChange(event.target.value, sortOrder);
  };

  const handleSortOrderChange = () => {
    onChange(sortBy, sortOrder === 'asc' ? 'desc' : 'asc');
  };

  return (
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
      <FormControl size="small" sx={{ minWidth: 150 }}>
        <InputLabel id="sort-by-label">Ordenar por</InputLabel>
        <Select
          labelId="sort-by-label"
          id="sort-by-select"
          value={sortBy}
          label="Ordenar por"
          onChange={handleSortByChange}
        >
          {SORT_OPTIONS.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <Box
        component="button"
        onClick={handleSortOrderChange}
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          p: 1,
          cursor: 'pointer',
          bgcolor: 'background.paper',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minWidth: 40,
          minHeight: 40,
          '&:hover': {
            bgcolor: 'action.hover',
          },
        }}
        aria-label={sortOrder === 'asc' ? 'Ordenar crescente' : 'Ordenar decrescente'}
      >
        {sortOrder === 'asc' ? <ArrowUpward fontSize="small" /> : <ArrowDownward fontSize="small" />}
      </Box>
    </Box>
  );
}
