# Phase 1.1 - Referência Rápida

## ✅ O que foi implementado

### Autenticação
- Login funcional com paridade ao legado
- Rotas protegidas com `RequireAuth`
- Logout limpa storage
- Credenciais: `admin` / `plante1998`

### Rotas
- `/login` - Página de login (pública)
- `/` - Pedidos (protegida)
- `/clientes` - Clientes (protegida, stub)
- `/pedidos/novo` - Novo pedido (protegida, stub)
- `/pedidos/:id` - Detalhes (protegida, stub)

### Navegação
- Menu no AppBar com links
- Botão de logout com dropdown
- Nome de usuário exibido

### Refresh
- Auto-refresh: 15s (pedidos), 8s (stats)
- Botão manual de atualizar
- Indicador visual de loading

---

## 📁 Arquivos Criados

**Frontend:**
- `RequireAuth.tsx` - Route guard
- `LoginPage.tsx` - Página de login
- `CustomersPage.tsx` - Stub clientes
- `CreateOrderPage.tsx` - Stub novo pedido
- `OrderDetailsPage.tsx` - Stub detalhes
- `customers.ts` - API hooks clientes

**Docs:**
- `phase1_1-smoke.md` - Testes
- `phase1_1-implementation-summary.md` - Resumo completo

---

## 🔧 Arquivos Modificados

**Frontend:**
- `authStore.tsx` - Login, getAuthHeader, cache
- `router.tsx` - Rotas + layout
- `App.tsx` - Simplificado
- `AppShell.tsx` - Menu + logout
- `OrdersPage.tsx` - Refresh button fix
- `pedidos.ts` - React Query config
- `http.ts` - Auth header injection
- `vite.config.ts` - Proxy config

**Backend:**
- `auth.py` - Validação de credenciais
- `middleware.py` - Senha atualizada

---

## 🐛 Problemas Resolvidos

1. ✅ Erro de inicialização `logout` → Reordenado código
2. ✅ `useNavigate` fora do Router → Layout route com `Outlet`
3. ✅ setState durante render → Inicialização síncrona + useEffect
4. ✅ Login não autenticava → Validação de credenciais no backend
5. ✅ Warning MUI Tooltip → Envolvido em `<span>`

---

## 🚀 Como Usar

**Login:**
- Usuário: `admin`
- Senha: `plante1998`

**Desenvolvimento:**
```bash
# Terminal 1: Backend
cd backend
flask cli start

# Terminal 2: Frontend v2
cd frontend_v2
npm run dev
```

**Acessar:**
- Frontend v2: `http://localhost:5173`
- Backend: `http://localhost:5000`

---

## 📊 Status

- ✅ Autenticação funcionando
- ✅ Rotas protegidas funcionando
- ✅ Navegação funcionando
- ✅ Refresh automático funcionando
- ✅ Refresh manual funcionando
- ✅ Compatibilidade com legado (storage keys)

**Pronto para:** Migração gradual de telas (Phase 1.2+)


