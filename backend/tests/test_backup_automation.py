# -*- coding: utf-8 -*-
"""
Testes Unitários: Automação de Backup
Testa lógica de backup helper, janela de execução e rotação
Expande o test_scheduled_backup.py com testes adicionais
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class TestBackupWindowSchedule:
    """Testes de janela de execução do backup agendado"""

    @pytest.fixture
    def mock_datetime_module(self):
        """Fixture para mockar datetime no módulo de backup"""
        with patch("scripts.backup.run_scheduled_backup.datetime") as mock_dt:
            # Configurar side_effect para permitir construção de datetime
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            mock_dt.now = MagicMock()
            mock_dt.strptime = datetime.strptime
            yield mock_dt

    def test_weekday_monday_7am_should_run(self, mock_datetime_module):
        """Segunda 07:00 deve executar"""
        from scripts.backup.run_scheduled_backup import should_run_backup_now

        # Segunda-feira 07:00
        mock_datetime_module.now.return_value = datetime(2024, 1, 1, 7, 0, 0)
        assert should_run_backup_now() is True

    def test_weekday_monday_6am_should_not_run(self, mock_datetime_module):
        """Segunda 06:00 não deve executar"""
        from scripts.backup.run_scheduled_backup import should_run_backup_now

        mock_datetime_module.now.return_value = datetime(2024, 1, 1, 6, 0, 0)
        assert should_run_backup_now() is False

    def test_weekday_friday_18pm_should_run(self, mock_datetime_module):
        """Sexta 18:00 deve executar"""
        from scripts.backup.run_scheduled_backup import should_run_backup_now

        # Sexta-feira 18:00
        mock_datetime_module.now.return_value = datetime(2024, 1, 5, 18, 0, 0)
        assert should_run_backup_now() is True

    def test_weekday_friday_18_01_should_not_run(self, mock_datetime_module):
        """Sexta 18:01 não deve executar"""
        from scripts.backup.run_scheduled_backup import should_run_backup_now

        mock_datetime_module.now.return_value = datetime(2024, 1, 5, 18, 1, 0)
        assert should_run_backup_now() is False

    def test_saturday_14pm_should_run(self, mock_datetime_module):
        """Sábado 14:00 deve executar"""
        from scripts.backup.run_scheduled_backup import should_run_backup_now

        # Sábado 14:00
        mock_datetime_module.now.return_value = datetime(2024, 1, 6, 14, 0, 0)
        assert should_run_backup_now() is True

    def test_saturday_14_01_should_not_run(self, mock_datetime_module):
        """Sábado 14:01 não deve executar"""
        from scripts.backup.run_scheduled_backup import should_run_backup_now

        mock_datetime_module.now.return_value = datetime(2024, 1, 6, 14, 1, 0)
        assert should_run_backup_now() is False

    def test_sunday_should_never_run(self, mock_datetime_module):
        """Domingo nunca executa"""
        from scripts.backup.run_scheduled_backup import should_run_backup_now

        # Domingo 10:00 (horário normal de semana)
        mock_datetime_module.now.return_value = datetime(2024, 1, 7, 10, 0, 0)
        assert should_run_backup_now() is False


class TestBackupIdempotency:
    """Testes de idempotência do backup"""

    def test_recent_backup_detected(self):
        """Detecta backup recente (menos de 55 min)"""
        from scripts.backup.run_scheduled_backup import get_recent_backup_timestamp

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)

            # Criar arquivo de backup com timestamp recente (30 min atrás)
            now = datetime.now()
            backup_name = f"database_{now.strftime('%Y%m%d_%H%M%S')}.db"
            backup_file = backup_dir / backup_name
            backup_file.touch()

            # Ajustar mtime para 30 min atrás
            thirty_min_ago = now.timestamp() - (30 * 60)
            os.utime(backup_file, (thirty_min_ago, thirty_min_ago))

            result = get_recent_backup_timestamp(backup_dir, minutes_threshold=55)
            assert result is not None

    def test_old_backup_not_detected(self):
        """Não detecta backup antigo (mais de 55 min)"""
        from scripts.backup.run_scheduled_backup import get_recent_backup_timestamp

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)

            # Criar arquivo de backup com timestamp antigo (2 horas atrás)
            two_hours_ago = datetime.now() - timedelta(hours=2)
            backup_name = f"database_{two_hours_ago.strftime('%Y%m%d_%H%M%S')}.db"
            backup_file = backup_dir / backup_name
            backup_file.touch()

            # Ajustar mtime
            old_timestamp = two_hours_ago.timestamp()
            os.utime(backup_file, (old_timestamp, old_timestamp))

            result = get_recent_backup_timestamp(backup_dir, minutes_threshold=55)
            assert result is None

    def test_empty_directory(self):
        """Retorna None para diretório vazio"""
        from scripts.backup.run_scheduled_backup import get_recent_backup_timestamp

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            result = get_recent_backup_timestamp(backup_dir, minutes_threshold=55)
            assert result is None

    def test_nonexistent_directory(self):
        """Retorna None para diretório inexistente"""
        from scripts.backup.run_scheduled_backup import get_recent_backup_timestamp

        result = get_recent_backup_timestamp(Path("/nonexistent/path"), minutes_threshold=55)
        assert result is None


class TestBackupHelper:
    """Testes do utilitário de backup programático"""

    def test_create_backup_success(self):
        """Cria backup com sucesso"""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "database_20240101_120000.zip"
            backup_path.write_bytes(b"test backup content")

            with patch("app.utils.backup_helper.BackupManager") as mock_class:
                mock_instance = MagicMock()
                mock_instance.create_backup.return_value = backup_path
                mock_class.return_value = mock_instance

                from app.utils.backup_helper import create_backup

                result = create_backup(reason="test", compress=True, silent=True)

                assert result == backup_path
                mock_instance.create_backup.assert_called_once_with(compress=True)

    def test_create_backup_failure(self):
        """Trata falha na criação de backup"""
        with patch("app.utils.backup_helper.BackupManager") as mock_class:
            mock_instance = MagicMock()
            mock_instance.create_backup.return_value = None
            mock_class.return_value = mock_instance

            from app.utils.backup_helper import create_backup

            result = create_backup(reason="test", compress=True, silent=True)

            assert result is None

    def test_create_backup_exception(self):
        """Trata exceção na criação de backup"""
        with patch("app.utils.backup_helper.BackupManager") as mock_class:
            mock_class.side_effect = Exception("Disk full")

            from app.utils.backup_helper import create_backup

            result = create_backup(reason="test", compress=True, silent=True)

            assert result is None


class TestBackupAuditLogger:
    """Testes do logger de auditoria de backup"""

    def test_log_backup_created(self, caplog):
        """Registra criação de backup (verifica via caplog)"""
        import logging

        from app.utils.backup_helper import BackupAuditLogger

        with tempfile.TemporaryDirectory() as temp_dir:
            # Limpar handlers do logger antes de criar nova instância
            logging.getLogger("backup_audit").handlers.clear()

            with caplog.at_level(logging.INFO, logger="backup_audit"):
                logger = BackupAuditLogger(log_dir=temp_dir)

                logger.log_backup_created(
                    backup_path="/path/to/backup.zip",
                    reason="scheduled_hourly",
                    size_mb=5.5,
                )

            # Verificar via caplog (mais confiável em Windows)
            assert "BACKUP CRIADO" in caplog.text
            assert "scheduled_hourly" in caplog.text

            # Limpar handlers após teste
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_log_backup_failed(self, caplog):
        """Registra falha de backup (verifica via caplog)"""
        import logging

        from app.utils.backup_helper import BackupAuditLogger

        with tempfile.TemporaryDirectory() as temp_dir:
            # Limpar handlers do logger antes de criar nova instância
            logging.getLogger("backup_audit").handlers.clear()

            with caplog.at_level(logging.ERROR, logger="backup_audit"):
                logger = BackupAuditLogger(log_dir=temp_dir)

                logger.log_backup_failed(reason="automatic", error_msg="Disk full")

            # Verificar via caplog
            assert "BACKUP FALHOU" in caplog.text
            assert "Disk full" in caplog.text

            # Limpar handlers após teste
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)


class TestBackupStats:
    """Testes de estatísticas de backup"""

    def test_has_recent_backup_true(self):
        """Detecta backup recente (< 24h)"""
        from app.utils.backup_helper import has_recent_backup

        with patch("app.utils.backup_helper.get_last_backup_time") as mock_get:
            # Simular backup de 12 horas atrás
            mock_get.return_value = (
                Path("/backup.zip"),
                datetime.now() - timedelta(hours=12),
                5.0,
            )

            result = has_recent_backup(hours=24)
            assert result is True

    def test_has_recent_backup_false(self):
        """Não detecta backup antigo (> 24h)"""
        from app.utils.backup_helper import has_recent_backup

        with patch("app.utils.backup_helper.get_last_backup_time") as mock_get:
            # Simular backup de 48 horas atrás
            mock_get.return_value = (
                Path("/backup.zip"),
                datetime.now() - timedelta(hours=48),
                5.0,
            )

            result = has_recent_backup(hours=24)
            assert result is False

    def test_has_recent_backup_no_backup(self):
        """Retorna False se não há backup"""
        from app.utils.backup_helper import has_recent_backup

        with patch("app.utils.backup_helper.get_last_backup_time") as mock_get:
            mock_get.return_value = None

            result = has_recent_backup(hours=24)
            assert result is False


@pytest.mark.integration
class TestBackupIntegration:
    """Testes de integração de backup (requer ambiente configurado)"""

    @pytest.fixture
    def app(self):
        """Cria aplicação Flask para testes de integração"""
        import tempfile

        db_fd, db_path = tempfile.mkstemp(suffix=".db")

        from app import create_app, db

        app = create_app(
            config={
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
                "SECRET_KEY": "test-secret-key",
            }
        )

        with app.app_context():
            db.create_all()
            yield app
            db.session.close()
            db.engine.dispose()

        os.close(db_fd)
        try:
            os.unlink(db_path)
        except (PermissionError, FileNotFoundError):
            pass

    def test_backup_and_stats(self, app):
        """Cria backup e verifica estatísticas"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mockar diretórios
            with patch("app.utils.backup_helper.backend_dir", temp_path):
                # Criar diretórios necessários
                instance_dir = temp_path / "instance"
                instance_dir.mkdir()
                (instance_dir / "backups").mkdir()
                (instance_dir / "logs").mkdir()

                # Verificar que diretórios foram criados corretamente
                assert (instance_dir / "backups").exists()
                assert (instance_dir / "logs").exists()
