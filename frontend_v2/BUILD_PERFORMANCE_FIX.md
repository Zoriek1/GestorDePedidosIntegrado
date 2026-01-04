# Diagnóstico e Correção de Performance do Build

## Problema
Build está demorando ~10 minutos quando antes levava ~1 minuto.

## Possíveis Causas

### 1. TypeScript Type Checking Completo
O script `build` executa `tsc -b` que faz type checking completo antes do build do Vite.

### 2. Cache do Vite Corrompido
Cache do Vite pode estar corrompido ou desatualizado.

### 3. Service Worker Generation (PWA)
O `vite-plugin-pwa` gera service workers que podem ser lentos.

### 4. Antivírus Escaneando Arquivos
Antivírus pode estar escaneando arquivos durante o build.

### 5. Disco Lento/Fragmentado
Problemas de I/O do disco.

## Soluções Rápidas

### Solução 1: Limpar Cache e Rebuild
```powershell
cd frontend_v2
npm run clean
Remove-Item -Recurse -Force node_modules\.vite -ErrorAction SilentlyContinue
npm run build
```

### Solução 2: Pular Type Checking no Build (Mais Rápido)
Criar script alternativo que pula type checking:

```json
"build:fast": "vite build",
"build:check": "tsc --noEmit && vite build"
```

### Solução 3: Otimizar Vite Config
Adicionar configurações de performance no `vite.config.ts`.

### Solução 4: Verificar Antivírus
Adicionar exclusões para:
- `node_modules/`
- `dist/`
- `.vite/`

## Scripts de Diagnóstico

Execute para identificar o gargalo:

```powershell
# Medir tempo de cada etapa
Measure-Command { npm run type-check }  # TypeScript
Measure-Command { vite build }         # Vite apenas
```
