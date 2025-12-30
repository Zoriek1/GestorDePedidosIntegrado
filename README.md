# Plante Uma Flor - Sistema de Gestão de Pedidos PWA

![Version](https://img.shields.io/badge/version-3.0.1-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Flask](https://img.shields.io/badge/flask-3.0+-red)
![PWA](https://img.shields.io/badge/PWA-enabled-purple)
![License](https://img.shields.io/badge/license-MIT-yellow)

Progressive Web App (PWA) moderno e completo para gerenciamento de pedidos de floricultura. Sistema multiplataforma com interface web responsiva que funciona em qualquer dispositivo (desktop, tablet, smartphone) com suporte offline completo.

---

## 🚀 Início Rápido

### Instalação

```bash
# 1. Instalar dependências
cd backend
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 3. Iniciar servidor
flask cli start
```

### Acessar

- **Local**: `http://localhost:5000`
- **HTTPS**: `flask cli start --https` → `https://localhost:5000`
- **Swagger UI**: `http://localhost:5000/docs/swagger` (se implementado)

---

## 📚 Documentação

A documentação completa está organizada em `docs/`:

- **[docs/README.md](docs/README.md)** - Porta de entrada da documentação
- **[docs/architecture.md](docs/architecture.md)** - Arquitetura do sistema
- **[docs/dev.md](docs/dev.md)** - Guia de desenvolvimento
- **[docs/api.md](docs/api.md)** - Documentação da API
- **[docs/configuration.md](docs/configuration.md)** - Variáveis de ambiente
- **[docs/routes.md](docs/routes.md)** - Mapa de rotas (auto-gerado)

---

## 🎯 Principais Endpoints

- `GET /api/health` - Health check
- `GET /api/pedidos` - Listar pedidos
- `GET /api/stats` - Estatísticas
- `GET /api/auth/check` - Verificar autenticação
- `GET /api/clientes/buscar` - Buscar clientes

Veja [docs/api.md](docs/api.md) para documentação completa da API.

---

## 🛠️ Tecnologias

- **Backend**: Flask 3.0+, SQLAlchemy, SQLite
- **Frontend**: HTML5, JavaScript ES6+, Service Worker, IndexedDB
- **APIs Externas**: GraphHopper, OpenRouteService, Nominatim

---

## 📄 Licença

MIT License

---

**Plante Uma Flor** © 2024 - Sistema de Gestão de Pedidos PWA 
