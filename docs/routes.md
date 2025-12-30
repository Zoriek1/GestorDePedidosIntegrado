<!-- AUTO-GENERATED: do not edit -->

# Mapa de Rotas

Este arquivo é gerado automaticamente pelo script `backend/scripts/dump_routes.py`.

**Última atualização:** Gerado automaticamente

---

## Tabela de Rotas

| Método | Path | Endpoint | Blueprint | Função | Autenticação |
|--------|------|----------|-----------|--------|--------------|
| GET | `/` | `serve_frontend` | `main` | `serve_frontend` | Nenhuma |
| GET | `/<path:path>` | `serve_frontend` | `main` | `serve_frontend` | Nenhuma |
| GET | `/api/auth/check` | `auth.check_auth_status` | `auth` | `check_auth_status` | Nenhuma |
| POST | `/api/auth/login` | `auth.login` | `auth` | `login` | Nenhuma |
| GET | `/api/backup/status` | `api.obter_status_backup` | `api` | `obter_status_backup` | Nenhuma |
| POST | `/api/cleanup` | `api.limpar_pedidos_antigos` | `api` | `limpar_pedidos_antigos` | Nenhuma |
| GET | `/api/clientes` | `clientes.listar_clientes` | `clientes` | `listar_clientes` | Nenhuma |
| POST | `/api/clientes` | `clientes.criar_cliente` | `clientes` | `criar_cliente` | Nenhuma |
| DELETE | `/api/clientes/<int:cliente_id>` | `clientes.deletar_cliente` | `clientes` | `deletar_cliente` | Nenhuma |
| GET | `/api/clientes/<int:cliente_id>` | `clientes.obter_cliente` | `clientes` | `obter_cliente` | Nenhuma |
| PUT | `/api/clientes/<int:cliente_id>` | `clientes.atualizar_cliente` | `clientes` | `atualizar_cliente` | Nenhuma |
| GET | `/api/clientes/<int:cliente_id>/enderecos` | `clientes.listar_enderecos_cliente` | `clientes` | `listar_enderecos_cliente` | Nenhuma |
| POST | `/api/clientes/<int:cliente_id>/enderecos` | `clientes.adicionar_endereco_cliente` | `clientes` | `adicionar_endereco_cliente` | Nenhuma |
| GET | `/api/clientes/<int:cliente_id>/ltv` | `clientes.obter_ltv_cliente` | `clientes` | `obter_ltv_cliente` | Nenhuma |
| GET | `/api/clientes/<int:cliente_id>/pedidos` | `clientes.obter_pedidos_cliente` | `clientes` | `obter_pedidos_cliente` | Nenhuma |
| DELETE | `/api/clientes/enderecos/<int:endereco_id>` | `clientes.deletar_endereco` | `clientes` | `deletar_endereco` | Nenhuma |
| PUT | `/api/clientes/enderecos/<int:endereco_id>` | `clientes.atualizar_endereco` | `clientes` | `atualizar_endereco` | Nenhuma |
| POST | `/api/clientes/enderecos/<int:endereco_id>/principal` | `clientes.marcar_endereco_principal` | `clientes` | `marcar_endereco_principal` | Nenhuma |
| GET | `/api/clientes/search` | `clientes.buscar_clientes_autocomplete` | `clientes` | `buscar_clientes_autocomplete` | Nenhuma |
| GET | `/api/clientes/stats` | `clientes.obter_estatisticas` | `clientes` | `obter_estatisticas` | Nenhuma |
| GET | `/api/debug/config-floricultura` | `api.debug_config_floricultura` | `api` | `debug_config_floricultura` | Nenhuma |
| GET | `/api/debug/geocode` | `api.debug_geocode` | `api` | `debug_geocode` | Nenhuma |
| POST | `/api/debug/geocode` | `api.debug_geocode` | `api` | `debug_geocode` | Nenhuma |
| POST | `/api/debug/limpar-distancias` | `api.debug_limpar_distancias` | `api` | `debug_limpar_distancias` | Nenhuma |
| POST | `/api/debug/reset-floricultura` | `api.debug_reset_floricultura` | `api` | `debug_reset_floricultura` | Nenhuma |
| GET | `/api/debug/testar-apis` | `api.debug_testar_apis` | `api` | `debug_testar_apis` | Nenhuma |
| POST | `/api/exportar-planilha` | `api.exportar_planilha` | `api` | `exportar_planilha` | Edit Auth |
| GET | `/api/fontes-pedido` | `api.listar_fontes_pedido` | `api` | `listar_fontes_pedido` | Nenhuma |
| POST | `/api/fontes-pedido` | `api.criar_fonte_pedido` | `api` | `criar_fonte_pedido` | Edit Auth |
| DELETE | `/api/fontes-pedido/<int:fonte_id>` | `api.deletar_fonte_pedido` | `api` | `deletar_fonte_pedido` | Edit Auth |
| PUT | `/api/fontes-pedido/<int:fonte_id>` | `api.atualizar_fonte_pedido` | `api` | `atualizar_fonte_pedido` | Edit Auth |
| GET | `/api/fontes-pedido/all` | `api.listar_todas_fontes` | `api` | `listar_todas_fontes` | Nenhuma |
| GET | `/api/health` | `api.health_check` | `api` | `health_check` | Nenhuma |
| GET | `/api/pedidos` | `api.listar_pedidos` | `api` | `listar_pedidos` | Nenhuma |
| GET | `/api/pedidos` | `pedidos.listar_pedidos` | `pedidos` | `listar_pedidos` | Nenhuma |
| POST | `/api/pedidos` | `api.criar_pedido` | `api` | `criar_pedido` | Edit Auth |
| POST | `/api/pedidos` | `pedidos.criar_pedido` | `pedidos` | `criar_pedido` | Edit Auth |
| DELETE | `/api/pedidos/<int:pedido_id>` | `pedidos.deletar_pedido` | `pedidos` | `deletar_pedido` | Edit Auth |
| GET | `/api/pedidos/<int:pedido_id>` | `api.obter_pedido` | `api` | `obter_pedido` | Nenhuma |
| GET | `/api/pedidos/<int:pedido_id>` | `pedidos.obter_pedido` | `pedidos` | `obter_pedido` | Nenhuma |
| PUT | `/api/pedidos/<int:pedido_id>` | `api.atualizar_pedido` | `api` | `atualizar_pedido` | Nenhuma |
| PUT | `/api/pedidos/<int:pedido_id>` | `pedidos.atualizar_pedido` | `pedidos` | `atualizar_pedido` | Edit Auth |
| POST | `/api/pedidos/<int:pedido_id>/calcular-taxa` | `api.calcular_taxa_pedido` | `api` | `calcular_taxa_pedido` | Nenhuma |
| GET | `/api/pedidos/<int:pedido_id>/distancia` | `api.calcular_distancia_pedido_endpoint` | `api` | `calcular_distancia_pedido_endpoint` | Nenhuma |
| POST | `/api/pedidos/<int:pedido_id>/marcar-impresso` | `api.marcar_impresso` | `api` | `marcar_impresso` | Nenhuma |
| POST | `/api/pedidos/<int:pedido_id>/marcar-impresso` | `pedidos.marcar_impresso` | `pedidos` | `marcar_impresso` | Edit Auth |
| PUT | `/api/pedidos/<int:pedido_id>/marcar-impresso` | `api.marcar_impresso` | `api` | `marcar_impresso` | Nenhuma |
| PUT | `/api/pedidos/<int:pedido_id>/marcar-impresso` | `pedidos.marcar_impresso` | `pedidos` | `marcar_impresso` | Edit Auth |
| POST | `/api/pedidos/<int:pedido_id>/status` | `api.atualizar_status` | `api` | `atualizar_status` | Nenhuma |
| POST | `/api/pedidos/<int:pedido_id>/status` | `pedidos.atualizar_status` | `pedidos` | `atualizar_status` | Edit Auth |
| PUT | `/api/pedidos/<int:pedido_id>/status` | `api.atualizar_status` | `api` | `atualizar_status` | Nenhuma |
| PUT | `/api/pedidos/<int:pedido_id>/status` | `pedidos.atualizar_status` | `pedidos` | `atualizar_status` | Edit Auth |
| POST | `/api/pedidos/calcular-distancias` | `api.calcular_distancias_lote` | `api` | `calcular_distancias_lote` | Nenhuma |
| POST | `/api/pedidos/exportar-planilha` | `pedidos.exportar_planilha` | `pedidos` | `exportar_planilha` | Edit Auth |
| GET | `/api/pedidos/fonte/<int:fonte_id>` | `api.listar_pedidos_fonte` | `api` | `listar_pedidos_fonte` | Nenhuma |
| GET | `/api/pedidos/fonte/<int:fonte_id>/consolidado` | `api.estatisticas_fonte` | `api` | `estatisticas_fonte` | Nenhuma |
| GET | `/api/pedidos/overdue` | `api.pedidos_atrasados` | `api` | `pedidos_atrasados` | Nenhuma |
| GET | `/api/pedidos/por-data` | `api.get_pedidos_por_data` | `api` | `get_pedidos_por_data` | Nenhuma |
| GET | `/api/pedidos/por-data` | `pedidos.get_pedidos_por_data` | `pedidos` | `get_pedidos_por_data` | Nenhuma |
| POST | `/api/pedidos/rota-otimizada` | `api.calcular_rota_otimizada` | `api` | `calcular_rota_otimizada` | Nenhuma |
| POST | `/api/pedidos/rota-otimizada` | `rotas.calcular_rota_otimizada` | `rotas` | `calcular_rota_otimizada` | Nenhuma |
| GET | `/api/pedidos/rota-otimizada/<int:rota_id>` | `api.obter_rota_otimizada` | `api` | `obter_rota_otimizada` | Nenhuma |
| GET | `/api/pedidos/rota-otimizada/<int:rota_id>` | `rotas.obter_rota_otimizada` | `rotas` | `obter_rota_otimizada` | Nenhuma |
| GET | `/api/stats` | `api.obter_estatisticas` | `api` | `obter_estatisticas` | Nenhuma |
| GET | `/docs/openapi.json` | `api-docs.openapi_json` | `api-docs` | `_openapi_json` | Nenhuma |
| GET | `/docs/redoc` | `api-docs.openapi_redoc` | `api-docs` | `_openapi_redoc` | Nenhuma |
| GET | `/docs/swagger` | `api-docs.openapi_swagger_ui` | `api-docs` | `_openapi_swagger_ui` | Nenhuma |

---

## Legenda

- **Basic Auth**: Requer autenticação HTTP Basic
- **Edit Auth**: Requer autenticação para operações de edição
- **Nenhuma**: Rota pública (sem autenticação)

## Como Atualizar

Execute o script:

```bash
python backend/scripts/dump_routes.py
```

Ou use o comando:

```bash
cd backend
python scripts/dump_routes.py
```