# -*- coding: utf-8 -*-
"""
Testes Unitários: Fail-Closed (P0.2)
Testa comportamento de bloqueio quando backup falha
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.utils.destructive_action_guard import ensure_backup_before_destructive_action, BackupRequiredException


class TestFailClosed(unittest.TestCase):
    """Testes para fail-closed"""
    
    @patch('app.utils.destructive_action_guard.create_backup')
    def test_ensure_backup_success(self, mock_create_backup):
        """Deve permitir operação se backup for criado com sucesso"""
        from pathlib import Path
        mock_backup_path = MagicMock()
        mock_backup_path.stat.return_value.st_size = 1024 * 1024
        mock_create_backup.return_value = mock_backup_path
        
        result = ensure_backup_before_destructive_action(reason='test')
        self.assertTrue(result)
        mock_create_backup.assert_called_once()
    
    @patch('app.utils.destructive_action_guard.create_backup')
    def test_ensure_backup_failure_blocks(self, mock_create_backup):
        """Deve bloquear operação se backup falhar"""
        mock_create_backup.return_value = None
        
        with self.assertRaises(BackupRequiredException):
            ensure_backup_before_destructive_action(reason='test')
    
    @patch('app.utils.destructive_action_guard.create_backup')
    @patch('app.utils.audit_logger.log_action')
    def test_ensure_backup_failure_with_override(self, mock_log_action, mock_create_backup):
        """Deve permitir override se allow_override=True"""
        mock_create_backup.return_value = None
        
        result = ensure_backup_before_destructive_action(
            reason='test',
            context={'entity_type': 'pedido', 'pedido_id': 1},
            allow_override=True,
            actor='admin'
        )
        
        self.assertTrue(result)
        # Deve registrar em auditoria
        mock_log_action.assert_called_once()
        call_args = mock_log_action.call_args
        self.assertEqual(call_args[1]['action'], 'OVERRIDE_DELETE')


if __name__ == '__main__':
    unittest.main()

