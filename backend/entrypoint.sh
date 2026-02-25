#!/bin/sh
set -e
# Migrations (quando usar Flask-Migrate)
if command -v flask >/dev/null 2>&1; then
    flask db upgrade 2>/dev/null || true
fi
exec python wsgi.py
