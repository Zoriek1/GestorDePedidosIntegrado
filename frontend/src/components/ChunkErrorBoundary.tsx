import { Component, ReactNode } from 'react';

const CHUNK_ERROR_PATTERNS = [
  'Failed to fetch dynamically imported module',
  'ChunkLoadError',
  'Loading chunk',
  'Loading CSS chunk',
  'Importing a module script failed',
  'error loading dynamically imported module',
];

const RELOAD_TS_KEY = 'chunk_reload_ts';
const RELOAD_WINDOW_MS = 10_000;

function isChunkError(error: unknown): boolean {
  if (!error) return false;
  const message =
    error instanceof Error
      ? error.message
      : typeof error === 'string'
        ? error
        : '';
  const name = error instanceof Error ? error.name : '';
  return CHUNK_ERROR_PATTERNS.some(
    (pattern) => message.includes(pattern) || name.includes(pattern),
  );
}

function attemptReload(): boolean {
  try {
    const lastTs = Number(sessionStorage.getItem(RELOAD_TS_KEY) ?? '0');
    const now = Date.now();
    if (now - lastTs < RELOAD_WINDOW_MS) return false;
    sessionStorage.setItem(RELOAD_TS_KEY, String(now));
  } catch {
    /* sessionStorage unavailable — proceed anyway */
  }
  window.location.reload();
  return true;
}

type Status = 'ok' | 'reloading' | 'fallback';

interface State {
  status: Status;
  propagatedError: unknown;
}

interface Props {
  children: ReactNode;
}

export class ChunkErrorBoundary extends Component<Props, State> {
  state: State = { status: 'ok', propagatedError: null };

  componentDidMount() {
    window.addEventListener('unhandledrejection', this.handleUnhandledRejection);
    // Vite dispara vite:preloadError quando um import dinâmico (rota lazy) falha.
    // É o caminho que o React Router intercepta com a própria tela de erro antes
    // de chegar nos hooks acima — então escutamos aqui pra recarregar sozinho.
    window.addEventListener('vite:preloadError', this.handlePreloadError);
  }

  componentWillUnmount() {
    window.removeEventListener('unhandledrejection', this.handleUnhandledRejection);
    window.removeEventListener('vite:preloadError', this.handlePreloadError);
  }

  handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    if (!isChunkError(event.reason)) return;
    event.preventDefault();
    this.setState({ status: attemptReload() ? 'reloading' : 'fallback' });
  };

  handlePreloadError = (event: Event) => {
    // Deploy novo trocou os hashes e o app aberto pediu um chunk antigo. Recarrega
    // (1x por janela) pra pegar o index.html novo — no mobile evita ter que fechar
    // e reabrir o app. preventDefault impede o Vite de relançar o erro.
    event.preventDefault();
    this.setState({ status: attemptReload() ? 'reloading' : 'fallback' });
  };

  static getDerivedStateFromError(error: unknown): State {
    if (isChunkError(error)) {
      return {
        status: attemptReload() ? 'reloading' : 'fallback',
        propagatedError: null,
      };
    }
    return { status: 'ok', propagatedError: error };
  }

  componentDidCatch(error: unknown) {
    if (!isChunkError(error)) {
      console.error('[ChunkErrorBoundary] Non-chunk error:', error);
    }
  }

  handleManualReload = () => {
    try {
      sessionStorage.removeItem(RELOAD_TS_KEY);
    } catch {
      /* ignore */
    }
    window.location.reload();
  };

  render() {
    if (this.state.propagatedError) {
      throw this.state.propagatedError;
    }
    if (this.state.status === 'reloading') {
      return null;
    }
    if (this.state.status === 'fallback') {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#143d28',
            color: '#e8e8e8',
            fontFamily: '"Inter", "Roboto", sans-serif',
            padding: 24,
          }}
        >
          <div style={{ maxWidth: 420, textAlign: 'center' }}>
            <h1
              style={{
                color: '#d4af7a',
                fontSize: 24,
                margin: '0 0 16px',
                fontWeight: 600,
              }}
            >
              Atualização disponível
            </h1>
            <p style={{ margin: '0 0 24px', lineHeight: 1.5 }}>
              Uma nova versão do sistema foi publicada. Recarregue a página
              para continuar.
            </p>
            <button
              type="button"
              onClick={this.handleManualReload}
              style={{
                background: '#1a5c3a',
                color: '#fff',
                border: 'none',
                padding: '12px 24px',
                borderRadius: 8,
                fontSize: 16,
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              Recarregar agora
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
