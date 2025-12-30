# Guia de Desenvolvimento

Guia completo para desenvolvimento do projeto Plante Uma Flor.

---

## Setup Inicial

### Requisitos

- **Python 3.8+**
- **Node.js** (para frontend_v2, opcional)
- **Git** (opcional)

### Instalação

```bash
# 1. Clonar/Baixar o projeto
cd "Gestor de Pedidos Plante uma flor"

# 2. Instalar dependências Python
cd backend
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações (veja docs/configuration.md)
```

---

## Comandos Principais

### Iniciar Servidor

```bash
cd backend

# HTTP
flask cli start

# HTTPS
flask cli start --https

# Porta customizada
flask cli start --port 8080

# Modo estável (sem reloader)
flask cli start --no-reload
```

### Backups

```bash
# Criar backup
flask cli backup

# Listar backups
flask cli backup --list

# Estatísticas
flask cli backup --stats

# Restaurar backup
flask cli backup --restore caminho/para/backup.zip
```

### Migrações de Banco

```bash
# Inicializar (primeira vez)
flask cli db init

# Criar migração
flask cli db migrate -m "Descrição da migração"

# Aplicar migrações
flask cli db upgrade

# Ver histórico
flask cli db history

# Ver versão atual
flask cli db current
```

### SSL/Certificados

```bash
# Gerar certificados
flask cli ssl generate

# Com hostname customizado
flask cli ssl generate --hostname meu-servidor.local

# Verificar certificados
flask cli ssl check
```

---

## Estrutura do Código

### Backend

**Arquitetura em Camadas:**

- **Models** (`app/models/`): Definem estrutura de dados
- **Repositories** (`app/repositories/`): Isolamento de acesso ao banco
- **Schemas** (`app/schemas/`): Validação e serialização
- **Routes** (`app/routes/`): Endpoints da API organizados em blueprints
- **Services** (`app/services/`): Lógica de negócio

**Convenções:**

- Arquivos Python: `snake_case.py`
- Classes: `PascalCase`
- Funções: `snake_case`
- Constantes: `UPPER_CASE`

### Frontend

**Frontend Legacy** (`/frontend`):

- Módulos ES6 separados por funcionalidade
- Service Worker para cache
- IndexedDB para armazenamento

**Frontend v2** (`/frontend_v2`):

- React + TypeScript
- Componentes funcionais
- Hooks customizados para API

---

## Adicionar Nova Funcionalidade

### Backend

1. **Criar Model** (se necessário):
```python
# app/models/nova_entidade.py
from app import db

class NovaEntidade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    # campos...
```

2. **Criar Service** (se necessário):
```python
# app/services/novo_servico.py
class NovoService:
    def metodo(self):
        # lógica...
```

3. **Criar Endpoint**:
```python
# app/routes/api.py ou novo blueprint
@api_bp.route('/nova-rota', methods=['GET'])
def nova_rota():
    # implementação...
```

### Frontend v2

1. **Criar Componente**:
```typescript
// src/features/nova-feature/Component.tsx
export function Component() {
  // implementação...
}
```

2. **Adicionar Rota**:
```typescript
// src/app/router.tsx
<Route path="/nova-rota" element={<Component />} />
```

3. **Integrar com API**:
```typescript
// src/api/endpoints/nova-feature.ts
export function useNovaFeature() {
  // React Query hook
}
```

---

## Testes

### Testes Automatizados (pytest)

```bash
cd backend

# Rodar todos os testes
pytest

# Testes específicos
pytest tests/test_api.py

# Modo verboso
pytest -v

# Com cobertura
pytest --cov=app
```

### Scripts de Teste Manual

```bash
cd backend/scripts/tests
python testar_graphhopper.py
python testar_endereco_problema.py
```

---

## Debug

### Ativar Debug no Backend

Edite `.env`:
```env
DEBUG=True
FLASK_ENV=development
```

### Ativar Endpoints de Debug

```env
ENABLE_DEBUG_ENDPOINTS=true
```

Endpoints de debug disponíveis:
- `GET /api/debug/geocode` - Testar geocodificação
- `GET /api/debug/testar-apis` - Testar APIs externas
- `POST /api/debug/limpar-distancias` - Limpar distâncias calculadas

### Console do Navegador

- Pressione `F12` para abrir DevTools
- Aba "Console" mostra erros JavaScript
- Aba "Network" mostra requisições HTTP

---

## Qualidade de Código

### Linting e Formatação

```bash
cd backend

# Verificar linting
ruff check .

# Formatar código
black .

# Verificar formatação (sem alterar)
black --check .
```

### CI/CD

O projeto inclui GitHub Actions workflow que:
- Executa linting (ruff)
- Verifica formatação (black)
- Roda testes (pytest)
- Testa em múltiplas versões do Python (3.8, 3.9, 3.10, 3.11)

---

## Troubleshooting

### Servidor não inicia

**Sintoma:** Erro ao executar `flask cli start`

**Soluções:**
1. Verifique se Python 3.8+ está instalado: `python --version`
2. Instale dependências: `pip install -r requirements.txt`
3. Verifique se porta 5000 está livre: `flask cli check port --port 5000`
4. Verifique logs em `backend/instance/logs/`

### Porta 5000 já está em uso

**Sintoma:** "Port 5000 is already in use"

**Soluções:**
1. Pare o servidor anterior: `flask cli stop` (se disponível)
2. Ou mate o processo manualmente:
   ```bash
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   ```
3. Ou use outra porta: `flask cli start --port 8080`

### Certificado SSL inválido

**Sintoma:** Navegador mostra "Certificado inválido"

**Soluções:**
1. Instale o certificado CA no dispositivo
2. Regere os certificados: `flask cli ssl generate`
3. Verifique se o hostname/IP está nos certificados

### Distâncias não calculam

**Sintoma:** Campo de distância fica vazio

**Soluções:**
1. Verifique se API keys estão configuradas no `.env`
2. Verifique se endereço da floricultura está configurado
3. Verifique logs do servidor para erros
4. Teste manualmente: `GET /api/debug/testar-apis`

### Dados não sincronizam offline

**Sintoma:** Mudanças offline não aparecem quando online

**Soluções:**
1. Verifique se Service Worker está ativo
2. Limpe cache: `Ctrl+Shift+Delete` → Limpar cache
3. Verifique console do navegador para erros

---

## Logs

### Logs do Servidor

- `backend/instance/logs/access_YYYY-MM-DD.log` - Logs de acesso
- Console do servidor - Logs de latência e erros

### Logs de Latência

Formato: `[HH:MM:SS] METHOD path durationMs ms`

Exemplo:
```
[14:30:15] GET    /api/pedidos              45.23 ms
[14:30:16] POST   /api/pedidos             120.45 ms
```

---

## Migrações

### Criar Migração

Após alterar models:

```bash
flask cli db migrate -m "Descrição da mudança"
```

### Aplicar Migrações

```bash
flask cli db upgrade
```

### Ver Histórico

```bash
flask cli db history
```

**Importante:** Sempre crie uma migração antes de fazer mudanças nos models e teste em ambiente de desenvolvimento antes de aplicar em produção.

---

## Variáveis de Ambiente

Todas as variáveis estão documentadas em [configuration.md](configuration.md).

Principais:

- `SECRET_KEY` - Chave secreta para sessões
- `SQLALCHEMY_DATABASE_URI` - URI do banco de dados
- `ADMIN_PASSWORD` - Senha do administrador
- `GRAPHHOPPER_API_KEY` - Chave da API GraphHopper
- `OPENROUTE_API_KEY` - Chave da API OpenRouteService
- `ENDERECO_FLORICULTURA` - Endereço da floricultura

---

## Recursos Adicionais

- [Architecture](architecture.md) - Arquitetura do sistema
- [API Documentation](api.md) - Documentação da API
- [Configuration](configuration.md) - Variáveis de ambiente
- [Routes](routes.md) - Mapa de rotas

---

**Última atualização:** Dezembro 2024


Guia completo para desenvolvimento do projeto Plante Uma Flor.

---

## Setup Inicial

### Requisitos

- **Python 3.8+**
- **Node.js** (para frontend_v2, opcional)
- **Git** (opcional)

### Instalação

```bash
# 1. Clonar/Baixar o projeto
cd "Gestor de Pedidos Plante uma flor"

# 2. Instalar dependências Python
cd backend
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações (veja docs/configuration.md)
```

---

## Comandos Principais

### Iniciar Servidor

```bash
cd backend

# HTTP
flask cli start

# HTTPS
flask cli start --https

# Porta customizada
flask cli start --port 8080

# Modo estável (sem reloader)
flask cli start --no-reload
```

### Backups

```bash
# Criar backup
flask cli backup

# Listar backups
flask cli backup --list

# Estatísticas
flask cli backup --stats

# Restaurar backup
flask cli backup --restore caminho/para/backup.zip
```

### Migrações de Banco

```bash
# Inicializar (primeira vez)
flask cli db init

# Criar migração
flask cli db migrate -m "Descrição da migração"

# Aplicar migrações
flask cli db upgrade

# Ver histórico
flask cli db history

# Ver versão atual
flask cli db current
```

### SSL/Certificados

```bash
# Gerar certificados
flask cli ssl generate

# Com hostname customizado
flask cli ssl generate --hostname meu-servidor.local

# Verificar certificados
flask cli ssl check
```

---

## Estrutura do Código

### Backend

**Arquitetura em Camadas:**

- **Models** (`app/models/`): Definem estrutura de dados
- **Repositories** (`app/repositories/`): Isolamento de acesso ao banco
- **Schemas** (`app/schemas/`): Validação e serialização
- **Routes** (`app/routes/`): Endpoints da API organizados em blueprints
- **Services** (`app/services/`): Lógica de negócio

**Convenções:**

- Arquivos Python: `snake_case.py`
- Classes: `PascalCase`
- Funções: `snake_case`
- Constantes: `UPPER_CASE`

### Frontend

**Frontend Legacy** (`/frontend`):

- Módulos ES6 separados por funcionalidade
- Service Worker para cache
- IndexedDB para armazenamento

**Frontend v2** (`/frontend_v2`):

- React + TypeScript
- Componentes funcionais
- Hooks customizados para API

---

## Adicionar Nova Funcionalidade

### Backend

1. **Criar Model** (se necessário):
```python
# app/models/nova_entidade.py
from app import db

class NovaEntidade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    # campos...
```

2. **Criar Service** (se necessário):
```python
# app/services/novo_servico.py
class NovoService:
    def metodo(self):
        # lógica...
```

3. **Criar Endpoint**:
```python
# app/routes/api.py ou novo blueprint
@api_bp.route('/nova-rota', methods=['GET'])
def nova_rota():
    # implementação...
```

### Frontend v2

1. **Criar Componente**:
```typescript
// src/features/nova-feature/Component.tsx
export function Component() {
  // implementação...
}
```

2. **Adicionar Rota**:
```typescript
// src/app/router.tsx
<Route path="/nova-rota" element={<Component />} />
```

3. **Integrar com API**:
```typescript
// src/api/endpoints/nova-feature.ts
export function useNovaFeature() {
  // React Query hook
}
```

---

## Testes

### Testes Automatizados (pytest)

```bash
cd backend

# Rodar todos os testes
pytest

# Testes específicos
pytest tests/test_api.py

# Modo verboso
pytest -v

# Com cobertura
pytest --cov=app
```

### Scripts de Teste Manual

```bash
cd backend/scripts/tests
python testar_graphhopper.py
python testar_endereco_problema.py
```

---

## Debug

### Ativar Debug no Backend

Edite `.env`:
```env
DEBUG=True
FLASK_ENV=development
```

### Ativar Endpoints de Debug

```env
ENABLE_DEBUG_ENDPOINTS=true
```

Endpoints de debug disponíveis:
- `GET /api/debug/geocode` - Testar geocodificação
- `GET /api/debug/testar-apis` - Testar APIs externas
- `POST /api/debug/limpar-distancias` - Limpar distâncias calculadas

### Console do Navegador

- Pressione `F12` para abrir DevTools
- Aba "Console" mostra erros JavaScript
- Aba "Network" mostra requisições HTTP

---

## Qualidade de Código

### Linting e Formatação

```bash
cd backend

# Verificar linting
ruff check .

# Formatar código
black .

# Verificar formatação (sem alterar)
black --check .
```

### CI/CD

O projeto inclui GitHub Actions workflow que:
- Executa linting (ruff)
- Verifica formatação (black)
- Roda testes (pytest)
- Testa em múltiplas versões do Python (3.8, 3.9, 3.10, 3.11)

---

## Troubleshooting

### Servidor não inicia

**Sintoma:** Erro ao executar `flask cli start`

**Soluções:**
1. Verifique se Python 3.8+ está instalado: `python --version`
2. Instale dependências: `pip install -r requirements.txt`
3. Verifique se porta 5000 está livre: `flask cli check port --port 5000`
4. Verifique logs em `backend/instance/logs/`

### Porta 5000 já está em uso

**Sintoma:** "Port 5000 is already in use"

**Soluções:**
1. Pare o servidor anterior: `flask cli stop` (se disponível)
2. Ou mate o processo manualmente:
   ```bash
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   ```
3. Ou use outra porta: `flask cli start --port 8080`

### Certificado SSL inválido

**Sintoma:** Navegador mostra "Certificado inválido"

**Soluções:**
1. Instale o certificado CA no dispositivo
2. Regere os certificados: `flask cli ssl generate`
3. Verifique se o hostname/IP está nos certificados

### Distâncias não calculam

**Sintoma:** Campo de distância fica vazio

**Soluções:**
1. Verifique se API keys estão configuradas no `.env`
2. Verifique se endereço da floricultura está configurado
3. Verifique logs do servidor para erros
4. Teste manualmente: `GET /api/debug/testar-apis`

### Dados não sincronizam offline

**Sintoma:** Mudanças offline não aparecem quando online

**Soluções:**
1. Verifique se Service Worker está ativo
2. Limpe cache: `Ctrl+Shift+Delete` → Limpar cache
3. Verifique console do navegador para erros

---

## Logs

### Logs do Servidor

- `backend/instance/logs/access_YYYY-MM-DD.log` - Logs de acesso
- Console do servidor - Logs de latência e erros

### Logs de Latência

Formato: `[HH:MM:SS] METHOD path durationMs ms`

Exemplo:
```
[14:30:15] GET    /api/pedidos              45.23 ms
[14:30:16] POST   /api/pedidos             120.45 ms
```

---

## Migrações

### Criar Migração

Após alterar models:

```bash
flask cli db migrate -m "Descrição da mudança"
```

### Aplicar Migrações

```bash
flask cli db upgrade
```

### Ver Histórico

```bash
flask cli db history
```

**Importante:** Sempre crie uma migração antes de fazer mudanças nos models e teste em ambiente de desenvolvimento antes de aplicar em produção.

---

## Variáveis de Ambiente

Todas as variáveis estão documentadas em [configuration.md](configuration.md).

Principais:

- `SECRET_KEY` - Chave secreta para sessões
- `SQLALCHEMY_DATABASE_URI` - URI do banco de dados
- `ADMIN_PASSWORD` - Senha do administrador
- `GRAPHHOPPER_API_KEY` - Chave da API GraphHopper
- `OPENROUTE_API_KEY` - Chave da API OpenRouteService
- `ENDERECO_FLORICULTURA` - Endereço da floricultura

---

## Recursos Adicionais

- [Architecture](architecture.md) - Arquitetura do sistema
- [API Documentation](api.md) - Documentação da API
- [Configuration](configuration.md) - Variáveis de ambiente
- [Routes](routes.md) - Mapa de rotas

---

**Última atualização:** Dezembro 2024


