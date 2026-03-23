# Diagnóstico de deploy — RAM/CPU e pipeline

Runbook da **Fase 1** (correlação de picos) e notas sobre **recursão vs infra**.

## 1. Onde correlacionar o pico

Em push para `main`, o fluxo é:

1. **GitHub Actions** — jobs paralelos `backend` e `frontend`; o `frontend` roda `npm run build` no runner (`ubuntu-22.04`).
2. **Após ambos** — job `deploy` executa SSH na VPS: `git pull` + `docker compose up -d --build`.

**Como correlacionar:**

- No **GitHub**: abra o workflow → job **Frontend** (duração do step *Build*) e job **Deploy** (duração total / timeout).
- Na **VPS** (no horário do deploy): `htop` ou `docker stats` e, em outro terminal, acompanhe `docker compose build --progress=plain` (ou os logs do Actions no passo SSH).

Picos **simultâneos** (runner + VPS) somam carga; em VPS **4GB**, dois processos Node pesados (ou build Docker paralelo) agravam OOM/swap.

## 2. Build Compose — frontend uma ou duas vezes?

Antes da refatoração, `backend` e `meta-scheduler` usavam o mesmo `Dockerfile` completo (incluindo estágio Node). Com **BuildKit**, a segunda imagem costuma **reutilizar cache** de layers, mas builds **paralelos** ou **cache frio** podem gerar dois picos de `npm run build`.

**Comando (na VPS ou máquina local com Docker):**

```bash
cd /caminho/do/repo
docker compose build --progress=plain 2>&1 | tee /tmp/compose-build.log
```

Verifique quantas vezes aparecem linhas equivalentes a `npm run build` / estágio `frontend-assets` e se a segunda passagem indica `CACHED`.

**Após esta entrega:**

- **`meta-scheduler`** usa `target: scheduler` (só Python, **sem** Node).
- **`backend`** usa `target: backend` (Node/Vite ou `dist` pré-compilado via CI).
- Deploy em CI envia o `dist` do job frontend para `docker/prebuilt-dist/` e define `USE_PREBUILT_DIST=1` para **não** rodar Vite de novo na VPS.

## 3. Recursão / loop no backend

Suspeita de **recursão infinita** ou loop Python faz sentido para **CPU alta em runtime** (processo `python`/`waitress` contínuo), não como causa típica de pico **durante** `docker build`.

Se o sintoma for runtime:

- Coletar **logs** do container e **stack trace** (se houver).
- O **meta-scheduler** ([`backend/meta_scheduler_entrypoint.py`](../backend/meta_scheduler_entrypoint.py)) usa loop com `sleep`, não recursão profunda.

## 4. Validação (após ajustes na pipeline)

- **Deploy via Actions:** no log do job *Docker compose*, o build da imagem `backend` deve mostrar `frontend-assets: usando prebuilt` (e **não** `npm ci + vite build`).
- **Imagem do scheduler:** `docker compose build meta-scheduler` não deve listar estágios `node` / `npm`.
- **Local/VPS com Docker:** `docker compose build --progress=plain` e conferir uma única passagem pesada de frontend no serviço `backend` quando `USE_PREBUILT_DIST=0`.

## 5. Referências

- [DEPLOY_VPS.md](./DEPLOY_VPS.md) — fluxo Docker e variáveis.
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — CI e deploy.
