# Plante Uma Flor - Frontend V2

Sistema de gestão de pedidos desenvolvido com React, TypeScript e Vite.

## 🚀 Tecnologias

- **React 19** - Biblioteca UI
- **TypeScript** - Tipagem estática
- **Vite** - Build tool e dev server
- **Material-UI (MUI)** - Componentes de UI
- **React Query** - Gerenciamento de estado e cache
- **React Hook Form + Zod** - Formulários e validação
- **React Router** - Roteamento
- **PWA** - Progressive Web App com Service Worker
- **Dexie** - IndexedDB para funcionalidade offline

## 📋 Pré-requisitos

- Node.js 18+ e npm
- Backend Flask rodando na porta 5000 (ou configurar `VITE_API_TARGET`)

## 🛠️ Instalação

```bash
# Instalar dependências
npm install
```

## ⚙️ Configuração

### Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste conforme necessário:

```bash
cp .env.example .env
```

Variáveis disponíveis:

- `VITE_API_BASE_URL`: URL base da API (padrão: `/api`)
- `VITE_API_TARGET`: Target do proxy Vite em desenvolvimento (padrão: `http://localhost:5000`)
- `VITE_ENABLE_OFFLINE_DIAGNOSTICS`: Habilitar diagnósticos offline (padrão: `false`)

### Path Aliases

O projeto usa path aliases para imports mais limpos:

```typescript
import { Button } from '@/components/common/AppButton'
import { usePedidos } from '@/api/endpoints/pedidos'
import { useAuth } from '@/features/auth/authStore'
```

Aliases disponíveis:
- `@/*` → `src/*`
- `@/components/*` → `src/components/*`
- `@/features/*` → `src/features/*`
- `@/api/*` → `src/api/*`
- `@/lib/*` → `src/lib/*`
- `@/hooks/*` → `src/hooks/*`

## 🏃 Desenvolvimento

```bash
# Iniciar servidor de desenvolvimento
npm run dev

# O servidor estará disponível em http://localhost:5173
# Requisições para /api são automaticamente proxyadas para http://localhost:5000
```

### Estrutura do Projeto

```
src/
├── api/              # Cliente HTTP e endpoints da API
├── app/              # Configuração do app (router, providers)
├── components/       # Componentes reutilizáveis
├── features/         # Features organizadas por domínio
│   ├── auth/         # Autenticação
│   ├── pedidos/      # Gestão de pedidos
│   ├── customers/    # Gestão de clientes
│   └── rotas/        # Otimização de rotas
├── lib/              # Bibliotecas e utilitários
│   ├── offline/      # Funcionalidade offline (cache, outbox)
│   └── format/       # Formatação (data, moeda)
└── layout/           # Componentes de layout
```

## 🏗️ Build

```bash
# Build para produção
npm run build

# Os arquivos serão gerados em dist/
```

### Otimizações de Build

O build está otimizado com:
- **Code Splitting**: Chunks separados para vendors (React, MUI, etc.)
- **Tree Shaking**: Remoção de código não utilizado
- **Minificação**: Código minificado com esbuild
- **Source Maps**: Desabilitados em produção (habilitar se necessário)

## 📦 Deploy

### Servir Build Estático

```bash
# Usando serve (já incluído)
npm run serve:static

# Ou usando vite preview
npm run preview
```

### Cloudflare Tunnel

O frontend roda na porta 3000 e deve ser configurado no Cloudflare Tunnel:

```yaml
ingress:
  # API vai para o backend (porta 5000)
  - hostname: gestaopedidos.planteumaflor.online
    path: /api/*
    service: http://localhost:5000

  # Tudo mais vai para o frontend (porta 3000)
  - hostname: gestaopedidos.planteumaflor.online
    service: http://localhost:3000
```

**Importante**: A ordem importa! Regras mais específicas (`/api/*`) devem vir antes do catch-all.

## 🔧 Scripts Disponíveis

- `npm run dev` - Inicia servidor de desenvolvimento
- `npm run build` - Build para produção
- `npm run preview` - Preview do build (porta 3000)
- `npm run serve:static` - Serve build estático com `serve` (porta 3000)
- `npm run lint` - Executa ESLint

## 🐛 Tratamento de Erros

### Detecção de HTML em Respostas JSON

O cliente HTTP detecta automaticamente quando a API retorna HTML ao invés de JSON (geralmente quando o roteamento está incorreto). Nesses casos, retorna um erro claro:

```typescript
{
  ok: false,
  code: 'HTML_RESPONSE',
  message: 'Endpoint da API retornou HTML ao invés de JSON...'
}
```

### Type Guards

O código inclui type guards robustos para prevenir erros de runtime:

```typescript
// Verifica se é objeto antes de usar 'in' operator
if (pedidosData && typeof pedidosData === 'object' && 'pedidos' in pedidosData) {
  // Seguro para acessar pedidosData.pedidos
}
```

### Autenticação

- Respostas 401/403 disparam evento `puf_auth_invalid`
- O sistema automaticamente faz logout e redireciona para `/login`
- Credenciais são armazenadas em `localStorage` ou `sessionStorage`

## 📱 PWA (Progressive Web App)

O app é um PWA completo com:
- **Service Worker**: Cache de assets e funcionalidade offline
- **Manifest**: Permite instalação como app nativo
- **Offline Support**: Cache de dados e outbox para operações offline

### Cache Strategy

- **Fonts/Images**: CacheFirst (cache primeiro)
- **API Health**: NetworkFirst (rede primeiro, com timeout)
- **API Pedidos/Stats**: NetworkFirst com cache de 24h
- **Outras APIs**: NetworkOnly (sempre busca da rede)

## 🔐 Autenticação

- **Método**: Basic Auth
- **Usuário padrão**: `admin`
- **Armazenamento**: `localStorage` (remember) ou `sessionStorage`
- **Auto-logout**: Em caso de 401/403

## 📚 Estrutura de Features

Cada feature segue uma estrutura organizada:

```
features/pedidos/
├── components/        # Componentes específicos da feature
├── contexts/         # Contextos React
├── services/         # Serviços e interfaces
├── useCases/         # Casos de uso e lógica de negócio
├── schemas.ts        # Schemas Zod para validação
└── OrdersPage.tsx    # Páginas principais
```

## 🧪 Desenvolvimento

### TypeScript

- **Strict Mode**: Habilitado
- **Path Aliases**: Configurados para imports limpos
- **Type Safety**: Type guards em pontos críticos

### ESLint

Execute `npm run lint` para verificar problemas de código.

## 🐞 Troubleshooting

### Erro "Cannot use 'in' operator"

Se você ver este erro, significa que a API retornou HTML ao invés de JSON. Verifique:
1. Backend está rodando na porta 5000
2. Cloudflare Tunnel está roteando `/api/*` corretamente
3. Proxy do Vite está configurado corretamente

### Login não funciona

1. Verifique se o backend está acessível
2. Verifique credenciais (padrão: `admin` / `Plante1998`)
3. Verifique console do navegador para erros de CORS

### Build falha

1. Limpe `node_modules` e reinstale: `rm -rf node_modules && npm install`
2. Limpe cache do Vite: `rm -rf dist .vite`
3. Verifique se todas as dependências estão instaladas

## 📝 Notas

- O frontend roda independentemente na porta 3000
- O backend roda na porta 5000
- Em produção, use Cloudflare Tunnel para rotear corretamente
- A documentação Swagger está disponível apenas localmente em `http://localhost:5000/docs/swagger`
