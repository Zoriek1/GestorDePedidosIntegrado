# Documentação Técnica do Backend - Plante Uma Flor

Este documento detalha a arquitetura, padrões, endpoints e fluxos de dados do backend Python (Flask). O sistema está em fase avançada de refatoração para **Service-Oriented Architecture (SOA)** e **Clean Code**.

---

## 1. Visão Geral da Arquitetura

O backend utiliza **Python 3 + Flask** com banco de dados **SQLite** (gerenciado via **SQLAlchemy**). A arquitetura evoluiu de scripts monolíticos para uma estrutura em camadas.

### Padrões Adotados (Refatoração 2025)
*   **Repository Pattern:** Abstração completa do acesso a dados. O código de negócio não toca no `db.session` diretamente.
*   **Command Pattern:** Encapsulamento de ações complexas (ex: Impressão).
*   **Services:** Lógica de negócio pura e integrações externas (ex: Cálculo de Frete).
*   **Blueprints:** Organização modular das rotas da API.

---

## 2. Estrutura de Pastas e Responsabilidades

```text
backend/
├── app/
│   ├── commands/       # [NOVO] Ações encapsuladas (Regra de Negócio + View)
│   │   └── gerar_comprovante_command.py
│   ├── models/         # Definição das tabelas (SQLAlchemy)
│   │   ├── pedido.py   # Core do domínio
│   │   └── cliente.py
│   ├── repositories/   # [NOVO] Camada de acesso a dados (CRUD)
│   │   ├── pedido_repository.py
│   │   └── base_repository.py
│   ├── routes/         # Controllers da API (Recebem HTTP e chamam Services/Repos)
│   │   ├── pedidos.py
│   │   ├── clientes.py
│   │   └── api.py      # [LEGADO] Rotas mistas antigas
│   ├── schemas/        # Serialização de dados (DTOs)
│   ├── services/       # Regras de Negócio e Integrações
│   │   ├── distancia.py
│   │   └── taxa_entrega.py
│   └── utils/          # Helpers (Backup, Criptografia)
├── scripts/            # [LEGADO] Automações e Migrations manuais
└── data/               # Arquivo SQLite (database.db)
```

---

## 3. Fluxo de Dependências e Injeção

O sistema utiliza injeção de dependência manual (instanciação direta controlada) para manter a simplicidade, mas respeita a inversão de controle.

**Fluxo Padrão de uma Requisição (Clean Architecture):**

1.  **Route (Controller):** Recebe o Request JSON/Params.
    *   *Depende de:* Repositories, Commands ou Services.
    *   *Não faz:* Queries SQL diretas ou lógica complexa.
2.  **Command / Service:** Processa a regra de negócio.
    *   *Depende de:* Repositories.
    *   *Exemplo:* `GerarComprovanteCommand` busca dados, valida "Cliente == Destinatário" e gera HTML.
3.  **Repository:** Executa a query no banco.
    *   *Depende de:* Models (SQLAlchemy).
    *   *Retorna:* Objetos de Domínio (`Pedido`, `Cliente`) ou Listas.

---

## 4. Endpoints da API (API Reference)

A API é RESTful e retorna JSON (exceto endpoint de comprovante).

### 4.1. Pedidos (`/api/pedidos`)
| Método | Endpoint | Descrição | Status |
|:---:|:---|:---|:---|
| `GET` | `/` | Lista pedidos com filtros (status, data, busca). | **Refatorado** |
| `POST` | `/` | Cria um novo pedido (usado pelo Wizard). | **Refatorado** |
| `GET` | `/:id` | Detalhes de um pedido específico. | **Refatorado** |
| `PUT` | `/:id` | Atualiza dados do pedido. | **Refatorado** |
| `DELETE`| `/:id` | Remove pedido (Soft Delete ou Hard Delete com senha). | **Refatorado** |
| `PUT` | `/:id/status` | Altera apenas o status (ex: `agendado` -> `concluido`). | **Refatorado** |
| `GET` | `/:id/comprovante` | **[NOVO]** Retorna HTML pronto para impressão (Command). | **Novo** |
| `POST` | `/:id/marcar-impresso`| Flag `impresso=True`. | **Refatorado** |
| `POST` | `/exportar-planilha` | Dispara script legado de sync com Google Sheets. | **Híbrido** |

### 4.2. Clientes (`/api/clientes`)
| Método | Endpoint | Descrição | Status |
|:---:|:---|:---|:---|
| `GET` | `/busca` | Busca por nome/telefone (Autocomplete). | **Refatorado** |
| `POST` | `/` | Cadastra novo cliente (CRM). | **Refatorado** |

### 4.3. Estatísticas (`/api/stats`)
| Método | Endpoint | Descrição | Status |
|:---:|:---|:---|:---|
| `GET` | `/` | Retorna KPIs (Total, Agendados, Atrasados). | **Refatorado** |

### 4.4. Fontes (`/api/fontes-pedido`)
| Método | Endpoint | Descrição | Status |
|:---:|:---|:---|:---|
| `GET` | `/` | Lista fontes ativas (WhatsApp, Site, Catálogo). | **Novo** |

---

## 5. Diferenciação: Novo vs. Legado

### ✅ O Que é Novo / Refatorado
*   **Frontend V2:** Todo o diretório `frontend_v2` (React/Vite) consome exclusivamente as rotas JSON listadas acima.
*   **Repositories:** Toda leitura/escrita de `Pedido` e `Cliente` passa por `app/repositories`.
*   **Commands:** Lógica de impressão isolada em `app/commands`.
*   **Models:** Classes SQLAlchemy ricas (`Pedido.is_overdue()`, `to_dict()`).

### ⚠️ O Que é Legado (Manter com Cuidado)
*   **Scripts de Exportação:** `backend/scripts/export/exportar_vendas_sheets.py`. É um script complexo que integra com Google API. Foi "envelopado" na rota `/api/pedidos/exportar-planilha`, mas sua lógica interna é legada.
*   **Frontend V1:** Diretório `frontend/` (HTML/JS puro). Ainda existe para fallback, mas não deve receber novas features.
*   **Backups:** O sistema de backup em `scripts/backup/` e `app/utils/backup_helper.py` é funcional e crítico, misturando lógica de OS (bat/shell) com Python.

---

## 6. Autenticação e Segurança

*   **Middleware:** `@requires_auth` e `@requires_edit_auth`.
*   **Mecanismo:** Basic Auth (Token simples ou user/pass hardcoded no config).
*   **Cors:** Configurado globalmente para permitir acesso do `frontend_v2`.

## 7. Como Executar (Ambiente de Dev)

1.  **Backend:**
    ```bash
    cd backend
    # Ativar venv
    python main.py
    # Roda em http://localhost:5000
    ```

2.  **Frontend V2:**
    ```bash
    cd frontend_v2
    npm install
    npm run dev
    # Roda em http://localhost:5173
    ```

