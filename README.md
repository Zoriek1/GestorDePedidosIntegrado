# Plante Uma Flor - Sistema de Gestão de Pedidos PWA

![Version](https://img.shields.io/badge/version-3.0.1-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Flask](https://img.shields.io/badge/flask-3.0+-red)
![PWA](https://img.shields.io/badge/PWA-enabled-purple)
![License](https://img.shields.io/badge/license-MIT-yellow)

Progressive Web App (PWA) moderno e completo para gerenciamento de pedidos de floricultura. Sistema multiplataforma com interface web responsiva que funciona em qualquer dispositivo (desktop, tablet, smartphone) com suporte offline completo, cálculo automático de distâncias e rotas, sistema de taxas de entrega configurável e muito mais.

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Características Principais](#-características-principais)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Instalação e Configuração](#-instalação-e-configuração)
- [Funcionalidades Detalhadas](#-funcionalidades-detalhadas)
- [API REST - Documentação Completa](#-api-rest---documentação-completa)
- [Configuração de Taxas de Entrega](#-configuração-de-taxas-de-entrega)
- [HTTPS e Certificados SSL](#-https-e-certificados-ssl)
- [Scripts e Ferramentas](#-scripts-e-ferramentas)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Desenvolvimento](#-desenvolvimento)
- [Troubleshooting](#-troubleshooting)
- [Changelog](#-changelog)

---

## 🎯 Visão Geral

**Plante Uma Flor** é um sistema completo de gestão de pedidos desenvolvido especificamente para floriculturas. O sistema foi projetado para substituir aplicações desktop antigas por uma solução moderna, multiplataforma e acessível de qualquer dispositivo.

### Casos de Uso

- **Gestão de Pedidos**: Criar, editar, visualizar e gerenciar pedidos de flores
- **Cálculo de Rotas**: Calcular automaticamente distâncias e rotas de entrega
- **Taxas de Entrega**: Sistema configurável de cálculo de taxas baseado em faixas de distância
- **Painel Administrativo**: Visualização centralizada de todos os pedidos com filtros e busca
- **Impressão**: Geração de documentos profissionais para impressão em A4
- **Gestão de Clientes**: Cadastro e histórico de clientes

### Público-Alvo

- Floriculturas que precisam de um sistema moderno de gestão
- Empresas que buscam substituir sistemas desktop por soluções web
- Negócios que precisam de acesso multiplataforma aos dados

---

## ✨ Características Principais

### Multiplataforma
- ✅ Funciona em Windows, Android, iOS, Linux, macOS
- ✅ Interface responsiva adaptável a qualquer tamanho de tela
- ✅ PWA instalável como aplicativo nativo

### Offline First
- ✅ Funciona completamente sem conexão à internet
- ✅ Cache inteligente de assets e dados
- ✅ Sincronização automática quando online
- ✅ Service Worker para funcionamento offline
- ✅ IndexedDB para armazenamento local persistente

### Performance e UX
- ✅ Carregamento instantâneo com cache otimizado
- ✅ Interface moderna e intuitiva
- ✅ Navegação fluida entre telas
- ✅ Feedback visual em todas as ações

### Funcionalidades Avançadas
- ✅ Cálculo automático de distâncias usando GraphHopper e OpenRouteService
- ✅ Sistema de taxas de entrega configurável por faixas de distância
- ✅ Otimização de rotas de entrega
- ✅ Impressão profissional de pedidos
- ✅ Gestão completa de clientes com histórico
- ✅ Filtros e busca avançada no painel

### Segurança e Infraestrutura
- ✅ HTTPS com certificados SSL para rede local
- ✅ Autenticação de usuários
- ✅ Backup automático do banco de dados
- ✅ Sistema 100% portável (sem instalação)

---

## 🏗️ Arquitetura do Sistema

### Componentes Principais

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (PWA)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Service    │  │  IndexedDB   │  │   Router     │ │
│  │   Worker    │  │   (Cache)    │  │   (SPA)      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/HTTPS
                        │ REST API
┌───────────────────────▼─────────────────────────────────┐
│                  BACKEND (Flask)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Routes     │  │   Services   │  │   Models     │ │
│  │   (API)      │  │  (Business)  │  │  (Database)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│   SQLite     │ │ GraphHopper │ │ OpenRoute  │
│  (Database)  │ │     API     │ │   Service  │
└──────────────┘ └─────────────┘ └────────────┘
```

### Fluxo de Dados

1. **Criação de Pedido**: Frontend → API → Validação → Database
2. **Cálculo de Distância**: API → GraphHopper/OpenRouteService → Database
3. **Cálculo de Taxa**: API → TaxaEntregaService → JSON Config → Database
4. **Sincronização Offline**: IndexedDB ↔ API ↔ Database

### Tecnologias Utilizadas

#### Backend
- **Flask 3.0+**: Framework web Python
- **Flask-SQLAlchemy**: ORM para banco de dados
- **Flask-CORS**: Suporte a CORS para API
- **SQLite**: Banco de dados relacional
- **python-dateutil**: Manipulação de datas
- **requests**: Cliente HTTP para APIs externas
- **cryptography**: Criptografia para backups

#### Frontend
- **HTML5 + CSS3**: Estrutura e estilos
- **JavaScript ES6+**: Lógica da aplicação
- **Tailwind CSS**: Framework CSS utilitário
- **Service Worker API**: Funcionalidade offline
- **IndexedDB API**: Armazenamento local
- **Fetch API**: Comunicação com backend

#### APIs Externas
- **GraphHopper API**: Cálculo de rotas e distâncias
- **OpenRouteService API**: Geocodificação e rotas (fallback)
- **Nominatim (OpenStreetMap)**: Geocodificação gratuita
- **ViaCEP API**: Validação de CEP brasileiro

---

## 🚀 Instalação e Configuração

### Requisitos

- **Python 3.8 ou superior**
- **Navegador moderno** (Chrome, Edge, Firefox, Safari)
- **Rede local** (para acesso de múltiplos dispositivos)
- **Conexão com internet** (para cálculo de rotas e geocodificação)

### Instalação Passo a Passo

#### 1. Clonar/Baixar o Projeto

```bash
# Se usando Git
git clone <repository-url>
cd "Gestor de Pedidos Plante uma flor"

# Ou simplesmente extrair o ZIP do projeto
```

#### 2. Instalar Dependências Python

```bash
cd backend
pip install -r requirements.txt
```

#### 3. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na pasta `backend/`:

```env
# API Keys (opcional, mas recomendado)
GRAPHHOPPER_API_KEY=sua_chave_graphhopper
OPENROUTE_API_KEY=sua_chave_openroute

# Endereço da Floricultura
ENDERECO_FLORICULTURA=Rua Exemplo, 123, Bairro Centro, Goiânia, GO, 74000-000

# Autenticação (opcional)
EDIT_USERNAME=admin
EDIT_PASSWORD=sua_senha_segura

# Debug (opcional)
FLASK_ENV=development
DEBUG=True
ENABLE_DEBUG_ENDPOINTS=false
```

**Onde obter as API Keys:**

- **GraphHopper**: https://www.graphhopper.com/api/ (500 requisições/dia grátis)
- **OpenRouteService**: https://openrouteservice.org/dev/#/signup (2.000 requisições/dia grátis)

**Nota**: O sistema funciona sem API keys usando serviços gratuitos, mas com limitações de taxa.

#### 4. Iniciar o Servidor

**Opção 1 - Script Automático (Recomendado):**

```bash
# HTTP (modo simples)
backend\run\abrir_sistema.bat

# HTTPS (recomendado para produção)
backend\run\abrir_sistema_https.bat
```

**Opção 2 - Python Diretamente:**

```bash
cd backend
python main.py              # HTTP
python main.py --https      # HTTPS
```

#### 5. Acessar o Sistema

- **Local**: `http://localhost:5000` ou `https://localhost:5000`
- **Rede**: `http://SEU_IP:5000` ou `https://SEU_IP:5000`

---

## 💻 Funcionalidades Detalhadas

### 1. Gestão de Pedidos

#### Criar Pedido

Formulário intuitivo em 4 etapas:

1. **Dados do Cliente**
   - Nome do remetente (cliente)
   - Telefone do cliente
   - Nome do destinatário
   - Tipo de pedido (Entrega ou Retirada)

2. **Produto e Agendamento**
   - Descrição do produto
   - Flores e cores
   - Valor total
   - Data de entrega
   - Horário de entrega (formato HH:MM)

3. **Endereço** (apenas para "Entrega")
   - CEP (com validação automática)
   - Rua/Logradouro
   - Número
   - Bairro
   - Cidade
   - Observações de entrega

4. **Finalização**
   - Mensagem/Carta
   - Forma de pagamento
   - Observações gerais
   - Preview do pedido

#### Visualizar e Editar Pedidos

- Listagem completa no painel
- Edição de todos os campos
- Mudança rápida de status
- Visualização detalhada em modal

#### Status dos Pedidos

- **Agendado** (Azul): Pedido recém-criado, aguardando processamento
- **Produção** (Amarelo): Pedido em preparação
- **Pronto** (Verde): Pedido pronto para entrega
- **Entregue** (Roxo): Pedido entregue ao destinatário
- **Cancelado** (Vermelho): Pedido cancelado

### 2. Gestão de Clientes

- Cadastro completo de clientes
- Histórico de pedidos por cliente
- Busca e autocomplete
- Integração com sistema de pedidos

### 3. Cálculo de Distâncias e Rotas

O sistema calcula automaticamente:

- **Distância em linha reta**: Entre floricultura e endereço de entrega
- **Distância de rota**: Distância real de carro (usando GraphHopper/OpenRouteService)
- **Coordenadas GPS**: Latitude e longitude do endereço
- **Tempo estimado**: Tempo de viagem estimado

**Como funciona:**

1. Ao criar/editar um pedido com endereço, o sistema geocodifica o endereço
2. Calcula a distância usando a API de rotas
3. Armazena os dados no banco de dados
4. Usa os dados para cálculo de taxas e otimização de rotas

### 4. Sistema de Taxas de Entrega

Sistema configurável de cálculo de taxas baseado em **faixas de distância**.

**Características:**

- Configuração via arquivo JSON (`backend/config/taxa_entrega.json`)
- Suporte a múltiplas faixas de distância
- Taxa mínima e máxima configuráveis
- Cálculo automático baseado na distância do pedido

**Exemplo de Configuração:**

```json
{
  "tipo": "faixas",
  "faixas": [
    {
      "de_km": 0,
      "ate_km": 2,
      "taxa": 5.00,
      "descricao": "0-2 km"
    },
    {
      "de_km": 3,
      "ate_km": 5,
      "taxa": 10.00,
      "descricao": "3-5 km"
    }
  ],
  "taxa_minima": 5.00,
  "taxa_maxima": 50.00
}
```

**Lógica de Cálculo:**

- Se a distância está dentro de uma faixa, usa a taxa da faixa
- Se a distância está entre faixas, usa a taxa da próxima faixa (maior)
- Respeita os limites mínimo e máximo configurados

Veja seção [Configuração de Taxas de Entrega](#-configuração-de-taxas-de-entrega) para mais detalhes.

### 5. Painel Administrativo

#### Funcionalidades

- **Listagem de Pedidos**: Cards coloridos por status
- **Filtros**: Por status, data, busca textual
- **Estatísticas**: Total, entregues, em produção, atrasados
- **Ordenação**: Por data de entrega (mais próximos primeiro)
- **Busca em Tempo Real**: Filtro instantâneo por texto
- **Atualização Automática**: Refresh a cada 30 segundos
- **Impressão**: Geração de documento A4 para impressão

#### Filtros Disponíveis

- **Status**: Todos, Agendado, Produção, Pronto, Entregue, Cancelado
- **Data**: Todos, Hoje, Amanhã, Esta Semana, Este Mês, Personalizado
- **Busca**: Por cliente, destinatário, produto, endereço

### 6. Impressão de Pedidos

- Layout profissional otimizado para A4
- Informações completas do pedido
- Destaque visual para informações críticas
- Compatível com qualquer impressora

### 7. Funcionalidades Offline

O sistema funciona completamente offline:

- **Cache de Assets**: CSS, JS, imagens são cacheados
- **Armazenamento Local**: Pedidos salvos no IndexedDB
- **Sincronização**: Quando online, sincroniza automaticamente
- **Service Worker**: Gerencia cache e funcionalidade offline

---

## 🎯 API REST - Documentação Completa

### Base URL

```
http://localhost:5000/api
https://localhost:5000/api
```

### Autenticação

Alguns endpoints requerem autenticação. Configure no `.env`:

```env
EDIT_USERNAME=admin
EDIT_PASSWORD=sua_senha
```

### Endpoints Disponíveis

#### Health Check

```http
GET /api/health
```

**Resposta:**
```json
{
  "success": true,
  "status": "healthy",
  "message": "API funcionando normalmente"
}
```

#### Pedidos

##### Listar Pedidos

```http
GET /api/pedidos
```

**Query Parameters:**
- `status` (opcional): Filtrar por status
- `data_inicio` (opcional): Data inicial (YYYY-MM-DD)
- `data_fim` (opcional): Data final (YYYY-MM-DD)
- `search` (opcional): Busca textual

**Resposta:**
```json
{
  "success": true,
  "pedidos": [
    {
      "id": 1,
      "cliente": "João Silva",
      "telefone_cliente": "(62) 99999-9999",
      "destinatario": "Maria Santos",
      "produto": "Buquê de Rosas",
      "dia_entrega": "2024-12-15",
      "horario": "14:30",
      "status": "agendado",
      "distancia_km": 5.2,
      "taxa_entrega": 15.00
    }
  ],
  "total": 1
}
```

##### Criar Pedido

```http
POST /api/pedidos
Content-Type: application/json
```

**Body:**
```json
{
  "cliente": "João Silva",
  "telefone_cliente": "(62) 99999-9999",
  "destinatario": "Maria Santos",
  "tipo_pedido": "Entrega",
  "produto": "Buquê de Rosas",
  "flores_cor": "Rosas vermelhas",
  "valor": "150.00",
  "dia_entrega": "2024-12-15",
  "horario": "14:30",
  "cep": "74000-000",
  "rua": "Rua Exemplo",
  "numero": "123",
  "bairro": "Centro",
  "cidade": "Goiânia",
  "mensagem": "Parabéns!",
  "pagamento": "Cartão"
}
```

**Resposta:**
```json
{
  "success": true,
  "pedido": {
    "id": 1,
    "cliente": "João Silva",
    ...
  },
  "message": "Pedido criado com sucesso"
}
```

##### Obter Pedido

```http
GET /api/pedidos/:id
```

##### Atualizar Pedido

```http
PUT /api/pedidos/:id
Content-Type: application/json
```

**Body:** Mesmo formato do criar pedido

##### Atualizar Status

```http
PUT /api/pedidos/:id/status
Content-Type: application/json
```

**Body:**
```json
{
  "status": "producao"
}
```

##### Deletar Pedido

```http
DELETE /api/pedidos/:id
```

#### Distâncias e Rotas

##### Calcular Distância de um Pedido

```http
GET /api/pedidos/:id/distancia
```

##### Calcular Distâncias em Lote

```http
POST /api/pedidos/calcular-distancias
Content-Type: application/json
```

**Body:**
```json
{
  "pedido_ids": [1, 2, 3]
}
```

##### Calcular Taxa de Entrega

```http
POST /api/pedidos/:id/calcular-taxa
```

#### Rotas Otimizadas

##### Criar Rota Otimizada

```http
POST /api/pedidos/rota-otimizada
Content-Type: application/json
```

**Body:**
```json
{
  "pedido_ids": [1, 2, 3],
  "data_entrega": "2024-12-15"
}
```

##### Obter Rota Otimizada

```http
GET /api/pedidos/rota-otimizada/:rota_id
```

#### Estatísticas

##### Obter Estatísticas

```http
GET /api/stats
```

**Resposta:**
```json
{
  "total": 100,
  "agendados": 20,
  "producao": 15,
  "prontos": 10,
  "entregues": 50,
  "cancelados": 5,
  "atrasados": 3
}
```

##### Pedidos Atrasados

```http
GET /api/pedidos/overdue
```

#### Clientes

##### Listar Clientes

```http
GET /api/clientes
```

##### Criar Cliente

```http
POST /api/clientes
Content-Type: application/json
```

##### Buscar Clientes (Autocomplete)

```http
GET /api/clientes/buscar?q=joao
```

#### Autenticação

##### Login

```http
POST /api/auth/login
Content-Type: application/json
```

**Body:**
```json
{
  "username": "admin",
  "password": "senha"
}
```

##### Verificar Autenticação

```http
GET /api/auth/check
```

#### Utilitários

##### Limpar Pedidos Antigos

```http
POST /api/cleanup
Content-Type: application/json
```

**Body:**
```json
{
  "dias": 30
}
```

### Códigos de Status HTTP

- `200 OK`: Requisição bem-sucedida
- `201 Created`: Recurso criado com sucesso
- `400 Bad Request`: Dados inválidos
- `401 Unauthorized`: Não autenticado
- `403 Forbidden`: Sem permissão
- `404 Not Found`: Recurso não encontrado
- `500 Internal Server Error`: Erro no servidor

---

## 💰 Configuração de Taxas de Entrega

### Arquivo de Configuração

O sistema de taxas é configurado através do arquivo:

```
backend/config/taxa_entrega.json
```

### Estrutura do Arquivo

```json
{
  "tipo": "faixas",
  "faixas": [
    {
      "de_km": 0,
      "ate_km": 2,
      "taxa": 5.00,
      "descricao": "0-2 km"
    },
    {
      "de_km": 3,
      "ate_km": 5,
      "taxa": 10.00,
      "descricao": "3-5 km"
    }
  ],
  "taxa_minima": 5.00,
  "taxa_maxima": 50.00,
  "observacoes": "Valores podem ser customizados conforme necessário"
}
```

### Campos

- **tipo**: Tipo de cálculo (`"faixas"` para sistema de faixas)
- **faixas**: Array de faixas de distância
  - **de_km**: Distância inicial da faixa (inclusive)
  - **ate_km**: Distância final da faixa (inclusive)
  - **taxa**: Valor da taxa em reais
  - **descricao**: Descrição da faixa
- **taxa_minima**: Valor mínimo de taxa (aplicado se cálculo resultar em valor menor)
- **taxa_maxima**: Valor máximo de taxa (aplicado se cálculo resultar em valor maior)

### Lógica de Cálculo

1. O sistema busca a faixa onde a distância se encaixa
2. Se a distância está dentro de uma faixa (`de_km <= distancia <= ate_km`), usa a taxa da faixa
3. Se a distância está entre faixas, usa a taxa da **próxima faixa maior**
4. O valor final é limitado entre `taxa_minima` e `taxa_maxima`

### Exemplos

**Distância: 1.5 km**
- Faixa: 0-2 km
- Taxa: R$ 5,00

**Distância: 4 km**
- Faixa: 3-5 km
- Taxa: R$ 10,00

**Distância: 5.5 km**
- Entre faixas (5.5 > 5 e 5.5 < 6)
- Usa próxima faixa: 6-10 km
- Taxa: R$ 15,00

**Distância: 11.3 km**
- Faixa: 10-15 km
- Taxa: R$ 20,00

### Como Editar

1. Abra o arquivo `backend/config/taxa_entrega.json`
2. Edite as faixas conforme necessário
3. Salve o arquivo
4. Reinicie o servidor (ou aguarde o próximo cálculo)

**Importante**: Após editar, reinicie o servidor para garantir que as mudanças sejam aplicadas.

---

## 🔒 HTTPS e Certificados SSL

### Por que HTTPS?

- ✅ Permite instalação do PWA em dispositivos móveis
- ✅ Mais seguro para dados sensíveis
- ✅ Melhor experiência do usuário
- ✅ Requerido para algumas funcionalidades do navegador

### Setup Rápido (Recomendado)

Execute o configurador interativo:

```bash
cd backend
CONFIGURAR_SERVIDOR.bat
```

Este script irá:
1. Instalar mkcert (se necessário)
2. Configurar o hostname (padrão: `Gestor-pedidos.local`)
3. Gerar certificados SSL com hostname + multi-IP
4. Preparar certificado CA para distribuição

### Setup Manual

#### 1. Instalar mkcert

```bash
cd backend/ssl
INSTALAR_MKCERT_SIMPLES.bat
```

#### 2. Configurar Hostname (Opcional)

Edite `backend/config_servidor.ini`:

```ini
[SERVIDOR]
hostname=Gestor-pedidos.local
```

#### 3. Gerar Certificados

```bash
cd backend/ssl
GERAR_CERTIFICADOS_AUTO.bat
```

Este script gera certificados para:
- localhost
- Hostname configurado (ex: Gestor-pedidos.local)
- Todos os IPs da máquina

#### 4. Distribuir Certificado CA

```bash
cd backend/ssl
DISTRIBUIR_CERTIFICADO.bat
```

Isso copia o certificado CA (`rootCA.pem`) para a pasta `ssl/PARA_CLIENTES/`

#### 5. Iniciar Servidor HTTPS

```bash
cd backend/run
abrir_sistema_https.bat
```

### Instalar Certificado nos Clientes

#### Windows

1. Copie `ssl/PARA_CLIENTES/rootCA.pem` para o dispositivo cliente
2. Renomeie para `rootCA.crt`
3. Duplo clique no arquivo
4. Clique em "Instalar Certificado"
5. Selecione "Usuário Atual" ou "Computador Local"
6. Selecione "Colocar todos os certificados no seguinte repositório"
7. Clique em "Procurar" e selecione "Autoridades de Certificação Raiz Confiáveis"
8. Clique em "Concluir"

#### Android

1. Copie `rootCA.pem` para o dispositivo
2. Vá em Configurações → Segurança → Criptografia e credenciais
3. Toque em "Instalar certificado"
4. Selecione "Certificado CA"
5. Selecione o arquivo `rootCA.pem`
6. Confirme a instalação

#### iOS

1. Envie `rootCA.pem` para o dispositivo (por email, AirDrop, etc.)
2. Toque no arquivo
3. Vá em Configurações → Geral → Sobre → Certificados Confiáveis
4. Ative o certificado

### Acessar o Servidor

**No servidor:**
- `https://localhost:5000`
- `https://Gestor-pedidos.local:5000`

**Em outros dispositivos:**
- `https://Gestor-pedidos.local:5000` (após instalar certificado)
- `https://IP_DO_SERVIDOR:5000` (após instalar certificado)

### Troubleshooting HTTPS

**Erro: "Certificado inválido"**
- Certifique-se de que o certificado CA foi instalado no dispositivo
- Verifique se o hostname/IP está nos certificados gerados

**Erro: "Conexão recusada"**
- Verifique se o servidor está rodando em HTTPS
- Verifique se a porta 5000 não está bloqueada pelo firewall

**Certificado não funciona em alguns dispositivos**
- Regere os certificados incluindo todos os IPs
- Use o script `GERAR_CERTIFICADOS_MULTI_IP.bat`

---

## 🔧 Scripts e Ferramentas

### Estrutura de Scripts

```
backend/
├── run/                    # Scripts de uso diário
│   ├── abrir_sistema.bat          # Inicia HTTP + abre navegador
│   ├── abrir_sistema_https.bat    # Inicia HTTPS + abre navegador
│   └── iniciar_servidor_https.bat  # Inicia HTTPS apenas
│
├── ssl/                    # Scripts de certificados SSL
│   ├── INSTALAR_MKCERT.bat        # Instala mkcert
│   ├── GERAR_CERTIFICADOS_AUTO.bat # Gera certificados automático
│   └── DISTRIBUIR_CERTIFICADO.bat # Prepara certificado para clientes
│
├── UtilsScripts/           # Scripts utilitários avançados
│   ├── iniciar_servidor.bat       # Inicia servidor HTTP
│   ├── iniciar_servidor_invisivel.vbs # Inicia servidor invisível
│   ├── parar_servidor.bat          # Para o servidor
│   ├── verificar_porta.bat         # Verifica se porta está em uso
│   └── atualizar_cache_frontend.bat # Atualiza versão do cache
│
├── scripts/                # Scripts de manutenção
│   ├── backup_manual.bat          # Backup manual do banco
│   ├── agendar_backup_windows.bat  # Agenda backup automático
│   └── migrations/                # Scripts de migração do banco
│
└── CONFIGURAR_SERVIDOR.bat # Configurador principal (raiz)
```

### Scripts Principais

#### Uso Diário

**Iniciar Sistema (HTTP):**
```bash
backend\run\abrir_sistema.bat
```
- Inicia servidor HTTP
- Abre navegador automaticamente
- Modo mais simples

**Iniciar Sistema (HTTPS):**
```bash
backend\run\abrir_sistema_https.bat
```
- Inicia servidor HTTPS
- Abre navegador automaticamente
- Recomendado para produção

#### Configuração Inicial

**Configurar Servidor:**
```bash
backend\CONFIGURAR_SERVIDOR.bat
```
- Configurador interativo completo
- Instala mkcert
- Gera certificados
- Configura hostname

#### Manutenção

**Backup Manual:**
```bash
backend\scripts\backup_manual.bat
```
- Cria backup do banco de dados
- Salva em `backend/backups/`

**Agendar Backup:**
```bash
backend\scripts\agendar_backup_windows.bat
```
- Agenda backup automático diário
- Usa Agendador de Tarefas do Windows

**Atualizar Cache:**
```bash
backend\UtilsScripts\atualizar_cache_frontend.bat
```
- Atualiza versão do Service Worker
- Força atualização em todos os dispositivos

#### Utilitários

**Verificar Porta:**
```bash
backend\UtilsScripts\verificar_porta.bat
```
- Verifica se porta 5000 está em uso
- Mostra processo que está usando

**Parar Servidor:**
```bash
backend\UtilsScripts\parar_servidor.bat
```
- Para o servidor Flask
- Fecha processos Python relacionados

---

## 📂 Estrutura do Projeto

```
Gestor de Pedidos Plante uma flor/
├── backend/                          # Backend Flask
│   ├── app/                          # Aplicação principal
│   │   ├── __init__.py              # Factory do Flask
│   │   ├── config.py                # Configurações
│   │   ├── middleware.py            # Middleware de autenticação
│   │   ├── models/                  # Modelos de dados
│   │   │   ├── pedido.py           # Modelo de Pedido
│   │   │   ├── cliente.py          # Modelo de Cliente
│   │   │   ├── endereco_cliente.py  # Modelo de Endereço
│   │   │   └── rota_otimizada.py    # Modelo de Rota
│   │   ├── routes/                  # Rotas da API
│   │   │   ├── api.py              # Endpoints principais
│   │   │   └── clientes.py        # Endpoints de clientes
│   │   ├── services/                # Serviços de negócio
│   │   │   ├── distancia.py        # Cálculo de distâncias
│   │   │   ├── graphhopper.py      # Integração GraphHopper
│   │   │   └── taxa_entrega.py     # Cálculo de taxas
│   │   └── utils/                   # Utilitários
│   ├── config/                      # Arquivos de configuração
│   │   └── taxa_entrega.json       # Configuração de taxas
│   ├── scripts/                     # Scripts de manutenção
│   │   ├── migrations/             # Scripts de migração
│   │   ├── tests/                  # Scripts de teste
│   │   ├── backup.py               # Script de backup
│   │   └── restore.py              # Script de restauração
│   ├── ssl/                         # Certificados SSL
│   │   ├── cert.pem                # Certificado
│   │   ├── key.pem                 # Chave privada
│   │   ├── rootCA.pem             # Certificado CA
│   │   └── PARA_CLIENTES/          # Certificados para distribuição
│   ├── run/                         # Scripts de uso diário
│   ├── UtilsScripts/                # Scripts utilitários
│   ├── backups/                     # Backups do banco
│   ├── logs/                        # Logs do servidor
│   ├── main.py                      # Ponto de entrada
│   ├── requirements.txt             # Dependências Python
│   ├── config_servidor.ini         # Configuração do servidor
│   ├── database.db                  # Banco de dados SQLite
│   └── CONFIGURAR_SERVIDOR.bat      # Configurador principal
│
├── frontend/                        # Frontend PWA
│   ├── assets/                      # Recursos estáticos
│   │   ├── css/                    # Estilos
│   │   │   └── style.css          # CSS principal
│   │   ├── images/                # Imagens
│   │   │   ├── Buques.ico         # Ícone
│   │   │   └── Logo.png           # Logo
│   │   └── js/                    # JavaScript
│   │       ├── app.js             # Aplicação principal
│   │       ├── router.js          # Roteador SPA
│   │       ├── api.js             # Cliente API
│   │       ├── db.js              # IndexedDB
│   │       ├── auth.js            # Autenticação
│   │       ├── form.js            # Formulário de pedido
│   │       ├── painel.js          # Painel administrativo
│   │       └── components/        # Componentes
│   │           ├── modal.js      # Modal
│   │           ├── notification.js # Notificações
│   │           └── pedido-card.js # Card de pedido
│   ├── pages/                      # Páginas SPA
│   │   ├── criar-pedido.html      # Criar pedido
│   │   ├── painel.html            # Painel
│   │   ├── login.html             # Login
│   │   ├── clientes.html          # Clientes
│   │   └── rota-entrega.html       # Rotas
│   ├── index.html                  # Página principal
│   ├── manifest.json               # Manifest PWA
│   └── sw.js                       # Service Worker
│
├── logs/                           # Logs gerais
├── README.md                       # Este arquivo
└── .gitignore                     # Arquivos ignorados pelo Git
```

---

## 🛠️ Desenvolvimento

### Estrutura do Código

#### Backend

**Padrão MVC:**
- **Models**: Definem estrutura de dados (`app/models/`)
- **Views**: Endpoints da API (`app/routes/`)
- **Controllers**: Lógica de negócio (`app/services/`)

**Convenções:**
- Arquivos Python: `snake_case.py`
- Classes: `PascalCase`
- Funções: `snake_case`
- Constantes: `UPPER_CASE`

#### Frontend

**Arquitetura Modular:**
- Módulos ES6 separados por funcionalidade
- Componentes reutilizáveis
- Service Worker para cache
- IndexedDB para armazenamento

**Convenções:**
- Arquivos JS: `kebab-case.js` ou `camelCase.js`
- Classes: `PascalCase`
- Funções: `camelCase`
- Constantes: `UPPER_CASE`

### Adicionar Nova Funcionalidade

#### Backend

1. **Criar Model** (se necessário):
```python
# app/models/nova_entidade.py
class NovaEntidade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # campos...
```

2. **Criar Service** (se necessário):
```python
# app/services/novo_servico.py
class NovoService:
    def metodo(self):
        # lógica...
```

3. **Criar Endpoint**:
```python
# app/routes/api.py
@api_bp.route('/nova-rota', methods=['GET'])
def nova_rota():
    # implementação...
```

#### Frontend

1. **Criar Componente** (se necessário):
```javascript
// assets/js/components/novo-componente.js
class NovoComponente {
    // implementação...
}
```

2. **Adicionar Rota**:
```javascript
// assets/js/router.js
router.addRoute('/nova-rota', () => {
    // renderização...
});
```

3. **Integrar com API**:
```javascript
// assets/js/api.js
async novaFuncao() {
    const response = await fetch('/api/nova-rota');
    return response.json();
}
```

### Testes

Scripts de teste estão em `backend/scripts/tests/`:

```bash
cd backend/scripts/tests
python testar_graphhopper.py
python testar_endereco_problema.py
```

### Debug

**Ativar Debug no Backend:**

Edite `.env`:
```env
DEBUG=True
FLASK_ENV=development
```

**Ativar Endpoints de Debug:**

```env
ENABLE_DEBUG_ENDPOINTS=true
```

Endpoints de debug disponíveis:
- `GET /api/debug/geocode` - Testar geocodificação
- `GET /api/debug/testar-apis` - Testar APIs externas
- `POST /api/debug/limpar-distancias` - Limpar distâncias calculadas

---

## 🔍 Troubleshooting

### Problemas Comuns

#### Servidor não inicia

**Sintoma:** Erro ao executar `python main.py`

**Soluções:**
1. Verifique se Python 3.8+ está instalado: `python --version`
2. Instale dependências: `pip install -r requirements.txt`
3. Verifique se porta 5000 está livre: `backend\UtilsScripts\verificar_porta.bat`
4. Verifique logs em `backend/logs/`

#### Porta 5000 já está em uso

**Sintoma:** "Port 5000 is already in use"

**Soluções:**
1. Pare o servidor anterior: `backend\UtilsScripts\parar_servidor.bat`
2. Ou mate o processo manualmente:
   ```bash
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   ```

#### Certificado SSL inválido

**Sintoma:** Navegador mostra "Certificado inválido"

**Soluções:**
1. Instale o certificado CA no dispositivo
2. Regere os certificados: `backend\ssl\GERAR_CERTIFICADOS_AUTO.bat`
3. Verifique se o hostname/IP está nos certificados

#### PWA não instala

**Sintoma:** Botão de instalação não aparece

**Soluções:**
1. Use HTTPS (PWA só instala em HTTPS ou localhost)
2. Verifique se `manifest.json` está correto
3. Verifique console do navegador para erros
4. Limpe cache: `Ctrl+Shift+Delete`

#### Distâncias não calculam

**Sintoma:** Campo de distância fica vazio

**Soluções:**
1. Verifique se API keys estão configuradas no `.env`
2. Verifique se endereço da floricultura está configurado
3. Verifique logs do servidor para erros
4. Teste manualmente: `GET /api/debug/testar-apis`

#### Taxa de entrega incorreta

**Sintoma:** Taxa calculada não corresponde à configuração

**Soluções:**
1. Verifique `backend/config/taxa_entrega.json`
2. Verifique se JSON está válido (sem erros de sintaxe)
3. Reinicie o servidor após editar o JSON
4. Verifique logs do servidor (modo DEBUG)

#### Dados não sincronizam offline

**Sintoma:** Mudanças offline não aparecem quando online

**Soluções:**
1. Verifique se Service Worker está ativo
2. Limpe cache: `Ctrl+Shift+Delete` → Limpar cache
3. Atualize versão do cache: `backend\UtilsScripts\atualizar_cache_frontend.bat`
4. Verifique console do navegador para erros

### Logs e Diagnóstico

**Logs do Servidor:**
- `backend/logs/access_YYYY-MM-DD.log` - Logs de acesso
- `backend/servidor_https.log` - Logs do servidor HTTPS (se usando VBS)

**Console do Navegador:**
- Pressione `F12` para abrir DevTools
- Aba "Console" mostra erros JavaScript
- Aba "Network" mostra requisições HTTP

**Modo DEBUG:**
Ative no `.env`:
```env
DEBUG=True
```

Isso mostra logs detalhados no console do servidor.

---

## 📝 Changelog

### v3.0.1 (Atual)

**Melhorias:**
- ✅ Sistema de taxas de entrega com faixas específicas (de_km/ate_km)
- ✅ Lógica corrigida para valores entre faixas (usa próxima faixa maior)
- ✅ Cache atualizado (v14) para forçar atualização em todos os dispositivos
- ✅ Organização completa de arquivos e scripts
- ✅ Documentação completa e detalhada

**Organização:**
- 📁 Scripts de migração movidos para `backend/scripts/migrations/`
- 📁 Scripts de teste movidos para `backend/scripts/tests/`
- 📁 Arquivos .bat organizados em pastas apropriadas
- 🗑️ Documentações temporárias removidas do frontend
- 📄 README.md completamente reescrito e expandido

### v3.2

**Melhorias:**
- ✅ Ordenação inteligente de pedidos por proximidade da data
- ✅ Pedidos mais próximos aparecem primeiro no painel
- ✅ Template de impressão otimizado para 1 página única
- ✅ Campos de endereço condicionais (ocultos em "Retirada")
- ✅ Scripts backend organizados em pastas (run/ e UtilsScripts/)
- ✅ UX significativamente melhorada

### v3.1

**Melhorias:**
- ✅ Impressão profissional de pedidos em A4
- ✅ Layout otimizado para logística
- ✅ Destaque visual para informações críticas
- ✅ Suporte completo a HTTPS com mkcert

**Correções:**
- 🐛 Corrigido botão "Finalizar Pedido" no formulário
- 🐛 Melhorada navegação entre steps do formulário
- 🐛 Corrigida sincronização offline

### v3.0

**Inicial:**
- 🎉 Migração completa de Tkinter para PWA
- 🎉 Interface responsiva multiplataforma
- 🎉 Suporte offline com Service Worker
- 🎉 IndexedDB para armazenamento local
- 🎉 REST API completa
- 🎉 Painel com filtros e busca em tempo real

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Siga estes passos:

1. **Fork o projeto**
2. **Crie uma branch**: `git checkout -b feature/nova-funcionalidade`
3. **Commit suas mudanças**: `git commit -m "feat: adiciona nova funcionalidade"`
4. **Push para a branch**: `git push origin feature/nova-funcionalidade`
5. **Abra um Pull Request**

### Padrões de Commit

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Documentação
- `style:` Formatação
- `refactor:` Refatoração
- `test:` Testes
- `chore:` Manutenção

### Padrões de Código

- Siga as convenções de nomenclatura
- Adicione comentários em código complexo
- Mantenha funções pequenas e focadas
- Teste suas mudanças antes de commitar

---

## 📄 Licença

MIT License - veja LICENSE para detalhes.

---

## 💬 Suporte

- **Documentação**: Este README e arquivos em `docs/`
- **Issues**: Abra uma issue no repositório
- **Email**: suporte@example.com

---

## 🙏 Agradecimentos

Projeto desenvolvido para modernizar o sistema de gestão de pedidos, substituindo aplicação desktop Tkinter por PWA multiplataforma.

**Tecnologias e Recursos:**
- Flask Framework
- Tailwind CSS
- PWA best practices
- mkcert para HTTPS local
- GraphHopper e OpenRouteService para rotas

---

**Plante Uma Flor** © 2024 - Sistema de Gestão de Pedidos PWA  
Desenvolvido com ❤️ para floricultura
