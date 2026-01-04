# -*- coding: utf-8 -*-
"""
Testes Unitários: Soft Delete (P0.3)
Testa funcionalidade de soft delete em pedidos
"""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class TestSoftDelete(unittest.TestCase):
    """Testes para soft delete"""

    def test_pedido_is_deleted_property(self):
        """Testa propriedade is_deleted"""
        from app.models.pedido import Pedido

        pedido = Pedido()
        self.assertFalse(pedido.is_deleted)

        pedido.deleted_at = datetime.utcnow()
        self.assertTrue(pedido.is_deleted)

    def test_pedido_soft_delete(self):
        """Testa método soft_delete()"""
        from app.models.pedido import Pedido

        pedido = Pedido()
        self.assertIsNone(pedido.deleted_at)

        pedido.soft_delete()
        self.assertIsNotNone(pedido.deleted_at)
        self.assertTrue(pedido.is_deleted)

    def test_pedido_restore(self):
        """Testa método restore()"""
        from app.models.pedido import Pedido

        pedido = Pedido()
        pedido.deleted_at = datetime.utcnow()
        self.assertTrue(pedido.is_deleted)

        pedido.restore()
        self.assertIsNone(pedido.deleted_at)
        self.assertFalse(pedido.is_deleted)

    @patch('app.repositories.pedido_repository.db')
    def test_repository_soft_delete_pedido(self, mock_db):
        """Testa soft_delete_pedido no repository"""
        from app import create_app
        from app.models.pedido import Pedido
        from app.repositories.pedido_repository import PedidoRepository

        # Criar app context
        app = create_app()
        with app.app_context():
            repo = PedidoRepository()

            # Mock do pedido
            pedido = MagicMock(spec=Pedido)
            pedido.id = 1
            pedido.is_deleted = False
            pedido.soft_delete = MagicMock()
            pedido.cliente = "Teste"
            pedido.destinatario = "Dest"

            # Mock get_by_id
            repo.get_by_id = MagicMock(return_value=pedido)

            # Mock commit
            mock_db.session.commit = MagicMock()

            # Mock log_action (importado dentro do método)
            with patch('app.utils.audit_logger.log_action') as mock_log:
                result = repo.soft_delete_pedido(1, actor='test')

                self.assertIsNotNone(result)
                pedido.soft_delete.assert_called_once()
                mock_log.assert_called_once()
                self.assertEqual(mock_log.call_args[1]['action'], 'DELETE')

    @patch('app.repositories.pedido_repository.db')
    def test_repository_restore_pedido(self, mock_db):
        """Testa restore_pedido no repository"""
        from app import create_app
        from app.models.pedido import Pedido
        from app.repositories.pedido_repository import PedidoRepository

        # Criar app context
        app = create_app()
        with app.app_context():
            repo = PedidoRepository()

            # Mock do pedido deletado
            pedido = MagicMock(spec=Pedido)
            pedido.id = 1
            pedido.is_deleted = True
            pedido.restore = MagicMock()
            pedido.cliente = "Teste"
            pedido.destinatario = "Dest"

            # Mock get_by_id
            repo.get_by_id = MagicMock(return_value=pedido)

            # Mock commit
            mock_db.session.commit = MagicMock()

            # Mock log_action (importado dentro do método)
            with patch('app.utils.audit_logger.log_action') as mock_log:
                result = repo.restore_pedido(1, actor='test')

                self.assertIsNotNone(result)
                pedido.restore.assert_called_once()
                mock_log.assert_called_once()
                self.assertEqual(mock_log.call_args[1]['action'], 'RESTORE')


if __name__ == '__main__':
    unittest.main()

