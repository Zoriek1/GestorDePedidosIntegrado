# -*- coding: utf-8 -*-
"""
Testes Unitários: Restore Smoke Test (P0.4)
Testa funcionalidade básica do teste de restauração
"""
import sys
import tempfile
import unittest
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.backup.restore_smoke_test import (  # noqa: E402
    extract_backup_if_needed,
    find_most_recent_backup,
)


class TestRestoreSmokeTest(unittest.TestCase):
    """Testes para restore smoke test"""

    def test_find_most_recent_backup(self):
        """Testa encontrar backup mais recente"""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)

            # Criar backups com timestamps diferentes
            backup1 = backup_dir / "database_20240101_100000.db"
            backup2 = backup_dir / "database_20240101_120000.db"
            backup1.touch()
            backup2.touch()

            # Ajustar timestamps (backup2 mais recente)
            import os
            import time

            now = time.time()
            os.utime(backup1, (now - 3600, now - 3600))  # 1 hora atrás
            os.utime(backup2, (now, now))  # Agora

            result = find_most_recent_backup(backup_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result.name, backup2.name)

    def test_find_most_recent_backup_empty_dir(self):
        """Testa quando não há backups"""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            result = find_most_recent_backup(backup_dir)
            self.assertIsNone(result)

    def test_extract_backup_if_needed_db(self):
        """Testa extração de backup .db"""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "database_20240101_100000.db"
            backup_path.touch()

            temp_extract_dir = Path(temp_dir) / "extract"
            temp_extract_dir.mkdir()

            result = extract_backup_if_needed(backup_path, temp_extract_dir)
            self.assertTrue(result.exists())
            self.assertEqual(result.name, backup_path.name)


if __name__ == "__main__":
    unittest.main()
