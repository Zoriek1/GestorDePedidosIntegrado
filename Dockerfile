# Plante Uma Flor - Deploy VPS
# Multi-stage: frontend build + backend

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /build/frontend_v2

COPY frontend_v2/package.json frontend_v2/package-lock.json ./
RUN npm ci --omit=dev

COPY frontend_v2/ ./
RUN npm run build

# Stage 2: Backend
FROM python:3.11-slim
# Estrutura: /app/backend (código), /app/frontend_v2/dist (static)
# static.py: parent.parent.parent = /app
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /build/frontend_v2/dist ./frontend_v2/dist

ENV PYTHONPATH=/app/backend
ENV FLASK_APP=wsgi:app
WORKDIR /app/backend

RUN chmod +x /app/backend/entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/app/backend/entrypoint.sh"]
