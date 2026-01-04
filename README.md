# Plante Uma Flor - Sistema de Gestão de Pedidos PWA

![Version](https://img.shields.io/badge/version-3.0.1-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Flask](https://img.shields.io/badge/flask-3.0+-red)
![React](https://img.shields.io/badge/react-19-blue)
![TypeScript](https://img.shields.io/badge/typescript-5.9-blue)
![PWA](https://img.shields.io/badge/PWA-enabled-purple)
![License](https://img.shields.io/badge/license-MIT-yellow)

Progressive Web App (PWA) moderno e completo para gerenciamento de pedidos de floricultura. Sistema multiplataforma com interface web responsiva que funciona em qualquer dispositivo (desktop, tablet, smartphone) com suporte offline completo.

---

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.8+
- Node.js 18+
- npm ou yarn

### Instalação

```bash
# 1. Backend
cd backend
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 3. Frontend
cd ../frontend_v2
npm install
```

### Executar

```bash
# Terminal 1: Backend
cd backend
python main.py
# Roda em http://localhost:5000

# Terminal 2: Frontend
cd frontend_v2
npm run dev
# Roda em http://localhost:5173
```

### Acessar

- **Frontend (Desenvolvimento)**: `http://localhost:5173`
- **Backend API**: `http://localhost:5000/api`
- **Swagger UI**: `http://localhost:5000/docs/swagger` (se disponível)

---

## 📚 Documentação

A documentação completa está organizada em diretórios específicos:

### Backend

Documentação técnica do backend em [`backend/docs/`](backend/docs/):

- **[README.md](backend/docs/README.md)** - Índice da documentação backend
- **[ARCHITECTURE.md](backend/docs/ARCHITECTURE.md)** - Arquitetura e padrões (Repository, Command, Service)
- **[BLUEPRINTS.md](backend/docs/BLUEPRINTS.md)** - Organização de Blueprints Flask
- **[ROUTES.md](backend/docs/ROUTES.md)** - Documentação completa de endpoints
- **[DATABASE.md](backend/docs/DATABASE.md)** - Integração com SQLite, models, migrations
- **[OPENAPI.md](backend/docs/OPENAPI.md)** - Documentação OpenAPI/Swagger
- **[BACKUP.md](backend/docs/BACKUP.md)** - Sistema de backup (P0 + P1)
- **[TROUBLESHOOTING.md](backend/docs/TROUBLESHOOTING.md)** - Problemas comuns e soluções

### Frontend

Documentação técnica do frontend em [`frontend_v2/docs/`](frontend_v2/docs/):

- **[README.md](frontend_v2/docs/README.md)** - Índice da documentação frontend
- **[TECHNOLOGY.md](frontend_v2/docs/TECHNOLOGY.md)** - Stack tecnológico e dependências
- **[ARCHITECTURE.md](frontend_v2/docs/ARCHITECTURE.md)** - Arquitetura e estrutura do projeto
- **[DATA_PATTERNS.md](frontend_v2/docs/DATA_PATTERNS.md)** - Padrões de dados e state management
- **[FEATURES.md](frontend_v2/docs/FEATURES.md)** - Funcionalidades atuais e roadmap
- **[PRODUCTION.md](frontend_v2/docs/PRODUCTION.md)** - Build, deploy e configuração
- **[PWA.md](frontend_v2/docs/PWA.md)** - Progressive Web App e offline

---

## 🎯 Stack Principal

| Camada | Tecnologia |
|--------|-----------|
| **Backend** | Flask 3.0 + SQLAlchemy 2.0 + SQLite |
| **Frontend** | React 19 + TypeScript + Vite + MUI |
| **Offline** | Dexie (IndexedDB) + Workbox (Service Worker) |
| **Backup** | Sistema customizado (AES-256-GCM) |

---

## 📁 Estrutura do Projeto

```
.
├── backend/              # Backend Flask
│   ├── app/             # Aplicação Flask
│   │   ├── models/      # Entidades (Pedido, Cliente, AuditLog)
│   │   ├── repositories/# Acesso a dados (Repository Pattern)
│   │   ├── services/    # Lógica de negócio
│   │   ├── routes/      # Controllers HTTP (Blueprints)
│   │   ├── commands/    # Command Pattern
│   │   └── utils/       # Backup, encryption, audit
│   ├── docs/            # Documentação backend
│   ├── scripts/         # Scripts de automação
│   └── instance/        # Dados da instância (database.db, backups, logs)
│
└── frontend_v2/          # Frontend React
    ├── src/
    │   ├── features/    # Módulos por feature
    │   ├── components/  # Componentes compartilhados
    │   ├── api/         # Cliente HTTP
    │   └── lib/         # Bibliotecas (offline, format)
    └── docs/            # Documentação frontend
```

---

## 🏗️ Arquitetura e Padrões

### Backend

- **Service-Oriented Architecture**: Separação clara de responsabilidades
- **Repository Pattern**: Abstração completa do acesso a dados
- **Command Pattern**: Encapsulamento de ações complexas
- **Blueprints Flask**: Organização modular das rotas

### Frontend

- **Feature-Based Architecture**: Organização por features/módulos
- **React Query**: Gerenciamento de estado servidor e cache
- **React Hook Form + Zod**: Formulários e validação
- **PWA**: Progressive Web App com Service Worker e offline support

---

## 🔑 Principais Funcionalidades

- ✅ **Gestão de Pedidos**: Criação, edição, listagem e status
- ✅ **CRM de Clientes**: Gestão completa de clientes com histórico
- ✅ **Otimização de Rotas**: Cálculo de rotas otimizadas para entrega
- ✅ **Backup Automático**: Sistema robusto multi-camadas (P0 + P1)
- ✅ **Offline Support**: Funcionalidade completa offline com sincronização
- ✅ **PWA**: Instalação como app nativo
- ✅ **Autenticação**: Autenticação seletiva (visualização livre, ações protegidas)

---

## 🎯 Principais Endpoints da API

- `GET /api/health` - Health check
- `GET /api/pedidos` - Listar pedidos
- `POST /api/pedidos` - Criar pedido
- `GET /api/stats` - Estatísticas
- `GET /api/clientes/search` - Buscar clientes
- `GET /api/auth/check` - Verificar autenticação

Veja [backend/docs/ROUTES.md](backend/docs/ROUTES.md) para documentação completa da API.

---

## 🔐 Sistema de Backup

O sistema possui backup robusto multi-camadas:

- **P0.1**: Backup horário automático (Seg-Sex 07-18h, Sáb 07-14h)
- **P0.2**: Fail-closed (bloqueia DELETE sem backup)
- **P0.3**: Soft delete + auditoria
- **P0.4**: Teste diário de restauração

**Documentação completa**: [backend/docs/BACKUP.md](backend/docs/BACKUP.md)

**Comandos úteis**:
```bash
# Verificar health do backup
curl -u admin:<password> http://localhost:5000/api/admin/backup/health

# Backup manual
python backend/scripts/backup/backup.py
```

---

## 🛠️ Tecnologias

### Backend
- Flask 3.0+
- SQLAlchemy 2.0
- SQLite
- Flask-Smorest (OpenAPI)

### Frontend
- React 19
- TypeScript 5.9
- Vite 7.2
- Material-UI 7.3
- React Query 5.90
- React Hook Form + Zod
- Dexie (IndexedDB)
- Workbox (Service Worker)

### APIs Externas
- GraphHopper (rotas)
- OpenRouteService (rotas)
- Nominatim (geocodificação)

---

## 📝 Mudanças e Refatorações

### Refatorações Recentes

O sistema passou por refatorações significativas para adotar padrões modernos:

- ✅ **Service-Oriented Architecture**: Separação clara de responsabilidades
- ✅ **Repository Pattern**: Abstração completa do acesso a dados
- ✅ **Command Pattern**: Encapsulamento de ações complexas
- ✅ **Blueprints Flask**: Organização modular das rotas
- ✅ **TypeScript**: Tipagem estática no frontend
- ✅ **React Query**: Gerenciamento de estado servidor otimizado
- ✅ **PWA Completo**: Service Worker e offline support

### Estado do Código

- ✅ **Backend**: Maioria refatorada (rotas principais em blueprints organizados)
- ✅ **Frontend**: Completamente novo (React 19 + TypeScript)
- ⚠️ **Legado**: Algumas rotas antigas mantidas para compatibilidade (migração em andamento)

---

## 📄 Licença

MIT License

---

**Plante Uma Flor** © 2024 - Sistema de Gestão de Pedidos PWA

**Última atualização**: 2026-01-04
