# Contexto do Projeto: Servidor de Pedidos (Floricultura)

## 1. Arquitetura do Sistema
O sistema opera como um servidor central que gerencia pedidos, persistência e rotinas de manutenção.
- **Entrada de Dados:** Interface de Usuário (Botões de Ação) e API.
- **Persistência:** Arquivo local SQLite (`.db`).
- **Ciclo de Vida:** O servidor mantém processos contínuos (Backups, Listeners).

## 2. Regras de Negócio Críticas (Source of Truth)

### 2.1. Padrão de Comandos (UI & Ações)
> *"Botões com regra de classe"*
Todo botão ou ação disparada pela interface **NÃO** deve conter lógica solta. Deve seguir estritamente o **Command Pattern**:
- **Regra:** Cada botão instancia uma Classe de Comando específica.
- **Estrutura:** `Invoker (Botão)` -> `Command Class (Regra)` -> `Receiver (Serviço/Banco)`.
- **Exemplo:** O botão "Confirmar Pedido" não chama o banco. Ele instancia `new ConfirmarPedidoCommand(id).execute()`.

### 2.2. Persistência de Pedidos
> *"Pedidos devem ser postados na .db"*
- **Atomicidade:** A gravação no arquivo `.db` é a fonte única de verdade.
- **Fluxo de Dados:**
  1. Pedido chega na memória.
  2. Validação de campos (Clean Code: Fail Fast).
  3. Conversão para DTO.
  4. Inserção imediata na `.db` via Repository.
- **Restrição:** Nenhuma confirmação de sucesso é enviada ao cliente antes do *commit* no arquivo `.db` ser confirmado.

### 2.3. Rotinas de Manutenção e Backup
> *"Backup a cada 24h e no início do servidor"*
- **Gatilho 1 (Boot):** Assim que a classe `Server` inicializar (`onStart`), o primeiro método a rodar deve ser `BackupManager.performBackup()`.
- **Gatilho 2 (Cron):** Um agendador interno deve disparar a mesma função a cada 24h exatas.
- **Lógica de Arquivo:**
  - Origem: `database.db`
  - Destino: `./backups/backup_[TIMESTAMP].db`
  - Tratamento de Erro: Se o backup falhar, o servidor deve emitir um alerta crítico (Log/Notify), mas **não** deve parar de aceitar pedidos.

## 3. Estrutura de Classes Sugerida (Mapeamento Clean Code)

### Core (Domain)
- `Pedido`: Entidade rica com métodos de validação (`isValid()`, `calcularTotal()`).
- `IPedidoRepository`: Interface que define o contrato de salvar/ler `.db`.

### Application (Commands/Use Cases)
- `PostarPedidoCommand`: Implementa a lógica de receber o input e chamar o repositório.
- `RealizarBackupCommand`: Encapsula a lógica de cópia de arquivos.

### Infrastructure
- `SQLitePedidoRepository`: Implementação real que manipula o arquivo `.db`.
- `ServerScheduler`: Gerencia o timer de 24h.

## 4. Diretrizes de Refatoração (Para a IA)
Ao refatorar o código legado deste repositório:
1. Identifique onde os botões chamam funções diretas e extraia para Classes `Command`.
2. Centralize todas as chamadas SQL/File I/O em classes "Repository".
3. Garanta que o Backup seja uma classe isolada (`BackupService`), desacoplada da lógica de pedidos.