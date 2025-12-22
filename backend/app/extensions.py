# -*- coding: utf-8 -*-
"""
Extensões Flask
"""
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Instâncias globais de extensões

db = SQLAlchemy()
cors = CORS()
