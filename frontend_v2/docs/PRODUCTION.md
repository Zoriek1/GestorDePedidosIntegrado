# Produção e Deploy

Este documento descreve o processo de build, deploy, configuração e troubleshooting.

## Build

### Build para Produção

```bash
npm run build
```

Este comando:
1. Executa type check (`tsc -b`)
2. Faz build do Vite (`vite build`)
3. Gera arquivos em `dist/`

### Build Rápido (Sem Type Check)

```bash
npm run build:fast
```

Útil para builds mais rápidos durante desenvolvimento.

### Build com Type Check

```bash
npm run build:check
```

Executa type check completo antes do build.

## Otimizações de Build

O build está otimizado com:

- **Code Splitting**: Chunks separados para vendors (React, MUI, etc)
- **Tree Shaking**: Remoção de código não utilizado
- **Minificação**: Código minificado com esbuild
- **Source Maps**: Desabilitados em produção (habilitar se necessário)

### Code Splitting

O Vite divide automaticamente o código em chunks:

- `react-vendor-*.js`: React e dependências
- `mui-vendor-*.js`: Material-UI
- `index-*.js`: Código da aplicação
- Outros vendors separados (query, form, date, map)

### Performance do Build

**Problema Comum**: Build lento (~10 minutos)

**Possíveis Causas**:
1. TypeScript Type Checking Completo
2. Cache do Vite corrompido
3. Service Worker Generation (PWA)
4. Antivírus escaneando arquivos
5. Disco lento/fragmentado

**Soluções**:

#### 1. Limpar Cache e Rebuild

```powershell
cd frontend_v2
npm run clean
npm run build
```

#### 2. Pular Type Checking (Mais Rápido)

Use `build:fast`:

```bash
npm run build:fast
```

#### 3. Verificar Antivírus

Adicione exclusões para:
- `node_modules/`
- `dist/`
- `.vite/`

#### 4. Diagnóstico de Performance

```powershell
# Medir tempo de cada etapa
Measure-Command { npm run type-check }  # TypeScript
Measure-Command { vite build }          # Vite apenas
```

## Deploy

### Servir Build Estático

#### Opção 1: Usando serve

```bash
npm run serve:static
```

Serve em `http://localhost:3000`

#### Opção 2: Usando vite preview

```bash
npm run preview
```

Serve em `http://localhost:3000`

#### Opção 3: Servidor HTTP qualquer

Copie o conteúdo de `dist/` para o servidor web (Apache, Nginx, etc).

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

### Integração com Backend

O frontend serve arquivos estáticos, enquanto o backend serve a API:

- **Frontend**: `http://localhost:3000` (ou porta configurada)
- **Backend API**: `http://localhost:5000/api`

Em produção com Cloudflare Tunnel, tudo passa por um único domínio.

## Configuração

### Variáveis de Ambiente

Variáveis disponíveis (arquivo `.env`):

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `VITE_API_BASE_URL` | `/api` | URL base da API |
| `VITE_API_TARGET` | `http://localhost:5000` | Target do proxy Vite (desenvolvimento) |
| `VITE_ENABLE_OFFLINE_DIAGNOSTICS` | `false` | Habilitar diagnósticos offline |

### Configuração de Produção

Para produção, configure `VITE_API_BASE_URL`:

```env
VITE_API_BASE_URL=/api
```

## Performance

### Build Performance

- **Type Check**: Pode ser lento em projetos grandes
- **Vite Build**: Geralmente rápido (~1 minuto)
- **Service Worker**: Geração pode adicionar tempo

### Runtime Performance

- **Code Splitting**: Carregamento incremental
- **Lazy Loading**: Páginas carregadas sob demanda
- **Cache**: Service Worker cacheia assets

## Troubleshooting

### Build Falha

#### 1. Erro de TypeScript

```bash
# Verificar erros de tipo
npm run type-check
```

#### 2. Dependências Faltando

```bash
# Reinstalar dependências
rm -rf node_modules package-lock.json
npm install
```

#### 3. Cache Corrompido

```bash
# Limpar cache
npm run clean
npm run build
```

### Deploy Falha

#### 1. Arquivos não encontrados (404)

- Verifique se `dist/index.html` existe
- Verifique configuração do servidor (deve servir `index.html` para todas as rotas)

#### 2. API não acessível

- Verifique `VITE_API_BASE_URL`
- Verifique se backend está rodando
- Verifique configuração do Cloudflare Tunnel (se aplicável)

#### 3. Assets não carregam

- Verifique caminhos dos assets (devem ser relativos)
- Verifique Service Worker (pode estar cacheando versão antiga)

### Performance Lenta

#### 1. Build Lento

- Use `build:fast` durante desenvolvimento
- Verifique antivírus (pode estar escaneando arquivos)
- Limpe cache: `npm run clean`

#### 2. Runtime Lento

- Verifique bundle size (use devtools)
- Verifique quantidade de re-renders (React DevTools)
- Verifique queries do React Query (pode estar fazendo muitas requisições)

---

**Última atualização**: 2026-01-04  
**Ver também**: [PWA.md](PWA.md)
