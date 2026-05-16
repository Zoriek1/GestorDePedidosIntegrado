/**
 * Status Multi-Select Component
 * Permite selecionar múltiplos status simultaneamente
 */

import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  Chip,
  OutlinedInput,
  SelectChangeEvent,
} from '@mui/material';

export interface StatusMultiSelectProps {
  value: string[];
  onChange: (statuses: string[]) => void;
}

const STATUS_OPTIONS = [
  { value: 'agendado', label: 'Agendado' },
  { value: 'em_producao', label: 'Em Produção' },
  { value: 'pronto_entrega', label: 'Pronto Entrega' },
  { value: 'pronto_retirada', label: 'Pronto Retirada' },
  { value: 'em_rota', label: 'Em Rota' },
  { value: 'concluido', label: 'Concluído' },
  { value: 'atrasado', label: 'Atrasado' },
];

export function StatusMultiSelect({ value, onChange }: StatusMultiSelectProps) {
  const handleChange = (event: SelectChangeEvent<string[]>) => {
    const {
      target: { value: selected },
    } = event;
    // On autofill we get a stringified value.
    const newValue = typeof selected === 'string' ? selected.split(',') : selected;
    onChange(newValue);
  };

  return (
    <FormControl fullWidth size="small">
      <InputLabel id="status-multi-select-label">Status</InputLabel>
      <Select
        labelId="status-multi-select-label"
        id="status-multi-select"
        multiple
        value={value}
        onChange={handleChange}
        input={<OutlinedInput label="Status" />}
        renderValue={(selected) => (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {selected.map((val) => {
              const option = STATUS_OPTIONS.find((opt) => opt.value === val);
              return (
                <Chip key={val} label={option?.label || val} size="small" />
              );
            })}
          </Box>
        )}
      >
        {STATUS_OPTIONS.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            <Checkbox checked={value.indexOf(option.value) > -1} />
            <ListItemText primary={option.label} />
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
