# -*- coding: utf-8 -*-
"""
Script para verificar outboxes failed e se são retryable
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Carregar variáveis de ambiente
from dotenv import load_dotenv
env_path = backend_dir / ".env"
load_dotenv(env_path, override=True)

from app import create_app, db
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

app = create_app()

with app.app_context():
    print("=" * 60)
    print("VERIFICACAO DE OUTBOXES FAILED")
    print("=" * 60)
    print()
    
    # Buscar outboxes failed
    failed = MetaCapiOutbox.query.filter(MetaCapiOutbox.status == "failed").all()
    
    print(f"[INFO] Total de outboxes failed: {len(failed)}")
    print()
    
    # Verificar quais são retryable
    outbox_repo = MetaCapiOutboxRepository()
    retryable = outbox_repo.get_failed_retryable(limit=1000)
    
    print(f"[INFO] Outboxes failed RETRYABLE: {len(retryable)}")
    print(f"[INFO] Outboxes failed PERMANENT: {len(failed) - len(retryable)}")
    print()
    
    # Mostrar detalhes das primeiras 5
    print("[INFO] Primeiras 5 outboxes failed:")
    for i, entry in enumerate(failed[:5], 1):
        print(f"  {i}. Outbox #{entry.id} | Pedido #{entry.order_id}")
        print(f"     Status: {entry.status} | Error Type: {entry.error_type}")
        print(f"     Attempts: {entry.attempts}")
        print(f"     Last Error: {entry.last_error[:100] if entry.last_error else 'N/A'}")
        print()
