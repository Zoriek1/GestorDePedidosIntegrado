<div align="center">

# 🌷 Plante uma Flor · Gestor de Pedidos

**Sistema full-stack de gestão operacional para floricultura.**
Pedidos, entregas, recebíveis e atribuição de marketing em uma única plataforma, com PWA offline-first.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3-000000?style=flat-square&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-offline--first-5A0FC8?style=flat-square&logo=pwa&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

<img src="docs/screenshots/dashboard.png" alt="Dashboard do Gestor de Pedidos" width="720">

</div>

---

## O que é

Uma floricultura recebe pedidos de vários canais (loja, e-commerce, WhatsApp), precisa rotear entregas, pagar comissões de vendedores e devolver conversões para as plataformas de anúncio. Este sistema centraliza esse fluxo de ponta a ponta: do clique no anúncio até a quitação da comissão do entregador.

Construído como aplicação real em produção, não como projeto de demonstração.

---

## 🔧 Destaques técnicos

| Recurso | Por que importa |
|---|---|
| **Razão contábil double-entry** | Comissões, créditos e quitações registrados como lançamentos de débito/crédito. Saldo sempre consistente e auditável, sem números soltos no banco. |
| **Worker assíncrono com padrão outbox** | Eventos do Meta CAPI gravados em fila no Postgres e processados por um worker dedicado. Nenhuma conversão é perdida se a API da Meta cair. |
| **Atribuição cookie → CAPI com deduplicação** | Mesmo `event_id` no Pixel (browser) e no servidor: recupera conversões bloqueadas por adblock sem contar em dobro. |
| **PWA offline-first** | Funciona sem internet usando Dexie (IndexedDB) + Service Worker. O entregador opera na rua mesmo sem sinal, com sincronização ao reconectar. |
| **Webhooks Nuvemshop** | Pedidos do e-commerce entram automaticamente via webhook, sem digitação manual. |
| **RBAC com JWT** | Três papéis (admin, vendedor, entregador), cada um vendo apenas o que lhe cabe. |
| **Otimização de rotas + geocoding** | Cálculo de distância, taxa por pedido e ordenação de paradas via Google Maps. |
| **Push notifications (VAPID)** | Notificações nativas no celular do entregador a cada novo pedido. |

---

## 🧱 Arquitetura

```
                         ┌──────────────────────────┐
   Anúncios / E-commerce │   Nuvemshop  ·  UTMify    │
        WhatsApp / Loja  └────────────┬─────────────┘
                                      │ webhook / API
                          ┌───────────▼───────────┐
                          │     Flask 3 (API)      │
                          │  SQLAlchemy 2 · JWT    │
                          └───┬───────────────┬────┘
                              │               │
                   ┌──────────▼───┐    ┌──────▼─────────┐
                   │ PostgreSQL 16│    │  Outbox Worker │──► Meta CAPI
                   │  + Ledger    │    │ (envio async)  │──► Google
                   └──────────────┘    └────────────────┘
                              ▲
                              │ REST
                   ┌──────────┴───────────┐
                   │  React 19 · TS · Vite│
                   │  MUI · React Query   │
                   │  Dexie (PWA offline) │
                   └──────────────────────┘
```

Decisões centrais: separação clara entre API (Flask) e SPA (React); integrações processadas fora do ciclo de request via worker; estado de UI no React Query e estado offline no Dexie.

---

## 🎯 Fluxo de atribuição (cookie → painel de leads → conversão)

Coração do lado de marketing. Mostra como um clique vira lead rastreável e, no fim, uma conversão devolvida às plataformas de anúncio com alta qualidade de correspondência.

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. ENTRADA                                                         │
│    Clique no anúncio (Meta / Google)                               │
│            │                                                       │
│            ▼                                                       │
│    Landing Page / E-commerce                                       │
│            │                                                       │
│      Pixel dispara no browser ──► grava cookies 1st-party:         │
│            │                       _fbp      ID do browser         │
│            │                       _fbc      derivado do fbclid    │
│            │                       event_id  UUID para dedup       │
│            ▼                                                       │
│    Captura da URL: utm_source · utm_medium · utm_campaign          │
│                    fbclid · gclid                                  │
└────────────┬───────────────────────────────────────────────────── ┘
             │  formulário · token WhatsApp · webhook e-commerce
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. PAINEL DE LEADS   (Flask + Postgres)                            │
│    Lead criado com snapshot de atribuição:                         │
│    { fbp, fbc, event_id, utm_*, origem }                           │
│            │                                                       │
│            ▼  percorre a máquina de estados (abaixo)               │
└────────────┬───────────────────────────────────────────────────── ┘
             │  evento de transição de estado
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. SAÍDA   (Outbox Worker assíncrono)                              │
│    Enfileira o evento e envia para Meta CAPI / Google:             │
│      Lead       quando o lead é criado                             │
│      Purchase   quando o lead vira pedido (GANHO)                  │
│    Reusa o event_id do Pixel  ──►  deduplicação na Meta            │
└──────────────────────────────────────────────────────────────────┘
```

### Entrada: o que é capturado

| Identificador | Origem | Uso |
|---|---|---|
| `_fbp` | Pixel grava no browser | Match de usuário no CAPI (eleva o EMQ) |
| `_fbc` | Derivado do `fbclid` da URL | Liga a conversão ao clique exato do anúncio |
| `fbclid` / `gclid` | Query string do anúncio | Atribuição Meta / Google |
| `utm_*` | Query string | Origem, mídia e campanha |
| `event_id` | UUID gerado no browser | Chave de deduplicação browser ↔ servidor |

### Painel de leads: máquina de estados (7 situações)

```
        ┌──────────┐
        │   NOVO   │   lead capturado, sem atendimento
        └────┬─────┘
             ▼
     ┌────────────────┐
     │ EM_ATENDIMENTO │   vendedor em contato
     └───┬────────┬───┘
         ▼        ▼
  ┌───────────┐ ┌────────────┐
  │ ORÇAMENTO │ │ DESCARTADO │   spam / inválido
  └─────┬─────┘ └────────────┘
        ▼
  ┌────────────┐
  │ AGUARDANDO │   proposta enviada, aguardando decisão
  └──┬──────┬──┘
     ▼      ▼
 ┌───────┐ ┌─────────┐
 │ GANHO │ │ PERDIDO │
 └───┬───┘ └─────────┘
     │
     ▼  dispara Purchase no CAPI (reusa o event_id do lead)
```

> Os 7 grupos do funil são configuráveis no módulo de Leads. O diagrama acima mostra um fluxo representativo e os pontos onde os eventos de saída são disparados.

### Saída: conversões server-side com deduplicação

- **Deduplicação:** o Pixel envia o evento pelo navegador e o worker envia o mesmo evento (mesmo `event_id`) pelo servidor. A Meta descarta a duplicata e mantém a de maior qualidade. Isso recupera conversões perdidas por adblock ou bloqueio de cookie sem contar duas vezes.
- **Match quality:** `_fbp` e `_fbc` viajam no payload do CAPI e elevam o EMQ (Event Match Quality), melhorando a atribuição e o aprendizado das campanhas.
- **Entrega garantida:** o outbox persiste o evento antes de enviar. Se a API falhar, o evento fica na fila e é reprocessado com backoff. A idempotência pelo `event_id` evita reenvio contado em dobro.

---

## 🛠️ Stack

| Camada | Tecnologias |
|---|---|
| **Backend** | Flask 3 · SQLAlchemy 2 · PostgreSQL 16 · JWT |
| **Frontend** | React 19 · TypeScript · Vite · MUI · React Query · Dexie |
| **Infra** | Docker Compose · Waitress · Cloudflare Tunnel |
| **Integrações** | Meta CAPI · Nuvemshop · UTMify · Google (Sheets, Drive, Maps) |

---

## 🚀 Início rápido

### Desenvolvimento (Docker com hot-reload)

```bash
git clone git@github.com:Zoriek1/GestorDePedidosIntegrado.git
cd GestorDePedidosIntegrado
docker compose -f docker-compose.dev.yml up
```

App em **http://localhost:5173** (o Vite faz proxy de `/api` para o backend). Editou `backend/` ou `frontend/`? Recarrega sozinho.

Criar o primeiro admin:

```bash
docker compose -f docker-compose.dev.yml exec backend flask create-admin
```

### Produção

```bash
cp .env.example .env      # preencher segredos reais (NUNCA commitar)
docker compose up -d
docker compose exec backend flask create-admin
```

App em **http://localhost:5000**.

---

## ✨ Funcionalidades

### 📦 Pedidos e wizard de criação
Wizard guiado em 4 etapas (cliente, arranjo, entrega, pagamento) e edição em página única. Lista com filtros, paginação e impressão de comprovantes em lote (até 100, com 1, 2 ou 4 por folha).

<div align="center"><img src="docs/screenshots/pedidos-wizard.png" alt="Wizard de novo pedido" width="640"></div>

### 🛵 Entregas e rotas
Mapa do entregador, otimização de rota, cálculo de distância e taxa por pedido, acompanhamento de status em kanban.

<div align="center"><img src="docs/screenshots/entregas-rota.png" alt="Mapa e rota do entregador" width="640"></div>

### 🎯 Leads
Funil por situação (7 grupos), follow-up e exportação para planilha. Cada lead guarda o snapshot de atribuição descrito na seção de fluxo acima.

<div align="center"><img src="docs/screenshots/leads-funil.png" alt="Funil de leads" width="640"></div>

### 💰 Recebíveis (ledger)
Razão double-entry: comissões por venda, créditos semanais (fixo, almoço, transporte) e quitação. Admin vê tudo, vendedor vê o próprio, entregador vê "Recebíveis Hoje".

<div align="center"><img src="docs/screenshots/recebiveis.png" alt="Recebíveis" width="640"></div>

### 🔌 Integrações
Meta CAPI (eventos via outbox assíncrono), Nuvemshop (pedidos via webhook), UTMify (atribuição) e Google (Sheets para export, Drive para backup, Maps para geocoding e rotas).

<div align="center"><img src="docs/screenshots/integracoes.png" alt="Integrações" width="640"></div>

### 📱 PWA offline
Instalável, funciona offline com Dexie + Service Worker e envia push notifications (VAPID).

> 📷 **Como adicionar as fotos:** salve os prints em `docs/screenshots/` com os nomes acima (`dashboard.png`, `pedidos-wizard.png`, etc.). As imagens aparecem aqui automaticamente.

---

## 🗂️ Estrutura

```
backend/     Flask app (app/), tests/, scripts/ (migrations, backup, export, meta)
frontend/    React 19 (src/features/ feature-based, app/router.tsx)
docs/        Documentação + screenshots/
deploy/      Exemplos Caddy / Nginx / systemd
docker/      Stage do build (prebuilt-dist)
```

---

## 📚 Documentação

| Arquivo | Conteúdo |
|---|---|
| [AGENTS.md](AGENTS.md) | Referência de arquitetura e convenções (devs e agentes IA) |
| [docs/structure.md](docs/structure.md) | Arquitetura e onde colocar coisas novas |
| [docs/database.md](docs/database.md) | Postgres, models, money handling, migrations |
| [docs/deploy.md](docs/deploy.md) | Docker Compose, VPS, Cloudflare Tunnel |
| [docs/recebiveis.md](docs/recebiveis.md) | Ledger, comissões, créditos, quitação |
| [docs/integrations.md](docs/integrations.md) | Meta CAPI, Nuvemshop, UTMify, Google, Push |

---

## ⚙️ Comandos úteis

```bash
# Testes e lint (dev)
docker compose -f docker-compose.dev.yml exec backend pytest
docker compose -f docker-compose.dev.yml exec backend ruff check . --fix
docker compose -f docker-compose.dev.yml exec backend black .

# Frontend
cd frontend && npm run build && npm run lint
```

---

## 📄 Licença

MIT.
