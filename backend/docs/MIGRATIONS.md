# Migrações de Banco de Dados (Flask-Migrate/Alembic)

Este projeto usa **Flask-Migrate** (Alembic) para controlar alterações no schema do banco SQLite.

## Pré-requisitos

- Dependências instaladas (`pip install -r backend/requirements.txt`)
- Variável `FLASK_APP` apontando para a factory da aplicação

Exemplos (execute a partir da pasta `backend/`):

```bash
export FLASK_APP=app:create_app
```

No Windows (PowerShell):

```powershell
$env:FLASK_APP="app:create_app"
```

## Inicializar migrações (apenas 1ª vez)

```bash
flask db init
```

Isso cria a pasta `backend/migrations/`.

## Criar uma nova migração

Após alterar modelos em `backend/app/models/`, gere o arquivo:

```bash
flask db migrate -m "descricao_da_migracao"
```

Revise o arquivo gerado em `backend/migrations/versions/` antes de aplicar.

## Aplicar migrações no banco

```bash
flask db upgrade
```

Este comando é o caminho recomendado para atualizar o schema. Ele não altera dados já existentes.

## Verificar compatibilidade

- O app **não** cria tabelas automaticamente na inicialização.
- Para bancos existentes, basta executar `flask db upgrade` quando houver novas migrações.
- Para ambientes novos, rode `flask db init` (uma vez) e `flask db upgrade`.

Se o banco `backend/database.db` já existe, o app continua iniciando normalmente.
