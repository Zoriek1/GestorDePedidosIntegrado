@echo off
REM Script para iniciar servidor com output sem buffering
cd /d "%~dp0"
python -u wsgi.py
