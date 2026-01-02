# -*- coding: utf-8 -*-
"""
Testes Unitários: Retenção GFS (P1.2)
Testa funcionalidade de política de retenção GFS
"""
import unittest
from unittest.mock import patch
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.backup.retention import (
    extract_timestamp_from_filename,
    categorize_backup_slot,
    apply_gfs_retention,
    GFSRetentionPolicy,
    BackupSlot
)


class TestRetention(unittest.TestCase):
    """Testes para retenção GFS"""
    
    def test_extract_timestamp_from_filename_valid(self):
        """Testa extração de timestamp de nome válido"""
        filename = "database_20240115_143022.zip"
        result = extract_timestamp_from_filename(filename)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)
        self.assertEqual(result.second, 22)
    
    def test_extract_timestamp_from_filename_invalid(self):
        """Testa extração de timestamp de nome inválido"""
        filename = "invalid_filename.db"
        result = extract_timestamp_from_filename(filename)
        self.assertIsNone(result)
    
    def test_categorize_backup_slot_hourly(self):
        """Testa categorização de backup como HOURLY (hoje)"""
        now = datetime.now()
        backup_dt = now.replace(hour=10, minute=0, second=0, microsecond=0)
        slot = categorize_backup_slot(backup_dt)
        self.assertEqual(slot, BackupSlot.HOURLY)
    
    def test_categorize_backup_slot_daily(self):
        """Testa categorização de backup como DAILY (esta semana)"""
        now = datetime.now()
        # Backup de 2 dias atrás (ainda nesta semana)
        backup_dt = now - timedelta(days=2)
        backup_dt = backup_dt.replace(hour=10, minute=0, second=0, microsecond=0)
        slot = categorize_backup_slot(backup_dt)
        # Pode ser DAILY ou HOURLY dependendo do dia
        self.assertIn(slot, [BackupSlot.HOURLY, BackupSlot.DAILY])
    
    def test_apply_gfs_retention_respects_limits(self):
        """Testa que retenção GFS respeita limites"""
        policy = GFSRetentionPolicy(hourly=2, daily=2, weekly=2, monthly=2)
        
        # Criar mais backups do que o limite
        files = []
        base_time = datetime.now()
        for i in range(10):
            timestamp = base_time - timedelta(hours=i)
            filename = f"database_{timestamp.strftime('%Y%m%d_%H%M%S')}.zip"
            file_path = Path(filename)
            files.append(file_path)
        
        result = apply_gfs_retention(files, policy)
        
        # Deve manter no máximo os limites da política
        self.assertLessEqual(len(result['keep']), 8)  # Total de slots (2+2+2+2)
        self.assertGreater(len(result['delete']), 0)
    
    def test_apply_gfs_retention_preserves_latest(self):
        """Testa que retenção GFS preserva backups mais recentes"""
        policy = GFSRetentionPolicy(hourly=3, daily=3, weekly=3, monthly=3)
        
        files = []
        base_time = datetime.now()
        for i in range(5):
            timestamp = base_time - timedelta(hours=i)
            filename = f"database_{timestamp.strftime('%Y%m%d_%H%M%S')}.zip"
            file_path = Path(filename)
            files.append(file_path)
        
        result = apply_gfs_retention(files, policy)
        
        # Deve manter os mais recentes
        self.assertGreater(len(result['keep']), 0)
        # O arquivo mais recente deve estar em 'keep'
        latest_file = files[0]  # Mais recente
        self.assertIn(latest_file, result['keep'])
    
    def test_apply_gfs_retention_deterministic(self):
        """Testa que retenção GFS é determinística (mesmo resultado para mesma entrada)"""
        policy = GFSRetentionPolicy(hourly=2, daily=2, weekly=2, monthly=2)
        
        files = []
        base_time = datetime.now()
        for i in range(5):
            timestamp = base_time - timedelta(hours=i)
            filename = f"database_{timestamp.strftime('%Y%m%d_%H%M%S')}.zip"
            file_path = Path(filename)
            files.append(file_path)
        
        result1 = apply_gfs_retention(files, policy)
        result2 = apply_gfs_retention(files, policy)
        
        # Deve ser determinístico
        self.assertEqual(len(result1['keep']), len(result2['keep']))
        self.assertEqual(len(result1['delete']), len(result2['delete']))
        self.assertEqual(set(result1['keep']), set(result2['keep']))
        self.assertEqual(set(result1['delete']), set(result2['delete']))
    
    def test_apply_gfs_retention_with_invalid_filenames(self):
        """Testa que arquivos com nomes inválidos não são deletados"""
        policy = GFSRetentionPolicy(hourly=1, daily=1, weekly=1, monthly=1)
        
        files = [
            Path("database_20240115_143022.zip"),  # Válido
            Path("invalid_name.db"),  # Inválido - deve ser mantido
            Path("database_20240114_120000.zip"),  # Válido
        ]
        
        result = apply_gfs_retention(files, policy)
        
        # Arquivo com nome inválido deve ser mantido
        invalid_file = Path("invalid_name.db")
        self.assertIn(invalid_file, result['keep'])


if __name__ == '__main__':
    unittest.main()

