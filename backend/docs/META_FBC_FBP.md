# Meta Pixel Parameters (fbc e fbp)

## Visão Geral

Os parâmetros `fbc` (Facebook Click ID) e `fbp` (Facebook Browser ID) são importantes para melhorar a qualidade de correspondência de eventos na Meta Conversions API. A Meta recomenda o uso desses parâmetros para aumentar a pontuação de qualidade de correspondência de eventos.

**Referência oficial**: [Meta Parameter Builder Library](https://developers.facebook.com/docs/marketing-api/conversions-api/parameter-builder-feature-library)

## O que são?

- **fbc (Facebook Click ID)**: Identificador do clique no anúncio do Facebook. Vem do parâmetro `fbclid` na URL quando o usuário clica em um anúncio.
- **fbp (Facebook Browser ID)**: Identificador do navegador criado pelo Pixel do Facebook. Vem do cookie `_fbp` criado automaticamente pelo Pixel.

## Como funciona

1. **Frontend captura os valores**:
   - `fbc`: Extraído do parâmetro `fbclid` na URL (ex: `?fbclid=xxxxx`)
   - `fbp`: Lido do cookie `_fbp` criado pelo Pixel do Facebook

2. **Frontend envia para o backend**:
   - Ao criar um pedido, o frontend envia `fbc` e `fbp` no payload JSON

3. **Backend armazena**:
   - Os valores são salvos nos campos `fbc` e `fbp` da tabela `pedidos`

4. **Backend envia para Meta**:
   - Quando o pedido é marcado como pago, o evento Purchase é enviado para Meta com `fbc` e `fbp` no `user_data`

## Implementação no Frontend

### Exemplo de captura e envio

```javascript
// Capturar fbc da URL
function getFbcFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('fbclid') || null;
}

// Capturar fbp do cookie
function getFbpFromCookie() {
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === '_fbp') {
      return value || null;
    }
  }
  return null;
}

// Ao criar pedido, incluir fbc e fbp no payload
const pedidoData = {
  // ... outros campos do pedido ...
  fbc: getFbcFromUrl(),
  fbp: getFbpFromCookie(),
};

// Enviar para API
fetch('/api/pedidos', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(pedidoData),
});
```

### Usando Meta Parameter Builder SDK (Recomendado)

A Meta fornece um SDK JavaScript que facilita a captura desses parâmetros:

```html
<!-- Incluir o SDK do Parameter Builder -->
<script src="https://connect.facebook.net/en_US/fbevents.js"></script>
<script>
  // Inicializar Parameter Builder
  // Ver documentação: https://developers.facebook.com/docs/marketing-api/conversions-api/parameter-builder-feature-library
</script>
```

**Nota**: A implementação completa do Parameter Builder SDK é opcional. A captura manual de `fbc` e `fbp` já melhora significativamente a qualidade dos eventos.

## Migration

Para adicionar os campos `fbc` e `fbp` na tabela `pedidos`, execute:

```bash
python backend/scripts/migrations/add_fbc_fbp_to_pedidos.py
```

## Benefícios

- ✅ **Aumento de 0.7 pontos** na pontuação de qualidade de correspondência de eventos (conforme Meta)
- ✅ Melhor rastreamento de conversões originadas de anúncios do Facebook
- ✅ Melhor atribuição de eventos a campanhas específicas
- ✅ Redução de eventos duplicados

## Notas Importantes

1. **Case-sensitive**: `fbc` é case-sensitive. Não normalize ou converta para lowercase.
2. **Opcional**: Se `fbc` ou `fbp` não estiverem disponíveis, o evento ainda será enviado normalmente.
3. **Validade**: `fbc` geralmente é válido por 1-7 dias após o clique no anúncio.
4. **Cookie _fbp**: O cookie `_fbp` é criado automaticamente pelo Pixel do Facebook quando a página carrega.

## Verificação

Para verificar se os valores estão sendo capturados:

1. **No banco de dados**:
   ```sql
   SELECT id, cliente, fbc, fbp FROM pedidos WHERE fbc IS NOT NULL OR fbp IS NOT NULL;
   ```

2. **No payload enviado para Meta**:
   - Verificar logs do script `send_daily_purchases_to_meta.py`
   - Verificar no Meta Events Manager se os eventos têm melhor qualidade de correspondência

## Referências

- [Meta Parameter Builder Library](https://developers.facebook.com/docs/marketing-api/conversions-api/parameter-builder-feature-library)
- [Meta Conversions API Best Practices](https://developers.facebook.com/docs/marketing-api/conversions-api/best-practices)
