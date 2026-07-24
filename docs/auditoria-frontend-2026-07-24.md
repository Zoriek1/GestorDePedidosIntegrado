# Auditoria de Frontend — Gestor de Pedidos

**Data:** 24 de julho de 2026  
**Ambiente avaliado:** [gestaopedidos.planteumaflor.online](https://gestaopedidos.planteumaflor.online/)  
**Escopo:** interface publicada em desktop e mobile, experiência de uso, responsividade, acessibilidade e revisão do código-fonte.

## Resumo executivo

A base visual do aplicativo é boa. A identidade da Plante Uma Flor está consistente, o login é bem resolvido, as áreas de toque têm dimensões adequadas e diferentes componentes já possuem tratamentos específicos para celular.

Os maiores ganhos agora estão em:

1. Corrigir interações que parecem disponíveis, mas não respondem.
2. Reorganizar a navegação e os nomes das áreas.
3. Manter filtros e visualizações na URL.
4. Reduzir a densidade e o comprimento das telas no celular.
5. Corrigir lacunas de acessibilidade.
6. Refinar a hierarquia visual e o significado das cores.

## Prioridade alta

### 1. O cartão do pedido parece clicável, mas não abre o pedido

O problema foi confirmado no aplicativo publicado: ao clicar no título de um pedido, a página permanece no painel.

O callback ainda contém um `TODO` sem implementação:

- `frontend/src/features/pedidos/OrdersPage.tsx:108`

Mesmo assim, ele é passado para todos os cartões:

- `frontend/src/features/pedidos/OrdersPage.tsx:675`

**Recomendação**

- Fazer o cartão navegar para `/pedidos/:id`.
- Preferencialmente, renderizar a área clicável como um link real.
- Garantir acesso por teclado e foco visível.
- Manter os botões internos do cartão independentes da navegação principal.

### 2. A arquitetura de navegação tem inconsistências

Foram identificados três pontos principais:

- O item **Funcionários** abre uma página chamada **Recebíveis**:
  - `frontend/src/layout/AppShell.tsx:89`
- Existe uma página de Clientes, mas ela não está disponível na navegação principal:
  - `frontend/src/app/router.tsx:83`
- Os itens principais de navegação são botões, não links:
  - `frontend/src/layout/AppShell.tsx:324`

O uso de botões impede comportamentos naturais da web, como:

- Abrir em nova aba.
- Usar Ctrl+clique.
- Copiar o endereço do destino.
- Visualizar o destino no navegador.

**Recomendação**

Organizar a navegação principal como:

`Pedidos · Clientes · Vendas · Leads · Rotas · Financeiro`

Usar links reais do React Router para os destinos.

Se “Funcionários” precisar continuar como uma área principal, criar uma tela de equipe com abas como:

- Funcionários
- Recebíveis
- Comissões
- Configurações de pagamento

### 3. Filtros e visualizações não ficam registrados na URL

Busca, status, período, paginação e modo de visualização são mantidos apenas no estado interno dos componentes.

Arquivos relevantes:

- `frontend/src/features/pedidos/OrdersPage.tsx:54`
- `frontend/src/features/sales/SalesPage.tsx:26`
- `frontend/src/features/leads/LeadsPage.tsx:336`

Com isso, o usuário perde o contexto quando:

- Atualiza a página.
- Usa o botão voltar.
- Compartilha um endereço.
- Abre a mesma análise em outra aba.

**Recomendação**

Representar o estado nos parâmetros da URL, por exemplo:

```text
/?status=agendado&periodo=hoje&view=lista
/vendas?inicio=2026-07-01&fim=2026-07-24
/leads?periodo=14d&status=lead_pendente&page=2
```

Também é importante retornar para a primeira página sempre que um filtro for alterado.

### 4. A página de Vendas fica excessivamente longa no celular

No teste com viewport de 390 × 844 px:

- A página chegou a aproximadamente 10.000 px de altura.
- Os botões de período ocuparam uma grande área antes dos indicadores.
- A tabela possuía cerca de 731 px de largura.
- Todas as vendas do período foram renderizadas de uma vez.

A renderização da lista está em:

- `frontend/src/features/sales/components/SalesTable.tsx:75`

**Recomendação**

- Usar um seletor de período compacto ou uma faixa horizontal rolável.
- Exibir as vendas como cartões no celular.
- Oferecer paginação com 25 itens por padrão.
- Considerar virtualização para períodos muito grandes.
- Permitir esconder ou expandir a lista detalhada.
- Manter os indicadores e gráficos mais importantes antes dos controles secundários.

### 5. Existem lacunas importantes de acessibilidade

#### Elementos clicáveis sem teclado

O cabeçalho de cada grupo de pedidos é um `Paper` com `onClick`, mas não é um botão e não possui tratamento de teclado:

- `frontend/src/features/pedidos/components/OrderList.tsx:90`

#### Logo implementado como botão genérico

O logo usa `role="button"`, mas não possui comportamento equivalente para Enter e Espaço:

- `frontend/src/layout/AppShell.tsx:262`

#### Botões de ícone sem nome acessível

Há botões de ícone em Leads que dependem apenas de tooltip:

- `frontend/src/features/leads/components/LeadActions.tsx:65`

#### Hierarquia incorreta de títulos

Algumas páginas começam diretamente em `h5`, sem um `h1`:

- `frontend/src/features/leads/LeadsPage.tsx:942`
- `frontend/src/features/ledger/LedgerPage.tsx:132`

#### Conteúdo horizontal escondido

O CSS global usa `overflow-x: hidden`, o que pode mascarar controles que ultrapassam a tela:

- `frontend/src/index.css:151`

**Recomendação**

- Usar elementos HTML semânticos.
- Adicionar um link “Pular para o conteúdo”.
- Garantir um único `h1` por página.
- Adicionar `aria-label` em todos os botões de ícone.
- Fazer cartões e cabeçalhos responderem a teclado.
- Corrigir a origem dos vazamentos horizontais em vez de escondê-los globalmente.
- Testar os fluxos principais apenas com teclado.

Referência utilizada: [Vercel Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines).

## Melhorias de experiência visual

### 6. A tela de Pedidos está pesada no topo

Antes do primeiro pedido aparecem:

- Título e subtítulo.
- Alternância entre lista e quadro.
- Ações de rota e impressão.
- Exportação.
- Ocultação de concluídos.
- Atualização.
- Seis indicadores.
- Campo de busca.
- Filtros rápidos de data.
- Filtros de status.

Isso reduz a área útil para a tarefa principal: acompanhar e movimentar pedidos.

**Recomendação**

- Transformar os KPIs em uma faixa mais compacta.
- Tornar cada KPI clicável para aplicar o filtro correspondente.
- Destacar uma única ação primária.
- Colocar exportação e impressão dentro de um menu secundário.
- Considerar um cabeçalho fixo e compacto depois da rolagem.
- Deixar “Novo Pedido” visível, além do botão flutuante.

### 7. As cores dos KPIs de Vendas confundem significado com decoração

Cada indicador usa uma cor diferente:

- `frontend/src/features/sales/components/SalesKPIGrid.tsx:103`

Além disso, qualquer diferença negativa é apresentada em vermelho, mesmo quando o período atual ainda está incompleto.

**Recomendação**

- Usar valores principais em cor neutra.
- Reservar verde, vermelho e amarelo para significado semântico.
- Comparar mês parcial com a mesma quantidade de dias do período anterior.
- Exibir claramente “até 24/07”, quando aplicável.
- Separar valor realizado, projeção e meta.
- Não tratar automaticamente toda queda como problema.

### 8. Os controles de Leads ficam cortados no celular

Durante o teste, opções como **Personalizado** e **Sem resposta** apareceram truncadas.

O controle de situação força todos os segmentos na mesma linha:

- `frontend/src/features/leads/components/SituacaoSegmented.tsx:37`

A página também apresentou mais de 100 botões visíveis para o conjunto carregado.

**Recomendação**

- Substituir o controle segmentado por um menu compacto no celular.
- Mostrar apenas a ação principal no cartão.
- Colocar as ações secundárias em um menu.
- Usar uma faixa horizontal rolável para períodos ou um seletor.
- Manter telefone, idade e status como informações prioritárias.
- Recolher informações de campanha em uma seção expansível.

### 9. A página de Recebíveis está estreita no desktop

O conteúdo é limitado a 800 px:

- `frontend/src/features/ledger/LedgerPage.tsx:123`

Isso gera bastante espaço vazio nas laterais e comprime controles que poderiam aproveitar melhor telas grandes.

**Recomendação**

- Usar uma largura entre 1.000 e 1.200 px no desktop.
- Separar resumo, lançamentos e histórico em colunas ou abas.
- Manter a largura estreita apenas para formulários e diálogos.

### 10. A página de Rotas está bem adaptada ao celular, mas pode melhorar no desktop

O comportamento mobile é positivo:

- O mapa fica fechado inicialmente.
- Há um botão explícito para exibi-lo.
- A lista de entregas permanece prioritária.

No desktop, mapa e lista funcionam bem, mas o cartão da entrega trunca bastante o endereço.

**Recomendação**

- Permitir redimensionar a área do mapa e da lista.
- Exibir o endereço completo em tooltip ou expansão.
- Diferenciar visualmente origem, destino e sequência.
- Manter ações de otimização desabilitadas com explicação visível do motivo.

## Qualidade técnica e polimento

### 11. Os gráficos geram avisos de dimensão

O navegador registrou avisos do Recharts informando largura e altura `-1` durante a montagem.

Arquivos relacionados:

- `frontend/src/features/sales/components/SalesChart.tsx`
- `frontend/src/features/sales/components/SalesChannelDonut.tsx`
- `frontend/src/features/sales/components/SalesByHourChart.tsx`

**Recomendação**

- Garantir `min-width: 0` nos itens de Grid e seus pais.
- Renderizar o gráfico somente quando o contêiner possuir dimensões válidas.
- Verificar o comportamento durante mudanças de breakpoint.

### 12. O mapa usa uma API de marcador descontinuada

O navegador registrou aviso sobre `google.maps.Marker`.

Uso atual:

- `frontend/src/features/rotas/RoutePage.tsx:427`

**Recomendação**

Planejar a migração para `google.maps.marker.AdvancedMarkerElement`.

Não é uma quebra imediata, mas evita depender de uma API que receberá menos manutenção.

### 13. Animações precisam respeitar movimento reduzido

Foram encontrados:

- Uso de `animate.css`.
- `transition: all`.
- Animações encadeadas nos cartões de indicadores.

Exemplos:

- `frontend/src/features/auth/LoginPage.tsx:365`
- `frontend/src/features/pedidos/components/OrderList.tsx:99`

**Recomendação**

- Respeitar `prefers-reduced-motion`.
- Animar apenas `transform` e `opacity`.
- Substituir `transition: all` por propriedades específicas.
- Evitar atrasos sequenciais longos quando muitos cartões aparecem.

### 14. Textos e estados de carregamento podem ser padronizados

Exemplos atuais:

- `Atualizando...`
- `Ocultando...`
- `Comparar com...`
- `Entrando...`

**Recomendação**

Usar a reticência tipográfica:

- `Atualizando…`
- `Ocultando…`
- `Comparar com…`
- `Entrando…`

Também é recomendável centralizar esses padrões em componentes comuns.

## Pontos positivos encontrados

- Identidade visual coerente com a marca.
- Login visualmente bem resolvido.
- Boa legibilidade geral no desktop.
- Áreas de toque de pelo menos 44 px em vários componentes.
- Leads utiliza cartões específicos no celular.
- Rotas esconde o mapa no celular e prioriza a lista.
- Busca de Vendas possui debounce.
- Leads e Pedidos possuem estados vazios.
- Confirmações e toasts já são centralizados em providers.
- Existe tratamento de carregamento e erro nas páginas principais.

## Ordem recomendada de implementação

### Fase 1 — Correções de alto impacto

1. Fazer o cartão do pedido abrir os detalhes.
2. Transformar a navegação em links reais.
3. Corrigir “Funcionários” versus “Recebíveis”.
4. Tornar Clientes acessível pela navegação.
5. Adicionar nomes acessíveis aos botões de ícone.
6. Corrigir títulos e elementos clicáveis sem teclado.

### Fase 2 — Estado e produtividade

1. Sincronizar filtros de Pedidos com a URL.
2. Sincronizar filtros de Vendas com a URL.
3. Sincronizar filtros de Leads com a URL.
4. Preservar paginação e modo lista/quadro.
5. Tornar os KPIs de Pedidos filtros clicáveis.

### Fase 3 — Experiência mobile

1. Compactar os períodos de Vendas.
2. Criar cartões mobile para a lista de vendas.
3. Reduzir ações visíveis nos cartões de Leads.
4. Substituir o status segmentado de Leads no celular.
5. Corrigir truncamentos e vazamentos horizontais.

### Fase 4 — Refinamento visual e técnico

1. Melhorar a semântica das cores dos KPIs.
2. Corrigir os avisos de dimensão dos gráficos.
3. Migrar os marcadores do Google Maps.
4. Implementar movimento reduzido.
5. Padronizar textos, reticências e estados de carregamento.

## Resultado esperado

Com essas mudanças, o aplicativo deve:

- Reduzir cliques sem resposta.
- Facilitar encontrar cada módulo.
- Preservar o contexto de trabalho.
- Exibir mais conteúdo operacional por tela.
- Ficar mais confortável no celular.
- Oferecer melhor suporte a teclado e leitores de tela.
- Usar cores com significado mais claro.
- Reduzir avisos e riscos técnicos no frontend.
