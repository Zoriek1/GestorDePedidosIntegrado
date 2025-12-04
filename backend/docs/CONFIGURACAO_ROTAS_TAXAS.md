# Configuração de Rotas e Taxas de Entrega

## Visão Geral

O sistema utiliza **GraphHopper** para cálculo de rotas e distâncias, com fallback para **OpenRouteService**. As taxas de entrega são calculadas automaticamente baseadas na distância, seguindo uma configuração customizável.

---

## 🔑 Configuração de API Keys

### GraphHopper API Key

O sistema usa a API pública do GraphHopper para calcular rotas otimizadas.

**Configuração:**

1. Obtenha uma API key gratuita em: https://www.graphhopper.com/api/
   - Plano gratuito: 500 requisições/dia
   - Planos pagos: Mais requisições, sem limitações

2. Adicione a chave no arquivo `.env` na raiz do backend:

```env
GRAPHHOPPER_API_KEY=sua_chave_aqui
```

**Nota:** Se não configurar a API key, o sistema tentará usar a chave demo (limitada).

### OpenRouteService API Key (Fallback)

O sistema mantém suporte ao OpenRouteService como fallback caso o GraphHopper falhe.

**Configuração:**

```env
OPENROUTE_API_KEY=sua_chave_openroute_aqui
```

**Onde obter:** https://openrouteservice.org/dev/#/signup

### Endereço da Floricultura

Configure o endereço da floricultura para cálculo de distâncias:

```env
ENDERECO_FLORICULTURA=Rua Exemplo, 123, Bairro Centro, Goiânia, GO, 74000-000
```

---

## 💰 Configuração de Taxas de Entrega

### Arquivo de Configuração

As taxas de entrega são configuradas no arquivo:

```
backend/config/taxa_entrega.json
```

### Estrutura de Configuração

#### Opção 1: Sistema de Faixas (Recomendado)

```json
{
  "tipo": "faixas",
  "faixas": [
    {
      "ate_km": 5,
      "taxa": 10.00,
      "descricao": "Até 5 km"
    },
    {
      "ate_km": 10,
      "taxa": 15.00,
      "descricao": "De 5 a 10 km"
    },
    {
      "ate_km": 20,
      "taxa": 20.00,
      "descricao": "De 10 a 20 km"
    },
    {
      "ate_km": null,
      "taxa": 30.00,
      "descricao": "Acima de 20 km"
    }
  ],
  "taxa_minima": 5.00,
  "taxa_maxima": 50.00
}
```

**Como funciona:**
- O sistema verifica a distância do pedido
- Aplica a taxa correspondente à faixa
- Respeita os limites mínimo e máximo

#### Opção 2: Valor por Quilômetro

```json
{
  "tipo": "por_km",
  "valor_por_km": 2.50,
  "taxa_base": 5.00,
  "taxa_minima": 5.00,
  "taxa_maxima": 50.00
}
```

**Fórmula:** `taxa = taxa_base + (distancia_km × valor_por_km)`

**Exemplo:**
- Distância: 10 km
- Taxa: 5.00 + (10 × 2.50) = 30.00
- Limitado a 50.00 (taxa_maxima)

### Campos da Configuração

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `tipo` | string | `"faixas"` ou `"por_km"` |
| `faixas` | array | Lista de faixas (apenas para tipo "faixas") |
| `faixas[].ate_km` | number/null | Distância máxima da faixa (null = sem limite) |
| `faixas[].taxa` | number | Taxa em reais para esta faixa |
| `faixas[].descricao` | string | Descrição da faixa (opcional) |
| `valor_por_km` | number | Valor por km (apenas para tipo "por_km") |
| `taxa_base` | number | Taxa base (apenas para tipo "por_km") |
| `taxa_minima` | number | Taxa mínima aplicada (sempre) |
| `taxa_maxima` | number | Taxa máxima aplicada (sempre) |

---

## 🗺️ Cálculo de Rotas

### Rota Simples (2 pontos)

Calcula a distância e duração entre a floricultura e um endereço de entrega.

**Endpoint:** `GET /api/pedidos/<pedido_id>/distancia`

**Uso:**
- Calcula automaticamente ao criar/atualizar pedido
- Pode ser recalculado manualmente
- Resultado salvo no campo `distancia_km` do pedido

### Rota Otimizada (Múltiplos pontos)

Calcula a melhor sequência de entrega para múltiplos pedidos.

**Endpoint:** `POST /api/pedidos/rota-otimizada`

**Funcionalidades:**
- Otimiza ordem dos pedidos para menor distância total
- Calcula rota completa (origem → pedidos → origem)
- Salva rota no banco para consulta posterior
- Visualização em mapa interativo

**Algoritmos:**
- **Até 5 pedidos:** Otimização exata (testa todas as permutações)
- **Mais de 5 pedidos:** Heurística Nearest Neighbor (mais rápida)

---

## 📊 Armazenamento de Dados

### Campos no Modelo Pedido

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `distancia_km` | Float | Distância calculada em km |
| `taxa_entrega` | Float | Taxa de entrega calculada (R$) |
| `coords_lat` | Float | Latitude do endereço (cache) |
| `coords_lon` | Float | Longitude do endereço (cache) |

### Modelo RotaOtimizada

Armazena rotas otimizadas calculadas:

- `distancia_total_km`: Distância total da rota
- `duracao_total_min`: Duração estimada total
- `sequencia_pedidos`: IDs dos pedidos na ordem otimizada
- `waypoints_coords`: Coordenadas dos pontos de parada
- `metodo_otimizacao`: Método usado (exata, nearest_neighbor)

---

## 🔄 Cache e Performance

### Cache de Coordenadas

- Coordenadas da floricultura: Calculadas uma vez e reutilizadas
- Coordenadas dos pedidos: Salvas no banco (`coords_lat`, `coords_lon`)
- Evita geocodificação repetida do mesmo endereço

### Cache de Distâncias

- Distâncias calculadas são salvas no pedido
- Não recalcula se já existe (a menos que `force_recalc=true`)
- Reduz chamadas à API e melhora performance

### Cache de Rotas Otimizadas

- Rotas calculadas são salvas no banco
- Podem ser consultadas posteriormente
- Útil para rotas recorrentes

---

## 🛠️ Endpoints da API

### Calcular Distância Individual

```http
GET /api/pedidos/<pedido_id>/distancia?force_recalc=true
```

**Resposta:**
```json
{
  "success": true,
  "pedido_id": 1,
  "distancia_km": 12.5,
  "duracao_min": 18,
  "cached": false
}
```

### Calcular Taxa de Entrega

```http
POST /api/pedidos/<pedido_id>/calcular-taxa
```

**Resposta:**
```json
{
  "success": true,
  "pedido_id": 1,
  "distancia_km": 12.5,
  "taxa_entrega": 20.00
}
```

### Calcular Rota Otimizada

```http
POST /api/pedidos/rota-otimizada
Content-Type: application/json

{
  "pedido_ids": [1, 2, 3, 4],
  "nome": "Rota Manhã"
}
```

**Resposta:**
```json
{
  "success": true,
  "rota_id": 1,
  "distancia_total_km": 45.2,
  "duracao_total_min": 65,
  "sequencia_pedidos": [2, 1, 4, 3],
  "num_pedidos": 4
}
```

### Obter Rota Otimizada

```http
GET /api/pedidos/rota-otimizada/<rota_id>
```

---

## 🐛 Troubleshooting

### GraphHopper não está funcionando

1. Verifique se a API key está configurada no `.env`
2. Verifique os logs do servidor para erros
3. O sistema automaticamente usa OpenRouteService como fallback

### Taxas não estão sendo calculadas

1. Verifique se o arquivo `backend/config/taxa_entrega.json` existe
2. Verifique se a distância do pedido foi calculada primeiro
3. Verifique os logs para erros de configuração

### Rotas otimizadas muito lentas

- Para muitos pedidos (>10), o cálculo pode ser lento
- O sistema usa heurística para pedidos > 5
- Considere calcular rotas em horários de menor uso

### Coordenadas não estão sendo salvas

- Verifique se os campos `coords_lat` e `coords_lon` existem no banco
- Execute migração se necessário: `python migrate_add_coords_fields.py`

---

## 📝 Exemplos de Uso

### Calcular distância e taxa para um pedido

```javascript
// 1. Calcular distância
const distancia = await API.calcularDistanciaPedido(pedidoId);

// 2. Calcular taxa (automaticamente calcula distância se necessário)
const taxa = await API.calcularTaxaEntrega(pedidoId);
```

### Calcular rota otimizada

```javascript
// Obter pedidos elegíveis
const pedidos = await API.getPedidos();

// Calcular rota
const rota = await API.calcularRotaOtimizada(
  pedidos.map(p => p.id),
  'Rota Manhã'
);

// Visualizar rota
window.location.href = `/pages/rota-entrega.html?id=${rota.rota_id}`;
```

---

## 🔐 Segurança

- **Nunca commite** arquivos `.env` com API keys
- Use variáveis de ambiente em produção
- Monitore uso da API para evitar exceder limites
- Implemente rate limiting se necessário

---

## 📚 Referências

- [GraphHopper API Documentation](https://docs.graphhopper.com/)
- [OpenRouteService Documentation](https://openrouteservice.org/dev/#/api-docs)
- [Nominatim (Geocodificação)](https://nominatim.org/release-docs/latest/api/Overview/)

---

**Última atualização:** 2024

