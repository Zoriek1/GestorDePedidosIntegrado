# Documentação do Backend

Esta pasta contém documentação adicional do backend do sistema Plante Uma Flor.

## Estrutura de Documentação

A documentação principal do projeto está no [README.md](../../README.md) na raiz do projeto, que contém:

- Visão geral completa do sistema
- Guia de instalação e configuração
- Documentação completa da API REST
- Configuração de taxas de entrega
- Setup de HTTPS e certificados SSL
- Guia de desenvolvimento
- Troubleshooting

## Documentação Adicional

Documentação adicional específica do backend pode ser adicionada nesta pasta conforme necessário:

- Guias de migração do banco de dados
- Documentação de serviços internos
- Guias de configuração avançada
- Documentação de APIs externas integradas

## Estrutura do Backend

```
backend/
├── app/                    # Aplicação Flask
│   ├── models/            # Modelos de dados (SQLAlchemy)
│   ├── routes/            # Endpoints da API REST
│   ├── services/          # Lógica de negócio
│   └── utils/              # Utilitários
├── config/                 # Arquivos de configuração
│   └── taxa_entrega.json  # Configuração de taxas
├── scripts/                # Scripts de manutenção
│   ├── migrations/        # Scripts de migração do banco
│   ├── tests/             # Scripts de teste
│   └── backup.py          # Scripts de backup
├── ssl/                    # Certificados SSL
├── run/                    # Scripts de uso diário
├── UtilsScripts/           # Scripts utilitários
├── backups/                # Backups do banco de dados
├── logs/                   # Logs do servidor
└── main.py                 # Ponto de entrada
```

## Serviços Principais

### DistanciaService
Localização: `app/services/distancia.py`

Responsável por:
- Geocodificação de endereços
- Cálculo de distâncias usando GraphHopper e OpenRouteService
- Validação de endereços e CEPs

### TaxaEntregaService
Localização: `app/services/taxa_entrega.py`

Responsável por:
- Cálculo de taxas de entrega baseado em faixas de distância
- Leitura da configuração em `config/taxa_entrega.json`
- Aplicação de limites mínimo e máximo

### GraphHopperService
Localização: `app/services/graphhopper.py`

Responsável por:
- Integração com API GraphHopper
- Cálculo de rotas otimizadas
- Fallback para OpenRouteService

## Modelos de Dados

### Pedido
Localização: `app/models/pedido.py`

Modelo principal do sistema, contém todos os campos de um pedido:
- Dados do cliente e destinatário
- Informações do produto
- Endereço de entrega
- Status e controle

### Cliente
Localização: `app/models/cliente.py`

Sistema de gestão de clientes:
- Cadastro de clientes
- Histórico de pedidos
- Endereços cadastrados

### RotaOtimizada
Localização: `app/models/rota_otimizada.py`

Otimização de rotas de entrega:
- Agrupamento de pedidos por data
- Cálculo de rota otimizada
- Sequência de entregas

## Configuração

### Variáveis de Ambiente

Arquivo `.env` na raiz do backend:

```env
# API Keys
GRAPHHOPPER_API_KEY=sua_chave
OPENROUTE_API_KEY=sua_chave

# Endereço da Floricultura
ENDERECO_FLORICULTURA=Endereço completo

# Autenticação
EDIT_USERNAME=admin
EDIT_PASSWORD=senha

# Debug
DEBUG=True
FLASK_ENV=development
ENABLE_DEBUG_ENDPOINTS=false
```

### Arquivo de Configuração do Servidor

`config_servidor.ini`:

```ini
[SERVIDOR]
hostname=Gestor-pedidos.local
```

## Scripts de Migração

Scripts de migração do banco de dados estão em `scripts/migrations/`:

- `add_distancia_column.py` - Adiciona coluna de distância
- `add_endereco_columns.py` - Adiciona colunas de endereço
- `add_oculto_column.py` - Adiciona coluna oculto
- `criar_tabelas_clientes.py` - Cria tabelas de clientes
- `migrate_add_endereco_fields.py` - Migração de campos de endereço
- `migrate_add_rota_fields.py` - Migração de campos de rota

**Como executar:**
```bash
cd backend/scripts/migrations
python nome_do_script.py
```

## Logs

Logs do servidor são salvos em:
- `logs/access_YYYY-MM-DD.log` - Logs de acesso HTTP
- `servidor_https.log` - Logs do servidor HTTPS (se usando VBS)

## Backup e Restauração

### Backup Manual

```bash
backend\scripts\backup_manual.bat
```

Cria backup do banco de dados em `backups/` com timestamp.

### Restauração

```bash
cd backend/scripts
python restore.py caminho_do_backup.zip
```

## Desenvolvimento

Para mais informações sobre desenvolvimento, veja a seção [Desenvolvimento](../../README.md#-desenvolvimento) no README principal.

