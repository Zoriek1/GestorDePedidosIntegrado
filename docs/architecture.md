# Arquitetura do Sistema

Visão geral da arquitetura do sistema Plante Uma Flor.

---

## Visão Geral

O sistema é composto por:

- **Backend Flask**: API REST que gerencia dados e lógica de negócio
- **Frontend Legacy** (`/frontend`): PWA vanilla JS com Service Worker e IndexedDB
- **Frontend v2** (`/frontend_v2`): React + TypeScript + Vite (em migração gradual)

Ambos os frontends consomem a mesma API REST em `/api/*`.

---

## Componentes Principais

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (PWA)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Service    │  │  IndexedDB   │  │   Router     │ │
│  │   Worker    │  │   (Cache)    │  │   (SPA)      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/HTTPS
                        │ REST API
┌───────────────────────▼─────────────────────────────────┐
│                  BACKEND (Flask)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Routes     │  │   Services   │  │   Models     │ │
│  │   (API)      │  │  (Business)  │  │  (Database)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│   SQLite     │ │ GraphHopper │ │ OpenRoute  │
│  (Database)  │ │     API     │ │   Service  │
└──────────────┘ └─────────────┘ └────────────┘
```

---

## Estrutura do Backend

### Organização em Camadas

```
backend/app/
├── models/          # Modelos de dados (SQLAlchemy)
├── repositories/    # Camada de acesso ao banco
├── schemas/         # Validação/serialização (Marshmallow)
├── routes/          # Endpoints da API (Blueprints)
├── services/         # Lógica de negócio
└── utils/           # Utilitários
```

### Fluxo de Dados

1. **Request** → `routes/` (Blueprints)
2. **Validação** → `schemas/` (Marshmallow)
3. **Lógica** → `services/` (Business logic)
4. **Persistência** → `repositories/` → `models/` → Database

---

## Estrutura do Frontend

### Frontend Legacy (`/frontend`)

- **Vanilla JavaScript** (ES6+)
- **Service Worker** para cache e offline
- **IndexedDB** para armazenamento local
- **SPA Router** customizado

### Frontend v2 (`/frontend_v2`)

- **React** + **TypeScript**
- **Vite** como build tool
- **React Router** para navegação
- **React Query** para gerenciamento de estado e cache
- **Material-UI** para componentes

---

## Fluxos Principais

### 1. Criação de Pedido

```
Frontend → POST /api/pedidos
    ↓
Routes (pedidos.py)
    ↓
Schemas (validação)
    ↓
Services (lógica de negócio)
    ↓
Repositories → Models → Database
    ↓
Response JSON
```

### 2. Cálculo de Distância

```
Frontend → GET /api/pedidos/:id/distancia
    ↓
Routes → Services/distancia.py
    ↓
Geocodificação (Nominatim/OpenRouteService)
    ↓
Cálculo de rota (GraphHopper/OpenRouteService)
    ↓
Salvar no Database
    ↓
Response JSON
```

### 3. Sincronização Offline

```
Frontend (offline)
    ↓
IndexedDB (armazenamento local)
    ↓
[Quando online]
    ↓
Service Worker detecta conexão
    ↓
Sincroniza com API
    ↓
Atualiza IndexedDB
```

---

## Tecnologias Utilizadas

### Backend

- **Flask 3.0+**: Framework web
- **Flask-SQLAlchemy**: ORM
- **Flask-CORS**: CORS support
- **SQLite**: Banco de dados
- **Marshmallow**: Validação/serialização
- **python-dateutil**: Manipulação de datas
- **requests**: Cliente HTTP
- **cryptography**: Criptografia para backups

### Frontend Legacy

- **HTML5 + CSS3**: Estrutura e estilos
- **JavaScript ES6+**: Lógica
- **Tailwind CSS**: Framework CSS
- **Service Worker API**: Offline
- **IndexedDB API**: Armazenamento local

### Frontend v2

- **React**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool
- **React Router**: Navegação
- **React Query**: State management
- **Material-UI**: Componentes

### APIs Externas

- **GraphHopper API**: Cálculo de rotas
- **OpenRouteService API**: Geocodificação e rotas (fallback)
- **Nominatim (OpenStreetMap)**: Geocodificação gratuita
- **ViaCEP API**: Validação de CEP

---

## Segurança

### Autenticação

- **Basic Auth** para endpoints críticos
- Decorators `@requires_auth` e `@requires_edit_auth`
- Credenciais configuráveis via env vars

### Rate Limiting

- Limite de 60 requisições/minuto por IP
- Limite de 1000 requisições/hora por IP

### HTTPS

- Certificados SSL com mkcert (desenvolvimento)
- Suporte a hostname customizado
- Certificado CA distribuível

---

## Banco de Dados

### SQLite

- Localização: `%USERPROFILE%/var/lib/database/database.db` (Windows)
- PRAGMAs configurados: WAL mode, foreign keys, busy timeout
- Migrações: Flask-Migrate (Alembic)

### Modelos Principais

- `Pedido`: Pedidos de flores
- `Cliente`: Clientes
- `EnderecoCliente`: Endereços de clientes
- `FontePedido`: Fontes de pedidos (ex: iFood, WhatsApp)
- `RotaOtimizada`: Rotas de entrega otimizadas

---

## Configuração

### Variáveis de Ambiente

Todas as variáveis estão documentadas em [configuration.md](configuration.md).

Principais categorias:

- **Database**: `SQLALCHEMY_DATABASE_URI`
- **Auth**: `ADMIN_PASSWORD`
- **APIs Externas**: `GRAPHHOPPER_API_KEY`, `OPENROUTE_API_KEY`
- **Servidor**: `HOST`, `PORT`, `DEBUG`

---

## Logging e Observabilidade

### Logs de Acesso

- Arquivo: `backend/instance/logs/access_YYYY-MM-DD.log`
- Formato: `timestamp | IP | user | METHOD path | status`

### Logs de Latência

- Console (dev): `[HH:MM:SS] METHOD path durationMs ms`
- Logger (prod): Estruturado, sem PII

---

## Backup

### Automático

- Backup ao iniciar servidor (se não houver backup recente)
- Backup antes de operações críticas (deletar pedido, etc.)

### Manual

```bash
flask cli backup
```

### Localização

- Google Drive: `%USERPROFILE%/Meu Drive/Plante Uma Flor Confidential/Database - Pedidos Gestor`
- Local: `backend/instance/backups/`

---

## Próximos Passos

- **Phase 2**: Backend "descobrível" (em andamento)
  - Mapa de rotas automático
  - Documentação modular
  - Swagger/OpenAPI
  - Configuração centralizada

---

**Última atualização:** Dezembro 2024


Visão geral da arquitetura do sistema Plante Uma Flor.

---

## Visão Geral

O sistema é composto por:

- **Backend Flask**: API REST que gerencia dados e lógica de negócio
- **Frontend Legacy** (`/frontend`): PWA vanilla JS com Service Worker e IndexedDB
- **Frontend v2** (`/frontend_v2`): React + TypeScript + Vite (em migração gradual)

Ambos os frontends consomem a mesma API REST em `/api/*`.

---

## Componentes Principais

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (PWA)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Service    │  │  IndexedDB   │  │   Router     │ │
│  │   Worker    │  │   (Cache)    │  │   (SPA)      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/HTTPS
                        │ REST API
┌───────────────────────▼─────────────────────────────────┐
│                  BACKEND (Flask)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Routes     │  │   Services   │  │   Models     │ │
│  │   (API)      │  │  (Business)  │  │  (Database)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│   SQLite     │ │ GraphHopper │ │ OpenRoute  │
│  (Database)  │ │     API     │ │   Service  │
└──────────────┘ └─────────────┘ └────────────┘
```

---

## Estrutura do Backend

### Organização em Camadas

```
backend/app/
├── models/          # Modelos de dados (SQLAlchemy)
├── repositories/    # Camada de acesso ao banco
├── schemas/         # Validação/serialização (Marshmallow)
├── routes/          # Endpoints da API (Blueprints)
├── services/         # Lógica de negócio
└── utils/           # Utilitários
```

### Fluxo de Dados

1. **Request** → `routes/` (Blueprints)
2. **Validação** → `schemas/` (Marshmallow)
3. **Lógica** → `services/` (Business logic)
4. **Persistência** → `repositories/` → `models/` → Database

---

## Estrutura do Frontend

### Frontend Legacy (`/frontend`)

- **Vanilla JavaScript** (ES6+)
- **Service Worker** para cache e offline
- **IndexedDB** para armazenamento local
- **SPA Router** customizado

### Frontend v2 (`/frontend_v2`)

- **React** + **TypeScript**
- **Vite** como build tool
- **React Router** para navegação
- **React Query** para gerenciamento de estado e cache
- **Material-UI** para componentes

---

## Fluxos Principais

### 1. Criação de Pedido

```
Frontend → POST /api/pedidos
    ↓
Routes (pedidos.py)
    ↓
Schemas (validação)
    ↓
Services (lógica de negócio)
    ↓
Repositories → Models → Database
    ↓
Response JSON
```

### 2. Cálculo de Distância

```
Frontend → GET /api/pedidos/:id/distancia
    ↓
Routes → Services/distancia.py
    ↓
Geocodificação (Nominatim/OpenRouteService)
    ↓
Cálculo de rota (GraphHopper/OpenRouteService)
    ↓
Salvar no Database
    ↓
Response JSON
```

### 3. Sincronização Offline

```
Frontend (offline)
    ↓
IndexedDB (armazenamento local)
    ↓
[Quando online]
    ↓
Service Worker detecta conexão
    ↓
Sincroniza com API
    ↓
Atualiza IndexedDB
```

---

## Tecnologias Utilizadas

### Backend

- **Flask 3.0+**: Framework web
- **Flask-SQLAlchemy**: ORM
- **Flask-CORS**: CORS support
- **SQLite**: Banco de dados
- **Marshmallow**: Validação/serialização
- **python-dateutil**: Manipulação de datas
- **requests**: Cliente HTTP
- **cryptography**: Criptografia para backups

### Frontend Legacy

- **HTML5 + CSS3**: Estrutura e estilos
- **JavaScript ES6+**: Lógica
- **Tailwind CSS**: Framework CSS
- **Service Worker API**: Offline
- **IndexedDB API**: Armazenamento local

### Frontend v2

- **React**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool
- **React Router**: Navegação
- **React Query**: State management
- **Material-UI**: Componentes

### APIs Externas

- **GraphHopper API**: Cálculo de rotas
- **OpenRouteService API**: Geocodificação e rotas (fallback)
- **Nominatim (OpenStreetMap)**: Geocodificação gratuita
- **ViaCEP API**: Validação de CEP

---

## Segurança

### Autenticação

- **Basic Auth** para endpoints críticos
- Decorators `@requires_auth` e `@requires_edit_auth`
- Credenciais configuráveis via env vars

### Rate Limiting

- Limite de 60 requisições/minuto por IP
- Limite de 1000 requisições/hora por IP

### HTTPS

- Certificados SSL com mkcert (desenvolvimento)
- Suporte a hostname customizado
- Certificado CA distribuível

---

## Banco de Dados

### SQLite

- Localização: `%USERPROFILE%/var/lib/database/database.db` (Windows)
- PRAGMAs configurados: WAL mode, foreign keys, busy timeout
- Migrações: Flask-Migrate (Alembic)

### Modelos Principais

- `Pedido`: Pedidos de flores
- `Cliente`: Clientes
- `EnderecoCliente`: Endereços de clientes
- `FontePedido`: Fontes de pedidos (ex: iFood, WhatsApp)
- `RotaOtimizada`: Rotas de entrega otimizadas

---

## Configuração

### Variáveis de Ambiente

Todas as variáveis estão documentadas em [configuration.md](configuration.md).

Principais categorias:

- **Database**: `SQLALCHEMY_DATABASE_URI`
- **Auth**: `ADMIN_PASSWORD`
- **APIs Externas**: `GRAPHHOPPER_API_KEY`, `OPENROUTE_API_KEY`
- **Servidor**: `HOST`, `PORT`, `DEBUG`

---

## Logging e Observabilidade

### Logs de Acesso

- Arquivo: `backend/instance/logs/access_YYYY-MM-DD.log`
- Formato: `timestamp | IP | user | METHOD path | status`

### Logs de Latência

- Console (dev): `[HH:MM:SS] METHOD path durationMs ms`
- Logger (prod): Estruturado, sem PII

---

## Backup

### Automático

- Backup ao iniciar servidor (se não houver backup recente)
- Backup antes de operações críticas (deletar pedido, etc.)

### Manual

```bash
flask cli backup
```

### Localização

- Google Drive: `%USERPROFILE%/Meu Drive/Plante Uma Flor Confidential/Database - Pedidos Gestor`
- Local: `backend/instance/backups/`

---

## Próximos Passos

- **Phase 2**: Backend "descobrível" (em andamento)
  - Mapa de rotas automático
  - Documentação modular
  - Swagger/OpenAPI
  - Configuração centralizada

---

**Última atualização:** Dezembro 2024


