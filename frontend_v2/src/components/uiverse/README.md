# Componentes Uiverse

Esta pasta contém componentes adaptados do [uiverse.io](https://uiverse.io).

## Estrutura

- Cada componente do Uiverse deve ter sua própria pasta
- Use CSS Modules (`.module.css`) para estilos complexos
- Adapte cores para usar variáveis CSS do tema (`--color-primary`, etc.)
- Mantenha CSS isolado - não converta para `sx` prop do MUI quando houver `::before`, `::after`, `@keyframes`

## Exemplo de Estrutura

```
uiverse/
├── AnimatedButton/
│   ├── AnimatedButton.tsx
│   └── AnimatedButton.module.css
└── README.md
```

## Como Usar

Quando receber código do Uiverse:
1. Criar pasta do componente
2. Criar arquivo `.module.css` com estilos
3. Adaptar cores para variáveis do tema
4. Criar componente React TypeScript
5. Integrar com MUI quando necessário
