import { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { CircleAlert, CircleCheck, FlaskConical, RefreshCw } from 'lucide-react';
import {
  type MarketingDestination,
  type MarketingDiagnosticResult,
  useMarketingConfig,
  useMarketingDiagnostic,
  useMarketingOutbox,
} from '../../api/endpoints/marketing';
import { ErrorState } from '../../components/common/ErrorState';
import { Loading } from '../../components/common/Loading';
import { useToast } from '../../components/system/useToast';

const destinations: Array<{ id: MarketingDestination; label: string }> = [
  { id: 'meta', label: 'Meta CAPI' },
  { id: 'ga4', label: 'Google Analytics 4' },
  { id: 'google_ads', label: 'Google Ads' },
];

function resultColor(result?: MarketingDiagnosticResult) {
  if (!result) return 'default' as const;
  if (result.ok) return 'success' as const;
  if (result.status === 'not_tested') return 'warning' as const;
  return 'error' as const;
}

function resultLabel(result?: MarketingDiagnosticResult) {
  if (!result) return 'Não testado';
  if (result.ok) return 'Validado';
  if (result.status === 'not_tested') return 'Código necessário';
  return 'Falhou';
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('pt-BR');
}

export default function MarketingPage() {
  const configQuery = useMarketingConfig();
  const outboxQuery = useMarketingOutbox();
  const diagnostic = useMarketingDiagnostic();
  const { success, error: showError } = useToast();
  const [metaTestEventCode, setMetaTestEventCode] = useState('');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<
    Partial<Record<MarketingDestination, MarketingDiagnosticResult>>
  >({});

  const runDiagnostics = async () => {
    setRunning(true);
    setResults({});
    try {
      const next: Partial<Record<MarketingDestination, MarketingDiagnosticResult>> = {};
      for (const destination of destinations) {
        try {
          next[destination.id] = await diagnostic.mutateAsync({
            destination: destination.id,
            metaTestEventCode: destination.id === 'meta' ? metaTestEventCode.trim() : undefined,
          });
        } catch (error) {
          next[destination.id] = {
            destination: destination.id,
            ok: false,
            status: 'failed',
            duration_ms: 0,
            error: error instanceof Error ? error.message : 'diagnostic_request_failed',
          };
        }
        setResults({ ...next });
      }
      const passed = Object.values(next).filter((item) => item?.ok).length;
      if (passed === destinations.length) success('Todas as integrações foram validadas');
      else showError(`${passed} de ${destinations.length} integrações validadas`);
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Falha ao executar os diagnósticos');
    } finally {
      setRunning(false);
      outboxQuery.refetch();
    }
  };

  if (configQuery.isLoading || outboxQuery.isLoading) return <Loading />;
  if (configQuery.isError) {
    return <ErrorState message={configQuery.error.message} onRetry={() => configQuery.refetch()} />;
  }

  const config = configQuery.data;
  const configured: Record<MarketingDestination, boolean> = {
    meta: Boolean(config?.meta.configured),
    ga4: Boolean(config?.ga4.configured),
    google_ads: Boolean(config?.google_ads.configured),
  };

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h6">Integrações de marketing</Typography>
        <Typography variant="body2" color="text.secondary">
          Valide credenciais e payloads sem criar pedido, lead, lançamento no Bling ou conversão
          real no Google Ads.
        </Typography>
      </Box>

      <Alert severity="info">
        Este diagnóstico confirma a comunicação com as APIs. A atribuição completa do Google Ads
        ainda exige um clique real no anúncio e um pedido concluído.
      </Alert>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' },
          gap: 2,
        }}
      >
        {destinations.map((destination) => {
          const result = results[destination.id];
          return (
            <Card key={destination.id} variant="outlined">
              <CardContent>
                <Stack spacing={1.5}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="subtitle1">{destination.label}</Typography>
                    <Chip
                      size="small"
                      label={configured[destination.id] ? 'Configurado' : 'Incompleto'}
                      color={configured[destination.id] ? 'success' : 'error'}
                      variant="outlined"
                    />
                  </Stack>
                  <Chip
                    icon={result?.ok ? <CircleCheck /> : result ? <CircleAlert /> : undefined}
                    label={resultLabel(result)}
                    color={resultColor(result)}
                    sx={{ alignSelf: 'flex-start' }}
                  />
                  {result && (
                    <Typography variant="caption" color="text.secondary">
                      HTTP {result.http_status ?? '—'} · {result.duration_ms} ms
                      {result.error ? ` · ${result.error}` : ''}
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Box>

      <Stack spacing={1} sx={{ maxWidth: 520 }}>
        <TextField
          label="Código do Meta Test Events"
          type="password"
          value={metaTestEventCode}
          onChange={(event) => setMetaTestEventCode(event.target.value)}
          helperText="Usado somente nesta requisição; não é salvo nem exibido nos resultados."
          size="small"
        />
        <Button
          variant="contained"
          startIcon={running ? <CircularProgress size={18} color="inherit" /> : <FlaskConical />}
          onClick={runDiagnostics}
          disabled={running}
        >
          {running ? 'Validando integrações…' : 'Validar integrações'}
        </Button>
      </Stack>

      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h6">Últimos envios reais</Typography>
          <Typography variant="body2" color="text.secondary">
            Os diagnósticos acima não aparecem nesta tabela.
          </Typography>
        </Box>
        <Button startIcon={<RefreshCw />} onClick={() => outboxQuery.refetch()}>
          Atualizar
        </Button>
      </Stack>

      {outboxQuery.isError ? (
        <ErrorState message={outboxQuery.error.message} onRetry={() => outboxQuery.refetch()} />
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Pedido</TableCell>
                <TableCell>Destino</TableCell>
                <TableCell>Evento</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>HTTP</TableCell>
                <TableCell>Próxima consulta</TableCell>
                <TableCell>Erro</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(outboxQuery.data?.items ?? []).map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.pedido_id}</TableCell>
                  <TableCell>{item.destino}</TableCell>
                  <TableCell>{item.evento}</TableCell>
                  <TableCell>
                    <Chip size="small" label={item.status} variant="outlined" />
                  </TableCell>
                  <TableCell>{item.last_http_status ?? '—'}</TableCell>
                  <TableCell>{formatDate(item.next_status_check_at)}</TableCell>
                  <TableCell sx={{ maxWidth: 300, wordBreak: 'break-word' }}>
                    {item.last_error || '—'}
                  </TableCell>
                </TableRow>
              ))}
              {!outboxQuery.data?.items?.length && (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    Nenhuma conversão registrada.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Stack>
  );
}
