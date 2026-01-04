# -*- coding: utf-8 -*-
"""
Testes Unitários: Utilitários de Drive (P1.4)
Testa funcionalidade de detecção de separação de drives
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.backup.drive_utils import get_drive_letter, check_drive_separation


class TestDriveUtils(unittest.TestCase):
    """Testes para utilitários de drive"""
    
    @patch('scripts.backup.drive_utils.sys.platform', 'win32')
    @patch('scripts.backup.drive_utils.os.path.splitdrive')
    def test_get_drive_letter_windows(self, mock_splitdrive):
        """Testa extração de letra de drive no Windows"""
        mock_splitdrive.return_value = ('C:', '\\path\\to\\file')
        
        result = get_drive_letter(Path('C:\\path\\to\\file.db'))
        
        self.assertEqual(result, 'C:')
        mock_splitdrive.assert_called_once()
    
    @patch('scripts.backup.drive_utils.sys.platform', 'linux')
    def test_get_drive_letter_linux_returns_none(self):
        """Testa que get_drive_letter retorna None no Linux"""
        result = get_drive_letter(Path('/home/user/file.db'))
        self.assertIsNone(result)
    
    @patch('scripts.backup.drive_utils.sys.platform', 'win32')
    @patch('scripts.backup.drive_utils.get_drive_letter')
    def test_check_drive_separation_same_drive_warning(self, mock_get_drive):
        """Testa warning quando DB e backup estão no mesmo drive"""
        # Todos no mesmo drive C:
        mock_get_drive.side_effect = ['C:', 'C:', 'D:']
        
        warnings = check_drive_separation(
            db_path=Path('C:\\db\\database.db'),
            backup_dir=Path('C:\\backups'),
            secondary_dir=Path('D:\\secondary')
        )
        
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any('mesmo drive' in w.lower() or 'same drive' in w.lower() for w in warnings))
    
    @patch('scripts.backup.drive_utils.sys.platform', 'win32')
    @patch('scripts.backup.drive_utils.get_drive_letter')
    def test_check_drive_separation_different_drives_ok(self, mock_get_drive):
        """Testa que não há warnings quando drives são diferentes"""
        # Cada um em drive diferente
        mock_get_drive.side_effect = ['C:', 'D:', 'E:']
        
        warnings = check_drive_separation(
            db_path=Path('C:\\db\\database.db'),
            backup_dir=Path('D:\\backups'),
            secondary_dir=Path('E:\\secondary')
        )
        
        self.assertEqual(len(warnings), 0)
    
    @patch('scripts.backup.drive_utils.sys.platform', 'linux')
    def test_check_drive_separation_linux_no_warnings(self):
        """Testa que não há warnings no Linux (sem conceito de drive)"""
        warnings = check_drive_separation(
            db_path=Path('/home/user/database.db'),
            backup_dir=Path('/home/user/backups'),
            secondary_dir=Path('/mnt/secondary')
        )
        
        self.assertEqual(len(warnings), 0)
    
    @patch('scripts.backup.drive_utils.sys.platform', 'win32')
    @patch('scripts.backup.drive_utils.get_drive_letter')
    def test_check_drive_separation_secondary_same_as_db_warning(self, mock_get_drive):
        """Testa warning quando secondary_dir está no mesmo drive do DB"""
        # Mock deve retornar baseado na ordem das chamadas:
        # 1. db_path -> 'C:'
        # 2. backup_dir -> 'D:'
        # 3. secondary_dir -> 'C:'
        call_order = []
        def mock_side_effect(path):
            call_order.append(str(path))
            if len(call_order) == 1:  # db_path
                return 'C:'
            elif len(call_order) == 2:  # backup_dir
                return 'D:'
            elif len(call_order) == 3:  # secondary_dir
                return 'C:'
            return None
        
        mock_get_drive.side_effect = mock_side_effect
        
        warnings = check_drive_separation(
            db_path=Path('C:\\db\\database.db'),
            backup_dir=Path('D:\\backups'),
            secondary_dir=Path('C:\\secondary')
        )
        
        # Verificar que warnings foram gerados
        self.assertGreater(len(warnings), 0, f"Esperado pelo menos 1 warning, mas obteve: {warnings}")
        # Verificar que há warning sobre secondary (pode ser "secundário" ou "secondary")
        has_secondary_warning = any('secondary' in w.lower() or 'secundário' in w.lower() for w in warnings)
        self.assertTrue(has_secondary_warning, f"Esperado warning sobre secondary/secundário, mas obteve: {warnings}")
    
    @patch('scripts.backup.drive_utils.sys.platform', 'win32')
    @patch('scripts.backup.drive_utils.get_drive_letter')
    def test_check_drive_separation_no_secondary_dir(self, mock_get_drive):
        """Testa que verificação funciona sem secondary_dir"""
        mock_get_drive.side_effect = ['C:', 'C:']  # DB e backup no mesmo drive
        
        warnings = check_drive_separation(
            db_path=Path('C:\\db\\database.db'),
            backup_dir=Path('C:\\backups'),
            secondary_dir=None
        )
        
        # Deve gerar warning sobre DB e backup no mesmo drive
        self.assertGreater(len(warnings), 0)


if __name__ == '__main__':
    unittest.main()

