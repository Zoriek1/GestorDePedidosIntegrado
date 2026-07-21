# Grupo 7: Black + TypeScript

> **Tarefas:** 8.2 (Black) + 8.3 (TypeScript)

**Goal:** Formatar codebase com Black e verificar/corrigir erros TypeScript.

**Architecture:** Black para Python (formatação automática), tsc --noEmit para TypeScript (type checking).

**Tech Stack:** Black, TypeScript/Vite

## Global Constraints

- Black: line-length 100, target Python 3.8
- TypeScript: strict: true, noUnusedLocals, noUnusedParameters
- **Depende de:** Grupo 6 (Ruff deve rodar antes de Black)

---

## Tarefa 7.1: Rodar Black no codebase

**Files:**
- Modify: múltiplos arquivos Python

- [ ] **Step 1: Verificar diff pendente do Black**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\backend"
black --check .
```

Se retornar diff, rodar:

```bash
black .
```

- [ ] **Step 2: Verificar compatibilidade com Ruff**

```bash
ruff check .
```

Black e Ruff estão configurados para serem compatíveis (mesmo line-length 100).

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "style: black formatting pass"
```

---

## Tarefa 7.2: TypeScript — verificar e corrigir erros

**Files:**
- Review: `frontend/` (100% TypeScript, 70+ arquivos .ts/.tsx)

- [ ] **Step 1: Verificar erros de tipagem**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\frontend"
npx tsc --noEmit
```

- [ ] **Step 2: Corrigir erros encontrados**

Se houver erros, corrigir um por vez. Erros comuns:
- `noUnusedLocals`: remover imports/variáveis não usadas
- `noUnusedParameters`: prefixar com `_` ou remover
- Type mismatches: ajustar tipos

- [ ] **Step 3: Rodar testes frontend (se existirem)**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\frontend"
npx vitest run
```

- [ ] **Step 4: Confirmar zero erros**

```bash
npx tsc --noEmit
```

Esperado: zero errors.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix(frontend): TypeScript strict mode fixes"
```
