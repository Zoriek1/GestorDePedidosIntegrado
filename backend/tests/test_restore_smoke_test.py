# -*- coding: utf-8 -*-
"""
Testes Unitários: Restore Smoke Test (P0.4)
Testa funcionalidade básica do teste de restauração
"""
import sqlite3
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
    run_integrity_check,
    run_sanity_checks,
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

    def test_run_integrity_check_valid_db(self):
        """Testa integrity check em banco válido"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"

            # Criar banco SQLite válido
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.commit()
            conn.close()

            success, msg = run_integrity_check(db_path)
            self.assertTrue(success)
            self.assertEqual(msg, 'ok')

    def test_run_sanity_checks_valid_db(self):
        """Testa sanity checks em banco válido"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"

            # Criar banco SQLite com tabelas essenciais
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE pedidos (id INTEGER)")
            conn.execute("CREATE TABLE clientes (id INTEGER)")
            conn.execute("CREATE TABLE fonte_pedido (id INTEGER)")
            conn.execute("INSERT INTO pedidos (id) VALUES (1)")
            conn.execute("INSERT INTO clientes (id) VALUES (1)")
            conn.commit()
            conn.close()

            success, errors = run_sanity_checks(db_path)
            self.assertTrue(success)
            self.assertEqual(len(errors), 0)

    def test_run_sanity_checks_missing_table(self):
        """Testa sanity checks quando falta tabela essencial"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"

            # Criar banco SQLite sem tabela pedidos
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE clientes (id INTEGER)")
            conn.commit()
            conn.close()

            success, errors = run_sanity_checks(db_path)
            self.assertFalse(success)
            self.assertGreater(len(errors), 0)
            self.assertTrue(any('pedidos' in err.lower() for err in errors))


if __name__ == '__main__':
    unittest.main()

