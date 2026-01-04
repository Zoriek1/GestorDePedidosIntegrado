# -*- coding: utf-8 -*-
"""
Testes Unitários: Status de Backup (P1.5)
Testa funcionalidade de status persistente de backup
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.backup.status import (
    BackupStatus,
    read_backup_status,
    update_backup_status,
    get_backup_health,
    get_status_file_path
)


class TestBackupStatus(unittest.TestCase):
    """Testes para status de backup"""
    
    def setUp(self):
        """Configura ambiente de teste"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Limpa arquivos temporários"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('scripts.backup.status.Config')
    def test_read_backup_status_empty_file(self, mock_config):
        """Testa leitura de status quando arquivo não existe"""
        mock_config.INSTANCE_DIR = self.temp_dir
        
        status = read_backup_status()
        
        self.assertIsNotNone(status)
        self.assertIsNone(status.last_backup_ok_at)
        self.assertEqual(status.backups_local_count, 0)
    
    @patch('scripts.backup.status.Config')
    def test_read_write_backup_status_atomic(self, mock_config):
        """Testa escrita e leitura atômica de status"""
        mock_config.INSTANCE_DIR = self.temp_dir
        
        # Escrever status
        test_timestamp = datetime.now().isoformat()
        update_backup_status(last_backup_ok_at=test_timestamp, backups_local_count=5)
        
        # Ler status
        status = read_backup_status()
        
        self.assertEqual(status.last_backup_ok_at, test_timestamp)
        self.assertEqual(status.backups_local_count, 5)
    
    @patch('scripts.backup.status.Config')
    def test_update_backup_status_partial(self, mock_config):
        """Testa atualização parcial de status"""
        mock_config.INSTANCE_DIR = self.temp_dir
        
        # Atualizar apenas um campo
        test_timestamp = datetime.now().isoformat()
        update_backup_status(last_backup_ok_at=test_timestamp)
        
        status = read_backup_status()
        self.assertEqual(status.last_backup_ok_at, test_timestamp)
        # Outros campos devem manter valores padrão ou anteriores
        self.assertIsNone(status.last_backup_error)
    
    @patch('scripts.backup.status.Config')
    def test_health_rules_ok_warn_fail(self, mock_config):
        """Testa regras de health OK/WARN/FAIL"""
        mock_config.INSTANCE_DIR = self.temp_dir
        
        # Health OK: backup recente
        now = datetime.now()
        update_backup_status(last_backup_ok_at=now.isoformat())
        health = get_backup_health(max_age_hours=24)
        self.assertEqual(health['health'], 'OK')
        self.assertEqual(len(health['issues']), 0)
        
        # Health FAIL: backup muito antigo
        old_time = now - timedelta(hours=25)
        update_backup_status(last_backup_ok_at=old_time.isoformat())
        health = get_backup_health(max_age_hours=24)
        self.assertEqual(health['health'], 'FAIL')
        self.assertGreater(len(health['issues']), 0)
        
        # Health FAIL: restore test falhou
        update_backup_status(
            last_backup_ok_at=now.isoformat(),
            last_restore_test_error='Test failed'
        )
        health = get_backup_health(max_age_hours=24)
        self.assertEqual(health['health'], 'FAIL')
        self.assertTrue(any('restore test' in issue.lower() for issue in health['issues']))
        
        # Health WARN: remoto não OK há mais de 24h (sem erro de restore test)
        old_remote = now - timedelta(hours=25)
        update_backup_status(
            last_backup_ok_at=now.isoformat(),
            last_remote_ok_at=old_remote.isoformat(),
            last_restore_test_error=None  # Limpar erro anterior
        )
        health = get_backup_health(max_age_hours=24)
        self.assertEqual(health['health'], 'WARN')
        self.assertTrue(any('remoto' in issue.lower() or 'remote' in issue.lower() for issue in health['issues']))
    
    @patch('scripts.backup.status.Config')
    def test_status_persistence(self, mock_config):
        """Testa persistência de status entre leituras"""
        mock_config.INSTANCE_DIR = self.temp_dir
        
        # Escrever status com múltiplos campos
        backup_time = datetime.now().isoformat()
        remote_time = (datetime.now() - timedelta(hours=1)).isoformat()
        update_backup_status(
            last_backup_ok_at=backup_time,
            last_remote_ok_at=remote_time,
            backups_local_count=10,
            backups_remote_count=5
        )
        
        # Ler múltiplas vezes - deve ser consistente
        status1 = read_backup_status()
        status2 = read_backup_status()
        
        self.assertEqual(status1.last_backup_ok_at, status2.last_backup_ok_at)
        self.assertEqual(status1.last_remote_ok_at, status2.last_remote_ok_at)
        self.assertEqual(status1.backups_local_count, status2.backups_local_count)
        self.assertEqual(status1.backups_remote_count, status2.backups_remote_count)
    
    def test_backup_status_to_dict(self):
        """Testa conversão de BackupStatus para dicionário"""
        status = BackupStatus(
            last_backup_ok_at='2024-01-15T10:00:00',
            backups_local_count=5
        )
        
        status_dict = status.to_dict()
        
        self.assertEqual(status_dict['last_backup_ok_at'], '2024-01-15T10:00:00')
        self.assertEqual(status_dict['backups_local_count'], 5)
        self.assertIsNone(status_dict['last_backup_error'])


if __name__ == '__main__':
    unittest.main()

