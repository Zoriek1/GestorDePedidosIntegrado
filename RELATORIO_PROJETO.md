# Relatório Geral do Projeto - Plante Uma Flor

## 📋 Visão Geral

**Plante Uma Flor** é um sistema completo de gestão de pedidos desenvolvido especificamente para floriculturas. O sistema foi projetado para substituir aplicações desktop antigas por uma solução moderna, multiplataforma e acessível de qualquer dispositivo.

### Informações Básicas
- **Versão**: 3.0.1
- **Tipo**: Progressive Web App (PWA)
- **Arquitetura**: Frontend (PWA) + Backend (Flask REST API)
- **Banco de Dados**: SQLite
- **Linguagens**: Python (Backend), JavaScript (Frontend)

---

## 🏗️ Arquitetura do Sistema

### Componentes Principais

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

### Tecnologias Utilizadas

#### Backend
- **Flask 3.0+**: Framework web Python
- **Flask-SQLAlchemy**: ORM para banco de dados
- **Flask-CORS**: Suporte a CORS para API
- **Flask-Migrate**: Migrações de banco de dados
- **SQLite**: Banco de dados relacional
- **python-dateutil**: Manipulação de datas
- **requests**: Cliente HTTP para APIs externas
- **cryptography**: Criptografia para backups
- **marshmallow**: Validação e serialização de dados

#### Frontend
- **HTML5 + CSS3**: Estrutura e estilos
- **JavaScript ES6+**: Lógica da aplicação
- **Tailwind CSS**: Framework CSS utilitário
- **Service Worker API**: Funcionalidade offline
- **IndexedDB API**: Armazenamento local
- **Fetch API**: Comunicação com backend

#### APIs Externas
- **GraphHopper API**: Cálculo de rotas e distâncias
- **OpenRouteService API**: Geocodificação e rotas (fallback)
- **Nominatim (OpenStreetMap)**: Geocodificação gratuita
- **ViaCEP API**: Validação de CEP brasileiro

---

## 📁 Estrutura de Pastas

### Estrutura Geral

```
Gestor de Pedidos Plante uma flor/
├── backend/                          # Backend Flask
│   ├── app/                          # Aplicação principal
│   │   ├── __init__.py              # Factory do Flask
│   │   ├── cli.py                   # CLI unificado
│   │   ├── config.py                # Configurações
│   │   ├── middleware.py            # Middleware de autenticação
│   │   ├── cors.py                  # Configuração CORS
│   │   ├── errors.py                # Tratamento de erros
│   │   ├── extensions.py            # Extensões Flask
│   │   ├── factory.py               # Application Factory
│   │   ├── static.py                # Rotas estáticas
│   │   │
│   │   ├── models/                  # Modelos de dados
│   │   │   ├── pedido.py           # Modelo de Pedido
│   │   │   ├── cliente.py          # Modelo de Cliente
│   │   │   ├── endereco_cliente.py  # Modelo de Endereço
│   │   │   ├── rota_otimizada.py    # Modelo de Rota
│   │   │   ├── fonte_pedido.py      # Modelo de Fonte de Pedido
│   │   │   └── pedido_fonte.py      # Tabela auxiliar de pedidos por fonte
│   │   │
│   │   ├── routes/                  # Rotas da API (blueprints)
│   │   │   ├── api.py              # Endpoints gerais (legado)
│   │   │   ├── pedidos.py          # Endpoints de pedidos
│   │   │   ├── clientes.py         # Endpoints de clientes
│   │   │   ├── rotas.py            # Endpoints de rotas
│   │   │   └── auth.py             # Endpoints de autenticação
│   │   │
│   │   ├── repositories/            # Camada de acesso ao banco
│   │   │   ├── base_repository.py  # Repository base
│   │   │   ├── pedido_repository.py # Repository de pedidos
│   │   │   └── cliente_repository.py # Repository de clientes
│   │   │
│   │   ├── schemas/                 # Validação/serialização
│   │   │   ├── common.py           # Helpers de resposta
│   │   │   ├── pedido_schema.py    # Schema de pedidos
│   │   │   └── cliente_schema.py   # Schema de clientes
│   │   │
│   │   ├── services/                # Serviços de negócio
│   │   │   ├── distancia.py        # Cálculo de distâncias
│   │   │   ├── graphhopper.py       # Integração GraphHopper
│   │   │   └── taxa_entrega.py     # Cálculo de taxas
│   │   │
│   │   └── utils/                   # Utilitários
│   │       ├── backup_helper.py    # Gerenciamento de backups
│   │       └── fonte_helper.py     # Helpers para fontes
│   │
│   ├── instance/                    # Dados de runtime (não versionados)
│   │   ├── database.db              # Banco de dados
│   │   ├── ssl/                     # Certificados SSL
│   │   ├── logs/                    # Logs do servidor
│   │   └── backups/                 # Backups do banco
│   │
│   ├── config/                      # Arquivos de configuração
│   │   ├── config_servidor.ini     # Configuração do servidor
│   │   ├── taxa_entrega.json       # Configuração de taxas
│   │   └── google_credentials.json # Credenciais Google (não versionado)
│   │
│   ├── scripts/                     # Scripts de manutenção
│   │   ├── migrations/             # Scripts de migração (legado)
│   │   ├── tests/                  # Scripts de teste
│   │   ├── backup/                 # Scripts de backup
│   │   ├── export/                 # Scripts de exportação
│   │   ├── ssl/                    # Scripts de SSL
│   │   └── server/                 # Scripts de servidor
│   │
│   ├── tests/                       # Testes pytest
│   │   ├── conftest.py             # Fixtures
│   │   ├── test_api.py             # Testes de API
│   │   ├── test_api_endpoints.py   # Testes de endpoints
│   │   ├── test_models.py          # Testes de models
│   │   ├── test_repositories.py    # Testes de repositories
│   │   ├── test_schemas.py         # Testes de schemas
│   │   └── test_integration.py     # Testes de integração
│   │
│   ├── main.py                      # Ponto de entrada
│   ├── requirements.txt             # Dependências Python
│   ├── pytest.ini                   # Configuração pytest
│   └── pyproject.toml               # Configuração ruff/black
│
├── frontend/                        # Frontend PWA
│   ├── assets/                      # Recursos estáticos
│   │   ├── css/                    # Estilos
│   │   │   └── style.css          # CSS principal
│   │   ├── images/                # Imagens
│   │   └── js/                    # JavaScript
│   │       ├── app.js             # Aplicação principal
│   │       ├── router.js          # Roteador SPA
│   │       ├── api.js             # Cliente API
│   │       ├── db.js              # IndexedDB
│   │       ├── auth.js            # Autenticação
│   │       ├── form.js            # Formulário de pedido
│   │       ├── painel.js          # Painel administrativo
│   │       └── components/        # Componentes
│   │           ├── modal.js       # Modal
│   │           ├── notification.js # Notificações
│   │           └── pedido-card.js # Card de pedido
│   │
│   ├── pages/                      # Páginas SPA
│   │   ├── criar-pedido.html      # Criar pedido
│   │   ├── painel.html            # Painel
│   │   ├── login.html             # Login
│   │   ├── clientes.html          # Clientes
│   │   ├── rota-entrega.html       # Rotas
│   │   └── fontes-pedido.html     # Fontes de pedido
│   │
│   ├── index.html                  # Página principal
│   ├── manifest.json               # Manifest PWA
│   └── sw.js                       # Service Worker
│
└── README.md                       # Documentação principal
```

---

## 🗂️ Categorias/Modelos de Dados

### 1. Pedido (`app/models/pedido.py`)
Modelo principal do sistema. Contém todos os dados de um pedido de flores.

**Campos Principais:**
- **Step 1 - Dados do Cliente**: `cliente`, `telefone_cliente`, `destinatario`, `tipo_pedido`
- **Step 2 - Produto e Agendamento**: `produto`, `flores_cor`, `valor`, `dia_entrega`, `horario`
- **Step 3 - Logística**: `cep`, `rua`, `numero`, `bairro`, `cidade`, `endereco`, `obs_entrega`
- **Step 4 - Finalização**: `mensagem`, `pagamento`, `observacoes`, `status_pagamento`
- **Controle**: `status`, `quantidade`, `oculto`, `impresso`
- **Relacionamentos**: `cliente_id`, `fonte_pedido_id`
- **Cálculos**: `distancia_km`, `taxa_entrega`, `coords_lat`, `coords_lon`
- **Timestamps**: `created_at`, `updated_at`

**Status Possíveis:**
- `agendado` (Azul): Pedido recém-criado
- `em_producao` (Amarelo): Pedido em preparação
- `pronto_entrega` (Verde): Pronto para entrega
- `em_rota` (Laranja): Em rota de entrega
- `pronto_retirada` (Verde): Pronto para retirada
- `concluido` (Roxo): Pedido concluído
- `cancelado` (Vermelho): Pedido cancelado

### 2. Cliente (`app/models/cliente.py`)
Modelo para gerenciar clientes do sistema.

**Campos:**
- `id`, `nome`, `telefone`, `email`, `observacoes`
- `created_at`, `updated_at`

**Relacionamentos:**
- Um cliente pode ter múltiplos pedidos
- Um cliente pode ter múltiplos endereços

### 3. EnderecoCliente (`app/models/endereco_cliente.py`)
Endereços associados a clientes.

**Campos:**
- `id`, `cliente_id`, `cep`, `rua`, `numero`, `bairro`, `cidade`
- `complemento`, `referencia`, `principal`
- `created_at`, `updated_at`

### 4. FontePedido (`app/models/fonte_pedido.py`)
Fontes de onde os pedidos são originados (Ifood, Site, WhatsApp, etc).

**Campos:**
- `id`, `nome`, `ativo`
- `created_at`, `updated_at`

**Funcionalidades:**
- Sistema de numeração sequencial por fonte
- Tabelas auxiliares para rastreamento de pedidos por fonte

### 5. RotaOtimizada (`app/models/rota_otimizada.py`)
Rotas otimizadas de entrega calculadas pelo sistema.

**Campos:**
- `id`, `nome`, `distancia_total_km`, `duracao_total_min`
- `origem_lat`, `origem_lon`, `num_pedidos`
- `sequencia_pedidos` (JSON), `waypoints_coords` (JSON)
- `metodo_otimizacao`, `created_at`

---

## 🔌 Endpoints da API

### Base URL
```
http://localhost:5000/api
https://localhost:5000/api
```

### Autenticação
Alguns endpoints requerem autenticação via `@requires_edit_auth`. Configure no `.env`:
```env
EDIT_USERNAME=admin
EDIT_PASSWORD=sua_senha
```

### Endpoints por Categoria

#### Health Check
- `GET /api/health` - Verifica status da API

#### Pedidos (`/api/pedidos`)
- `GET /api/pedidos` - Lista pedidos (com filtros opcionais)
  - Query params: `status`, `data_inicio`, `data_fim`, `search`, `limit`
- `GET /api/pedidos/<id>` - Obtém pedido específico
- `POST /api/pedidos` - Cria novo pedido (requer auth)
- `PUT /api/pedidos/<id>` - Atualiza pedido (requer auth)
- `DELETE /api/pedidos/<id>` - Deleta pedido (requer auth)
- `PUT /api/pedidos/<id>/status` - Atualiza status do pedido
- `POST /api/pedidos/<id>/marcar-impresso` - Marca pedido como impresso
- `GET /api/pedidos/por-data?data=YYYY-MM-DD` - Pedidos por data
- `GET /api/pedidos/overdue` - Lista pedidos atrasados
- `GET /api/pedidos/<id>/distancia` - Calcula distância do pedido
- `POST /api/pedidos/calcular-distancias` - Calcula distâncias em lote
- `POST /api/pedidos/<id>/calcular-taxa` - Calcula taxa de entrega

#### Rotas Otimizadas (`/api/pedidos/rota-otimizada`)
- `POST /api/pedidos/rota-otimizada` - Cria rota otimizada
- `GET /api/pedidos/rota-otimizada/<rota_id>` - Obtém rota otimizada

#### Clientes (`/api/clientes`)
- `GET /api/clientes` - Lista clientes
- `GET /api/clientes/<id>` - Obtém cliente específico
- `POST /api/clientes` - Cria novo cliente (requer auth)
- `PUT /api/clientes/<id>` - Atualiza cliente (requer auth)
- `DELETE /api/clientes/<id>` - Deleta cliente (requer auth)
- `GET /api/clientes/buscar?q=termo` - Busca clientes (autocomplete)

#### Fontes de Pedido (`/api/fontes-pedido`)
- `GET /api/fontes-pedido` - Lista fontes ativas
- `GET /api/fontes-pedido/all` - Lista todas as fontes
- `POST /api/fontes-pedido` - Cria nova fonte (requer auth)
- `PUT /api/fontes-pedido/<id>` - Atualiza fonte (requer auth)
- `DELETE /api/fontes-pedido/<id>` - Desativa fonte (requer auth)
- `GET /api/pedidos/fonte/<fonte_id>` - Lista pedidos de uma fonte
- `GET /api/pedidos/fonte/<fonte_id>/consolidado` - Estatísticas da fonte

#### Autenticação (`/api/auth`)
- `POST /api/auth/login` - Login de usuário
- `GET /api/auth/check` - Verifica status de autenticação

#### Estatísticas e Utilitários
- `GET /api/stats` - Estatísticas gerais dos pedidos
- `GET /api/backup/status` - Status dos backups
- `POST /api/cleanup` - Arquivar pedidos antigos (requer auth)
- `POST /api/exportar-planilha` - Exporta vendas para Google Sheets (requer auth)

#### Debug (requer `ENABLE_DEBUG_ENDPOINTS=true`)
- `GET /api/debug/geocode` - Testa geocodificação
- `POST /api/debug/limpar-distancias` - Limpa cache de distâncias
- `GET /api/debug/config-floricultura` - Verifica configuração da floricultura
- `POST /api/debug/reset-floricultura` - Reseta cache da floricultura
- `GET /api/debug/testar-apis` - Testa APIs externas

---

## 🧪 Testes

### Estrutura de Testes

O projeto possui uma suíte completa de testes usando **pytest**:

```
backend/tests/
├── conftest.py              # Fixtures compartilhadas
├── test_api.py              # Testes de API
├── test_api_endpoints.py    # Testes de endpoints específicos
├── test_models.py           # Testes de modelos
├── test_repositories.py     # Testes de repositories
├── test_schemas.py          # Testes de schemas
└── test_integration.py      # Testes de integração
```

### Configuração (pytest.ini)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
```

### Como Executar Testes

```bash
cd backend

# Executar todos os testes
pytest

# Executar testes específicos
pytest tests/test_api.py
pytest tests/test_models.py

# Modo verboso
pytest -v

# Com cobertura
pytest --cov=app

# Excluir testes lentos
pytest -m "not slow"

# Apenas testes de integração
pytest -m integration
```

### Cobertura de Testes

O projeto possui testes para:
- ✅ Modelos de dados (Pedido, Cliente, etc)
- ✅ Repositories (camada de acesso ao banco)
- ✅ Schemas (validação de dados)
- ✅ Endpoints da API
- ✅ Integração entre componentes

---

## 🔧 Funcionalidades Principais

### 1. Gestão de Pedidos
- Criação de pedidos em 4 etapas (Cliente → Produto → Endereço → Finalização)
- Edição completa de pedidos
- Mudança rápida de status
- Visualização detalhada em modal
- Impressão profissional em A4

### 2. Gestão de Clientes
- Cadastro completo de clientes
- Histórico de pedidos por cliente
- Busca e autocomplete
- Múltiplos endereços por cliente

### 3. Cálculo de Distâncias e Rotas
- Cálculo automático de distâncias usando GraphHopper/OpenRouteService
- Geocodificação de endereços (Nominatim + OpenRouteService)
- Cache de coordenadas para evitar geocodificação repetida
- Cálculo de tempo estimado de viagem

### 4. Sistema de Taxas de Entrega
- Configuração via arquivo JSON (`backend/config/taxa_entrega.json`)
- Sistema de faixas de distância (de_km/ate_km)
- Taxa mínima e máxima configuráveis
- Cálculo automático baseado na distância

### 5. Otimização de Rotas
- Agrupamento por horário de entrega
- Otimização geográfica dentro de grupos
- Sequência otimizada de entregas
- Links para visualização no GraphHopper Maps e Google Maps

### 6. Fontes de Pedido
- Sistema de numeração sequencial por fonte
- Rastreamento de pedidos por origem (Ifood, Site, etc)
- Estatísticas consolidadas por fonte
- Tabelas auxiliares para cada fonte

### 7. Funcionalidades Offline
- Service Worker para cache de assets
- IndexedDB para armazenamento local de pedidos
- Sincronização automática quando online
- Funcionamento completo sem internet

### 8. Backup Automático
- Backup automático ao iniciar servidor (se não houver backup recente)
- Backup antes de operações críticas (deletar pedido, etc)
- Scripts de backup manual e agendado
- Restauração de backups

### 9. HTTPS e SSL
- Suporte a HTTPS com certificados SSL
- Geração automática de certificados com mkcert
- Suporte a hostname customizado
- Certificados para múltiplos IPs

### 10. Exportação
- Exportação de vendas para Google Sheets
- Integração com Google Sheets API
- Scripts de exportação manual e agendada

---

## 📊 Arquitetura de Código

### Padrões Utilizados

#### Backend
- **Application Factory Pattern**: `app/factory.py`
- **Repository Pattern**: `app/repositories/`
- **Service Layer**: `app/services/`
- **Schema Validation**: `app/schemas/` (Marshmallow)
- **Blueprint Organization**: Rotas organizadas por domínio

#### Frontend
- **SPA (Single Page Application)**: Roteamento client-side
- **Component Pattern**: Componentes reutilizáveis
- **Service Worker**: Cache e funcionalidade offline
- **IndexedDB**: Armazenamento local persistente

### Convenções de Código

#### Python
- Arquivos: `snake_case.py`
- Classes: `PascalCase`
- Funções: `snake_case`
- Constantes: `UPPER_CASE`

#### JavaScript
- Arquivos: `kebab-case.js` ou `camelCase.js`
- Classes: `PascalCase`
- Funções: `camelCase`
- Constantes: `UPPER_CASE`

---

## 🔐 Segurança

### Autenticação
- Autenticação seletiva (apenas criar/deletar requerem auth)
- Visualização livre para facilitar uso
- Middleware de autenticação em rotas específicas

### Rate Limiting
- 60 requisições por minuto
- 1000 requisições por hora
- Configurável via variável de ambiente

### HTTPS
- Suporte completo a HTTPS
- Certificados SSL auto-assinados (mkcert)
- Distribuição de certificado CA para clientes

### Debug Endpoints
- Endpoints de debug desabilitados por padrão
- Requer `ENABLE_DEBUG_ENDPOINTS=true` no `.env`
- Proteção adicional com autenticação

---

## 📦 Dependências Principais

### Backend (requirements.txt)
```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.0
Flask-Migrate==4.0.5
marshmallow==3.20.1
SQLAlchemy>=2.0.36
python-dateutil==2.8.2
python-dotenv==1.0.0
requests==2.31.0
cryptography==41.0.0
pytest==7.4.3
pytest-cov==4.1.0
ruff==0.1.6
black==23.12.1
```

### Frontend (package.json)
```
tailwindcss: ^3.4.1
workbox-build: ^7.0.0
rollup: ^4.0.0
```

---

## 🚀 Scripts e Ferramentas

### Scripts de Servidor
- `backend/scripts/server/start/` - Scripts para iniciar servidor
- `backend/scripts/server/stop/` - Scripts para parar servidor
- `backend/scripts/server/utils/` - Utilitários do servidor

### Scripts de Backup
- `backend/scripts/backup/backup.py` - Script de backup
- `backend/scripts/backup/restore.py` - Script de restauração
- `backend/scripts/backup/agendar_backup_windows.bat` - Agendar backup

### Scripts de Migração
- `backend/scripts/migrations/` - Scripts de migração do banco
- Migrações Flask-Migrate também disponíveis via CLI

### Scripts de SSL
- `backend/scripts/ssl/` - Scripts para gerar certificados SSL

### Scripts de Exportação
- `backend/scripts/export/exportar_vendas.py` - Exportação manual
- `backend/scripts/export/exportar_vendas_sheets.py` - Exportação para Google Sheets

### CLI Unificado
O projeto possui um CLI unificado via Flask CLI:

```bash
# Iniciar servidor
flask cli start
flask cli start --https
flask cli start --port 8080

# Backups
flask cli backup
flask cli backup --list
flask cli backup --restore caminho/backup.zip

# SSL
flask cli ssl generate
flask cli ssl check

# Banco de dados
flask cli db init
flask cli db migrate -m "Descrição"
flask cli db upgrade
```

---

## 📝 Configurações Importantes

### Arquivos de Configuração

1. **`.env`** (backend/.env) - Variáveis de ambiente
   - `GRAPHHOPPER_API_KEY` - Chave da API GraphHopper
   - `OPENROUTE_API_KEY` - Chave da API OpenRouteService
   - `ENDERECO_FLORICULTURA` - Endereço da floricultura
   - `EDIT_USERNAME` / `EDIT_PASSWORD` - Credenciais de autenticação
   - `DEBUG` - Modo debug
   - `ENABLE_DEBUG_ENDPOINTS` - Habilitar endpoints de debug

2. **`config/taxa_entrega.json`** - Configuração de taxas
   - Faixas de distância
   - Taxa mínima e máxima

3. **`config/config_servidor.ini`** - Configuração do servidor
   - Hostname do servidor

4. **`config/google_credentials.json`** - Credenciais Google Sheets (não versionado)

---

## 📈 Estatísticas do Projeto

### Linhas de Código (estimativa)
- **Backend**: ~15.000+ linhas de Python
- **Frontend**: ~5.000+ linhas de JavaScript
- **Total**: ~20.000+ linhas de código

### Arquivos
- **Python**: ~69 arquivos
- **JavaScript**: ~23 arquivos
- **HTML**: ~7 páginas
- **Testes**: 6 arquivos de teste

### Modelos de Dados
- 5 modelos principais (Pedido, Cliente, EnderecoCliente, FontePedido, RotaOtimizada)
- Tabelas auxiliares dinâmicas para fontes de pedido

### Endpoints da API
- ~40+ endpoints REST
- Organizados em 5 blueprints principais

---

## 🎯 Próximos Passos Sugeridos

1. **Melhorias de Performance**
   - Cache de queries frequentes
   - Otimização de índices do banco
   - Compressão de respostas JSON

2. **Funcionalidades Futuras**
   - Dashboard com gráficos
   - Relatórios avançados
   - Notificações push
   - Integração com WhatsApp Business API

3. **Testes**
   - Aumentar cobertura de testes
   - Testes E2E com Selenium/Playwright
   - Testes de performance

4. **Documentação**
   - Documentação da API (Swagger/OpenAPI)
   - Guias de contribuição
   - Documentação de deployment

---

## 📞 Suporte e Manutenção

### Logs
- Logs de acesso: `backend/instance/logs/access_YYYY-MM-DD.log`
- Logs do servidor: `backend/logs/`
- Logs de backup: `backend/instance/logs/backup_audit.log`

### Troubleshooting
- Verificar porta: `backend/scripts/server/utils/verificar_porta.bat`
- Parar servidor: `backend/scripts/server/stop/parar_servidor.bat`
- Verificar certificados SSL: `flask cli ssl check`

---

**Relatório gerado em**: 2025-01-28
**Versão do Projeto**: 3.0.1
**Última atualização**: 2024-12-26


