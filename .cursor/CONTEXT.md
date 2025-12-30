# Contexto do Projeto: Servidor de Pedidos (Floricultura)

## 1. Visão Geral
Sistema backend (com possível interface de administração) responsável por gerenciar o ciclo de vida de pedidos de uma floricultura. O sistema preza pela integridade dos dados e operações atômicas.

## 2. Glossário (Linguagem Ubíqua)
Use estes termos exatos nas classes e variáveis:
- **Order (Pedido):** A entidade central. Um agrupamento de itens solicitados por um cliente.
- **Arrangement (Arranjo):** Produto composto (flores + vaso + fitas).
- **Customer (Cliente):** A pessoa que compra.
- **Recipient (Destinatário):** A pessoa que recebe (pode ser diferente do cliente).
- **Dispatch (Despacho):** O ato de enviar o pedido para entrega.

## 3. Regras de Negócio (Business Rules)

### 3.1. Gestão de Pedidos (Core)
- **Persistência Atômica:**
  - Todo `Order` criado ou modificado deve ser imediatamente persistido no banco de dados (`.db` / SQLite/Postgres).
  - Use o padrão **Repository** (`IOrderRepository.save(order)`). Nunca faça queries SQL diretas nos Controllers.
- **Imutabilidade Pós-Despacho:**
  - Pedidos com status `DISPATCHED` ou `DELIVERED` não podem ser alterados, apenas cancelados (via soft-delete ou status `CANCELED`).

### 3.2. Infraestrutura e Segurança
- **Rotina de Backup (Cron Job):**
  - O sistema deve possuir um `BackupService` que roda automaticamente:
    1. No startup da aplicação (`onServerStart`).
    2. A cada 24 horas (ex: 00:00).
  - O backup deve copiar o arquivo `.db` atual para uma pasta `/backups` com timestamp (`db_YYYYMMDD_HHmm.bak`).

### 3.3. Interface e Comandos ("Botões com Regra de Classe")
- **Padrão Command (UI/Ações):**
  - Botões ou gatilhos de ação no sistema não devem conter lógica de negócio.
  - Cada "Botão" deve instanciar uma classe que implementa a interface `ICommand`.
  - Exemplo: O botão "Finalizar Pedido" chama a classe `FinalizeOrderCommand`.
  - Isso permite desfazer ações (undo) e logar quem clicou no quê.

### 3.4. Estoque e Disponibilidade
- **Validação de Estoque:**
  - Antes de confirmar um pedido, o `InventoryService` deve verificar se há flores suficientes para todos os arranjos.

## 4. Arquitetura Técnica (Clean Code & Java-Mindset)

### Camadas (Layers)
1.  **Domain:** Entidades e Interfaces (ex: `Order`, `IOrderRepository`). Sem dependências externas.
2.  **Application:** Casos de uso (ex: `CreateOrderUseCase`, `RunBackupUseCase`).
3.  **Infrastructure:** Implementação concreta (ex: `SQLiteOrderRepository`, `FileSystemBackupService`).
4.  **Interface/API:** Controllers REST ou Interface Gráfica.

### Padrões Obrigatórios
- **Dependency Injection:** Todas as dependências (Repositories, Services) devem ser injetadas via construtor.
- **Typed Errors:** Lance exceções específicas (ex: `BackupFailedException`, `OrderEmptyException`), nunca erros genéricos.