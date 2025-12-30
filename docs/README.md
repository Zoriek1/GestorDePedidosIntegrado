# Documentação - Plante Uma Flor

Porta de entrada da documentação completa do projeto.

---

## 📖 Índice

### Documentação Principal

- **[architecture.md](architecture.md)** - Arquitetura do sistema, componentes, fluxos de dados
- **[dev.md](dev.md)** - Guia de desenvolvimento, setup, comandos, troubleshooting
- **[api.md](api.md)** - Documentação completa da API REST
- **[configuration.md](configuration.md)** - Variáveis de ambiente e configurações
- **[routes.md](routes.md)** - Mapa completo de rotas (auto-gerado)

### Documentação por Fase

- **[README.md](README.md)** (este arquivo) - Índice geral
- **Phase 0**: Telemetria e diagnósticos
  - [phase0-smoke.md](phase0-smoke.md)
  - [phase0-notes.md](phase0-notes.md)
  - [phase0-commits.md](phase0-commits.md)
- **Phase 1**: Frontend v2 Setup
  - [phase1-implementation-report.md](phase1-implementation-report.md)
  - [phase1-smoke.md](phase1-smoke.md)
  - [phase1-notes.md](phase1-notes.md)
  - [phase1-refetch-improvements.md](phase1-refetch-improvements.md)
- **Phase 1.1**: Auth Parity + Gradual Migration
  - [phase1_1-implementation-summary.md](phase1_1-implementation-summary.md)
  - [phase1_1-quick-reference.md](phase1_1-quick-reference.md)
  - [phase1_1-smoke.md](phase1_1-smoke.md)

---

## 🚀 Início Rápido

### Requisitos

- Python 3.8+
- Navegador moderno (Chrome, Edge, Firefox, Safari)

### Instalação

```bash
# 1. Instalar dependências
cd backend
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações (veja docs/configuration.md)

# 3. Iniciar servidor
flask cli start
```

### Acessar

- **Local**: `http://localhost:5000`
- **HTTPS**: `flask cli start --https` → `https://localhost:5000`
- **Swagger UI**: `http://localhost:5000/docs/swagger` (se implementado)

---

## 📚 Guias por Tarefa

### Para Desenvolvedores

1. **[dev.md](dev.md)** - Setup completo, comandos, troubleshooting
2. **[architecture.md](architecture.md)** - Entender a estrutura do código
3. **[api.md](api.md)** - Como consumir a API

### Para Configuração

1. **[configuration.md](configuration.md)** - Todas as variáveis de ambiente
2. **[routes.md](routes.md)** - Ver todas as rotas disponíveis

### Para Entender o Projeto

1. **[architecture.md](architecture.md)** - Visão geral do sistema
2. **[phase1_1-quick-reference.md](phase1_1-quick-reference.md)** - O que foi implementado recentemente

---

## 🔍 Encontrar Informações

### "Onde está a rota X?"

→ Veja [routes.md](routes.md) (mapa completo de rotas)

### "Quais variáveis de ambiente existem?"

→ Veja [configuration.md](configuration.md)

### "Como rodar em desenvolvimento?"

→ Veja [dev.md](dev.md)

### "Como consumir a API?"

→ Veja [api.md](api.md)

### "Qual a arquitetura do sistema?"

→ Veja [architecture.md](architecture.md)

---

## 📊 Status do Projeto

- ✅ **Phase 0**: Completo (Telemetria e diagnósticos)
- ✅ **Phase 1**: Completo (Frontend v2 Setup)
- ✅ **Phase 1.1**: Completo (Auth Parity + Gradual Migration)
- ⏳ **Phase 2**: Em andamento (Backend "Descobrível")

---

## 🔗 Links Úteis

- **Swagger UI**: `http://localhost:5000/docs/swagger` (quando implementado)
- **Health Check**: `http://localhost:5000/api/health`
- **Repositório**: [GitHub](https://github.com/...) (se aplicável)

---

**Última atualização:** Dezembro 2024

Porta de entrada da documentação completa do projeto.

---

## 📖 Índice

### Documentação Principal

- **[architecture.md](architecture.md)** - Arquitetura do sistema, componentes, fluxos de dados
- **[dev.md](dev.md)** - Guia de desenvolvimento, setup, comandos, troubleshooting
- **[api.md](api.md)** - Documentação completa da API REST
- **[configuration.md](configuration.md)** - Variáveis de ambiente e configurações
- **[routes.md](routes.md)** - Mapa completo de rotas (auto-gerado)

### Documentação por Fase

- **[README.md](README.md)** (este arquivo) - Índice geral
- **Phase 0**: Telemetria e diagnósticos
  - [phase0-smoke.md](phase0-smoke.md)
  - [phase0-notes.md](phase0-notes.md)
  - [phase0-commits.md](phase0-commits.md)
- **Phase 1**: Frontend v2 Setup
  - [phase1-implementation-report.md](phase1-implementation-report.md)
  - [phase1-smoke.md](phase1-smoke.md)
  - [phase1-notes.md](phase1-notes.md)
  - [phase1-refetch-improvements.md](phase1-refetch-improvements.md)
- **Phase 1.1**: Auth Parity + Gradual Migration
  - [phase1_1-implementation-summary.md](phase1_1-implementation-summary.md)
  - [phase1_1-quick-reference.md](phase1_1-quick-reference.md)
  - [phase1_1-smoke.md](phase1_1-smoke.md)

---

## 🚀 Início Rápido

### Requisitos

- Python 3.8+
- Navegador moderno (Chrome, Edge, Firefox, Safari)

### Instalação

```bash
# 1. Instalar dependências
cd backend
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações (veja docs/configuration.md)

# 3. Iniciar servidor
flask cli start
```

### Acessar

- **Local**: `http://localhost:5000`
- **HTTPS**: `flask cli start --https` → `https://localhost:5000`
- **Swagger UI**: `http://localhost:5000/docs/swagger` (se implementado)

---

## 📚 Guias por Tarefa

### Para Desenvolvedores

1. **[dev.md](dev.md)** - Setup completo, comandos, troubleshooting
2. **[architecture.md](architecture.md)** - Entender a estrutura do código
3. **[api.md](api.md)** - Como consumir a API

### Para Configuração

1. **[configuration.md](configuration.md)** - Todas as variáveis de ambiente
2. **[routes.md](routes.md)** - Ver todas as rotas disponíveis

### Para Entender o Projeto

1. **[architecture.md](architecture.md)** - Visão geral do sistema
2. **[phase1_1-quick-reference.md](phase1_1-quick-reference.md)** - O que foi implementado recentemente

---

## 🔍 Encontrar Informações

### "Onde está a rota X?"

→ Veja [routes.md](routes.md) (mapa completo de rotas)

### "Quais variáveis de ambiente existem?"

→ Veja [configuration.md](configuration.md)

### "Como rodar em desenvolvimento?"

→ Veja [dev.md](dev.md)

### "Como consumir a API?"

→ Veja [api.md](api.md)

### "Qual a arquitetura do sistema?"

→ Veja [architecture.md](architecture.md)

---

## 📊 Status do Projeto

- ✅ **Phase 0**: Completo (Telemetria e diagnósticos)
- ✅ **Phase 1**: Completo (Frontend v2 Setup)
- ✅ **Phase 1.1**: Completo (Auth Parity + Gradual Migration)
- ⏳ **Phase 2**: Em andamento (Backend "Descobrível")

---

## 🔗 Links Úteis

- **Swagger UI**: `http://localhost:5000/docs/swagger` (quando implementado)
- **Health Check**: `http://localhost:5000/api/health`
- **Repositório**: [GitHub](https://github.com/...) (se aplicável)

---

**Última atualização:** Dezembro 2024
