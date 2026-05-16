# Plante Uma Flor - Deploy VPS
# Targets:
#   backend     — API + SPA (Vite no build ou dist pré-compilado em docker/prebuilt-dist/)
#   scheduler   — meta-scheduler apenas Python (sem Node)

# ---------------------------------------------------------------------------
# Estágio: assets do frontend (Vite na VPS OU cópia de docker/prebuilt-dist/)
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend-assets
WORKDIR /build/frontend

ARG USE_PREBUILT_DIST=0
COPY docker/prebuilt-dist /prebuilt

COPY frontend/package.json frontend/package-lock.json ./
COPY frontend/ ./

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ARG VITE_GOOGLE_MAPS_API_KEY
ENV VITE_GOOGLE_MAPS_API_KEY=$VITE_GOOGLE_MAPS_API_KEY

# Com USE_PREBUILT_DIST=1 e index.html vindo do CI, não roda Vite na VPS.
RUN if [ "$USE_PREBUILT_DIST" = "1" ] && [ -f /prebuilt/index.html ]; then \
      echo "frontend-assets: usando prebuilt (docker/prebuilt-dist)"; \
      rm -rf dist && mkdir -p dist && cp -a /prebuilt/. dist/; \
    else \
      echo "frontend-assets: npm ci + vite build"; \
      npm ci && npm run build; \
    fi

# ---------------------------------------------------------------------------
# Target: meta-scheduler (sem frontend / sem Node)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS scheduler
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/

ENV PYTHONPATH=/app/backend
WORKDIR /app/backend

# entrypoint definido no docker-compose.yml

# ---------------------------------------------------------------------------
# Target: backend (API + static SPA)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS backend
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-assets /build/frontend/dist ./frontend/dist

ENV PYTHONPATH=/app/backend
ENV FLASK_APP=wsgi:app
WORKDIR /app/backend

RUN chmod +x /app/backend/entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/app/backend/entrypoint.sh"]
