# Análise de Complexidade — Backend (Julho/2026)

> **Ferramenta:** [radon](https://radon.readthedocs.io) 6.0.1
> **Escopo:** `backend/app` (exclui `migrations/` e `tests/`)
> **Data:** 2026-07-09
> **Métricas:** Complexidade Ciclomática (CC) por bloco + Índice de Manutenibilidade (MI) por arquivo

---

## 1. Como ler as métricas

**Complexidade Ciclomática (CC)** — número de caminhos independentes numa função. Quanto maior, mais difícil de testar e manter.

| Nota | CC | Significado |
|------|-----|-------------|
| A | 1–5 | simples |
| B | 6–10 | ok |
| C | 11–20 | atenção |
| D | 21–30 | complexo |
| E | 31–40 | difícil |
| F | 41+ | crítico |

**Índice de Manutenibilidade (MI)** — nota de 0 a 100 por arquivo (combina CC, volume de Halstead e linhas). Quanto **menor**, pior.

| Nota | MI | Significado |
|------|-----|-------------|
| A | ≥ 20 | manutenível |
| B | 10–19 | médio |
| C | < 10 | ruim |

---

## 2. Panorama geral

Base **saudável no agregado**, com risco concentrado numa cauda pequena de funções/arquivos.

**CC — 964 blocos analisados, média B (5,82):**

| Nota | Blocos | % |
|------|--------|-----|
| A | 656 | 68,0% |
| B | 183 | 19,0% |
| C | 86 | 8,9% |
| D | 24 | 2,5% |
| E | 4 | 0,4% |
| F | 11 | 1,1% |

**MI — 123 arquivos:**

| Nota | Arquivos |
|------|----------|
| A (≥20) | 116 |
| B (10–19) | 1 |
| C (<10) | 6 |

**Conclusão:** 87% dos blocos são A/B e 94% dos arquivos são A. **7 arquivos** (MI < 20) concentram a dívida técnica e são o alvo deste documento.

---

## 3. Arquivos que merecem mudança

Ordenados por prioridade (MI mais baixo primeiro). Números de linha referentes ao código em 2026-07-09.

### 🔴 Prioridade 1 — crítico (MI ≈ 0)

#### `app/routes/pedidos.py` — MI 0,0 · 1.809 SLOC · CC máx 82

O arquivo mais crítico da base. Duas rotas gigantes fazem validação, montagem de dados, regra de negócio e persistência numa função só (*fat controllers*).

| Bloco | Linha | CC |
|-------|-------|-----|
| `criar_pedido` | 1308 | **F 82** |
| `atualizar_pedido` | 1692 | **F 81** |
| `_build_payment_snapshot` | 109 | D 26 |
| `atribuir_entregadores_lote` | 846 | C 20 |
| `_collect_delivery_details` | 187 | C 17 |

**Ação:** extrair a lógica de `criar_pedido`/`atualizar_pedido` para um *service* ou *command* (o projeto já tem `app/services` e `app/commands`). A rota deve só validar entrada, delegar e formatar resposta. Quebrar a montagem do payload em funções por responsabilidade (cliente, endereço, itens, pagamento, agendamento).

---

#### `app/integrations/nuvemshop/mapper.py` — MI 0,0 · 745 SLOC · CC máx 64

Mapper de pedido da Nuvemshop com muita ramificação para lidar com campos customizados e variações de formato.

| Bloco | Linha | CC |
|-------|-------|-----|
| `map_nuvemshop_order_to_pedido_data` | 885 | **F 64** |
| `_extract_schedule_from_custom_fields` | 802 | D 28 |
| `_detect_express_from_order` | 509 | D 23 |
| `_is_pickup_order` | 677 | D 21 |

**Ação:** dividir `map_nuvemshop_order_to_pedido_data` em extratores focados (cliente, endereço, itens, frete, agendamento) e compor o resultado. Trocar cadeias `if/elif` sobre nome de campo customizado por um mapa de configuração (`{nome_campo: parser}`).

---

#### `app/routes/leads.py` — MI 0,0 · 963 SLOC · CC máx 46

Mesmo padrão de *fat controller* das rotas de pedido, agora em leads.

| Bloco | Linha | CC |
|-------|-------|-----|
| `listar_leads` | 882 | **F 46** |
| `atualizar_status_leads_em_lote` | 1122 | D 29 |
| `criar_lead` | 403 | D 26 |
| `_apply_lead_status_update` | 614 | D 22 |
| `desqualificar_leads_em_lote` | 1200 | D 22 |

**Ação:** `listar_leads` — extrair a montagem de filtros para um objeto/*builder* de query (padrão já existente em `PedidoRepository.buscar_com_filtros`). Consolidar as três operações em lote, que compartilham estrutura, num único fluxo parametrizado.

---

#### `app/integrations/bling/service.py` — MI 0,0 · 1.151 SLOC · CC máx 36

Serviço de integração muito grande. O MI cai por volume total + complexidade somada, mais do que por um único bloco.

| Bloco | Linha | CC |
|-------|-------|-----|
| `ensure_contact_for_pedido` | 168 | E 36 |
| `_contact_address_from_pedido` | 248 | C 16 |
| `process_outbox` | 511 | C 16 |
| `_sync_payment_methods` | 1082 | C 15 |

**Ação:** o problema principal é tamanho — considerar dividir a classe por responsabilidade (ex.: contatos, outbox, sincronização de métodos/contas financeiras) em serviços menores. `ensure_contact_for_pedido` deve ter a normalização/validação de endereço extraída.

---

### 🟠 Prioridade 2 — alto (MI 4–8)

#### `app/services/meta_capi.py` — MI 4,3 · 676 SLOC · CC máx 50

| Bloco | Linha | CC |
|-------|-------|-----|
| `build_purchase_event` | 426 | **F 50** |
| `build_external_ids_for_event` | 354 | D 28 |
| `sanitize_event_payload` | 789 | D 23 |
| `send_events` | 864 | D 23 |

**Ação:** `build_purchase_event` monta um payload grande com muitos campos condicionais — extrair a construção de cada seção (user_data, custom_data, external_ids) para *helpers* e reduzir os `if campo is not None`.

---

#### `app/services/distancia.py` — MI 8,1 · 837 SLOC · CC máx 51

| Bloco | Linha | CC |
|-------|-------|-----|
| `geocodificar` | 537 | **F 51** |
| `calcular_distancia` | 821 | **F 41** |
| `buscar_endereco_por_cep` | 91 | C 19 |
| `calcular_distancia_pedido` | 1009 | C 19 |

**Ação:** os dois métodos F provavelmente tratam múltiplos provedores/fallbacks e cache num fluxo linear. Extrair cada provedor (ex.: Nominatim, cache, fallback) para um método próprio e orquestrar com uma estratégia clara de tentativa/fallback.

---

### 🟡 Prioridade 3 — limítrofe (MI 10–19)

#### `app/routes/nuvemshop.py` — MI 16,0 · 814 SLOC · CC máx 22

Único arquivo nota B. Nenhum bloco é F/E, mas o volume + vários blocos C/D derrubam o MI.

| Bloco | Linha | CC |
|-------|-------|-----|
| `_enrich_pedido_from_api` | 596 | D 22 |
| `definir_agendamento_pedido` | 715 | C 18 |
| `debug_pedido_especifico` | 900 | C 18 |
| `nuvemshop_oauth_callback` | 190 | C 16 |

**Ação:** menor urgência. Avaliar mover rotas `debug_*` para fora do arquivo de produção e extrair `_enrich_pedido_from_api` para o *service* da integração.

---

## 4. Resumo priorizado

| # | Arquivo | MI | SLOC | Pior bloco | Ação central |
|---|---------|-----|------|-----------|--------------|
| 1 | `routes/pedidos.py` | 0,0 | 1.809 | `criar_pedido` (82) | Mover regra p/ service/command |
| 2 | `integrations/nuvemshop/mapper.py` | 0,0 | 745 | `map_...to_pedido_data` (64) | Quebrar em extratores |
| 3 | `routes/leads.py` | 0,0 | 963 | `listar_leads` (46) | Query builder + unificar lotes |
| 4 | `integrations/bling/service.py` | 0,0 | 1.151 | `ensure_contact_for_pedido` (36) | Dividir a classe |
| 5 | `services/meta_capi.py` | 4,3 | 676 | `build_purchase_event` (50) | Extrair montagem de payload |
| 6 | `services/distancia.py` | 8,1 | 837 | `geocodificar` (51) | Isolar provedores/fallback |
| 7 | `routes/nuvemshop.py` | 16,0 | 814 | `_enrich_pedido_from_api` (22) | Separar debug + enrich no service |

**Meta sugerida:** nenhuma função acima de CC 20 (nota D) e nenhum arquivo com MI < 20.

---

## 5. Como reproduzir

**Forma recomendada — script pronto** (roda no container, instala o radon se faltar):

```bash
# a partir da raiz do GestorDePedidosIntegrado (ou de qualquer lugar via caminho)
./backend/scripts/maintenance/analise_complexidade.sh          # resumo: C+ (CC) e B/C (MI)
./backend/scripts/maintenance/analise_complexidade.sh --full   # inclui blocos nota B
```

**Manual**, se preferir rodar os comandos direto:

```bash
# radon esta em requirements-dev.txt, mas NAO na imagem de producao;
# instalar ad-hoc no container:
docker compose exec backend pip install radon

# Complexidade ciclomatica (ordenada, com score)
docker compose exec backend python -m radon cc app --exclude "*/migrations/*" -s -a --order SCORE

# Indice de manutenibilidade por arquivo
docker compose exec backend python -m radon mi app --exclude "*/migrations/*" -s
```
