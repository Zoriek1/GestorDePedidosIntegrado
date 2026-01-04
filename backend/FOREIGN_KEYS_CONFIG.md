# Configuração de Foreign Keys

## Problema

Se o servidor não inicia e você suspeita que é por causa das foreign keys, você pode desabilitá-las temporariamente.

## Solução: Desabilitar Foreign Keys

Adicione esta linha no arquivo `.env`:

```env
SQLITE_FOREIGN_KEYS=OFF
```

### Valores aceitos:
- `ON`, `1`, `TRUE`, `YES` → Foreign keys habilitadas (padrão)
- `OFF`, `0`, `FALSE`, `NO` → Foreign keys desabilitadas

## Como usar

### 1. Desabilitar Foreign Keys (para debug)

Edite `backend/.env` e adicione:

```env
# Desabilitar foreign keys (temporário, para debug)
SQLITE_FOREIGN_KEYS=OFF
```

### 2. Reiniciar o servidor

```batch
cd backend
python wsgi.py
```

### 3. Verificar

Ao iniciar, você verá:

```
[DB] PRAGMAs configurados via event hook: WAL, synchronous, foreign_keys=OFF, busy_timeout
```

## Aviso

⚠️ **Desabilitar foreign keys pode causar problemas de integridade de dados!**

Use apenas para:
- Debug de problemas de inicialização
- Migração de dados
- Testes temporários

**Sempre reabilite depois:**

```env
SQLITE_FOREIGN_KEYS=ON
```

## Outras configurações SQLite

Você também pode configurar:

```env
# Modo de sincronização (FULL, NORMAL, OFF)
SQLITE_SYNCHRONOUS=FULL
```

## Limpeza do .env

O arquivo `.env` foi limpo automaticamente, removendo duplicações de:
- `FLASK_ENV`
- `HOST`
- `PORT`

Agora essas configurações aparecem apenas uma vez no arquivo.
