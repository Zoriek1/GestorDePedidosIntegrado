# Template para Componentes Uiverse

## Quando você me passar código do Uiverse:

1. **Me diga**: "Quero usar este componente do Uiverse: [cole o código]"
2. **Me diga**: "Quero usar em: [localização, ex: OrderCard, AppShell, etc]"
3. **Eu vou**:
   - Criar pasta do componente em `components/uiverse/`
   - Adaptar cores para variáveis do tema
   - Substituir `#000`, `#fff`, etc. por variáveis CSS
   - Criar CSS Module com estilos isolados
   - Criar componente React TypeScript
   - Integrar com animate.css se necessário
   - Integrar no local solicitado

## Exemplo de Pedido:

```
"Quero usar este botão do Uiverse:

<button class="btn">Click me</button>

<style>
.btn {
  background: #000;
  color: #fff;
  /* ... mais estilos ... */
}
</style>

Quero usar em: OrderCardActions (substituir botão de deletar)"
```

## O que eu vou fazer:

1. ✅ Criar `components/uiverse/AnimatedDeleteButton/`
2. ✅ Adaptar `#000` → `var(--color-primary)`
3. ✅ Adaptar `#fff` → `var(--color-surface)`
4. ✅ Criar CSS Module
5. ✅ Criar componente TypeScript
6. ✅ Integrar no OrderCardActions
7. ✅ Adicionar animação do animate.css

## Regras que seguirei:

- ✅ CSS complexo (::before, ::after, @keyframes) → CSS Module
- ✅ Cores → Variáveis CSS do tema
- ✅ Animações → animate.css via hook
- ✅ TypeScript → Props tipadas
- ✅ Integração MUI → Quando necessário, mas CSS isolado
