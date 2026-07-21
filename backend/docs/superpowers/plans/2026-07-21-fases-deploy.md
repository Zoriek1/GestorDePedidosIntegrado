# Fases Operacionais — Deploy e Ativação Produção

> **Pré-requisito:** Todos os grupos (2–7) concluídos e testados.

**Goal:** Preparar, deployar e ativar em produção de forma segura e gradual.

**Architecture:** Docker + Waitress WSGI + Cloudflare Tunnel.

**Tech Stack:** Docker, Waitress, Cloudflare

## Global Constraints

- Entrypoint: `entrypoint.sh` (migrations + wsgi.py)
- Servidor: Waitress WSGI (production), Werkzeug (development)
- SSL via Cloudflare Tunnel

---

## Fase 1: Preparação

- [ ] **Step 1: Rodar todos os testes**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado\backend"
python -m pytest tests/ -v --tb=short
```

- [ ] **Step 2: Rodar linting completo**

```bash
ruff check . && black --check .
```

- [ ] **Step 3: Verificar Docker build**

```bash
cd "C:\Gestor de Pedidos Plante uma flor\GestorDePedidosIntegrado"
docker build -t gestor-pedidos-backend ./backend
```

- [ ] **Step 4: Documentar variáveis de ambiente necessárias**

```bash
rg "os\.environ\.get\(" --type py -o -n | sort -u
```

Verificar quais env vars são obrigatórias vs opcionais.

---

## Fase 2: Deploy

- [ ] **Step 1: Deploy com features desabilitadas**

```env
BLING_ENABLED=false
MARKETING_DISPATCH_ENABLED=false
UTMIFY_ENABLED=false
ENABLE_AUTH=true
ENABLE_RATE_LIMIT=true
```

- [ ] **Step 2: Verificar health check**

```bash
curl -k https://gestaopedidos.planteumaflor.online/api/health
```

- [ ] **Step 3: Verificar logs**

```bash
docker logs gestor-pedidos-backend --tail 50
```

- [ ] **Step 4: Verificar que workers iniciam**

```bash
docker ps | grep -E "bling|meta_capi"
```

---

## Fase 5: Ativação produção

- [ ] **Step 1: Ativar Bling gradualmente**

```env
BLING_ENABLED=true
```

Monitorar por 1h.

- [ ] **Step 2: Ativar Marketing Dispatch**

```env
MARKETING_DISPATCH_ENABLED=true
```

Monitorar por 1h.

- [ ] **Step 3: Ativar UTMify (se necessário)**

```env
UTMIFY_ENABLED=true
```

- [ ] **Step 4: Configurar multi-tenant**

```env
FORCE_MULTI_TENANT=true  # se aplicável
```

- [ ] **Step 5: Monitorar por 24h**

- Verificar logs de erro
- Verificar métricas de rate limiting
- Verificar workers processando corretamente
- Verificar envios Meta CAPI/GA4

- [ ] **Step 6: Confirmar estabilidade**

Marcar como concluído se:
- Zero erros críticos em 24h
- Workers processando normalmente
- Rate limiting funcionando
- CORS sem problemas
