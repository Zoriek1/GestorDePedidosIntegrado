# -*- coding: utf-8 -*-
"""
Testes Unitários: Backup Agendado (P0.1)
Testa lógica de janela de execução e idempotência
"""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.backup.run_scheduled_backup import (  # noqa: E402
    get_recent_backup_timestamp,
    should_run_backup_now,
)


class TestScheduledBackup(unittest.TestCase):
    """Testes para backup agendado"""

    def test_should_run_backup_now_segunda_07_00(self):
        """Segunda-feira 07:00 deve executar"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 7, 0, 0)  # Segunda 07:00
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = should_run_backup_now()
            self.assertTrue(result)

    def test_should_run_backup_now_segunda_18_00(self):
        """Segunda-feira 18:00 deve executar"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 18, 0, 0)  # Segunda 18:00
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = should_run_backup_now()
            self.assertTrue(result)

    def test_should_run_backup_now_segunda_06_59(self):
        """Segunda-feira 06:59 não deve executar"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 6, 59, 0)  # Segunda 06:59
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = should_run_backup_now()
            self.assertFalse(result)

    def test_should_run_backup_now_segunda_18_01(self):
        """Segunda-feira 18:01 não deve executar"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 18, 1, 0)  # Segunda 18:01
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = should_run_backup_now()
            self.assertFalse(result)

    def test_should_run_backup_now_sabado_07_00(self):
        """Sábado 07:00 deve executar"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 6, 7, 0, 0)  # Sábado 07:00
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = should_run_backup_now()
            self.assertTrue(result)

    def test_should_run_backup_now_sabado_14_00(self):
        """Sábado 14:00 deve executar"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 6, 14, 0, 0)  # Sábado 14:00
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = should_run_backup_now()
            self.assertTrue(result)

    def test_should_run_backup_now_sabado_06_59(self):
        """Sábado 06:59 não deve executar"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 6, 6, 59, 0)  # Sábado 06:59
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = should_run_backup_now()
            self.assertFalse(result)

    def test_should_run_backup_now_sabado_14_01(self):
        """Sábado 14:01 não deve executar"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 6, 14, 1, 0)  # Sábado 14:01
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = should_run_backup_now()
            self.assertFalse(result)

    def test_should_run_backup_now_domingo(self):
        """Domingo não deve executar"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 7, 10, 0, 0)  # Domingo 10:00
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = should_run_backup_now()
            self.assertFalse(result)

    def test_get_recent_backup_timestamp_with_recent_backup(self):
        """Deve encontrar backup recente"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)

            # Criar backup "recente" (30 minutos atrás)
            now = datetime.now()
            backup_file = backup_dir / f"database_{now.strftime('%Y%m%d_%H%M%S')}.db"
            backup_file.touch()

            # Ajustar timestamp para 30 minutos atrás
            import os

            thirty_min_ago = now.timestamp() - 30 * 60
            os.utime(backup_file, (thirty_min_ago, thirty_min_ago))

            result = get_recent_backup_timestamp(backup_dir, minutes_threshold=55)
            self.assertIsNotNone(result)

    def test_get_recent_backup_timestamp_with_old_backup(self):
        """Não deve encontrar backup antigo"""
        import tempfile
        from datetime import timedelta
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)

            # Criar backup "antigo" (2 horas atrás)
            # Usar timestamp no nome do arquivo que seja antigo
            two_hours_ago = datetime.now() - timedelta(hours=2)
            backup_file = backup_dir / f"database_{two_hours_ago.strftime('%Y%m%d_%H%M%S')}.db"
            backup_file.touch()

            # Ajustar timestamp do arquivo para 2 horas atrás também
            import os

            file_timestamp = two_hours_ago.timestamp()
            os.utime(backup_file, (file_timestamp, file_timestamp))

            result = get_recent_backup_timestamp(backup_dir, minutes_threshold=55)
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
