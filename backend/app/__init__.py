# -*- coding: utf-8 -*-
"""
Plante Uma Flor v3.0 - PWA
Sistema de Gerenciamento de Pedidos - Backend Flask API

Este módulo exporta apenas as interfaces públicas:
- db: Instância global do SQLAlchemy
- create_app: Application Factory

IMPORTANTE: Manter esta estrutura simples garante que todos os imports
existentes continuem funcionando:
- from app import db ✅
- from app import create_app ✅
- from app import create_app, db ✅
"""
from app.extensions import db
from app.factory import create_app

__all__ = ["db", "create_app"]
