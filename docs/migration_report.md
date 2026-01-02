# Relatório de Migração e Diferenças (Main vs Develop)

**Data:** 30 de Dezembro de 2024  
**Objetivo:** Mapear diferenças e operacionalizar a branch `develop` como sucessora da `main`.

---

## 1. Visão Geral das Diferenças

| Componente | Branch `main` (Legado) | Branch `develop` (Novo/Atual) | Status |
| :--- | :--- | :--- | :--- |
| **Frontend** | `frontend/` (HTML/JS/jQuery) | `frontend_v2/` (React/Vite/TS/MUI) | **V2 é superior**, mas o backend ainda serve a V1. |
| **Backend** | Flask | Flask + Melhorias | **Develop** tem correções críticas de startup e imports. |
| **Arquitetura** | Monolito acoplado | API REST + SPA Moderno | `develop` está pronta para desacoplamento. |
| **PWA/Offline** | Service Worker manual | `vite-plugin-pwa` + Dexie + Sync | `develop` tem offline robusto (Phase 1.3.1). |
| **Documentação** | Básica | Completa (`docs/`) | `develop` documenta todo o histórico. |

## 2. Análise Técnica

### Frontend V2 (`frontend_v2`)
- **Vantagens:** Componentização real, TypeScript (segurança), React Query (cache de servidor), MUI (UI moderna), PWA automático.
- **Estado Atual:** Funcional em modo dev (`npm run dev`), conectando ao backend via HTTPS (correção aplicada hoje).
- **Desafio:** Não está sendo servido automaticamente pelo backend em produção.

### Backend (`backend`)
- **Correções Aplicadas na Develop:**
  - `main.py`: Correção do loop de reloader que travava terminal (Porta em uso).
  - `config.py`: Alias `Config = BaseConfig` para corrigir crash de import.
  - `auth.py` / `middleware.py`: Logs de diagnóstico adicionados e ajustados.
- **Ponto de Atenção:** `backend/app/static.py` ainda aponta para `../../frontend` (V1).

## 3. Plano de Operacionalização (Tornar Develop a "Nova Main")

Para que a `develop` opere de forma "semelhante à passada porém melhor" (ou seja, rodar tudo com um comando só e entregar a interface nova):

### Passo 1: Build do Frontend V2
Gerar os arquivos estáticos otimizados do novo frontend.
- Comando: `cd frontend_v2 && npm run build`
- Saída: `frontend_v2/dist`

### Passo 2: Atualizar Backend para Servir V2
Modificar o backend para servir os arquivos da pasta `dist` do V2.
- **Arquivo:** `backend/app/static.py`
- **Mudança:** Alterar `frontend_dir` para apontar para `frontend_v2/dist`.

### Passo 3: Validação Integrada
1. Parar todos os servidores.
2. Rodar apenas `python main.py` no backend.
3. Acessar `https://localhost:5000` (ou IP).
4. **Resultado Esperado:** O novo React App deve abrir diretamente, sem precisar de `npm run dev`.

### Passo 4: Limpeza (Opcional)
- Futuramente, a pasta `frontend` antiga pode ser arquivada ou removida.
- Remover logs de debug (`log_debug`) do backend.

---

## 4. Conclusão

A branch `develop` já contém o código superior. A única "peça solta" é a integração de deployment: o backend ainda não sabe que o frontend novo existe e continua servindo o antigo. Realizando os passos acima, a `develop` se torna uma aplicação completa e moderna, substituindo totalmente a experiência da `main`.

