# -*- coding: utf-8 -*-
"""
Testes Unitários: Audit Log (P0.3)
Testa registro de eventos de auditoria
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class TestAuditLog(unittest.TestCase):
    """Testes para audit log"""

    @patch('app.utils.audit_logger.db')
    def test_log_action_create(self, mock_db):
        """Testa registro de ação CREATE"""
        from app.models.audit_log import AuditLog
        from app.utils.audit_logger import log_action

        mock_db.session.add = MagicMock()
        mock_db.session.commit = MagicMock()

        log_action(
            action='CREATE',
            entity_type='pedido',
            entity_id=1,
            actor='user1',
            metadata={'cliente': 'Teste'}
        )

        # Verificar que add foi chamado
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

        # Verificar argumentos
        call_args = mock_db.session.add.call_args[0][0]
        self.assertIsInstance(call_args, AuditLog)
        self.assertEqual(call_args.action, 'CREATE')
        self.assertEqual(call_args.entity_type, 'pedido')
        self.assertEqual(call_args.entity_id, 1)
        self.assertEqual(call_args.actor, 'user1')

    @patch('app.utils.audit_logger.db')
    def test_log_action_delete(self, mock_db):
        """Testa registro de ação DELETE"""
        from app.utils.audit_logger import log_action

        mock_db.session.add = MagicMock()
        mock_db.session.commit = MagicMock()

        log_action(
            action='DELETE',
            entity_type='pedido',
            entity_id=1,
            actor='user1'
        )

        mock_db.session.add.assert_called_once()
        call_args = mock_db.session.add.call_args[0][0]
        self.assertEqual(call_args.action, 'DELETE')

    @patch('app.utils.audit_logger.db')
    def test_log_action_restore(self, mock_db):
        """Testa registro de ação RESTORE"""
        from app.utils.audit_logger import log_action

        mock_db.session.add = MagicMock()
        mock_db.session.commit = MagicMock()

        log_action(
            action='RESTORE',
            entity_type='pedido',
            entity_id=1,
            actor='user1'
        )

        mock_db.session.add.assert_called_once()
        call_args = mock_db.session.add.call_args[0][0]
        self.assertEqual(call_args.action, 'RESTORE')

    @patch('app.utils.audit_logger.db')
    def test_log_action_handles_error_gracefully(self, mock_db):
        """Testa que erros em auditoria não quebram a operação principal"""
        from app.utils.audit_logger import log_action

        mock_db.session.add.side_effect = Exception("Database error")
        mock_db.session.commit = MagicMock()

        # Não deve levantar exceção
        try:
            log_action(
                action='CREATE',
                entity_type='pedido',
                entity_id=1
            )
        except Exception:
            self.fail("log_action não deve levantar exceção em caso de erro")

        # Deve ter feito rollback
        mock_db.session.rollback.assert_called_once()


if __name__ == '__main__':
    unittest.main()

