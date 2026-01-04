import { Tabs, Tab } from '@mui/material';

export interface StatusTabsProps {
  value: string;
  onChange: (status: string) => void;
}

const STATUS_TABS = [
  { value: '', label: 'Todos' },
  { value: 'agendado', label: 'Agendado' },
  { value: 'em_producao', label: 'Produção' },
  { value: 'pronto_entrega', label: 'Pronto Entrega' },
  { value: 'pronto_retirada', label: 'Pronto Retirada' },
  { value: 'em_rota', label: 'Em Rota' },
  { value: 'concluido', label: 'Concluídos' },
];

export function StatusTabs({ value, onChange }: StatusTabsProps) {
  return (
    <Tabs
      value={value}
      onChange={(_e, v) => onChange(v)}
      variant="scrollable"
      scrollButtons="auto"
      allowScrollButtonsMobile
      sx={{
        '.MuiTab-root': { textTransform: 'none', fontWeight: 600, minHeight: 44 },
      }}
    >
      {STATUS_TABS.map((tab) => (
        <Tab key={tab.value} label={tab.label} value={tab.value} />
      ))}
    </Tabs>
  );
}


