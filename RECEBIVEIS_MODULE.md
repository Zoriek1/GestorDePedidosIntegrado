# Módulo de Recebíveis, Autenticação e Comissões — Plante Uma Flor

> **Versão:** 1.0  
> **Data:** 2026-04-14  
> **Repositório:** `Zoriek1/Gestor-de-Pedidos-WEB-PUF`  
> **Stack:** Flask 3.0 + SQLAlchemy 2.0 + SQLite | React 19 + TypeScript + Vite + MUI

---

## 1. Visão Geral

Este documento especifica a implementação de três subsistemas integrados ao Gestor de Pedidos PWA:

1. **Auth robusto** — login com usuários, roles e sessão JWT
2. **Configuração de remuneração** — salário (semanal/mensal) + comissão por fonte, configurável por admin
3. **Ledger de recebíveis** — conta corrente entre vendedor e empresa com saldo devedor em tempo real

O design é **multi-tenant ready**: nenhuma regra de negócio é hardcoded para um usuário específico. Toda configuração vive no banco.

---

## 2. Arquitetura de Dados

### 2.1 Novas Tabelas

#### `users`

| Coluna | Tipo | Constraints | Descrição |
|--------|------|-------------|-----------|
| `id` | INTEGER | PK, AUTOINCREMENT | — |
| `name` | VARCHAR(200) | NOT NULL | Nome de exibição |
| `email` | VARCHAR(200) | UNIQUE, NOT NULL | Login |
| `password_hash` | VARCHAR(256) | NOT NULL | bcrypt hash |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT 'vendedor' | `admin` \| `vendedor` \| `viewer` |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Soft-disable sem deletar |
| `created_at` | DATETIME | NOT NULL, DEFAULT NOW | — |
| `updated_at` | DATETIME | NOT NULL, DEFAULT NOW | — |

**Roles:**
- `admin` — acessa tudo, cadastra usuários, configura salários/comissões, registra pagamentos
- `vendedor` — vê seus pedidos, vê seu ledger (somente leitura do extrato)
- `viewer` — somente leitura de pedidos (sem acesso ao módulo financeiro)

#### `payroll_config`

| Coluna | Tipo | Constraints | Descrição |
|--------|------|-------------|-----------|
| `id` | INTEGER | PK | — |
| `user_id` | INTEGER | FK → users, NOT NULL | — |
| `category` | VARCHAR(50) | NOT NULL | `fixo_semanal` \| `fixo_mensal` \| `almoco` \| `transporte` \| `custom` |
| `label` | VARCHAR(100) | NOT NULL | Nome de exibição (ex: "Salário Semanal", "Vale Almoço") |
| `amount` | REAL | NOT NULL | Valor em R$ |
| `frequency` | VARCHAR(20) | NOT NULL | `semanal` \| `mensal` |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | — |
| `created_at` | DATETIME | NOT NULL | — |

**Index:** `(user_id, category)` UNIQUE quando `is_active = TRUE`

#### `commission_config`

| Coluna | Tipo | Constraints | Descrição |
|--------|------|-------------|-----------|
| `id` | INTEGER | PK | — |
| `user_id` | INTEGER | FK → users, NOT NULL | — |
| `source` | VARCHAR(50) | NOT NULL | `whatsapp` \| `site` \| `balcao` \| `indicacao` \| `lucro_bruto` |
| `rate` | REAL | NOT NULL | Percentual como decimal (0.03 = 3%) |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | — |
| `created_at` | DATETIME | NOT NULL | — |

**Index:** `(user_id, source)` UNIQUE quando `is_active = TRUE`

> **Nota sobre `lucro_bruto`:** esta source é um placeholder. Quando `source = 'lucro_bruto'`, o cálculo será `(receita_vendas - custo_anuncios) * rate`. A implementação do cálculo fica para fase futura — por ora, o admin pode cadastrar a config mas o sistema não gera entries automáticas para essa source. A UI deve mostrar um badge "Em breve" ou "Configuração salva, cálculo manual".

#### `ledger_entry`

| Coluna | Tipo | Constraints | Descrição |
|--------|------|-------------|-----------|
| `id` | INTEGER | PK | — |
| `user_id` | INTEGER | FK → users, NOT NULL | Vendedor dono do saldo |
| `type` | VARCHAR(10) | NOT NULL | `CREDIT` \| `DEBIT` |
| `category` | VARCHAR(50) | NOT NULL | Ver categorias abaixo |
| `amount` | REAL | NOT NULL | Sempre positivo |
| `description` | TEXT | NULLABLE | Anotação livre |
| `pedido_id` | INTEGER | FK → pedidos, NULLABLE | Só para comissões |
| `week_ref` | DATE | NOT NULL | Segunda-feira da semana de referência |
| `created_at` | DATETIME | NOT NULL, DEFAULT NOW | — |
| `created_by` | INTEGER | FK → users, NOT NULL | Quem lançou |

**Categorias válidas:**

| Categoria | Type | Origem |
|-----------|------|--------|
| `fixo_semanal` | CREDIT | Automático ou manual |
| `fixo_mensal` | CREDIT | Automático ou manual |
| `almoco` | CREDIT | Automático ou manual |
| `transporte` | CREDIT | Automático ou manual |
| `comissao_whatsapp` | CREDIT | Automático ao fechar pedido |
| `comissao_site` | CREDIT | Automático ao fechar pedido |
| `comissao_balcao` | CREDIT | Automático ao fechar pedido |
| `comissao_indicacao` | CREDIT | Automático ao fechar pedido |
| `comissao_lucro` | CREDIT | Manual (futuro: automático) |
| `custom_credit` | CREDIT | Manual — bônus, ajuste |
| `pagamento` | DEBIT | Admin registra pagamento |
| `adiantamento` | DEBIT | Admin registra adiantamento |
| `ajuste_debito` | DEBIT | Admin — correção |

**Indexes:**
- `(user_id, week_ref)` — consultas por semana
- `(pedido_id)` — evitar comissão duplicada (UNIQUE quando NOT NULL)

### 2.2 Alteração em Tabela Existente

#### `pedidos` — nova coluna

| Coluna | Tipo | Constraints | Descrição |
|--------|------|-------------|-----------|
| `vendedor_id` | INTEGER | FK → users, NULLABLE | Quem realizou a venda |

> NULLABLE para retrocompatibilidade. Pedidos antigos sem vendedor não geram comissão.

---

## 3. Sistema de Autenticação

### 3.1 Backend (Flask)

**Dependências novas:**
```
flask-bcrypt
PyJWT
```

**Fluxo:**
1. `POST /api/auth/login` — recebe `{email, password}`, valida bcrypt, retorna `{access_token, user}`
2. Access token: JWT com payload `{user_id, role, exp}`, assinado com `SECRET_KEY`, TTL = 24h
3. Token enviado no header `Authorization: Bearer <token>`
4. Decorator `@require_auth(roles=['admin'])` protege rotas

**Arquivos a criar/modificar:**

```
backend/app/
├── models/
│   ├── user.py                    # NOVO — Model User
│   ├── payroll_config.py          # NOVO
│   ├── commission_config.py       # NOVO
│   └── ledger_entry.py            # NOVO
├── repositories/
│   ├── user_repository.py         # NOVO
│   └── ledger_repository.py       # NOVO
├── services/
│   ├── auth_service.py            # NOVO — login, hash, JWT encode/decode
│   ├── commission_service.py      # NOVO — calcula e cria entries
│   └── ledger_service.py          # NOVO — saldo, extrato, lançamentos
├── routes/
│   ├── auth_routes.py             # NOVO — Blueprint /api/auth/*
│   ├── user_routes.py             # NOVO — Blueprint /api/users/* (admin)
│   └── ledger_routes.py           # NOVO — Blueprint /api/ledger/*
├── decorators/
│   └── auth_decorator.py          # NOVO — @require_auth
└── utils/
    └── jwt_utils.py               # NOVO — encode/decode helpers
```

### 3.2 Endpoints

#### Auth

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `POST` | `/api/auth/login` | Público | Login → retorna JWT + user info |
| `POST` | `/api/auth/logout` | Bearer | Invalida token (client-side) |
| `GET` | `/api/auth/me` | Bearer | Retorna user logado |
| `PUT` | `/api/auth/password` | Bearer | Altera própria senha |

#### Users (admin only)

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `GET` | `/api/users` | Admin | Lista usuários |
| `POST` | `/api/users` | Admin | Cria usuário |
| `PUT` | `/api/users/<id>` | Admin | Edita usuário |
| `DELETE` | `/api/users/<id>` | Admin | Desativa (soft) |
| `GET` | `/api/users/<id>/config` | Admin | Retorna payroll + commission config |
| `PUT` | `/api/users/<id>/payroll` | Admin | Configura salário |
| `PUT` | `/api/users/<id>/commission` | Admin | Configura comissões |

#### Ledger

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `GET` | `/api/ledger/balance` | Vendedor/Admin | Saldo devedor do user logado (ou `?user_id=X` para admin) |
| `GET` | `/api/ledger/entries` | Vendedor/Admin | Extrato com filtros `?week_ref=`, `?category=`, `?from=`, `?to=` |
| `POST` | `/api/ledger/entries` | Admin | Lançamento manual (pagamento, ajuste, bônus) |
| `POST` | `/api/ledger/generate-weekly` | Admin | Gera CREDITs fixos da semana para todos vendedores ativos |
| `GET` | `/api/ledger/summary` | Admin | Resumo de todos vendedores (saldo de cada um) |
| `GET` | `/api/ledger/export` | Vendedor/Admin | Export CSV/XLSX do extrato |

### 3.3 Segurança

- **Hashing:** bcrypt com cost factor 12
- **JWT:** HS256, secret via `JWT_SECRET_KEY` no `.env`
- **SQL Injection:** zero risco — todo acesso via SQLAlchemy ORM (Repository Pattern)
- **Rate limiting:** 5 tentativas de login por minuto por IP (usar `flask-limiter`)
- **Senha mínima:** 8 caracteres
- **CORS:** manter config existente, adicionar header `Authorization` ao `Access-Control-Allow-Headers`
- **Seed admin:** script de bootstrap cria primeiro admin via CLI: `flask create-admin --email admin@puf.com --password <pw>`

### 3.4 Frontend (React)

**Arquivos a criar:**

```
frontend_v2/src/
├── features/
│   ├── auth/
│   │   ├── components/
│   │   │   └── LoginPage.tsx        # Tela de login (MUI)
│   │   ├── hooks/
│   │   │   └── useAuth.ts           # Hook de auth state
│   │   ├── services/
│   │   │   └── authApi.ts           # Chamadas /api/auth/*
│   │   └── context/
│   │       └── AuthContext.tsx       # Provider com user + token
│   ├── users/
│   │   ├── components/
│   │   │   ├── UserListPage.tsx      # CRUD de usuários (admin)
│   │   │   └── UserConfigDialog.tsx  # Modal: payroll + commission config
│   │   └── services/
│   │       └── userApi.ts
│   └── ledger/
│       ├── components/
│       │   ├── LedgerPage.tsx        # Extrato com saldo running
│       │   ├── BalanceCard.tsx       # Card com saldo devedor
│       │   ├── EntryList.tsx         # Lista de lançamentos
│       │   ├── PaymentDialog.tsx     # Modal: registrar pagamento (admin)
│       │   └── WeeklyGenerateBtn.tsx # Botão: gerar créditos semanais
│       └── services/
│           └── ledgerApi.ts
├── components/
│   └── ProtectedRoute.tsx            # Wrapper que redireciona se !auth
└── lib/
    └── authStorage.ts                # Token em memória (NÃO localStorage)
```

**Gerenciamento de token:**
- Access token em variável React (Context ou Zustand) — **nunca** em localStorage
- Se quiser persistir sessão entre refreshes: cookie httpOnly setado pelo backend (alternativa ao JWT puro)
- Interceptor no Axios/fetch que adiciona `Authorization: Bearer <token>` em toda request

**Navegação por role:**

| Menu Item | admin | vendedor | viewer |
|-----------|-------|----------|--------|
| Pedidos | ✅ | ✅ | ✅ (read-only) |
| Clientes | ✅ | ✅ | ✅ (read-only) |
| Rotas | ✅ | ✅ | ❌ |
| Recebíveis | ✅ (todos) | ✅ (próprio) | ❌ |
| Usuários | ✅ | ❌ | ❌ |
| Config Comissão | ✅ | ❌ | ❌ |
| Backup | ✅ | ❌ | ❌ |

---

## 4. Lógica de Negócio

### 4.1 Geração Automática de Comissão

**Trigger:** quando um pedido muda de status para `entregue` (ou equivalente ao "fechado").

```python
# commission_service.py (pseudocódigo)

def generate_commission(pedido, vendedor_id):
    """Chamado pelo service de pedidos ao fechar um pedido."""
    
    # 1. Verificar se já existe entry para esse pedido (idempotência)
    existing = ledger_repo.get_by_pedido_id(pedido.id)
    if existing:
        return  # já processado
    
    # 2. Determinar fonte do pedido
    source = map_fonte_to_source(pedido.fonte_pedido)
    # ex: FontePedido.WHATSAPP → 'whatsapp'
    
    # 3. Buscar config de comissão do vendedor para essa fonte
    config = commission_config_repo.get_active(
        user_id=vendedor_id, 
        source=source
    )
    if not config:
        return  # sem comissão configurada para essa fonte
    
    if source == 'lucro_bruto':
        return  # placeholder — não calcular automaticamente (futuro)
    
    # 4. Calcular valor
    commission_amount = pedido.valor_total * config.rate
    
    # 5. Criar entry no ledger
    ledger_repo.create(LedgerEntry(
        user_id=vendedor_id,
        type='CREDIT',
        category=f'comissao_{source}',
        amount=round(commission_amount, 2),
        description=f'Comissão {config.rate*100:.0f}% — Pedido #{pedido.id}',
        pedido_id=pedido.id,
        week_ref=get_monday(pedido.data_entrega),
        created_by=vendedor_id  # sistema, em nome do vendedor
    ))
```

### 4.2 Geração de Créditos Fixos (Semanal/Mensal)

**Opção A — Manual (recomendado inicialmente):**  
Admin clica "Gerar Semana" → sistema cria CREDITs para todos os vendedores com `payroll_config` ativo.

**Opção B — Automático (futuro):**  
Scheduler (APScheduler ou cron externo) roda todo domingo 23:59 e gera automaticamente.

```python
# ledger_service.py

def generate_weekly_credits(week_ref: date, created_by: int):
    """Gera créditos fixos semanais para todos os vendedores ativos."""
    
    vendedores = user_repo.get_active_by_role('vendedor')
    
    for vendedor in vendedores:
        configs = payroll_config_repo.get_active(user_id=vendedor.id)
        
        for config in configs:
            if config.frequency != 'semanal':
                continue
            
            # Idempotência: verificar se já existe entry para essa semana + categoria
            existing = ledger_repo.get_by_week_and_category(
                user_id=vendedor.id,
                week_ref=week_ref,
                category=config.category
            )
            if existing:
                continue
            
            ledger_repo.create(LedgerEntry(
                user_id=vendedor.id,
                type='CREDIT',
                category=config.category,
                amount=config.amount,
                description=config.label,
                week_ref=week_ref,
                created_by=created_by
            ))
```

### 4.3 Cálculo de Saldo

```python
def get_balance(user_id: int) -> dict:
    """Retorna saldo devedor (quanto a empresa deve ao vendedor)."""
    
    credits = db.session.query(
        func.coalesce(func.sum(LedgerEntry.amount), 0)
    ).filter(
        LedgerEntry.user_id == user_id,
        LedgerEntry.type == 'CREDIT'
    ).scalar()
    
    debits = db.session.query(
        func.coalesce(func.sum(LedgerEntry.amount), 0)
    ).filter(
        LedgerEntry.user_id == user_id,
        LedgerEntry.type == 'DEBIT'
    ).scalar()
    
    return {
        'total_credits': round(credits, 2),
        'total_debits': round(debits, 2),
        'balance': round(credits - debits, 2),  # positivo = empresa deve
    }
```

---

## 5. Migração e Retrocompatibilidade

### 5.1 Migration Script

Criar `backend/scripts/migrations/add_auth_and_ledger.py`:

1. Criar tabelas `users`, `payroll_config`, `commission_config`, `ledger_entry`
2. Adicionar coluna `vendedor_id` à tabela `pedidos`
3. Criar usuário admin seed
4. **NÃO** quebrar funcionalidade existente — rotas sem `@require_auth` continuam públicas

### 5.2 Ativação Gradual

**Fase 1 — Deploy sem enforcement:**
- Tabelas criadas, login funciona, mas rotas existentes não exigem auth
- Admin cria usuários, configura payroll/commission
- Testar o ledger manualmente

**Fase 2 — Ativação de auth:**
- Adicionar `@require_auth` às rotas existentes gradualmente
- Flag no `.env`: `AUTH_REQUIRED=true|false` para rollback fácil

**Fase 3 — Automação:**
- Comissão automática ao fechar pedido
- Geração semanal automática (scheduler)

---

## 6. Variáveis de Ambiente (adicionar ao .env)

```env
# Auth
JWT_SECRET_KEY=<gerar com: python -c "import secrets; print(secrets.token_hex(32))">
JWT_EXPIRATION_HOURS=24
AUTH_REQUIRED=false
BCRYPT_LOG_ROUNDS=12

# Admin seed
ADMIN_EMAIL=admin@planteumaflor.com
ADMIN_PASSWORD=<senha_forte>
```

---

## 7. Testes Mínimos

| Cenário | Expectativa |
|---------|-------------|
| Login com credenciais válidas | 200 + JWT |
| Login com senha errada | 401 |
| Acesso a `/api/ledger/balance` sem token | 401 |
| Vendedor acessa ledger de outro vendedor | 403 |
| Admin registra pagamento | DEBIT criado, saldo abate |
| Fechar pedido WhatsApp com config 3% | CREDIT de comissão criado automaticamente |
| Gerar semana duplicada | Idempotente — sem entries duplicadas |
| `pedido_id` duplicado no ledger | Constraint impede |

---

## 8. UI/UX — Wireframes Conceituais

### 8.1 Tela de Login
- MUI Card centralizado, campos email + senha, botão "Entrar"
- Logo Plante Uma Flor no topo
- Sem opção de "criar conta" (admin cria)

### 8.2 Painel de Recebíveis (Vendedor)

```
┌─────────────────────────────────────────┐
│  Saldo Devedor                          │
│  R$ 2.340,00              [Exportar]    │
│  ─────────────────────────────────────  │
│                                         │
│  Semana 07/04 – 13/04                   │
│  ├── Salário Semanal      + R$ 500,00   │
│  ├── Vale Almoço          + R$ 180,00   │
│  ├── Comissão WPP #142    +  R$ 12,30   │
│  ├── Comissão Site #145   +  R$ 25,00   │
│  └── Pagamento Pix        - R$ 680,00   │
│                                         │
│  Semana 31/03 – 06/04                   │
│  ├── ...                                │
└─────────────────────────────────────────┘
```

### 8.3 Painel Admin — Configuração de Usuário

```
┌─────────────────────────────────────────┐
│  Configurar: Caio                       │
│                                         │
│  REMUNERAÇÃO FIXA                       │
│  ┌────────────┬──────────┬──────────┐   │
│  │ Categoria  │ Valor    │ Freq.    │   │
│  ├────────────┼──────────┼──────────┤   │
│  │ Salário    │ R$500,00 │ Semanal  │   │
│  │ Almoço     │ R$180,00 │ Semanal  │   │
│  └────────────┴──────────┴──────────┘   │
│  [+ Adicionar]                          │
│                                         │
│  COMISSÕES                              │
│  ┌────────────┬──────────┬──────────┐   │
│  │ Fonte      │ Taxa     │ Status   │   │
│  ├────────────┼──────────┼──────────┤   │
│  │ WhatsApp   │ 3%       │ Ativo    │   │
│  │ Site       │ 5%       │ Ativo    │   │
│  │ Lucro Bruto│ —        │ Em breve │   │
│  └────────────┴──────────┴──────────┘   │
│  [+ Adicionar]                          │
│                                         │
│  [Salvar Configurações]                 │
└─────────────────────────────────────────┘
```

---

## 9. Checklist de Implementação

- [ ] **Model `User`** — SQLAlchemy + bcrypt hash
- [ ] **Model `PayrollConfig`** — com relationship para User
- [ ] **Model `CommissionConfig`** — com relationship para User
- [ ] **Model `LedgerEntry`** — com relationships para User e Pedido
- [ ] **Migration script** — cria tabelas + coluna `vendedor_id` em pedidos
- [ ] **AuthService** — login, JWT encode/decode, password hash/verify
- [ ] **Auth decorator** — `@require_auth(roles=[...])`
- [ ] **JWT utils** — encode, decode, validate expiration
- [ ] **UserRepository** — CRUD + filtros por role
- [ ] **LedgerRepository** — CRUD + saldo + extrato + idempotência
- [ ] **CommissionService** — gera comissão ao fechar pedido
- [ ] **LedgerService** — gera créditos fixos, calcula saldo
- [ ] **Auth routes** — login, logout, me, change password
- [ ] **User routes** — CRUD admin + config endpoints
- [ ] **Ledger routes** — balance, entries, generate, export
- [ ] **Integração no PedidoService** — chamar `generate_commission()` ao fechar
- [ ] **CLI `flask create-admin`** — seed do primeiro admin
- [ ] **Frontend: AuthContext + LoginPage**
- [ ] **Frontend: ProtectedRoute wrapper**
- [ ] **Frontend: Interceptor JWT no HTTP client**
- [ ] **Frontend: LedgerPage + BalanceCard + EntryList**
- [ ] **Frontend: UserListPage + UserConfigDialog (admin)**
- [ ] **Frontend: PaymentDialog (admin)**
- [ ] **Frontend: Navegação condicional por role**
- [ ] **Testes mínimos** — auth + comissão + idempotência
- [ ] **Docs** — atualizar ROUTES.md, DATABASE.md, ARCHITECTURE.md

---

## 10. Prompt para Claude Code

> Cole este bloco no Claude Code com o repositório aberto.

```
Preciso implementar o módulo de autenticação, comissões e recebíveis no Gestor de Pedidos.

LEIA PRIMEIRO: o arquivo RECEBIVEIS_MODULE.md na raiz do projeto contém a especificação completa com:
- Schema de todas as tabelas novas (users, payroll_config, commission_config, ledger_entry)
- Alteração na tabela pedidos (nova coluna vendedor_id)
- Todos os endpoints (auth, users, ledger) com métodos, rotas e permissões
- Lógica de negócio (geração de comissão, créditos fixos, cálculo de saldo)
- Estrutura de arquivos backend e frontend
- Regras de segurança (bcrypt, JWT, rate limiting)

REGRAS DE IMPLEMENTAÇÃO:
1. Siga os padrões existentes do projeto: Repository Pattern, Service Layer, Blueprints Flask, Feature-Based Architecture no React
2. Use SQLAlchemy ORM para todos os acessos a dados — NUNCA interpolar strings em queries
3. JWT com PyJWT, hash com flask-bcrypt
4. Token em memória no React (Context), NUNCA localStorage
5. Toda rota financeira (ledger) exige @require_auth
6. Comissão é idempotente: constraint UNIQUE em pedido_id no ledger_entry
7. O source 'lucro_bruto' no commission_config é um placeholder — NÃO implementar cálculo automático, apenas permitir cadastro da config
8. Manter retrocompatibilidade: flag AUTH_REQUIRED=false no .env para ativação gradual
9. Criar migration script em backend/scripts/migrations/add_auth_and_ledger.py
10. Criar comando CLI: flask create-admin

ORDEM DE IMPLEMENTAÇÃO:
Fase 1: Models + Migration + Seed admin
Fase 2: AuthService + JWT + Decorator + Auth routes
Fase 3: User routes (admin CRUD + config)
Fase 4: LedgerService + LedgerRepository + Ledger routes
Fase 5: Integração comissão no PedidoService
Fase 6: Frontend Auth (Context + Login + ProtectedRoute)
Fase 7: Frontend Ledger (LedgerPage + BalanceCard + EntryList)
Fase 8: Frontend Admin (UserListPage + UserConfigDialog + PaymentDialog)

Comece pela Fase 1. Ao terminar cada fase, me mostre o que foi criado e pergunte se devo prosseguir.
```

---

*Documento gerado para uso como referência de implementação e prompt de desenvolvimento.*
