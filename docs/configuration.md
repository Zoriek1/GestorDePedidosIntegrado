# Configuração - Variáveis de Ambiente

Documentação completa de todas as variáveis de ambiente suportadas pelo sistema.

---

## Visão Geral

O sistema usa variáveis de ambiente para configuração. Crie um arquivo `.env` na pasta `backend/` baseado em `backend/.env.example`.

**Importante:**
- `.env` é local e **não deve ser versionado** (está no `.gitignore`)
- `.env.example` é versionado e serve como template
- Valores padrão são seguros e permitem o sistema funcionar sem configuração

---

## Tabela de Variáveis

### Segurança

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `SECRET_KEY` | `plante-uma-flor-pwa-secret-key-2024` | ✅ Produção | Chave secreta para sessões Flask | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | `plante1998` | ❌ | Senha do administrador (Basic Auth) | `minha_senha_segura` |
| `ENABLE_AUTH` | `true` | ❌ | Habilitar autenticação global | `true` / `false` |
| `ENABLE_RATE_LIMIT` | `true` | ❌ | Habilitar rate limiting | `true` / `false` |
| `ENABLE_DEBUG_ENDPOINTS` | `false` | ❌ | Habilitar endpoints de debug | `true` / `false` |

### Servidor

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `HOST` | `0.0.0.0` | ❌ | Host do servidor | `0.0.0.0` (qualquer IP) / `127.0.0.1` (apenas local) |
| `PORT` | `5000` | ❌ | Porta do servidor | `5000` / `8080` |
| `DEBUG` | `false` | ❌ | Modo debug (desabilitar em produção) | `true` / `false` |
| `FLASK_ENV` | `development` | ❌ | Ambiente Flask | `development` / `production` / `testing` |
| `APP_ENV` | `development` | ❌ | Ambiente da aplicação (alternativa) | `development` / `production` |
| `USE_HTTPS` | `false` | ❌ | Usar HTTPS | `true` / `false` |
| `NO_RELOAD` | `false` | ❌ | Desabilitar reloader automático | `true` / `false` |
| `FORCE_START` | `false` | ❌ | Forçar início mesmo se porta em uso | `true` / `false` |

### Banco de Dados

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `SQLALCHEMY_DATABASE_URI` | Auto (SQLite) | ❌ | URI do banco de dados | `sqlite:///C:/path/to/database.db` |
| `SQLITE_SYNCHRONOUS` | `FULL` | ❌ | Modo síncrono do SQLite | `FULL` / `NORMAL` / `OFF` |
| `ALLOW_DB_BOOTSTRAP` | `false` | ❌ | Permitir bootstrap automático | `true` / `false` |

**Nota:** Por padrão, o banco SQLite é criado em `%USERPROFILE%/var/lib/database/database.db` (Windows).

### APIs Externas

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `GRAPHHOPPER_API_KEY` | (vazio) | ⚠️ Recomendado | Chave da API GraphHopper | `abc123...` |
| `OPENROUTE_API_KEY` | (vazio) | ⚠️ Recomendado | Chave da API OpenRouteService | `abc123...` |
| `ENDERECO_FLORICULTURA` | (vazio) | ⚠️ Para distâncias | Endereço completo da floricultura | `Rua Exemplo, 123, Bairro Centro, Goiânia, GO, 74000-000` |

**Onde obter API Keys:**
- **GraphHopper**: https://www.graphhopper.com/api/ (500 req/dia grátis)
- **OpenRouteService**: https://openrouteservice.org/dev/#/signup (2.000 req/dia grátis)

**Nota:** O sistema funciona sem API keys usando serviços gratuitos (Nominatim), mas com limitações de taxa.

### Backup

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `GDRIVE_BACKUP_DIR` | Auto (Google Drive) | ❌ | Diretório do Google Drive para backups | `C:\Users\Usuario\Meu Drive\...` |
| `GDRIVE_BACKUP_FOLDER_ID` | (vazio) | ❌ | ID da pasta do Google Drive | `1a2b3c4d5e6f7g8h` |

**Nota:** Por padrão, usa `%USERPROFILE%/Meu Drive/Plante Uma Flor Confidential/Database - Pedidos Gestor`.

### Google Services

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | (vazio) | ⚠️ Para Sheets | Caminho para credenciais do Google | `C:\path\to\credentials.json` |
| `GOOGLE_CREDENTIALS_PATH` | (vazio) | ⚠️ Para Sheets | Caminho alternativo para credenciais | `C:\path\to\credentials.json` |

**Nota:** Necessário apenas para exportação de planilhas para Google Sheets.

---

## Configuração por Ambiente

### Desenvolvimento

```env
FLASK_ENV=development
DEBUG=false
ENABLE_DEBUG_ENDPOINTS=true
NO_RELOAD=false
```

### Produção

```env
FLASK_ENV=production
DEBUG=false
SECRET_KEY=<gerar-chave-segura>
ENABLE_DEBUG_ENDPOINTS=false
USE_HTTPS=true
```

### Testes

```env
FLASK_ENV=testing
DEBUG=true
TESTING=true
```

---

## Valores Padrão Seguros

O sistema funciona com valores padrão seguros mesmo sem `.env`:

- ✅ Banco de dados criado automaticamente
- ✅ Autenticação habilitada (senha padrão: `plante1998`)
- ✅ Rate limiting habilitado
- ✅ Debug desabilitado
- ✅ Endpoints de debug desabilitados

**Atenção:** Em produção, sempre configure:
- `SECRET_KEY` (gerar chave segura)
- `ADMIN_PASSWORD` (senha forte)
- `DEBUG=false`
- `ENABLE_DEBUG_ENDPOINTS=false`

---

## Exemplo de `.env` Mínimo

```env
# Mínimo necessário para funcionar
SECRET_KEY=minha-chave-secreta-gerada
ADMIN_PASSWORD=minha_senha_segura
ENDERECO_FLORICULTURA=Rua Exemplo, 123, Bairro Centro, Goiânia, GO, 74000-000
```

---

## Exemplo de `.env` Completo

Veja `backend/.env.example` para exemplo completo com todas as variáveis documentadas.

---

## Validação

O sistema valida automaticamente:

- ✅ `SECRET_KEY` em produção (aviso se usar default)
- ✅ Banco de dados acessível
- ✅ Diretórios de backup criados automaticamente

---

## Troubleshooting

### "SECRET_KEY não definida!"

**Solução:** Configure `SECRET_KEY` no `.env`:
```env
SECRET_KEY=python -c "import secrets; print(secrets.token_hex(32))"
```

### "Distâncias não calculam"

**Solução:** Configure `ENDERECO_FLORICULTURA`:
```env
ENDERECO_FLORICULTURA=Rua, Número, Bairro, Cidade, Estado, CEP
```

### "APIs externas falhando"

**Solução:** Configure pelo menos uma API key:
```env
GRAPHHOPPER_API_KEY=sua_chave_aqui
# OU
OPENROUTE_API_KEY=sua_chave_aqui
```

---

## Recursos Adicionais

- [Dev Guide](dev.md) - Guia de desenvolvimento
- [Architecture](architecture.md) - Arquitetura do sistema
- [API Documentation](api.md) - Documentação da API

---

**Última atualização:** Dezembro 2024


Documentação completa de todas as variáveis de ambiente suportadas pelo sistema.

---

## Visão Geral

O sistema usa variáveis de ambiente para configuração. Crie um arquivo `.env` na pasta `backend/` baseado em `backend/.env.example`.

**Importante:**
- `.env` é local e **não deve ser versionado** (está no `.gitignore`)
- `.env.example` é versionado e serve como template
- Valores padrão são seguros e permitem o sistema funcionar sem configuração

---

## Tabela de Variáveis

### Segurança

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `SECRET_KEY` | `plante-uma-flor-pwa-secret-key-2024` | ✅ Produção | Chave secreta para sessões Flask | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | `plante1998` | ❌ | Senha do administrador (Basic Auth) | `minha_senha_segura` |
| `ENABLE_AUTH` | `true` | ❌ | Habilitar autenticação global | `true` / `false` |
| `ENABLE_RATE_LIMIT` | `true` | ❌ | Habilitar rate limiting | `true` / `false` |
| `ENABLE_DEBUG_ENDPOINTS` | `false` | ❌ | Habilitar endpoints de debug | `true` / `false` |

### Servidor

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `HOST` | `0.0.0.0` | ❌ | Host do servidor | `0.0.0.0` (qualquer IP) / `127.0.0.1` (apenas local) |
| `PORT` | `5000` | ❌ | Porta do servidor | `5000` / `8080` |
| `DEBUG` | `false` | ❌ | Modo debug (desabilitar em produção) | `true` / `false` |
| `FLASK_ENV` | `development` | ❌ | Ambiente Flask | `development` / `production` / `testing` |
| `APP_ENV` | `development` | ❌ | Ambiente da aplicação (alternativa) | `development` / `production` |
| `USE_HTTPS` | `false` | ❌ | Usar HTTPS | `true` / `false` |
| `NO_RELOAD` | `false` | ❌ | Desabilitar reloader automático | `true` / `false` |
| `FORCE_START` | `false` | ❌ | Forçar início mesmo se porta em uso | `true` / `false` |

### Banco de Dados

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `SQLALCHEMY_DATABASE_URI` | Auto (SQLite) | ❌ | URI do banco de dados | `sqlite:///C:/path/to/database.db` |
| `SQLITE_SYNCHRONOUS` | `FULL` | ❌ | Modo síncrono do SQLite | `FULL` / `NORMAL` / `OFF` |
| `ALLOW_DB_BOOTSTRAP` | `false` | ❌ | Permitir bootstrap automático | `true` / `false` |

**Nota:** Por padrão, o banco SQLite é criado em `%USERPROFILE%/var/lib/database/database.db` (Windows).

### APIs Externas

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `GRAPHHOPPER_API_KEY` | (vazio) | ⚠️ Recomendado | Chave da API GraphHopper | `abc123...` |
| `OPENROUTE_API_KEY` | (vazio) | ⚠️ Recomendado | Chave da API OpenRouteService | `abc123...` |
| `ENDERECO_FLORICULTURA` | (vazio) | ⚠️ Para distâncias | Endereço completo da floricultura | `Rua Exemplo, 123, Bairro Centro, Goiânia, GO, 74000-000` |

**Onde obter API Keys:**
- **GraphHopper**: https://www.graphhopper.com/api/ (500 req/dia grátis)
- **OpenRouteService**: https://openrouteservice.org/dev/#/signup (2.000 req/dia grátis)

**Nota:** O sistema funciona sem API keys usando serviços gratuitos (Nominatim), mas com limitações de taxa.

### Backup

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `GDRIVE_BACKUP_DIR` | Auto (Google Drive) | ❌ | Diretório do Google Drive para backups | `C:\Users\Usuario\Meu Drive\...` |
| `GDRIVE_BACKUP_FOLDER_ID` | (vazio) | ❌ | ID da pasta do Google Drive | `1a2b3c4d5e6f7g8h` |

**Nota:** Por padrão, usa `%USERPROFILE%/Meu Drive/Plante Uma Flor Confidential/Database - Pedidos Gestor`.

### Google Services

| Variável | Default | Obrigatório? | Descrição | Exemplo |
|----------|---------|--------------|-----------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | (vazio) | ⚠️ Para Sheets | Caminho para credenciais do Google | `C:\path\to\credentials.json` |
| `GOOGLE_CREDENTIALS_PATH` | (vazio) | ⚠️ Para Sheets | Caminho alternativo para credenciais | `C:\path\to\credentials.json` |

**Nota:** Necessário apenas para exportação de planilhas para Google Sheets.

---

## Configuração por Ambiente

### Desenvolvimento

```env
FLASK_ENV=development
DEBUG=false
ENABLE_DEBUG_ENDPOINTS=true
NO_RELOAD=false
```

### Produção

```env
FLASK_ENV=production
DEBUG=false
SECRET_KEY=<gerar-chave-segura>
ENABLE_DEBUG_ENDPOINTS=false
USE_HTTPS=true
```

### Testes

```env
FLASK_ENV=testing
DEBUG=true
TESTING=true
```

---

## Valores Padrão Seguros

O sistema funciona com valores padrão seguros mesmo sem `.env`:

- ✅ Banco de dados criado automaticamente
- ✅ Autenticação habilitada (senha padrão: `plante1998`)
- ✅ Rate limiting habilitado
- ✅ Debug desabilitado
- ✅ Endpoints de debug desabilitados

**Atenção:** Em produção, sempre configure:
- `SECRET_KEY` (gerar chave segura)
- `ADMIN_PASSWORD` (senha forte)
- `DEBUG=false`
- `ENABLE_DEBUG_ENDPOINTS=false`

---

## Exemplo de `.env` Mínimo

```env
# Mínimo necessário para funcionar
SECRET_KEY=minha-chave-secreta-gerada
ADMIN_PASSWORD=minha_senha_segura
ENDERECO_FLORICULTURA=Rua Exemplo, 123, Bairro Centro, Goiânia, GO, 74000-000
```

---

## Exemplo de `.env` Completo

Veja `backend/.env.example` para exemplo completo com todas as variáveis documentadas.

---

## Validação

O sistema valida automaticamente:

- ✅ `SECRET_KEY` em produção (aviso se usar default)
- ✅ Banco de dados acessível
- ✅ Diretórios de backup criados automaticamente

---

## Troubleshooting

### "SECRET_KEY não definida!"

**Solução:** Configure `SECRET_KEY` no `.env`:
```env
SECRET_KEY=python -c "import secrets; print(secrets.token_hex(32))"
```

### "Distâncias não calculam"

**Solução:** Configure `ENDERECO_FLORICULTURA`:
```env
ENDERECO_FLORICULTURA=Rua, Número, Bairro, Cidade, Estado, CEP
```

### "APIs externas falhando"

**Solução:** Configure pelo menos uma API key:
```env
GRAPHHOPPER_API_KEY=sua_chave_aqui
# OU
OPENROUTE_API_KEY=sua_chave_aqui
```

---

## Recursos Adicionais

- [Dev Guide](dev.md) - Guia de desenvolvimento
- [Architecture](architecture.md) - Arquitetura do sistema
- [API Documentation](api.md) - Documentação da API

---

**Última atualização:** Dezembro 2024

