# Documentação do Backend

Bem-vindo à documentação técnica do backend do sistema Plante Uma Flor.

## Índice

### Arquitetura e Padrões

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitetura do sistema, padrões de design (Repository, Command, Service), estrutura de pastas e fluxo de dependências
- **[BLUEPRINTS.md](BLUEPRINTS.md)** - Organização de Blueprints Flask, lista de blueprints registrados e como adicionar novos
- **[ROUTES.md](ROUTES.md)** - Documentação completa de todos os endpoints da API REST

### Integração e Configuração

- **[DATABASE.md](DATABASE.md)** - Integração com SQLite, models, Repository Pattern, migrations e configurações do banco
- **[OPENAPI.md](OPENAPI.md)** - Documentação OpenAPI/Swagger, estado atual e roadmap

### Operação e Manutenção

- **[BACKUP.md](BACKUP.md)** - Sistema de backup completo (P0 + P1), encriptação, integração e comandos
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Problemas comuns e soluções

### Documentação de Referência

- **[ESTUDO_BACKUP_COMPLETO.md](ESTUDO_BACKUP_COMPLETO.md)** - Estudo completo e detalhado do sistema de backup
- **[BACKUP_P1_GUIA.md](BACKUP_P1_GUIA.md)** - Guia de configuração do pacote P1 (Robustez Operacional)
- **[CONFIGURAR_GOOGLE_SHEETS.md](CONFIGURAR_GOOGLE_SHEETS.md)** - Configuração de integração com Google Sheets

---

## Início Rápido

Para começar a desenvolver:

1. **Entender a arquitetura**: Comece por [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Explorar as rotas**: Veja [ROUTES.md](ROUTES.md) para entender os endpoints disponíveis
3. **Configurar o banco**: Consulte [DATABASE.md](DATABASE.md) para setup e migrations

## Estrutura do Backend

```
backend/
├── app/
│   ├── models/          # Entidades do domínio (SQLAlchemy)
│   ├── repositories/    # Camada de acesso a dados (Repository Pattern)
│   ├── services/        # Lógica de negócio e integrações
│   ├── routes/          # Controllers HTTP (Blueprints)
│   ├── commands/        # Command Pattern (ações encapsuladas)
│   ├── schemas/         # DTOs e serialização
│   ├── utils/           # Helpers (backup, encryption, audit)
│   └── openapi/         # Documentação OpenAPI/Swagger
├── scripts/             # Scripts de automação (backup, migrations)
└── instance/            # Dados da instância (database.db, backups, logs)
```

## Padrões Principais

- **Repository Pattern**: Abstração completa do acesso a dados
- **Command Pattern**: Encapsulamento de ações complexas
- **Service-Oriented Architecture**: Separação clara de responsabilidades
- **Blueprints Flask**: Organização modular das rotas

---

**Última atualização**: 2026-01-04
