# Plano UI/UX — Complemento à Auditoria de Frontend

**Data:** 24 de julho de 2026
**Documento companion:** [auditoria-frontend-2026-07-24.md](auditoria-frontend-2026-07-24.md)
**Método:** validação item a item da auditoria contra o código-fonte, seguida de plano de UI mobile, refinamento visual, dark mode e reorganização de navegação.
**Status:** planejamento aprovado — implementação não iniciada.

---

## 1. Validação da auditoria

Resultado geral: **12 dos 14 itens estão corretos**. Há 1 imprecisão técnica, nuances que mudam a implementação de alguns itens, e 5 achados novos que a auditoria não viu.

### 1.1 Itens confirmados (com nuances)

| # | Item da auditoria | Status | Nuance encontrada no código |
|---|---|---|---|
| 1 | Card não abre pedido | ✅ Correto — e mais fácil do que parece | A rota `/pedidos/:id` **já existe** (`frontend/src/app/router.tsx:118` → `OrderDetailsPage`). O fix é navegar no handler vazio (`OrdersPage.tsx:108-111`). As variantes Kanban (`compact`) e entregador (`operacional`) **já navegam no clique** — só a lista principal está quebrada. Hoje o usuário chega aos detalhes pelo menu ⋮ → "Ver" (`OrderCard.tsx:218-221`). |
| 2 | Navegação inconsistente | ✅ Correto | Botões MUI confirmados (`AppShell.tsx:324-346`). **Mas:** Clientes não está totalmente órfão — está escondido em *Configurações → aba Clientes* (`SettingsPage.tsx:166`); idem Funcionários (`:168`) e Fontes (`:165`). No desktop, Configurações só é acessível pelo menu do avatar (`AppShell.tsx:460-466`). |
| 3 | Filtros fora da URL | ✅ Correto | Pedidos (`OrdersPage.tsx:54-63`) e Vendas (`SalesPage.tsx:26-38`) são `useState`. **Leads usa `localStorage`** (`LeadsPage.tsx:336`, chave `leads:filters:v1`) — a auditoria não mencionou; o fix precisa reconciliar URL ↔ localStorage (URL vira fonte da verdade). |
| 4 | Vendas longa no mobile | ✅ Correto — e pior | **Não existe paginação nenhuma** (`SalesTable.tsx:75` renderiza tudo). Também não há variante mobile: tabela única sempre. |
| 5 | Lacunas de acessibilidade | ✅ Correto | Confirmados: `Paper onClick` sem teclado (`OrderList.tsx:90`), logo `role="button"` sem suporte (`AppShell.tsx:261-273`), h5 sem h1 em Leads (`LeadsPage.tsx:942`) e Ledger (`LedgerPage.tsx:132`). **Correção fina:** 3 dos 7 icon buttons de Leads **têm** aria-label; faltam 4 (WhatsApp, Ver pedido, Ver desabilitado, Criar pedido — `LeadActions.tsx:65,145,152,159`). Pedidos (`OrdersPage.tsx:315`) e Vendas (`SalesPage.tsx:169`) **têm** h1 correto. |
| 6 | Pedidos pesada no topo | ✅ Correto | Inventário bate: header + toggle lista/quadro + 4 ações + 6 KPIs + busca + date filters + status tabs. |
| 7 | Cores dos KPIs de Vendas | ✅ Correto | 6 cores decorativas hardcoded (`SalesKPIGrid.tsx:46-88`); vermelho para qualquer negativo (`:118-120`). |
| 8 | Leads cortado no mobile | ✅ Correto | O "sempre em linha" é **intencional** — comentário explícito em `SituacaoSegmented.tsx:37-39`. |
| 9 | Ledger estreito | ✅ Correto | `maxWidth: 800` (`LedgerPage.tsx:123`). |
| 10 | Rotas OK no mobile | ✅ Correto | Sem ação urgente; melhorias de desktop são opcionais. |
| 11 | Warnings Recharts | ✅ Plausível | Padrão atual: `Box` altura fixa + `ResponsiveContainer 100%×100%`. O `-1` vem da montagem antes do layout. Recomendação (`min-width: 0` nos Grids) é a correta. |
| 13 | Reduced-motion | ✅ Correto — e menor do que parece | animate.css é importado globalmente (`main.tsx:3`) mas só **2 componentes** usam: `LoginPage` (4 classes) e `StatsCard` (via `useAnimateOnMount`). O stagger dos KPIs acumula **600ms** (6 × 100ms). |
| 14 | Reticências | ✅ Correto | Cosmético, barato. |

### 1.2 Item impreciso

**Item 12 — Google Maps Marker.** A auditoria sugere uso direto de `google.maps.Marker` em `RoutePage.tsx:427` e recomenda migrar para `AdvancedMarkerElement`. **Na verdade** o código usa o componente `<Marker>` da lib `@react-google-maps/api@2.20.8` — o aviso de deprecação vem de dentro da lib. Essa lib **não exporta** um componente `AdvancedMarker` oficial; a migração exige wrapper customizado (ou aguardar suporte upstream). Prioridade "baixa" está certa, mas a implementação é diferente e mais trabalhosa do que o sugerido.

### 1.3 Achados novos (não estavam na auditoria)

1. **`App.css` residual do template Vite está ATIVO** — `App.tsx:4` importa o CSS boilerplate que aplica `#root { max-width: 1280px; margin: 0 auto; padding: 2rem; text-align: center }` em toda a app, além de keyframes `logo-spin`. Suspeito nº 1 como causa-raiz de parte dos vazamentos horizontais. Verificar e remover é quick win.
2. **Área "Equipe" já existe embrionária** — Configurações tem abas MUI (`Tabs scrollable`, `SettingsPage.tsx:141-158`) com Funcionários (`UserListPage`), Clientes, Fontes, Integrações. A área Equipe é **promoção de código existente**, não criação do zero.
3. **Tabela de usuários não é responsiva** — `UserListPage.tsx:249-297` usa `<Table>` sempre, sem variante mobile.
4. **Código morto** — `KPICard.tsx` (zero usos), `useAnimate()` (zero consumidores), `elevation: 4` inválido dentro de `sx` (`OrderList.tsx:102`).
5. **Não existe bottom navigation** — mobile hoje é hamburger (2 toques p/ navegar) + FAB (só na página de Pedidos, `AppShell.tsx:494-556`). Para um app operacional usado o dia inteiro no celular (entregador), é o maior gap de UI mobile.

---

## 2. Plano de UI Mobile

### 2.1 Bottom navigation por role

Hoje: hamburger + FAB. Proposta: barra inferior fixa com destinos por role (reaproveita lógica de roles de `AppShell.tsx:85-96`):

- **Admin/vendedor:** `Pedidos · Clientes · Vendas · Rota · Mais` (Mais → Leads, Equipe, Configurações)
- **Entregador:** `Entregas · Recebíveis · Pedidos · Perfil`
- **FAB "Novo Pedido":** manter elevado acima da barra (padrão Material) ou integrar como botão central.

### 2.2 Padrão de card mobile (mini design system)

Extrair um padrão único a partir dos dois bons exemplos internos existentes:

- `LeadsPage.tsx:1175` (`renderCard` inline): card com status, info primária, long-press p/ seleção
- `EntregadorTodayView.tsx`: hero com total + agrupamento por dia + CTA full-width

**Padrão alvo:** título + chip de status + 1-2 infos primárias + 1 ação primária + menu ⋮ p/ secundárias.

Aplicar em:

- **Vendas** (novo — resolve item 4 da auditoria)
- **Equipe → Funcionários** (`UserListPage`, hoje tabela fixa)
- **Clientes** (verificar variante mobile de `CustomersTable` — usa `down('md')`)

### 2.3 Ajustes por página

- **Vendas:** cards no mobile (`down('sm')`, mesmo breakpoint de Leads) · período como faixa de chips rolável · **paginação 25 (criar — hoje inexistente)** · ordem: KPIs compactos → gráfico principal → lista → gráficos secundários em accordion.
- **Leads:** `SituacaoSegmented` → `Select` compacto no mobile · ações secundárias no menu ⋮ · info de campanha em accordion (padrão já usado nos descartados, `LeadsPage.tsx:1399-1424`).
- **Pedidos:** KPIs viram **chips compactos roláveis horizontalmente que também são filtros** — resolve item 6 (topo pesado) + "KPIs clicáveis" (Fase 2) de uma vez · header sticky compacto após scroll.
- **Vazamentos horizontais:** corrigir as fontes (App.css residual, tabelas sem scroll container, segmented controls) e **só então** remover o `overflow-x: hidden` global (`index.css:152-155`).

### 2.4 Motion e toque

- `prefers-reduced-motion` global em `index.css` (hoje só `wizardNovo.css:246` respeita).
- Trocar `transition: all` (`OrderList.tsx:99`) por propriedades específicas; cortar stagger dos KPIs para ≤200ms total.
- Touch targets 44px já existem (`index.css:94-99, 126-143`) — manter.

---

## 3. Refinamento visual + Dark mode

### 3.1 Refinamento (identidade mantida)

- Extrair tema de `providers.tsx` para `app/theme.ts` com tokens semânticos; `BRAND` (hoje local em `AppShell.tsx:44-56`) vira `palette`.
- KPIs: valores em cor neutra; verde/vermelho/âmbar só com significado semântico; comparação de período parcial exibe "até DD/MM" e compara dias equivalentes.
- Fraunces para display de página (hoje limitada a h4/h5, `providers.tsx:44-45`); garantir h1 único por página.
- Textos de loading com reticência tipográfica (`…`), centralizados em componentes comuns.

### 3.2 Dark mode — estratégia

**O código está bem preparado:** tema MUI único e centralizado (`providers.tsx:30-83`), `CssBaseline` presente (`:93`), páginas já usam tokens `background.*`, e há só **~78 hex hardcoded em 17 arquivos** — 6 arquivos concentram 60+ ocorrências:

1. `OrdersKPIGrid.tsx` (12)
2. `RoutePage.tsx` (12)
3. `SalesKPIGrid.tsx` (8)
4. `AppShell.tsx` / `BRAND` (7)
5. `SalesChannelDonut.tsx` (6)
6. `IntegrationCard.tsx` (5)

**Passos (MUI v7 nativo, sem libs):**

1. `theme.ts` com `colorSchemes: { light, dark }` + `cssVariables: true`.
2. Migrar `BRAND` e os 6 arquivos-foco para tokens do tema.
3. Recharts: cores de série via tema; Google Maps: `styles` dark no `GoogleMap`.
4. Toggle no menu do avatar + `prefers-color-scheme` como default + persistência em localStorage.
5. `<meta name="theme-color">` dinâmico (hoje fixo `#143d28` em `index.html:7`).
6. CSS vars de `index.css` espelhadas para `[data-theme="dark"]` ou substituídas pelas vars do MUI.

**Risco principal:** cores de status (chips de pedido) precisam de contraste nos dois modos — definir variantes light/dark por status no tema, não por arquivo.

---

## 4. Área Equipe com abas

- Nova rota `/equipe` com abas (mesmo padrão `Tabs scrollable` de Configurações):
  - **Funcionários** — `UserListPage` (movido de Configurações)
  - **Recebíveis** — `LedgerPage`
  - **Comissões** — verificar o que já tem UI (backend `users_bp` tem payroll + comissão)
  - **Pagamento** — config de payroll
- Nav principal vira: `Pedidos · Clientes · Vendas · Leads · Rotas · Equipe` — como **links reais** (`NavLink`), não botões.
- `/recebiveis` → redirect para `/equipe?tab=recebiveis` (compatibilidade).
- Entregador mantém item próprio "Recebíveis" na nav → `EntregadorTodayView` (não vê Equipe).
- Remover abas Funcionários e Clientes de Configurações (evita duplicidade — Clientes vai para a nav principal).

---

## 5. Estado na URL (Fase 2 da auditoria)

- **Pedidos:** `status`, `search`, `page`, `view` (lista/quadro) → `useSearchParams`.
- **Vendas:** `inicio`, `fim`, comparar → `useSearchParams`.
- **Leads:** URL vira fonte da verdade; `localStorage` (`leads:filters:v1`) vira fallback inicial.
- Reset para página 1 sempre que um filtro mudar.
- KPIs de Pedidos clicáveis aplicando o filtro correspondente (ver 2.3).

---

## 6. Ordem de execução

| Bloco | Conteúdo | Esforço | Depende de |
|---|---|---|---|
| **0 — Quick wins** | Card clicável (navegar p/ `/pedidos/:id`) · remover App.css residual + código morto (KPICard, useAnimate, elevation inválido) · aria-labels (4 botões) · h1 em Leads/Ledger · teclado nos headers de grupo | P (½–1 dia) | — |
| **1 — Navegação** | Links reais (`NavLink`) · Clientes na nav · área Equipe com abas · redirect `/recebiveis` | M (1–2 dias) | — |
| **2 — URL state** | Pedidos, Vendas, Leads (+ reconciliar localStorage) | M (1–2 dias) | — |
| **3 — Mobile** | Bottom nav · cards Vendas/Equipe · KPI-chips de Pedidos · Leads compacto · correção de vazamentos + remover overflow-x global | G (3–5 dias) | 1 |
| **4 — Refino visual** | theme.ts · KPIs semânticos · tipografia · textos/reticências | M (1–2 dias) | — |
| **5 — Dark mode** | colorSchemes + migração dos 6 arquivos + mapas/gráficos + toggle | M–G (2–3 dias) | 4 |
| **6 — Técnico** | Recharts -1 · wrapper AdvancedMarker · reduced-motion global | P–M (1 dia) | — |

Blocos 0, 1, 2 e 4 são independentes entre si. 3 depende de 1 (bottom nav). 5 depende de 4 (theme.ts).

---

## 7. Notas

- **AGENTS.md desatualizado:** diz que auth usa Zustand, mas `zustand` não está no `package.json` — o auth é um `AuthProvider` custom (`src/features/auth/authStore`). Corrigir o doc na primeira implementação.
- Versões relevantes: MUI `^7.3.6`, React `^19.2.0`, react-router-dom `^7.11.0`, recharts `^3.6.0`, `@react-google-maps/api` `^2.20.8`, animate.css `^4.1.1`.
- Fontes (Jost/Fraunces) via Google Fonts em `index.html:10-12`; Inter é só fallback de stack, não é carregada.
