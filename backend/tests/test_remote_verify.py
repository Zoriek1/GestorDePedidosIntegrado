# -*- coding: utf-8 -*-
"""
Testes Unitários: Verificação Remota (P1.3)
Testa funcionalidade de verificação de backup remoto
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.backup.remote_verify import (  # noqa: E402
    _calculate_file_hash,
    copy_and_verify_remote,
)


class TestRemoteVerify(unittest.TestCase):
    """Testes para verificação remota"""

    def setUp(self):
        """Cria diretórios temporários para testes"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_file = self.temp_dir / "source.db"
        self.dest_dir = self.temp_dir / "dest"
        self.dest_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Limpa arquivos temporários"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_copy_and_verify_by_size_success(self):
        """Testa cópia e verificação por tamanho bem-sucedida"""
        # Criar arquivo de origem
        test_content = b"Test backup content"
        self.source_file.write_bytes(test_content)

        success, error = copy_and_verify_remote(
            source=self.source_file,
            dest_dir=self.dest_dir,
            check_hash=False,
            stability_wait_seconds=0,  # Pular stability check em testes
        )

        self.assertTrue(success)
        self.assertIsNone(error)

        # Verificar que arquivo foi copiado
        dest_file = self.dest_dir / self.source_file.name
        self.assertTrue(dest_file.exists())
        self.assertEqual(dest_file.stat().st_size, self.source_file.stat().st_size)

    def test_copy_and_verify_by_hash_success(self):
        """Testa cópia e verificação por hash bem-sucedida"""
        # Criar arquivo de origem
        test_content = b"Test backup content for hash verification"
        self.source_file.write_bytes(test_content)

        success, error = copy_and_verify_remote(
            source=self.source_file,
            dest_dir=self.dest_dir,
            check_hash=True,
            stability_wait_seconds=0,
        )

        self.assertTrue(success)
        self.assertIsNone(error)

    def test_copy_and_verify_source_not_exists(self):
        """Testa falha quando arquivo de origem não existe"""
        non_existent = self.temp_dir / "nonexistent.db"

        success, error = copy_and_verify_remote(
            source=non_existent,
            dest_dir=self.dest_dir,
            check_hash=False,
            stability_wait_seconds=0,
        )

        self.assertFalse(success)
        self.assertIsNotNone(error)
        self.assertIn("não existe", error.lower() or "not found" in error.lower())

    def test_copy_and_verify_size_mismatch(self):
        """Testa falha quando tamanho não bate"""
        from unittest.mock import patch

        test_content = b"Test content"
        self.source_file.write_bytes(test_content)

        def copy_with_wrong_size(src, dst):
            # Simula cópia mal-sucedida: destino existe, mas com tamanho diferente.
            Path(dst).write_bytes(b"x")
            return str(dst)

        with patch("scripts.backup.remote_verify.shutil.copy2", side_effect=copy_with_wrong_size):
            success, error = copy_and_verify_remote(
                source=self.source_file,
                dest_dir=self.dest_dir,
                check_hash=False,
                stability_wait_seconds=0,
            )

        self.assertFalse(success)
        self.assertIsNotNone(error)
        self.assertIn("tamanho diferente", error.lower())

    def test_calculate_file_hash(self):
        """Testa cálculo de hash SHA-256"""
        test_content = b"Test content for hash"
        self.source_file.write_bytes(test_content)

        hash1 = _calculate_file_hash(self.source_file)
        hash2 = _calculate_file_hash(self.source_file)

        # Hash deve ser determinístico
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA-256 hex = 64 caracteres

        # Hash diferente para conteúdo diferente
        self.source_file.write_bytes(b"Different content")
        hash3 = _calculate_file_hash(self.source_file)
        self.assertNotEqual(hash1, hash3)

    def test_copy_and_verify_hash_mismatch(self):
        """Testa falha quando hash não bate"""
        test_content = b"Original content"
        self.source_file.write_bytes(test_content)

        # A função copy_and_verify_remote copia primeiro, então vamos usar mock
        # para simular que o arquivo destino tem conteúdo diferente
        from unittest.mock import patch

        # Copiar arquivo correto primeiro
        dest_file = self.dest_dir / self.source_file.name
        shutil.copy2(self.source_file, dest_file)

        # Modificar destino para ter conteúdo diferente
        dest_file.write_bytes(b"Modified content")

        # Agora chamar a função - ela vai copiar novamente, mas vamos mockar
        # o cálculo de hash do destino para retornar hash diferente
        from scripts.backup.remote_verify import _calculate_file_hash

        original_hash_func = _calculate_file_hash

        def mock_hash_dest(file_path):
            if file_path == dest_file:
                # Retornar hash de conteúdo diferente
                import hashlib

                return hashlib.sha256(b"Modified content").hexdigest()
            return original_hash_func(file_path)

        with patch(
            "scripts.backup.remote_verify._calculate_file_hash",
            side_effect=mock_hash_dest,
        ):
            success, error = copy_and_verify_remote(
                source=self.source_file,
                dest_dir=self.dest_dir,
                check_hash=True,
                stability_wait_seconds=0,
            )

            # Deve falhar porque hash não bate
            self.assertFalse(success)
            self.assertIsNotNone(error)
            error_lower = error.lower() if error else ""
            self.assertTrue("hash" in error_lower or "diferente" in error_lower)


if __name__ == "__main__":
    unittest.main()
