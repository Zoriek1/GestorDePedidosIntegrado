/**
 * Orders Pagination Component
 */

import { Box, Pagination, FormControl, InputLabel, Select, MenuItem, SelectChangeEvent, Typography } from '@mui/material';

export interface OrdersPaginationProps {
  page: number;
  perPage: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPerPageChange: (perPage: number) => void;
}

const PER_PAGE_OPTIONS = [10, 20, 50, 100];

export function OrdersPagination({
  page,
  perPage,
  total,
  totalPages,
  onPageChange,
  onPerPageChange,
}: OrdersPaginationProps) {
  const handlePerPageChange = (event: SelectChangeEvent<number>) => {
    onPerPageChange(event.target.value as number);
  };

  if (totalPages <= 1) {
    return null;
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2, mt: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Mostrando {((page - 1) * perPage) + 1} - {Math.min(page * perPage, total)} de {total} pedidos
        </Typography>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel id="per-page-label">Por página</InputLabel>
          <Select
            labelId="per-page-label"
            id="per-page-select"
            value={perPage}
            label="Por página"
            onChange={handlePerPageChange}
          >
            {PER_PAGE_OPTIONS.map((option) => (
              <MenuItem key={option} value={option}>
                {option}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>
      <Pagination
        count={totalPages}
        page={page}
        onChange={(_event, value) => onPageChange(value)}
        color="primary"
        showFirstButton
        showLastButton
      />
    </Box>
  );
}
