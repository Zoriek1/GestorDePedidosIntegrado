# Diagnóstico de Confiabilidade de Dados - Plante Uma Flor

**Data**: 2025-01-28  
**Versão do Sistema**: 3.0.1  
**Analista**: Engenheiro de Software Sênior (Backend + SRE)

---

## A) RESUMO EXECUTIVO

O sistema apresenta **riscos críticos de perda de dados** decorrentes de três problemas principais: (1) posicionamento do SQLite dentro da árvore do repositório (`backend/instance/database.db`), tornando-o vulnerável a operações de deploy que recriam diretórios; (2) uso de `db.create_all()` em produção, que pode causar schema drift e silenciosamente criar um novo banco vazio se o arquivo não existir; (3) ausência de configurações de robustez do SQLite (WAL, synchronous, foreign_keys, busy_timeout) e de logs de diagnóstico no startup. O incidente dos "5 pedidos sumidos" após rebase/deploy é consistente com a hipótese de troca silenciosa do banco de dados, possivelmente agravada por múltiplos arquivos `database.db` no servidor (`backend/database.db` e `backend/instance/database.db`). As correções propostas priorizam mover o banco para fora do repositório com caminho absoluto via variável de ambiente, adicionar logs de diagnóstico no startup, implementar backups consistentes fora do repo, eliminar `create_all()` em produção e endurecer o SQLite com PRAGMAs apropriados.

---

## B) PRINCIPAIS RISCOS OPERACIONAIS

### P0 - CRÍTICO (Correção Imediata)

#### P0.1: Banco de Dados Dentro da Árvore do Repositório
**Localização**: `backend/instance/database.db` (relativo ao `BASE_DIR`)  
**Risco**: Operações de deploy (clone, `git clean -fdx`, scripts que recriam diretórios) podem apagar ou substituir o arquivo, mesmo com `.gitignore`.  
**Evidência**: 
- Config usa caminho relativo: `INSTANCE_DIR = BASE_DIR / 'instance'` → `DATABASE_PATH = INSTANCE_DIR / 'database.db'`
- `.gitignore` ignora `instance/` mas não protege em deploy
- Existe `backend/database.db` (fora de `instance/`), indicando possível confusão de caminhos

**Impacto**: Perda total de dados em deploy, sem aviso prévio.

---

#### P0.2: `db.create_all()` Executado Sempre em Produção
**Localização**: `backend/app/extensions.py:45` → `backend/app/factory.py:67`  
**Risco**: Se o arquivo `database.db` não existir ou for removido, `create_all()` cria um banco vazio silenciosamente, sem erro.  
**Evidência**:
```python
# backend/app/extensions.py:28-48
def init_database(app):
    with app.app_context():
        from app.models import Pedido, RotaOtimizada, Cliente, EnderecoCliente, FontePedido
        db.create_all()  # ← SEMPRE executa, mesmo se DB não existir
        print("[OK] Banco de dados inicializado")
```

**Impacto**: Troca silenciosa de banco (novo vazio substitui o antigo com dados), causando "sumiço" de registros.

---

#### P0.3: Ausência de Logs de Diagnóstico no Startup
**Localização**: `backend/app/extensions.py`, `backend/main.py`  
**Risco**: Impossível verificar qual arquivo está sendo usado, seu tamanho, data de modificação e PRAGMAs ativos.  
**Evidência**: Apenas `print("[OK] Banco de dados inicializado")` sem detalhes do arquivo.

**Impacto**: Dificulta diagnóstico de incidentes e não detecta troca de banco.

---

#### P0.4: Backups Armazenados Dentro do Repositório
**Localização**: `backend/instance/backups/`  
**Risco**: Mesmo risco de P0.1 - backups podem ser apagados em deploy.  
**Evidência**: `backup_dir = instance_dir / 'backups'` (dentro de `instance/`)

**Impacto**: Perda de backups junto com o banco em operações de deploy.

---

### P1 - ALTO (Correção Urgente)

#### P1.1: Ausência de Configurações de Robustez do SQLite
**Localização**: Nenhuma configuração de PRAGMA encontrada  
**Risco**: 
- Sem WAL: menor concorrência e risco de corrupção em falhas
- Sem `synchronous=FULL`: risco de dados não persistidos em crash
- Sem `foreign_keys=ON`: integridade referencial não garantida
- Sem `busy_timeout`: deadlocks em operações concorrentes

**Impacto**: Corrupção de dados, perda de integridade referencial, deadlocks.

---

#### P1.2: Uso de `create_all()` em Produção vs Migrations
**Localização**: `backend/app/extensions.py:45`  
**Risco**: Schema drift - `create_all()` não aplica migrations, pode criar tabelas desatualizadas ou faltantes.  
**Evidência**: Flask-Migrate configurado (`migrate = Migrate()`) mas não usado no startup.

**Impacto**: Inconsistências de schema, colunas faltantes, dados não migrados.

---

#### P1.3: Múltiplos Arquivos `database.db` no Servidor
**Localização**: `backend/database.db` e `backend/instance/database.db`  
**Risco**: Confusão sobre qual arquivo está sendo usado, possibilidade de aplicação usar o errado.  
**Evidência**: Listagem de diretórios mostra ambos os arquivos existentes.

**Impacto**: Dados podem estar sendo escritos em arquivo diferente do esperado.

---

### P2 - MÉDIO (Correção Planejada)

#### P2.1: Backup Não Usa `.backup` ou `VACUUM INTO`
**Localização**: `backend/scripts/backup/backup.py:107` usa `shutil.copy2()`  
**Risco**: Backup pode capturar estado inconsistente se houver transações em andamento.  
**Evidência**: `shutil.copy2(self.db_path, backup_path)` - cópia direta de arquivo.

**Impacto**: Backups podem estar inconsistentes, especialmente em operações concorrentes.

---

#### P2.2: Filtro `oculto=False` Pode Ocultar Pedidos Legítimos
**Localização**: `backend/app/repositories/pedido_repository.py:64`  
**Risco**: Se campo `oculto` for marcado incorretamente, pedidos desaparecem da UI.  
**Evidência**: `query = query.filter_by(oculto=False)` aplicado por padrão em todas as buscas.

**Impacto**: Pedidos podem "sumir" da interface mesmo existindo no banco.

---

## C) HIPÓTESES PARA O INCIDENTE "5 PEDIDOS SUMIRAM"

### Hipótese 1: Troca Silenciosa de Banco (MAIS PROVÁVEL) ⭐⭐⭐⭐⭐

**Cenário**:
1. Deploy executa `git clean -fdx` ou recria diretório `backend/instance/`
2. `database.db` é apagado ou movido
3. Aplicação inicia e `db.create_all()` cria novo banco vazio
4. Sistema funciona normalmente, mas sem os 5 pedidos anteriores

**Sinais para Confirmar**:
- ✅ Verificar data de criação de `backend/instance/database.db` (deve ser próxima ao deploy)
- ✅ Comparar tamanho do arquivo antes/depois do incidente
- ✅ Verificar logs de backup - último backup antes do incidente deve ter os 5 pedidos
- ✅ Executar `PRAGMA database_list` no SQLite para confirmar arquivo aberto

**Sinais para Refutar**:
- ❌ Arquivo `database.db` tem data de modificação anterior ao deploy
- ❌ Backups anteriores não contêm os 5 pedidos
- ❌ Logs mostram erro ao criar banco (indicaria problema diferente)

**Probabilidade**: 85%

---

### Hipótese 2: Uso de Arquivo `database.db` Errado ⭐⭐⭐

**Cenário**:
1. Existem dois arquivos: `backend/database.db` (antigo) e `backend/instance/database.db` (novo)
2. Após deploy, aplicação passa a usar `backend/instance/database.db` (vazio)
3. Dados antigos estão em `backend/database.db` (não usado)

**Sinais para Confirmar**:
- ✅ `backend/database.db` existe e tem tamanho maior que `backend/instance/database.db`
- ✅ `backend/database.db` contém os 5 pedidos (verificar via SQLite)
- ✅ Data de modificação de `backend/database.db` é anterior ao incidente

**Sinais para Refutar**:
- ❌ Apenas um arquivo `database.db` existe no servidor
- ❌ Ambos os arquivos têm mesma data de modificação

**Probabilidade**: 10%

---

### Hipótese 3: Pedidos Marcados como `oculto=True` ⭐⭐

**Cenário**:
1. Operação de limpeza ou migração marca pedidos como `oculto=True`
2. UI filtra `oculto=False` por padrão
3. Pedidos existem no banco mas não aparecem na interface

**Sinais para Confirmar**:
- ✅ Query `SELECT * FROM pedidos WHERE oculto = 1` retorna os 5 pedidos
- ✅ Campo `oculto` dos pedidos foi alterado próximo ao incidente
- ✅ Logs mostram operação de `cleanup_old_pedidos()` ou similar

**Sinais para Refutar**:
- ❌ Query retorna 0 pedidos com `oculto=1` na data do incidente
- ❌ Campo `oculto` não foi modificado

**Probabilidade**: 5%

---

## D) PLANO DE CORREÇÃO

### Fase 1: Correções P0 (Imediatas)

#### D1.1: Mover Database para Fora do Repositório

**Objetivo**: Eliminar risco de apagamento em deploy.

**Passos**:
1. Criar diretório de dados fora do repo (ex: `C:\Dados\PlanteUmaFlor\` no Windows, `/var/lib/plante-uma-flor/` no Linux)
2. Mover `backend/instance/database.db` para novo local
3. Configurar variável de ambiente `DATABASE_PATH` com caminho absoluto
4. Atualizar `backend/app/config.py` para usar variável de ambiente:

```python
# backend/app/config.py
DATABASE_PATH = Path(os.environ.get('DATABASE_PATH') or (INSTANCE_DIR / 'database.db'))
DATABASE_PATH = DATABASE_PATH if DATABASE_PATH.is_absolute() else INSTANCE_DIR / DATABASE_PATH
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH.as_posix()}'
```

5. Criar `.env.example` documentando `DATABASE_PATH`
6. Atualizar scripts de deploy para não tocar no diretório de dados

**Critérios de Aceite**:
- ✅ `DATABASE_PATH` é caminho absoluto configurado via env var
- ✅ Banco está fora da árvore do repositório
- ✅ Deploy não afeta o arquivo de banco
- ✅ Documentação atualizada

**Tempo Estimado**: 2 horas

---

#### D1.2: Adicionar Logs de Diagnóstico no Startup

**Objetivo**: Permitir verificação imediata de qual banco está sendo usado.

**Passos**:
1. Modificar `backend/app/extensions.py:init_database()`:

```python
def init_database(app):
    with app.app_context():
        db_path = Path(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
        
        # Logs de diagnóstico
        print(f"[DB] Caminho absoluto: {db_path.resolve()}")
        print(f"[DB] Arquivo existe: {db_path.exists()}")
        if db_path.exists():
            stat = db_path.stat()
            print(f"[DB] Tamanho: {stat.st_size / 1024:.2f} KB")
            print(f"[DB] Modificado: {datetime.fromtimestamp(stat.st_mtime)}")
        else:
            print("[DB] ⚠️ AVISO: Arquivo não existe! Criando novo banco...")
        
        # Verificar PRAGMAs
        if db_path.exists():
            conn = db.engine.connect()
            pragmas = {
                'journal_mode': conn.execute(text("PRAGMA journal_mode")).scalar(),
                'synchronous': conn.execute(text("PRAGMA synchronous")).scalar(),
                'foreign_keys': conn.execute(text("PRAGMA foreign_keys")).scalar(),
                'busy_timeout': conn.execute(text("PRAGMA busy_timeout")).scalar(),
            }
            conn.close()
            print(f"[DB] PRAGMAs: {pragmas}")
        
        # Importar models e criar tabelas (ou aplicar migrations)
        from app.models import Pedido, RotaOtimizada, Cliente, EnderecoCliente, FontePedido
        db.create_all()  # Temporário - será substituído por migrations
```

2. Adicionar import: `from datetime import datetime` e `from sqlalchemy import text`

**Critérios de Aceite**:
- ✅ Logs mostram caminho absoluto, tamanho, data de modificação
- ✅ Logs mostram PRAGMAs ativos
- ✅ Aviso claro se arquivo não existir

**Tempo Estimado**: 1 hora

---

#### D1.3: Backup Consistente e Armazenamento Fora do Repo

**Objetivo**: Garantir backups seguros e restaurables.

**Passos**:
1. Criar diretório de backups fora do repo (ex: `C:\Backups\PlanteUmaFlor\` ou `/var/backups/plante-uma-flor/`)
2. Modificar `backend/scripts/backup/backup.py` para usar `.backup` do SQLite:

```python
def create_backup(self, compress=True):
    if not self.db_path.exists():
        print(f"[ERRO] Banco de dados não encontrado: {self.db_path}")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"database_{timestamp}.db"
    backup_path = self.backup_dir / backup_name
    
    # Usar .backup do SQLite para backup consistente
    import sqlite3
    source_conn = sqlite3.connect(str(self.db_path))
    backup_conn = sqlite3.connect(str(backup_path))
    source_conn.backup(backup_conn)
    backup_conn.close()
    source_conn.close()
    
    # Verificar integridade
    # ... resto do código de compressão
```

3. Configurar variável de ambiente `BACKUP_DIR` para caminho absoluto
4. Implementar cópia externa (ex: para outro servidor/NAS) via script separado
5. Atualizar retenção para manter últimos 30 dias + 1 backup mensal

**Critérios de Aceite**:
- ✅ Backups usam `.backup()` do SQLite
- ✅ Backups armazenados fora do repo
- ✅ Cópia externa configurada (manual ou automática)
- ✅ Teste de restauração bem-sucedido

**Tempo Estimado**: 3 horas

---

### Fase 2: Correções P1 (Urgentes)

#### D2.1: Endurecer SQLite com PRAGMAs

**Objetivo**: Aumentar robustez e prevenir corrupção.

**Passos**:
1. Criar função de configuração de PRAGMAs em `backend/app/extensions.py`:

```python
def configure_sqlite_pragmas(db):
    """Configura PRAGMAs críticos do SQLite"""
    with db.engine.connect() as conn:
        # WAL mode: melhor concorrência e recuperação
        conn.execute(text("PRAGMA journal_mode = WAL"))
        
        # Synchronous FULL: garante persistência (trade-off: mais lento, mas seguro)
        conn.execute(text("PRAGMA synchronous = FULL"))
        
        # Foreign keys: integridade referencial
        conn.execute(text("PRAGMA foreign_keys = ON"))
        
        # Busy timeout: evitar deadlocks (30 segundos)
        conn.execute(text("PRAGMA busy_timeout = 30000"))
        
        conn.commit()
```

2. Chamar após `db.init_app(app)` em `init_extensions()`
3. Documentar trade-offs:
   - **WAL**: Melhor concorrência, mas requer `-wal` e `-shm` files
   - **synchronous=FULL**: Mais seguro, mas ~10x mais lento que NORMAL (aceitável para este caso)
   - **foreign_keys**: Validação adicional, pequeno overhead

**Critérios de Aceite**:
- ✅ PRAGMAs aplicados no startup
- ✅ Logs confirmam valores ativos
- ✅ Testes de concorrência passam
- ✅ Documentação de trade-offs atualizada

**Tempo Estimado**: 2 horas

---

#### D2.2: Substituir `create_all()` por Migrations em Produção

**Objetivo**: Eliminar schema drift e garantir consistência.

**Passos**:
1. Modificar `backend/app/extensions.py:init_database()`:

```python
def init_database(app):
    """Inicializa banco de dados usando migrations"""
    with app.app_context():
        db_path = Path(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
        
        # Logs de diagnóstico (já implementado em D1.2)
        # ...
        
        # Verificar se é primeira inicialização
        is_new_db = not db_path.exists()
        
        if is_new_db:
            # Primeira vez: criar todas as tabelas
            from app.models import Pedido, RotaOtimizada, Cliente, EnderecoCliente, FontePedido
            db.create_all()
            print("[DB] Banco criado com create_all() (primeira inicialização)")
        else:
            # Banco existente: aplicar migrations
            from flask_migrate import upgrade
            try:
                upgrade()
                print("[DB] Migrations aplicadas com sucesso")
            except Exception as e:
                print(f"[DB] ⚠️ ERRO ao aplicar migrations: {e}")
                print("[DB] Continuando com schema atual (pode haver inconsistências)")
```

2. Garantir que todas as migrations estejam criadas: `flask db migrate -m "Initial migration"`
3. Documentar processo: migrations obrigatórias em produção, `create_all()` apenas em primeira inicialização

**Critérios de Aceite**:
- ✅ `create_all()` apenas em primeira inicialização
- ✅ Migrations aplicadas automaticamente em produção
- ✅ Erro de migration não quebra startup (com aviso)
- ✅ Testes confirmam migrations funcionando

**Tempo Estimado**: 3 horas

---

#### D2.3: Consolidar Arquivos `database.db` Duplicados

**Objetivo**: Eliminar confusão sobre qual arquivo está em uso.

**Passos**:
1. Identificar qual arquivo está sendo usado (via logs de D1.2)
2. Se `backend/database.db` contém dados importantes:
   - Fazer backup de ambos
   - Migrar dados de `backend/database.db` para `backend/instance/database.db` (ou novo local de D1.1)
   - Verificar integridade após migração
3. Remover `backend/database.db` após confirmação
4. Adicionar validação no startup para alertar se múltiplos arquivos existem

**Critérios de Aceite**:
- ✅ Apenas um arquivo `database.db` em uso
- ✅ Dados migrados sem perda
- ✅ Arquivo duplicado removido
- ✅ Validação previne uso de arquivo errado

**Tempo Estimado**: 2 horas

---

### Fase 3: Melhorias P2 (Planejadas)

#### D3.1: Endpoint de Diagnóstico de Banco

**Objetivo**: Facilitar troubleshooting sem acesso ao servidor.

**Passos**:
1. Criar endpoint `GET /api/debug/database-info` (requer `ENABLE_DEBUG_ENDPOINTS=true`)
2. Retornar: caminho absoluto, tamanho, data modificação, PRAGMAs, contagem de registros por tabela
3. Adicionar validação de integridade básica

**Tempo Estimado**: 1 hora

---

#### D3.2: Monitoramento de Tamanho de Banco

**Objetivo**: Alertar sobre crescimento anormal ou redução súbita.

**Passos**:
1. Adicionar métrica de tamanho no startup
2. Comparar com último valor conhecido
3. Alertar se redução > 10% sem backup recente

**Tempo Estimado**: 1 hora

---

## E) CHECKLIST DE DEPLOY SEGURO

### Pré-Deploy

- [ ] **Backup obrigatório**: `flask cli backup` ou `python scripts/backup/backup.py`
- [ ] **Verificar caminho do banco**: Confirmar `DATABASE_PATH` aponta para arquivo correto
- [ ] **Verificar tamanho do banco**: Anotar tamanho atual para comparação pós-deploy
- [ ] **Verificar múltiplos arquivos**: `find . -name "database.db"` (Linux) ou `dir /s database.db` (Windows)
- [ ] **Testar restauração**: Restaurar backup em ambiente de teste

### Durante Deploy

- [ ] **NÃO executar `git clean -fdx`** sem backup confirmado
- [ ] **NÃO recriar diretório `instance/`** se banco estiver lá (usar caminho absoluto de D1.1)
- [ ] **Parar aplicação** antes de operações que possam afetar arquivos
- [ ] **Verificar variáveis de ambiente**: `DATABASE_PATH` e `BACKUP_DIR` configuradas

### Pós-Deploy

- [ ] **Verificar logs de startup**: Confirmar caminho absoluto do banco nos logs
- [ ] **Comparar tamanho**: Banco deve ter mesmo tamanho ou maior (nunca menor sem motivo)
- [ ] **Verificar PRAGMAs**: Logs devem mostrar WAL, synchronous=FULL, foreign_keys=ON
- [ ] **Testar query simples**: `SELECT COUNT(*) FROM pedidos` deve retornar valor esperado
- [ ] **Verificar backups**: Confirmar que backup pós-deploy foi criado
- [ ] **Validar UI**: Verificar se pedidos aparecem corretamente

### Rollback (se necessário)

- [ ] **Parar aplicação imediatamente**
- [ ] **Restaurar backup**: `flask cli backup --restore caminho/backup.zip`
- [ ] **Verificar integridade**: Confirmar contagem de registros
- [ ] **Reiniciar aplicação**: Verificar logs de startup

---

## F) KIT DIAGNÓSTICO

### Windows (PowerShell)

#### Localizar Múltiplos Arquivos database.db
```powershell
Get-ChildItem -Path . -Filter "database.db" -Recurse -File | Select-Object FullName, Length, LastWriteTime
```

#### Comparar Tamanho e Data
```powershell
$db1 = Get-Item "backend\instance\database.db"
$db2 = Get-Item "backend\database.db" -ErrorAction SilentlyContinue

Write-Host "DB1 (instance): $($db1.Length) bytes, Modificado: $($db1.LastWriteTime)"
if ($db2) {
    Write-Host "DB2 (raiz): $($db2.Length) bytes, Modificado: $($db2.LastWriteTime)"
    Write-Host "Diferença: $($db1.Length - $db2.Length) bytes"
}
```

#### Verificar Arquivo Efetivamente Aberto (via SQLite)
```powershell
# Instalar SQLite se necessário: choco install sqlite ou baixar de sqlite.org
sqlite3 backend\instance\database.db "PRAGMA database_list;"
```

#### Verificar PRAGMAs Críticos
```powershell
sqlite3 backend\instance\database.db "PRAGMA journal_mode; PRAGMA synchronous; PRAGMA foreign_keys; PRAGMA busy_timeout;"
```

#### Contar Registros por Tabela
```powershell
sqlite3 backend\instance\database.db "SELECT 'pedidos' as tabela, COUNT(*) as total FROM pedidos UNION ALL SELECT 'clientes', COUNT(*) FROM clientes;"
```

#### Verificar Pedidos Ocultos
```powershell
sqlite3 backend\instance\database.db "SELECT COUNT(*) as ocultos FROM pedidos WHERE oculto = 1;"
sqlite3 backend\instance\database.db "SELECT id, cliente, status, oculto, created_at FROM pedidos WHERE oculto = 1 ORDER BY created_at DESC LIMIT 10;"
```

#### Verificar Últimos Pedidos Criados
```powershell
sqlite3 backend\instance\database.db "SELECT id, cliente, status, created_at FROM pedidos ORDER BY created_at DESC LIMIT 10;"
```

#### Verificar Integridade do Banco
```powershell
sqlite3 backend\instance\database.db "PRAGMA integrity_check;"
```

---

### Linux (Bash)

#### Localizar Múltiplos Arquivos database.db
```bash
find . -name "database.db" -type f -exec ls -lh {} \;
```

#### Comparar Tamanho e Data
```bash
db1="backend/instance/database.db"
db2="backend/database.db"

if [ -f "$db1" ]; then
    echo "DB1 (instance): $(du -h "$db1" | cut -f1), Modificado: $(stat -c %y "$db1")"
fi

if [ -f "$db2" ]; then
    echo "DB2 (raiz): $(du -h "$db2" | cut -f1), Modificado: $(stat -c %y "$db2")"
    echo "Diferença: $(($(stat -c %s "$db1") - $(stat -c %s "$db2"))) bytes"
fi
```

#### Verificar Arquivo Efetivamente Aberto
```bash
sqlite3 backend/instance/database.db "PRAGMA database_list;"
```

#### Verificar PRAGMAs Críticos
```bash
sqlite3 backend/instance/database.db <<EOF
PRAGMA journal_mode;
PRAGMA synchronous;
PRAGMA foreign_keys;
PRAGMA busy_timeout;
EOF
```

#### Contar Registros por Tabela
```bash
sqlite3 backend/instance/database.db <<EOF
SELECT 'pedidos' as tabela, COUNT(*) as total FROM pedidos
UNION ALL
SELECT 'clientes', COUNT(*) FROM clientes;
EOF
```

#### Verificar Pedidos Ocultos
```bash
sqlite3 backend/instance/database.db "SELECT COUNT(*) as ocultos FROM pedidos WHERE oculto = 1;"
sqlite3 backend/instance/database.db "SELECT id, cliente, status, oculto, created_at FROM pedidos WHERE oculto = 1 ORDER BY created_at DESC LIMIT 10;"
```

#### Verificar Últimos Pedidos Criados
```bash
sqlite3 backend/instance/database.db "SELECT id, cliente, status, created_at FROM pedidos ORDER BY created_at DESC LIMIT 10;"
```

#### Verificar Integridade do Banco
```bash
sqlite3 backend/instance/database.db "PRAGMA integrity_check;"
```

---

### Análise de Backups

#### Listar Backups Disponíveis
```bash
# Windows
Get-ChildItem backend\instance\backups\*.zip, backend\instance\backups\*.db | Sort-Object LastWriteTime -Descending

# Linux
ls -lht backend/instance/backups/ | head -10
```

#### Verificar Conteúdo de Backup (extrair e verificar)
```bash
# Windows (PowerShell)
Expand-Archive -Path "backend\instance\backups\database_20251226_123619.zip" -DestinationPath "temp_backup"
sqlite3 temp_backup\database_20251226_123619.db "SELECT COUNT(*) FROM pedidos;"

# Linux
unzip -q backend/instance/backups/database_20251226_123619.zip -d temp_backup
sqlite3 temp_backup/database_20251226_123619.db "SELECT COUNT(*) FROM pedidos;"
```

---

## G) POR QUE `.gitignore` NÃO PROTEGE O SQLite EM DEPLOY

### Cenários Típicos de Perda

#### 1. `git clean -fdx` (Limpeza Agressiva)
```bash
git clean -fdx  # Remove TODOS os arquivos não rastreados, incluindo instance/
```
**Problema**: `.gitignore` impede commit, mas não impede `git clean` de apagar arquivos não rastreados. Se `instance/` não estiver no repo, será apagado.

**Solução**: Banco fora do repo + caminho absoluto via env var.

---

#### 2. Scripts de Deploy que Recriam Diretórios
```bash
# Script típico de deploy
rm -rf backend/instance/  # ← Apaga TUDO, incluindo database.db
git pull
# ... resto do deploy
```
**Problema**: Script assume que `instance/` pode ser recriado, mas `database.db` está lá.

**Solução**: Banco em local separado, não tocado por scripts de deploy.

---

#### 3. Clone em Novo Servidor
```bash
git clone repo.git
cd repo
python -m flask run  # ← Cria novo database.db vazio se não existir
```
**Problema**: Novo servidor não tem `database.db` do servidor antigo (não está no repo). `create_all()` cria banco vazio.

**Solução**: Processo de deploy documentado que restaura banco de backup antes de iniciar.

---

#### 4. Rebase/Merge que Recria Estrutura
```bash
git rebase main
# Conflitos resolvidos, diretórios recriados
```
**Problema**: Operações de merge podem recriar diretórios, especialmente se houver mudanças em `.gitignore`.

**Solução**: Banco completamente fora da árvore do repo.

---

### Conexão com o Incidente "5 Pedidos Sumidos"

**Sequência Provável**:
1. Deploy executou operação que apagou/recriou `backend/instance/`
2. `database.db` foi apagado (mesmo estando no `.gitignore`)
3. Aplicação iniciou e `db.create_all()` criou novo banco vazio
4. Sistema funcionou normalmente, mas sem os 5 pedidos
5. Nenhum erro foi gerado (comportamento silencioso de `create_all()`)

**Evidências que Confirmam**:
- ✅ Banco está em `backend/instance/` (dentro do repo)
- ✅ `create_all()` executa sempre, sem verificar existência
- ✅ Não há logs de diagnóstico
- ✅ Existe `backend/database.db` (possível arquivo antigo não migrado)

---

## H) PRIORIZAÇÃO DE IMPLEMENTAÇÃO

### Semana 1 (Crítico)
1. **D1.1**: Mover banco para fora do repo (2h)
2. **D1.2**: Logs de diagnóstico (1h)
3. **D1.3**: Backup consistente fora do repo (3h)
4. **D2.3**: Consolidar arquivos duplicados (2h)

**Total**: 8 horas

### Semana 2 (Alto)
1. **D2.1**: PRAGMAs do SQLite (2h)
2. **D2.2**: Substituir `create_all()` por migrations (3h)

**Total**: 5 horas

### Semana 3 (Melhorias)
1. **D3.1**: Endpoint de diagnóstico (1h)
2. **D3.2**: Monitoramento de tamanho (1h)

**Total**: 2 horas

---

## I) REFERÊNCIAS TÉCNICAS

- [SQLite Backup API](https://www.sqlite.org/backup.html)
- [SQLite PRAGMA Documentation](https://www.sqlite.org/pragma.html)
- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [SQLite Best Practices](https://www.sqlite.org/faq.html#q19)

---

**Documento gerado em**: 2025-01-28  
**Próxima revisão**: Após implementação das correções P0

