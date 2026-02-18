# Configuração do Conversions API Gateway

## O que é o Gateway?

O Conversions API Gateway é um serviço da Meta que atua como proxy entre seu servidor e a Meta, oferecendo:
- ✅ Melhor visualização de eventos no Events Manager
- ✅ Métricas aprimoradas de qualidade de dados
- ✅ Melhor correspondência de eventos
- ✅ Diagnósticos mais detalhados

## Passo 1: Configurar no Meta Events Manager

1. Acesse: https://business.facebook.com/events_manager2
2. Selecione seu Pixel: `370300471997593`
3. Vá em **Conversions API Gateway**
4. Clique em **Usar um Conversions API Gateway existente**
5. Insira o URL: `gestaopedidos.planteumaflor.online` (sem https://)
6. Clique em **Iniciar Conversions API Gateway**
7. Uma nova janela será aberta mostrando o status da conexão
8. Se você ver a mensagem "Token processado com sucesso" com a configuração JSON, significa que está funcionando
9. **Volte para a janela do Events Manager** e verifique se há alguma mensagem de sucesso ou próximo passo
10. Se necessário, faça login/autorize o acesso quando solicitado pela Meta

## Passo 2: Ativar no código

Adicione no arquivo `.env`:

```env
# Ativar Conversions API Gateway (melhora visualização)
META_CAPI_USE_GATEWAY=true

# Domínio do Gateway (padrão: gestaopedidos.planteumaflor.online)
META_CAPI_GATEWAY_DOMAIN=gestaopedidos.planteumaflor.online

# Endpoint completo do Gateway (opcional - se a Meta fornecer um endpoint específico)
# Se não fornecido, será construído automaticamente: https://{domain}/meta-gateway/{pixel_id}/events
# META_CAPI_GATEWAY_ENDPOINT=https://gestaopedidos.planteumaflor.online/meta-gateway/370300471997593/events
```

## Passo 3: Verificar configuração

Execute o script de verificação:

```bash
python backend/scripts/meta/verificar_config_meta.py
```

## Como funciona

- **Com Gateway ativado**: Eventos são enviados para `https://gestaopedidos.planteumaflor.online/meta-gateway/{pixel_id}/events`
- **Sem Gateway**: Eventos são enviados diretamente para `https://graph.facebook.com/v21.0/{pixel_id}/events`

## Fallback automático

Se o Gateway falhar, o sistema automaticamente tenta a integração direta (se configurado).

## Benefícios do Gateway

1. **Melhor visualização**: Eventos aparecem com mais detalhes no Events Manager
2. **Métricas aprimoradas**: Taxa de correspondência, qualidade de dados, etc.
3. **Diagnósticos**: Identificação mais fácil de problemas
4. **Validação**: Gateway valida eventos antes de enviar para Meta

## Troubleshooting

### A página mostra "Token processado com sucesso" mas nada acontece

Isso é **normal**! Significa que:
- ✅ O token foi processado corretamente
- ✅ A configuração foi retornada
- ✅ O backend está funcionando
- ✅ O JavaScript está enviando a configuração via `postMessage`

**Possíveis causas do botão de login não aparecer:**

1. **A Meta pode estar processando em background**: A Meta pode estar validando a configuração e pode levar alguns minutos para mostrar o próximo passo.

2. **Verificar no Events Manager**: 
   - Volte para a janela do **Meta Events Manager** (não feche a janela de autoconfig)
   - Verifique se há alguma mensagem de erro ou status
   - Verifique se o status do Gateway mudou para "Conectado" ou "Ativo"
   - Procure por mensagens na parte superior da tela

3. **Verificar console do navegador**:
   - Abra DevTools (F12) na janela do **Events Manager** (não na janela de autoconfig)
   - Vá na aba **Console** e verifique se há erros
   - Vá na aba **Network** e verifique se há requisições para `/capig/autoconfig` com status 200

4. **A Meta pode não precisar de login manual**: Se você já está logado no Meta Business e tem permissões no Pixel, a Meta pode estar tentando vincular automaticamente.

**Próximos passos:**
1. **Aguarde 1-2 minutos** para ver se a Meta processa a configuração
2. **Recarregue a página do Events Manager** (F5) para ver se o status mudou
3. **Verifique o status do Gateway** na seção "Conversions API Gateway" do Events Manager
4. Se ainda não aparecer nada, tente **fechar e reabrir** a janela de configuração

### A Meta não reconhece a configuração

Se a Meta não reconhecer automaticamente:
1. Verifique se o domínio está correto: `gestaopedidos.planteumaflor.online`
2. Certifique-se de que não está usando `https://` no campo de URL
3. Tente fechar e reabrir a janela de configuração
4. Verifique os logs do servidor para ver se há erros

### Como verificar se está funcionando

Após configurar, você pode verificar se o Gateway está ativo:
1. No Events Manager, vá em **Conversions API Gateway**
2. Deve mostrar o status como "Ativo" ou "Conectado"
3. Eventos enviados através do Gateway aparecerão com melhor visualização

### Documentação oficial da Meta

A Meta não fornece documentação técnica pública detalhada sobre o formato exato do endpoint `/capig/autoconfig`. O processo é gerenciado internamente pela Meta.

**Recursos oficiais:**
- [Centro de Ajuda do Meta Business - Conversions API](https://www.facebook.com/business/help/AboutConversionsAPI)
- [Vídeo explicativo do Conversions API Gateway](https://www.facebook.com/MetaforDevelopers/videos/conversions-api-gateway-a-simplified-path-to-implementing-the-conversions-api/153445780330068/)

**Nota importante**: O processo de autenticação/autorização é gerenciado pela Meta. Se o botão de login não aparecer, pode ser que:
- A Meta esteja processando a configuração em background
- Você já tenha as permissões necessárias e a Meta esteja vinculando automaticamente
- Haja um problema no lado da Meta que requer contato com o suporte

### Verificar se o Gateway está realmente funcionando

Mesmo sem o botão de login aparecer, você pode verificar se o Gateway está funcionando:

1. **Envie eventos de teste**:
   ```bash
   python backend/scripts/meta/reenviar_outboxes.py
   python backend/scripts/meta/send_daily_purchases_to_meta.py
   ```

2. **Verifique no Events Manager**:
   - Vá em **Eventos** ou **Test Events**
   - Verifique se os eventos aparecem
   - Se aparecerem, o Gateway está funcionando (mesmo sem o botão de login)

3. **Ative o Gateway no código**:
   ```env
   META_CAPI_USE_GATEWAY=true
   ```
   Isso fará com que os eventos sejam enviados através do Gateway

## Notas importantes

- O Gateway é **opcional** - a integração direta já funciona perfeitamente
- Você pode alternar entre Gateway e integração direta apenas mudando `META_CAPI_USE_GATEWAY`
- O domínio deve estar configurado corretamente no Meta Events Manager
- A página de autoconfig pode ficar aberta - ela não precisa ser fechada manualmente