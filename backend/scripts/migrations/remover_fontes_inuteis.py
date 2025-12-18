# -*- coding: utf-8 -*-
"""
Migration: Remover fontes de pedido inúteis (WhatsApp Paula, Ifood)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.models.fonte_pedido import FontePedido
from app.models.pedido import Pedido


def remover_fontes():
    """Remove fontes 'WhatsApp Paula' e 'Ifood' do banco"""
    app = create_app()
    
    with app.app_context():
        fontes_remover = ['WhatsApp (Paula)', 'Ifood', 'ifood', 'IFood']
        
        print("=" * 50)
        print("REMOVER FONTES INÚTEIS")
        print("=" * 50)
        
        for nome_fonte in fontes_remover:
            fonte = FontePedido.query.filter_by(nome=nome_fonte).first()
            
            if fonte:
                # Conta pedidos vinculados
                pedidos_count = Pedido.query.filter_by(fonte_pedido_id=fonte.id).count()
                
                if pedidos_count > 0:
                    print(f"⚠ '{nome_fonte}' tem {pedidos_count} pedidos vinculados.")
                    print(f"  Removendo vínculo dos pedidos...")
                    Pedido.query.filter_by(fonte_pedido_id=fonte.id).update({'fonte_pedido_id': None})
                
                db.session.delete(fonte)
                print(f"✓ Fonte '{nome_fonte}' removida")
            else:
                print(f"- Fonte '{nome_fonte}' não encontrada (ok)")
        
        db.session.commit()
        
        # Lista fontes restantes
        print("\nFontes restantes:")
        for f in FontePedido.query.all():
            print(f"  - {f.nome}")
        
        print("\n✓ Concluído!")


if __name__ == '__main__':
    remover_fontes()
