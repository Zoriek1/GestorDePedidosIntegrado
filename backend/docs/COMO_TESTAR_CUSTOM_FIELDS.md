# Como Testar Custom Fields dos Pedidos Nuvemshop

Este guia mostra como fazer requests para os endpoints de debug criados para visualizar os custom_fields dos pedidos.

## Informações Básicas

- **Base URL**: `http://localhost:5000/api` (ou a URL do seu servidor em produção)
- **Autenticação**: HTTP Basic Auth
- **Usuário**: `admin`
- **Senha**: Configurada via `ADMIN_PASSWORD` no `.env` (padrão: `plante1998`)

## Endpoints Disponíveis

### 1. Listar Pedidos Recentes

**Endpoint**: `GET /api/integrations/nuvemshop/debug/pedidos-recentes`

**Query Parameters**:
- `limit` (opcional, padrão: 10) - Número de pedidos a buscar
- `days` (opcional, padrão: 1) - Buscar pedidos dos últimos N dias

**Exemplo**: Buscar últimos 5 pedidos dos últimos 2 dias
```
GET /api/integrations/nuvemshop/debug/pedidos-recentes?limit=5&days=2
```

### 2. Ver Pedido Específico

**Endpoint**: `GET /api/integrations/nuvemshop/debug/pedido/<order_id>`

**Exemplo**: Ver pedido com ID 123456789
```
GET /api/integrations/nuvemshop/debug/pedido/123456789
```

---

## Formas de Fazer os Requests

### 1. Usando cURL (Terminal/CMD/PowerShell)

#### Windows PowerShell:
```powershell
# Pedidos recentes (últimos 10 pedidos do último dia)
$cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:plante1998"))
Invoke-RestMethod -Uri "http://localhost:5000/api/integrations/nuvemshop/debug/pedidos-recentes" -Headers @{Authorization="Basic $cred"} -Method GET

# Pedidos recentes com parâmetros customizados
Invoke-RestMethod -Uri "http://localhost:5000/api/integrations/nuvemshop/debug/pedidos-recentes?limit=5&days=2" -Headers @{Authorization="Basic $cred"} -Method GET

# Pedido específico (substitua 123456789 pelo ID real)
Invoke-RestMethod -Uri "http://localhost:5000/api/integrations/nuvemshop/debug/pedido/123456789" -Headers @{Authorization="Basic $cred"} -Method GET
```

#### Linux/Mac Terminal:
```bash
# Pedidos recentes
curl -u admin:plante1998 "http://localhost:5000/api/integrations/nuvemshop/debug/pedidos-recentes"

# Com parâmetros
curl -u admin:plante1998 "http://localhost:5000/api/integrations/nuvemshop/debug/pedidos-recentes?limit=5&days=2"

# Pedido específico
curl -u admin:plante1998 "http://localhost:5000/api/integrations/nuvemshop/debug/pedido/123456789"
```

### 2. Usando Postman

1. **Criar nova requisição GET**
2. **URL**: `http://localhost:5000/api/integrations/nuvemshop/debug/pedidos-recentes`
3. **Autenticação**:
   - Vá na aba "Authorization"
   - Selecione "Basic Auth"
   - Username: `admin`
   - Password: `plante1998` (ou sua senha configurada)
4. **Query Params** (opcional):
   - `limit`: 10
   - `days`: 1
5. **Enviar requisição**

### 3. Usando Navegador (com extensão)

#### Chrome/Firefox com extensão "ModHeader" ou similar:

1. Instale a extensão "ModHeader" no Chrome
2. Configure o header:
   - Name: `Authorization`
   - Value: `Basic YWRtaW46cGxhbnRlMTk5OA==` (base64 de `admin:plante1998`)
3. Acesse no navegador:
   ```
   http://localhost:5000/api/integrations/nuvemshop/debug/pedidos-recentes?limit=10&days=1
   ```

**Nota**: Para gerar o Base64, use:
- PowerShell: `[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:plante1998"))`
- Online: https://www.base64encode.org/

### 4. Usando Python (requests)

```python
import requests
from requests.auth import HTTPBasicAuth

base_url = "http://localhost:5000/api"
auth = HTTPBasicAuth('admin', 'plante1998')  # Use sua senha configurada

# Pedidos recentes
response = requests.get(
    f"{base_url}/integrations/nuvemshop/debug/pedidos-recentes",
    params={"limit": 10, "days": 1},
    auth=auth
)
print(response.json())

# Pedido específico
order_id = "123456789"
response = requests.get(
    f"{base_url}/integrations/nuvemshop/debug/pedido/{order_id}",
    auth=auth
)
print(response.json())
```

### 5. Usando JavaScript/Node.js

```javascript
const axios = require('axios');

const baseURL = 'http://localhost:5000/api';
const auth = {
  username: 'admin',
  password: 'plante1998'  // Use sua senha configurada
};

// Pedidos recentes
axios.get(`${baseURL}/integrations/nuvemshop/debug/pedidos-recentes`, {
  params: { limit: 10, days: 1 },
  auth: auth
})
.then(response => {
  console.log(JSON.stringify(response.data, null, 2));
})
.catch(error => {
  console.error('Erro:', error.response?.data || error.message);
});

// Pedido específico
const orderId = '123456789';
axios.get(`${baseURL}/integrations/nuvemshop/debug/pedido/${orderId}`, {
  auth: auth
})
.then(response => {
  console.log(JSON.stringify(response.data, null, 2));
})
.catch(error => {
  console.error('Erro:', error.response?.data || error.message);
});
```

---

## Estrutura da Resposta

### Endpoint: `/debug/pedidos-recentes`

```json
{
  "success": true,
  "data": {
    "total": 10,
    "pedidos": [
      {
        "order_id": "123456",
        "order_number": "789",
        "created_at": "2026-02-20T10:00:00-0300",
        "custom_fields_raw": [
          {
            "name": "Agendamento",
            "value": "21/02/2026 14:00 - 16:00"
          }
        ],
        "custom_fields_extraidos": {
          "dia_entrega": "2026-02-21",
          "horario": "14:00 - 16:00",
          "campo_nome": "Agendamento"
        },
        "mapeamento": {
          "dia_entrega": "2026-02-21",
          "horario": "14:00 - 16:00",
          "agendamento_source": "custom_field:Agendamento",
          "schedule_pending": false
        },
        "ja_importado": true,
        "pedido_id": 42
      }
    ]
  }
}
```

### Endpoint: `/debug/pedido/<order_id>`

Retorna informações mais detalhadas incluindo:
- `order_json`: JSON completo do pedido da API Nuvemshop
- `custom_fields_raw`: Campos personalizados brutos
- `custom_fields_extraidos`: Data/horário extraídos
- `mapeamento`: Resultado completo do mapeamento
- `status_importacao`: Se já foi importado e status
- `pedido_local`: Dados do pedido no banco local (se existir)

---

## Troubleshooting

### Erro 401 (Não autorizado)
- Verifique se o usuário e senha estão corretos
- Confirme que está usando HTTP Basic Auth
- Verifique se `ADMIN_PASSWORD` está configurado no `.env`

### Erro 404 (Não encontrado)
- Verifique se o servidor está rodando na porta 5000
- Confirme que a URL está correta
- Para pedido específico, verifique se o `order_id` existe

### Erro 500 (Erro interno)
- Verifique os logs do servidor
- Confirme que `NUVEMSHOP_USER_AGENT` está configurado no `.env`
- Verifique se há uma loja Nuvemshop ativa configurada

### Nenhum pedido retornado
- Aumente o parâmetro `days` para buscar em um período maior
- Verifique se há pedidos recentes na loja Nuvemshop
- Confirme que a loja está conectada e ativa

---

## Próximos Passos

Após visualizar os custom_fields:

1. **Validar estrutura**: Verifique se os custom_fields estão no formato esperado
2. **Verificar mapeamento**: Confirme se data/horário estão sendo extraídos corretamente
3. **Comparar com importados**: Veja se os pedidos já importados têm os mesmos dados
4. **Ajustar se necessário**: Se encontrar problemas, ajuste a função `_extract_schedule_from_custom_fields()` em `backend/app/integrations/nuvemshop/mapper.py`
