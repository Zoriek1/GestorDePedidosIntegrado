# Documentação do Frontend

Bem-vindo à documentação técnica do frontend do sistema Plante Uma Flor (React + TypeScript).

## Índice

### Stack e Tecnologias

- **[TECHNOLOGY.md](TECHNOLOGY.md)** - Stack tecnológico, dependências principais, versões e path aliases

### Arquitetura e Estrutura

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitetura do projeto, estrutura de pastas, padrão Feature-Based e convenções
- **[DATA_PATTERNS.md](DATA_PATTERNS.md)** - Padrões de dados, state management (React Query), formulários, offline e cache

### Funcionalidades

- **[FEATURES.md](FEATURES.md)** - Funcionalidades atuais por módulo e roadmap de funcionalidades futuras

### Produção e Deploy

- **[PRODUCTION.md](PRODUCTION.md)** - Build, deploy, configuração, performance e troubleshooting
- **[PWA.md](PWA.md)** - Progressive Web App, Service Worker, offline support e instalação

---

## Início Rápido

Para começar a desenvolver:

1. **Instalar dependências**: `npm install`
2. **Entender a stack**: Comece por [TECHNOLOGY.md](TECHNOLOGY.md)
3. **Explorar a arquitetura**: Veja [ARCHITECTURE.md](ARCHITECTURE.md) para entender a estrutura
4. **Desenvolvimento**: `npm run dev` (porta 5173)

## Estrutura do Frontend

```
frontend_v2/src/
├── features/        # Módulos organizados por feature (pedidos, clientes, etc)
├── components/      # Componentes reutilizáveis (common, form, system)
├── api/            # Cliente HTTP e endpoints da API
├── lib/            # Bibliotecas e utilitários (offline, format, http)
├── hooks/          # React hooks customizados
├── layout/         # Componentes de layout
└── app/            # Configuração do app (router, providers)
```

## Stack Principal

- **React 19** - Biblioteca UI
- **TypeScript** - Tipagem estática
- **Vite** - Build tool e dev server
- **Material-UI (MUI)** - Componentes de UI
- **React Query** - Gerenciamento de estado e cache
- **React Hook Form + Zod** - Formulários e validação
- **Dexie** - IndexedDB para funcionalidade offline
- **PWA** - Progressive Web App com Service Worker

---

**Última atualização**: 2026-01-04
