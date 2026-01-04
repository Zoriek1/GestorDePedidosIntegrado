# Troubleshooting

Este documento consolida problemas comuns e suas soluções.

## Problema: Output não aparece até Ctrl+C (Buffering)

### Sintoma

O servidor inicia, mas as mensagens só aparecem quando você pressiona Ctrl+C.

### Causa

O Python está usando **buffering** no output, então as mensagens ficam armazenadas em memória até o buffer ser esvaziado (flush).

### Solução 1: Usar script com -u (RECOMENDADO)

Use o script `iniciar_servidor.bat`:

```batch
cd backend
iniciar_servidor.bat
```

Ou execute diretamente com `-u`:

```batch
cd backend
python -u wsgi.py
```

O parâmetro `-u` desabilita o buffering.

### Solução 2: Variável de ambiente

Configure a variável de ambiente antes de executar:

```batch
set PYTHONUNBUFFERED=1
cd backend
python wsgi.py
```

Ou no PowerShell:

```powershell
$env:PYTHONUNBUFFERED=1
cd backend
python wsgi.py
```

### Solução 3: Usar o script automatizado

O script `iniciar_producao_completo.bat` já faz isso corretamente:

```batch
cd "c:\Gestor de Pedidos Plante uma flor"
iniciar_producao_completo.bat
```

### Mudanças feitas

1. **Adicionado `flush=True`** em todos os prints no `wsgi.py`
2. **Configurado `line_buffering=True`** no stdout/stderr para Windows
3. **Criado `iniciar_servidor.bat`** que usa `-u` automaticamente

### Verificação

Após iniciar, você deve ver imediatamente:

```
============================================================
PLANTE UMA FLOR - PWA v3.0 (PRODUÇÃO)
============================================================
...
[INFO] Iniciando Waitress...
[INFO] Escutando em 0.0.0.0:5000
```

### Nota

O servidor **está funcionando** mesmo quando o output não aparece. O problema é apenas visual - o Waitress está rodando normalmente, mas o output está buffered.

Para verificar se está funcionando (mesmo sem ver o output):
- Abra outro terminal
- Execute: `Invoke-RestMethod -Uri "http://localhost:5000/api/health"`
- Se retornar JSON, o servidor está funcionando!

## Problema: Servidor não responde após iniciar

### Sintoma

O servidor iniciou mas não está respondendo.

### Solução 1: Usar o script automatizado (RECOMENDADO)

```batch
cd "c:\Gestor de Pedidos Plante uma flor"
iniciar_producao_completo.bat
```

Este script:
- Faz o build do frontend automaticamente
- Inicia o Waitress corretamente
- Abre em uma janela separada

### Solução 2: Iniciar manualmente

#### Passo 1: Fazer build do frontend

```batch
cd frontend_v2
npm run build:fast
cd ..
```

#### Passo 2: Iniciar servidor

```batch
cd backend
python wsgi.py
```

**IMPORTANTE**: O servidor deve mostrar:

```
[OK] Servidor de produção iniciado!
[INFO] Iniciando Waitress...
[INFO] Escutando em 0.0.0.0:5000
```

Se você não ver essas mensagens, há um problema.

### Solução 3: Usar Waitress diretamente (alternativa)

Se `python wsgi.py` não funcionar, tente:

```batch
cd backend
python -m waitress --listen=0.0.0.0:5000 --threads=4 wsgi:app
```

### Verificação

Após iniciar, em OUTRO terminal, teste:

```powershell
# Teste 1: Health check
Invoke-RestMethod -Uri "http://localhost:5000/api/health"

# Teste 2: Frontend
Invoke-WebRequest -Uri "http://localhost:5000/" | Select-Object StatusCode

# Teste 3: Verificar porta
netstat -an | findstr ":5000" | findstr "LISTENING"
```

Se a porta 5000 não aparecer como LISTENING, o servidor não está escutando.

### Problemas Comuns

#### 1. Porta já em uso

```batch
# Verificar processos na porta 5000
netstat -ano | findstr ":5000"

# Matar processo (substitua PID pelo número)
taskkill /PID <PID> /F
```

#### 2. Waitress não instalado

```batch
pip install waitress
```

#### 3. Build do frontend não existe

```batch
cd frontend_v2
npm run build:fast
```

#### 4. Servidor trava durante inicialização

- Verifique se há erros no console
- Tente usar `python -m waitress` diretamente
- Verifique se o arquivo `frontend_v2/dist/index.html` existe

### Debug

Para ver mais informações, execute:

```batch
cd backend
python test_init.py
```

Isso verifica se a aplicação inicializa corretamente.

## Configuração de Foreign Keys

### Problema

Se o servidor não inicia e você suspeita que é por causa das foreign keys, você pode desabilitá-las temporariamente.

### Solução: Desabilitar Foreign Keys

Adicione esta linha no arquivo `.env`:

```env
SQLITE_FOREIGN_KEYS=OFF
```

### Valores aceitos:

- `ON`, `1`, `TRUE`, `YES` → Foreign keys habilitadas (padrão)
- `OFF`, `0`, `FALSE`, `NO` → Foreign keys desabilitadas

### Como usar

#### 1. Desabilitar Foreign Keys (para debug)

Edite `backend/.env` e adicione:

```env
# Desabilitar foreign keys (temporário, para debug)
SQLITE_FOREIGN_KEYS=OFF
```

#### 2. Reiniciar o servidor

```batch
cd backend
python wsgi.py
```

#### 3. Verificar

Ao iniciar, você verá:

```
[DB] PRAGMAs configurados via event hook: WAL, synchronous, foreign_keys=OFF, busy_timeout
```

### Aviso

⚠️ **Desabilitar foreign keys pode causar problemas de integridade de dados!**

Use apenas para:
- Debug de problemas de inicialização
- Migração de dados
- Testes temporários

**Sempre reabilite depois**:

```env
SQLITE_FOREIGN_KEYS=ON
```

### Outras configurações SQLite

Você também pode configurar:

```env
# Modo de sincronização (FULL, NORMAL, OFF)
SQLITE_SYNCHRONOUS=FULL
```

## Problema: Banco de dados não encontrado

### Sintoma

Erro ao iniciar: "Banco não encontrado" ou "database.db não existe"

### Solução

#### Desenvolvimento

O banco será criado automaticamente se não existir. Certifique-se de que:

1. O diretório `backend/instance/` existe
2. Permissões de escrita no diretório

#### Produção

Em produção, o banco deve existir antes de iniciar o servidor:

1. Execute migrations: `flask db upgrade`
2. Ou use `ALLOW_DB_BOOTSTRAP=true` no `.env` (apenas primeira vez)

### Localização do Banco

- **Desenvolvimento**: `backend/instance/database.db`
- **Produção**: `%USERPROFILE%/var/lib/database/database.db`

Configure via `DATABASE_PATH` no `.env`.

## Problema: Erro de importação de módulos

### Sintoma

`ModuleNotFoundError` ou `ImportError` ao iniciar o servidor

### Solução

1. Certifique-se de estar no diretório correto:
   ```batch
   cd backend
   ```

2. Verifique se as dependências estão instaladas:
   ```batch
   pip install -r requirements.txt
   ```

3. Verifique se está usando o ambiente virtual correto (se aplicável)

## Problema: CORS errors no frontend

### Sintoma

Erro de CORS ao fazer requisições do frontend para a API

### Solução

O CORS está configurado automaticamente em `app/cors.py`. Verifique:

1. Backend está rodando na porta 5000
2. Frontend está fazendo requisições para `/api` (proxy Vite) ou `http://localhost:5000/api`
3. Não há erros no console do backend sobre CORS

Se o problema persistir, verifique `app/cors.py` e adicione o domínio do frontend se necessário.

---

**Última atualização**: 2026-01-04
