# Memória do Projeto: Plante Uma Flor - Gestor de Pedidos

**Última atualização**: 2026-01-02  
**Versão do Sistema**: 3.0 (PWA)

---

## 📋 1. VISÃO GERAL DO PROJETO

### 1.1. Propósito
Sistema de gestão de pedidos para floricultura, operando como **Progressive Web App (PWA)** com suporte offline completo. O sistema gerencia pedidos, clientes, rotas de entrega e integrações com serviços externos de geolocalização.

### 1.2. Arquitetura Geral
- **Backend**: Flask (Python 3.8+) com SQLite
- **Frontend**: React 19 + TypeScript + Vite
- **Padrão**: Service-Oriented Architecture (SOA) / Clean Architecture
- **Persistência**: SQLite (arquivo `.db` fora do repositório)
- **Deploy**: Servidor local com suporte HTTPS

### 1.3. Características Principais
- ✅ PWA instalável em dispositivos móveis/desktop
- ✅ Funcionamento offline completo (IndexedDB + Service Worker)
- ✅ Sistema de backup robusto e multi-camadas (P0 + P1)
- ✅ Soft delete e trilha de auditoria
- ✅ Autenticação seletiva (visualização livre, ações protegidas)
- ✅ Integração com APIs de roteamento (GraphHopper, OpenRouteService)

---

## 🏗️ 2. ARQUITETURA DO BACKEND

### 2.1. Stack Tecnológica
- **Framework**: Flask 3.0+
- **ORM**: SQLAlchemy 2.0+
- **Banco**: SQLite (arquivo em `%USERPROFILE%/var/lib/database/database.db`)
- **Validação**: Marshmallow
- **Documentação API**: Flask-Smorest (Swagger UI)
- **Segurança**: Flask-CORS, Rate Limiting
- **Backup**: Sistema customizado com encriptação AES-256-GCM

### 2.2. Estrutura de Pastas (Backend)
```
backend/
├── app/
│   ├── commands/          # Command Pattern (ex: GerarComprovanteCommand)
│   ├── models/           # Entidades do domínio (SQLAlchemy)
│   │   ├── pedido.py     # Modelo principal com soft delete
│   │   ├── cliente.py
│   │   ├── audit_log.py  # Trilha de auditoria (P0.3)
│   │   └── ...
│   ├── repositories/     # Camada de acesso a dados (Repository Pattern)
│   │   ├── base_repository.py
│   │   ├── pedido_repository.py
│   │   └── cliente_repository.py
│   ├── services/         # Lógica de negócio e integrações
│   │   ├── distancia.py
│   │   ├── taxa_entrega.py
│   │   └── graphhopper.py
│   ├── routes/           # Controllers/Blueprints (HTTP handlers)
│   │   ├── pedidos.py
│   │   ├── clientes.py
│   │   ├── rotas.py
│   │   ├── auth.py
│   │   └── develop/      # Endpoints administrativos
│   ├── schemas/          # DTOs (Marshmallow)
│   ├── utils/            # Helpers (backup, encryption, audit)
│   ├── config.py         # Configurações centralizadas
│   ├── factory.py        # Application Factory
│   └── extensions.py     # Extensões Flask (db, etc)
├── scripts/
│   ├── backup/           # Sistema de backup completo
│   └── migrations/       # Migrações de schema
├── instance/             # Dados de runtime (não versionados)
│   ├── backups/          # Backups locais
│   ├── logs/             # Logs de auditoria
│   └── ssl/              # Certificados SSL
└── main.py              # Entry point do servidor
```

### 2.3. Padrões Arquiteturais

#### Repository Pattern
- **Abstração completa** do acesso a dados
- Código de negócio **nunca** toca `db.session` diretamente
- Métodos específicos por domínio (ex: `buscar_por_status`, `buscar_por_data`)
- Suporte a soft delete automático (filtragem de `deleted_at`)

#### Command Pattern
- Ações complexas encapsuladas em classes Command
- Exemplo: `GerarComprovanteCommand` (lógica + template)
- Estrutura: `Invoker (Botão/UI)` → `Command.execute()` → `Repository/Service`

#### Service Layer
- Lógica de negócio isolada em Services
- Integrações externas (APIs de roteamento)
- Cálculos (taxa de entrega, distâncias)

### 2.4. Fluxo de Dados (Pedidos)
```
1. HTTP Request → Route (Blueprint)
2. Route → Service/Repository
3. Repository → SQLAlchemy → SQLite
4. Validação (Fail Fast) → DTO
5. Commit no .db (atomicidade)
6. Response JSON
```

### 2.5. Modelos Principais

#### Pedido
- **Campos**: Cliente, destinatário, produto, endereço, data/hora, valor, status
- **Relacionamentos**: `cliente_id` (FK), `fonte_pedido_id` (FK)
- **Soft Delete**: `deleted_at` (P0.3)
- **Geolocalização**: `coords_lat`, `coords_lon` (cache)
- **Cálculos**: `distancia_km`, `taxa_entrega`

#### Cliente
- Dados do cliente (nome, telefone)
- Relacionamento com endereços (`endereco_cliente`)

#### AuditLog (P0.3)
- Trilha completa de operações críticas
- Campos: `ts`, `actor`, `action`, `entity_type`, `entity_id`, `metadata_json`

---

## 🎨 3. ARQUITETURA DO FRONTEND

### 3.1. Stack Tecnológica
- **Framework**: React 19.2
- **Build Tool**: Vite 7.2
- **TypeScript**: 5.9
- **UI Library**: Material-UI (MUI) 7.3
- **State Management**: React Query (TanStack Query) 5.90
- **Forms**: React Hook Form + Zod
- **Routing**: React Router DOM 7.11
- **Offline**: Dexie (IndexedDB) + Service Worker
- **Maps**: Leaflet + React-Leaflet

### 3.2. Estrutura de Pastas (Frontend)
```
frontend_v2/
├── src/
│   ├── api/              # Cliente HTTP e endpoints
│   │   ├── http.ts       # Axios configurado
│   │   └── endpoints/    # Definições de endpoints
│   ├── features/         # Feature-based organization
│   │   ├── pedidos/      # Módulo completo de pedidos
│   │   │   ├── components/
│   │   │   ├── services/
│   │   │   ├── useCases/
│   │   │   ├── CreateOrderPage.tsx
│   │   │   ├── OrdersPage.tsx
│   │   │   └── schemas.ts
│   │   ├── customers/
│   │   ├── auth/
│   │   └── rotas/
│   ├── components/       # Componentes compartilhados
│   │   ├── common/
│   │   ├── form/
│   │   └── system/
│   ├── lib/              # Utilitários
│   │   ├── offline/      # Cache, outbox, IndexedDB
│   │   └── format/
│   ├── layout/           # Layout principal (AppShell)
│   ├── app/             # Configuração da app
│   │   ├── router.tsx
│   │   └── providers.tsx
│   └── types/           # TypeScript types
├── public/              # Assets estáticos
└── dist/               # Build de produção
```

### 3.3. Padrões Frontend

#### Feature-Based Organization
- Cada feature é um módulo completo e isolado
- Componentes, serviços, casos de uso agrupados por feature
- Facilita manutenção e escalabilidade

#### Service Layer (Frontend)
- Interfaces TypeScript para serviços (ex: `IPedidoPrintService`)
- Implementações concretas com injeção de dependência
- Hooks customizados para uso nos componentes

#### Offline-First
- **IndexedDB** (Dexie) para cache local
- **Service Worker** (Workbox) para cache de assets
- **Outbox Pattern** para sincronização de operações offline
- **React Query** com cache offline

### 3.4. Rotas Principais
- `/` - Lista de pedidos
- `/pedidos/novo` - Criar pedido (wizard 4 steps)
- `/pedidos/:id` - Detalhes do pedido
- `/pedidos/:id/editar` - Editar pedido
- `/clientes` - Gestão de clientes
- `/rota-entrega` - Otimização de rotas
- `/fontes-pedido` - Gestão de fontes
- `/login` - Autenticação

---

## 🔐 4. SISTEMA DE BACKUP (P0 + P1)

### 4.1. Visão Geral
Sistema robusto e multi-camadas de backup com proteção contra perda de dados e robustez operacional.

### 4.2. Componentes P0 (Proteção contra Perda de Dados)

#### P0.1 - Backups Automáticos Horários
- **Frequência**: A cada 1 hora
- **Janelas**: Seg-Sex 07:00-18:00, Sáb 07:00-14:00
- **Idempotência**: Não cria se já existe backup nos últimos 55 minutos
- **Instalação**: `install_backup_task.ps1` (Windows Task Scheduler)

#### P0.2 - Fail-Closed para Operações Destrutivas
- **Comportamento**: Bloqueia operação se backup falhar
- **Rotas protegidas**: Todas as rotas DELETE críticas
- **Resposta**: HTTP 503 com mensagem clara
- **Override**: Suportado com auditoria obrigatória

#### P0.3 - Soft Delete + Trilha de Auditoria
- **Soft Delete**: Pedidos não são removidos fisicamente (`deleted_at`)
- **Auditoria**: Tabela `audit_log` registra todas as operações críticas
- **Recuperação**: Endpoints para restaurar e listar deletados
- **Migração**: `add_soft_delete_and_audit.py`

#### P0.4 - Teste Recorrente de Restauração
- **Frequência**: Diário às 06:30
- **Processo**: Restaura em sandbox, valida integridade, sanity checks
- **Instalação**: `install_restore_test_task.ps1`

### 4.3. Componentes P1 (Robustez Operacional)

#### P1.1 - Validação Forte e Padronizada
- **Módulo**: `validate_db.py`
- **Validações**: `PRAGMA integrity_check`, schema_version, sanity checks
- **Schema Version**: `APP_SCHEMA_VERSION = '1.0'` (em `config.py`)

#### P1.2 - Política de Retenção GFS
- **Algoritmo**: Grandfather-Father-Son
- **Configuração**: Via `.env` (HOURLY, DAILY, WEEKLY, MONTHLY)
- **Script**: `cleanup_backups.py`

#### P1.3 - Verificação de Offsite
- **Verificações**: Arquivo existe, tamanho, hash opcional
- **Integração**: Automática em `backup.py`

#### P1.4 - Diretório Secundário Local
- **Configuração**: `BACKUP_SECONDARY_DIR` (opcional)
- **Objetivo**: Segundo destino local (outro drive)

#### P1.5 - Health/Status Operacional
- **Arquivo**: `backend/instance/backup_status.json`
- **Endpoint**: `GET /api/admin/backup/health`
- **Health Levels**: OK, WARN, FAIL

### 4.4. Armazenamento de Backups
- **Local**: `backend/instance/backups/` (não encriptado)
- **Remoto**: Google Drive Desktop (encriptado AES-256-GCM)
- **Formato**: `.db`, `.zip`, `.zip.enc`

### 4.5. Gatilhos de Backup
1. **Startup do servidor** (`main.py`)
2. **Antes de operações destrutivas** (fail-closed - P0.2)
3. **Agendado horário** (P0.1)
4. **Teste de restauração** (P0.4)
5. **Manual** (CLI ou código)

---

## 🔑 5. REGRAS DE NEGÓCIO CRÍTICAS

### 5.1. Command Pattern (UI & Ações)
> *"Botões com regra de classe"*

- **Regra**: Cada botão/ação instancia uma Classe de Comando específica
- **Estrutura**: `Invoker (Botão)` → `Command Class` → `Receiver (Serviço/Banco)`
- **Exemplo**: Botão "Confirmar Pedido" → `new ConfirmarPedidoCommand(id).execute()`

### 5.2. Persistência de Pedidos
> *"Pedidos devem ser postados na .db"*

- **Atomicidade**: Gravação no `.db` é fonte única de verdade
- **Fluxo**:
  1. Pedido chega na memória
  2. Validação (Fail Fast)
  3. Conversão para DTO
  4. Inserção imediata na `.db` via Repository
- **Restrição**: Nenhuma confirmação antes do commit confirmado

### 5.3. Soft Delete
- Pedidos não são removidos fisicamente
- Coluna `deleted_at` marca como deletado
- Filtragem automática em todos os métodos `buscar_*`
- Endpoints para restaurar e listar deletados

### 5.4. Fail-Closed
- Operações destrutivas bloqueadas se backup falhar
- HTTP 503 com mensagem clara
- Override com auditoria obrigatória

---

## 🔧 6. CONFIGURAÇÕES E VARIÁVEIS DE AMBIENTE

### 6.1. Arquivo `.env` (Backend)
```env
# Segurança
SECRET_KEY=<chave-secreta>
ADMIN_PASSWORD=plante1998

# Banco de Dados
DATABASE_PATH=%USERPROFILE%/var/lib/database/database.db

# Backup
BACKUP_ENCRYPTION_KEY=<chave-base64>
GDRIVE_BACKUP_DIR=C:\Users\<USER>\Meu Drive\...
BACKUP_SECONDARY_DIR=D:\Backups\Secundario  # P1.4 (opcional)

# Retenção GFS (P1.2)
BACKUP_RETENTION_HOURLY=48
BACKUP_RETENTION_DAILY=30
BACKUP_RETENTION_WEEKLY=12
BACKUP_RETENTION_MONTHLY=12

# APIs Externas
GRAPHHOPPER_API_KEY=<key>
OPENROUTE_API_KEY=<key>
ENDERECO_FLORICULTURA=<endereco>

# Servidor
HOST=0.0.0.0
PORT=5000
FLASK_ENV=development
USE_HTTPS=false
```

### 6.2. Configurações do Frontend
- **API Target**: `VITE_API_TARGET` (padrão: `http://localhost:5000`)
- **PWA**: Configurado via `vite.config.ts` (Workbox)

---

## 📡 7. API ENDPOINTS PRINCIPAIS

### 7.1. Pedidos
- `GET /api/pedidos` - Listar pedidos (com filtros)
- `GET /api/pedidos/<id>` - Detalhes do pedido
- `POST /api/pedidos` - Criar pedido
- `PUT /api/pedidos/<id>` - Atualizar pedido
- `DELETE /api/pedidos/<id>` - Soft delete (P0.3)
- `POST /api/pedidos/<id>/restore` - Restaurar pedido deletado
- `GET /api/pedidos/deleted` - Listar deletados

### 7.2. Clientes
- `GET /api/clientes/buscar` - Buscar clientes
- `POST /api/clientes` - Criar cliente
- `DELETE /api/clientes/<id>` - Deletar cliente

### 7.3. Rotas
- `POST /api/rotas/otimizar` - Otimizar rota de entrega

### 7.4. Autenticação
- `POST /api/auth/login` - Login
- `GET /api/auth/check` - Verificar autenticação

### 7.5. Admin/Backup
- `GET /api/admin/backup/health` - Health do backup (P1.5)

---

## 🧪 8. TESTES

### 8.1. Estrutura de Testes
- **Framework**: pytest
- **Localização**: `backend/tests/`
- **Cobertura**: Testes unitários para componentes P0 e P1

### 8.2. Testes Principais
- `test_scheduled_backup.py` - P0.1
- `test_fail_closed.py` - P0.2
- `test_soft_delete.py` - P0.3
- `test_audit_log.py` - P0.3
- `test_restore_smoke_test.py` - P0.4
- `test_validate_db.py` - P1.1
- `test_retention.py` - P1.2
- `test_remote_verify.py` - P1.3
- `test_backup_status.py` - P1.5

---

## 🚀 9. COMANDOS E SCRIPTS ÚTEIS

### 9.1. Iniciar Servidor
```bash
# Desenvolvimento
python backend/main.py

# Com HTTPS
python backend/main.py --https

# Modo estável (sem reloader)
python backend/main.py --no-reload
```

### 9.2. Backup
```bash
# Backup manual
python backend/scripts/backup/backup.py

# Listar backups
python backend/scripts/backup/backup.py --list

# Restaurar backup
python backend/scripts/backup/restore.py

# Health do backup
curl -u admin:<password> http://localhost:5000/api/admin/backup/health
```

### 9.3. Migrações
```bash
# Soft delete e auditoria (P0.3)
python backend/scripts/migrations/add_soft_delete_and_audit.py

# Schema version (P1.1)
python backend/scripts/migrations/add_app_meta_schema_version.py
```

### 9.4. Frontend
```bash
# Desenvolvimento
npm run dev

# Build produção
npm run build

# Preview
npm run preview
```

---

## 📚 10. DOCUMENTAÇÃO RELACIONADA

### 10.1. Documentos Principais
- `.cursor/CONTEXT.md` - Contexto e regras de negócio
- `backend/docs/ESTUDO_BACKUP_COMPLETO.md` - Sistema de backup completo
- `backend/DOCUMENTACAO_TECNICA.md` - Arquitetura técnica do backend
- `docs/README.md` - Documentação geral do projeto

### 10.2. Guias de Configuração
- `backend/docs/BACKUP_P1_GUIA.md` - Configuração P1
- `backend/docs/CONFIGURAR_GOOGLE_SHEETS.md` - Integração Google Sheets

---

## 🎯 11. PRINCÍPIOS E DIRETRIZES

### 11.1. Clean Code
- **SOLID**: Princípios rigorosamente aplicados
- **Interfaces First**: Toda service/complex component tem interface
- **Encapsulation**: Classes com `private`/`protected` rigorosos
- **DTOs**: Sempre usar DTOs, nunca objetos genéricos
- **Fail Fast**: Validação imediata com erros claros

### 11.2. Naming Conventions
- **Ubiquitous Language**: Nomes devem refletir o domínio
- **Sem abreviações**: `customerRepository` não `custRepo`
- **Interfaces**: Prefixo claro (ex: `IPedidoService`)

### 11.3. Refatoração
- Identificar funções soltas → Extrair para Commands
- Centralizar SQL/File I/O → Repository Pattern
- Isolar Backup → Service isolado

---

## 🔄 12. FLUXOS PRINCIPAIS

### 12.1. Criar Pedido
```
1. Frontend: Wizard 4 steps (React Hook Form + Zod)
2. Submit → API POST /api/pedidos
3. Route → Validação (Schema)
4. Service → Lógica de negócio (cálculo taxa, etc)
5. Repository → Persistência no SQLite
6. Commit → Confirmação HTTP 201
7. Frontend: Atualização React Query cache
```

### 12.2. Deletar Pedido (com P0.2 e P0.3)
```
1. Frontend: DELETE /api/pedidos/<id>
2. Route → Fail-Closed Guard (P0.2)
3. Tentar criar backup
   ├─ Sucesso → Continuar
   └─ Falha → HTTP 503 (bloqueado)
4. Repository → Soft Delete (P0.3)
   - Marcar deleted_at
   - Não remover fisicamente
5. Auditoria → Registrar em audit_log
6. Response → HTTP 200
```

### 12.3. Backup Automático
```
1. Gatilho (startup/agendado/crítico)
2. BackupManager.create_backup()
3. SQLite backup nativo
4. Validação (PRAGMA integrity_check)
5. Compressão (opcional)
6. Encriptação (se remoto)
7. Cópia para diretórios (local + remoto + secundário)
8. Verificação remota (P1.3)
9. Atualizar status (P1.5)
10. Limpeza GFS (P1.2)
```

---

## ⚠️ 13. PONTOS DE ATENÇÃO

### 13.1. Banco de Dados
- **Localização**: Fora do repositório (`%USERPROFILE%/var/lib/database/`)
- **Backup**: Sempre antes de operações críticas
- **Soft Delete**: Filtragem automática em queries

### 13.2. Autenticação
- **Modo**: Seletiva (visualização livre, ações protegidas)
- **Usuário padrão**: `admin` / `plante1998`
- **Rotas protegidas**: Criar/editar/deletar pedidos

### 13.3. Offline
- **Cache**: IndexedDB (Dexie)
- **Sincronização**: Outbox pattern
- **Service Worker**: Workbox (Vite PWA)

### 13.4. Backup
- **Fail-Closed**: Operações destrutivas bloqueadas sem backup
- **Encriptação**: AES-256-GCM para remotos
- **Retenção**: GFS configurável

---

## 📝 14. NOTAS DE DESENVOLVIMENTO

### 14.1. Comandos Customizados
- `/refactor`: Extrair magic numbers, criar interfaces, aplicar guard clauses
- `/solid`: Analisar violações SOLID e sugerir refatoração

### 14.2. Idioma
- **Código**: Inglês (nomes, variáveis, funções)
- **Comentários**: Português (Brasil)
- **Documentação**: Português (Brasil)

### 14.3. Versionamento
- **Git**: Estrutura de branches conforme necessidade
- **Backups**: Não versionados (`.gitignore`)

---

**Fim da Memória do Projeto**
