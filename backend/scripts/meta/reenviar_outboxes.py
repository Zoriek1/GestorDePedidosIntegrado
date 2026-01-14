# -*- coding: utf-8 -*-
"""
Script para reenviar outboxes (marca como pending para reenvio)
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
from app.models.pedido import datetime_now_brazil

app = create_app()

with app.app_context():
    print("=" * 60)
    print("REENVIAR OUTBOXES META CAPI")
    print("=" * 60)
    print()
    
    # Buscar todos os registros enviados
    sent_entries = MetaCapiOutbox.query.filter_by(status="sent").all()
    
    print(f"[INFO] Total de registros enviados encontrados: {len(sent_entries)}")
    print()
    
    if not sent_entries:
        print("[INFO] Nenhum registro para reenviar")
        sys.exit(0)
    
    # Confirmar
    print(f"[AVISO] Isso vai marcar {len(sent_entries)} registros como 'pending' para reenvio")
    print("[AVISO] Os eventos serão reenviados para a Meta")
    print()
    
    # Marcar como pending
    print("[INFO] Marcando registros como pending...")
    updated_count = 0
    
    for entry in sent_entries:
        entry.status = "pending"
        entry.attempts = 0  # Resetar tentativas
        entry.last_error = None  # Limpar erro anterior
        entry.error_type = None  # Limpar tipo de erro
        entry.sent_at = None  # Limpar timestamp de envio
        entry.updated_at = datetime_now_brazil()
        updated_count += 1
    
    db.session.commit()
    
    print(f"[OK] {updated_count} registros marcados como pending")
    print()
    print("[INFO] Execute o script de envio para processar:")
    print("   python backend/scripts/meta/send_daily_purchases_to_meta.py")
    print()
