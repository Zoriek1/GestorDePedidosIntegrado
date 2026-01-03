# Exemplo de Adaptação de Componente Uiverse

## Template para Criar Componentes

Quando você me passar código do Uiverse, vou seguir este padrão:

### 1. Estrutura de Arquivos

```
uiverse/
└── NomeDoComponente/
    ├── NomeDoComponente.tsx
    └── NomeDoComponente.module.css
```

### 2. Adaptação de Cores

**Original (Uiverse):**
```css
background: #000;
color: #fff;
border: 1px solid #333;
```

**Adaptado (Tema):**
```css
background: var(--color-primary);
color: var(--color-surface);
border: 1px solid var(--color-border);
```

### 3. Componente React

```typescript
import React from 'react';
import styles from './NomeDoComponente.module.css';
import { useAnimateOnMount } from '../../../hooks/useAnimateOnMount';

interface NomeDoComponenteProps {
  // props aqui
}

export function NomeDoComponente({ ...props }: NomeDoComponenteProps) {
  const animationClass = useAnimateOnMount('fadeIn');
  
  return (
    <div className={`${styles.container} ${animationClass}`}>
      {/* conteúdo */}
    </div>
  );
}
```

### 4. CSS Module

```css
/* NomeDoComponente.module.css */
.container {
  /* Estilos adaptados do Uiverse */
  /* Usar variáveis CSS do tema */
}
```

## Regras Importantes

1. **CSS Complexo**: Manter em `.module.css`, não converter para `sx` prop
2. **Cores**: Sempre usar variáveis CSS do tema
3. **Animações**: Usar `useAnimateOnMount` hook para aplicar animate.css
4. **TypeScript**: Tipar todas as props
5. **Integração MUI**: Pode usar componentes MUI dentro, mas CSS fica isolado
