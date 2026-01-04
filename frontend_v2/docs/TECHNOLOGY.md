# Stack Tecnológico

Este documento descreve as tecnologias, dependências e configurações do frontend.

## Stack Principal

- **React 19** - Biblioteca UI moderna e performática
- **TypeScript 5.9** - Tipagem estática para maior segurança
- **Vite 7.2** - Build tool rápida e moderna
- **Material-UI (MUI) 7.3** - Biblioteca de componentes UI
- **React Query 5.90** - Gerenciamento de estado e cache
- **React Hook Form 7.69** - Gerenciamento de formulários
- **Zod 4.2** - Validação de schemas
- **React Router 7.11** - Roteamento
- **Dexie 3.2** - IndexedDB wrapper para funcionalidade offline
- **Vite PWA Plugin 1.2** - Progressive Web App com Service Worker

## Dependências Principais

### Core

| Pacote | Versão | Propósito |
|--------|--------|-----------|
| `react` | ^19.2.0 | Biblioteca UI |
| `react-dom` | ^19.2.0 | DOM bindings para React |
| `react-router-dom` | ^7.11.0 | Roteamento |

### UI e Estilização

| Pacote | Versão | Propósito |
|--------|--------|-----------|
| `@mui/material` | ^7.3.6 | Componentes Material Design |
| `@mui/icons-material` | ^7.3.6 | Ícones Material Design |
| `@mui/x-date-pickers` | ^8.23.0 | Seletores de data/hora |
| `@emotion/react` | ^11.14.0 | CSS-in-JS (requerido pelo MUI) |
| `@emotion/styled` | ^11.14.1 | Estilização (requerido pelo MUI) |
| `animate.css` | ^4.1.1 | Animações CSS |

### Estado e Dados

| Pacote | Versão | Propósito |
|--------|--------|-----------|
| `@tanstack/react-query` | ^5.90.15 | Cache e gerenciamento de estado servidor |
| `@tanstack/react-virtual` | ^3.11.2 | Virtualização de listas grandes |
| `dexie` | ^3.2.4 | IndexedDB wrapper para offline |

### Formulários e Validação

| Pacote | Versão | Propósito |
|--------|--------|-----------|
| `react-hook-form` | ^7.69.0 | Gerenciamento de formulários |
| `@hookform/resolvers` | ^5.2.2 | Resolvers para validação (Zod) |
| `zod` | ^4.2.1 | Validação de schemas TypeScript-first |

### Utilitários

| Pacote | Versão | Propósito |
|--------|--------|-----------|
| `date-fns` | ^4.1.0 | Manipulação de datas |
| `dayjs` | ^1.11.19 | Manipulação de datas (alternativa) |
| `clsx` | ^2.1.1 | Construção condicional de classes CSS |
| `react-number-format` | ^5.4.4 | Formatação de números/moeda |

### Mapas

| Pacote | Versão | Propósito |
|--------|--------|-----------|
| `leaflet` | ^1.9.4 | Biblioteca de mapas |
| `react-leaflet` | ^5.0.0 | Componentes React para Leaflet |

### DevDependencies

| Pacote | Versão | Propósito |
|--------|--------|-----------|
| `typescript` | ~5.9.3 | Compilador TypeScript |
| `vite` | ^7.2.4 | Build tool |
| `@vitejs/plugin-react` | ^5.1.1 | Plugin React para Vite |
| `vite-plugin-pwa` | ^1.2.0 | Plugin PWA para Vite |
| `eslint` | ^9.39.1 | Linter |
| `typescript-eslint` | ^8.46.4 | ESLint para TypeScript |

## Path Aliases

O projeto usa path aliases configurados no `vite.config.ts` e `tsconfig.json`:

| Alias | Caminho Real |
|-------|--------------|
| `@/*` | `src/*` |
| `@/components/*` | `src/components/*` |
| `@/features/*` | `src/features/*` |
| `@/api/*` | `src/api/*` |
| `@/lib/*` | `src/lib/*` |
| `@/hooks/*` | `src/hooks/*` |

### Uso

```typescript
// Em vez de:
import { Button } from '../../components/common/AppButton'

// Use:
import { Button } from '@/components/common/AppButton'
import { usePedidos } from '@/api/endpoints/pedidos'
import { useAuth } from '@/features/auth/authStore'
```

## Variáveis de Ambiente

Variáveis disponíveis (arquivo `.env`):

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `VITE_API_BASE_URL` | `/api` | URL base da API |
| `VITE_API_TARGET` | `http://localhost:5000` | Target do proxy Vite em desenvolvimento |
| `VITE_ENABLE_OFFLINE_DIAGNOSTICS` | `false` | Habilitar diagnósticos offline |

## Scripts Disponíveis

| Script | Descrição |
|--------|-----------|
| `npm run dev` | Inicia servidor de desenvolvimento (porta 5173) |
| `npm run build` | Build para produção (com type check) |
| `npm run build:fast` | Build rápido (sem type check) |
| `npm run build:check` | Type check + build |
| `npm run preview` | Preview do build (porta 3000) |
| `npm run serve:static` | Serve build estático com `serve` (porta 3000) |
| `npm run lint` | Executa ESLint |
| `npm run lint:fix` | Executa ESLint com auto-fix |
| `npm run type-check` | Apenas type check (sem build) |
| `npm run clean` | Limpa `dist/` e cache do Vite |

## TypeScript

- **Strict Mode**: Habilitado
- **Path Aliases**: Configurados para imports limpos
- **Type Safety**: Type guards em pontos críticos
- **Configuração**: `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`

## Vite

- **Dev Server**: HMR (Hot Module Replacement) rápido
- **Build**: Otimizado com code splitting e tree shaking
- **Proxy**: Requisições `/api` são proxyadas para `VITE_API_TARGET` em desenvolvimento
- **Configuração**: `vite.config.ts`

## ESLint

- **Configuração**: `eslint.config.js`
- **Plugins**: React hooks, React refresh, TypeScript
- **Executar**: `npm run lint`

---

**Última atualização**: 2026-01-04
