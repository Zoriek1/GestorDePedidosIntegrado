# -*- coding: utf-8 -*-
"""
Testes Unitários: Validação de Banco de Dados (P1.1)
Testa funcionalidade de validação padronizada de backups restaurados
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import sqlite3
import tempfile
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.backup.validate_db import validate_restored_db, ValidationResult


class TestValidateDb(unittest.TestCase):
    """Testes para validação de banco de dados"""
    
    def setUp(self):
        """Cria banco de dados temporário para testes"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / 'test.db'
    
    def tearDown(self):
        """Limpa arquivos temporários"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_test_db(self, with_tables=True, with_app_meta=False, schema_version=None):
        """Cria banco de teste com estrutura básica"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        if with_tables:
            # Criar tabelas essenciais
            cursor.execute("""
                CREATE TABLE pedidos (
                    id INTEGER PRIMARY KEY,
                    cliente TEXT,
                    status TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE clientes (
                    id INTEGER PRIMARY KEY,
                    nome TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE fonte_pedido (
                    id INTEGER PRIMARY KEY,
                    nome TEXT
                )
            """)
            
            # Inserir dados básicos
            cursor.execute("INSERT INTO pedidos (cliente, status) VALUES ('Teste', 'ativo')")
            cursor.execute("INSERT INTO clientes (nome) VALUES ('Cliente Teste')")
        
        if with_app_meta:
            cursor.execute("""
                CREATE TABLE app_meta (
                    key VARCHAR(50) PRIMARY KEY,
                    value TEXT
                )
            """)
            if schema_version:
                cursor.execute(
                    "INSERT INTO app_meta (key, value) VALUES ('schema_version', ?)",
                    (schema_version,)
                )
        
        conn.commit()
        conn.close()
    
    def test_validation_success(self):
        """Testa validação bem-sucedida"""
        self._create_test_db(with_app_meta=True, schema_version='1.0')
        
        result = validate_restored_db(
            db_path=self.db_path,
            app_schema_version='1.0',
            check_invariants=False
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.errors), 0)
    
    def test_integrity_check_failure_returns_error(self):
        """Testa que integrity check falho retorna erro"""
        # Criar arquivo vazio (não é um banco válido)
        # SQLite pode conectar a arquivo vazio, mas integrity_check falhará
        self.db_path.write_bytes(b'')
        
        result = validate_restored_db(
            db_path=self.db_path,
            app_schema_version='1.0',
            check_invariants=False
        )
        
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        # Verificar se há qualquer erro relacionado
        # Pode ser erro de conexão, integrity check, ou exceção
        error_text = ' '.join(result.errors).lower()
        # Aceitar qualquer erro (pode ser "integrity", "erro", "error", "exception", "database", etc)
        self.assertTrue(len(error_text) > 0)  # Apenas verificar que há erro
    
    def test_essential_tables_missing_returns_error(self):
        """Testa que tabelas essenciais ausentes retornam erro"""
        # Criar banco vazio (sem tabelas)
        conn = sqlite3.connect(str(self.db_path))
        conn.close()
        
        result = validate_restored_db(
            db_path=self.db_path,
            app_schema_version='1.0',
            check_invariants=False
        )
        
        self.assertFalse(result.success)
        # Deve ter erro sobre tabelas essenciais
        error_messages = ' '.join(result.errors).lower()
        self.assertTrue('pedidos' in error_messages or 'essencial' in error_messages)
    
    def test_schema_version_incompatible_returns_error(self):
        """Testa que schema_version incompatível retorna erro"""
        self._create_test_db(with_app_meta=True, schema_version='0.9')
        
        result = validate_restored_db(
            db_path=self.db_path,
            app_schema_version='1.0',
            check_invariants=False
        )
        
        self.assertFalse(result.success)
        self.assertTrue(any('incompatibilidade' in error.lower() or 'schema_version' in error.lower() for error in result.errors))
    
    def test_schema_version_compatible_succeeds(self):
        """Testa que schema_version compatível passa"""
        self._create_test_db(with_app_meta=True, schema_version='1.0')
        
        result = validate_restored_db(
            db_path=self.db_path,
            app_schema_version='1.0',
            check_invariants=False
        )
        
        self.assertTrue(result.success)
    
    def test_schema_version_missing_returns_warning(self):
        """Testa que schema_version ausente retorna warning (não erro)"""
        self._create_test_db(with_app_meta=False)
        
        result = validate_restored_db(
            db_path=self.db_path,
            app_schema_version='1.0',
            check_invariants=False
        )
        
        # Deve ter sucesso mas com warning
        self.assertTrue(result.success)
        self.assertGreater(len(result.warnings), 0)
        self.assertTrue(any('schema_version' in warning.lower() for warning in result.warnings))
    
    def test_invariants_check_optional(self):
        """Testa que check de invariantes é opcional"""
        self._create_test_db(with_app_meta=True, schema_version='1.0')
        
        # Sem check_invariants
        result1 = validate_restored_db(
            db_path=self.db_path,
            app_schema_version='1.0',
            check_invariants=False
        )
        self.assertTrue(result1.success)
        
        # Com check_invariants
        result2 = validate_restored_db(
            db_path=self.db_path,
            app_schema_version='1.0',
            check_invariants=True
        )
        # Deve passar também (não tem foreign keys violadas)
        self.assertTrue(result2.success)
    
    def test_file_not_found_returns_error(self):
        """Testa que arquivo não encontrado retorna erro"""
        non_existent_path = self.temp_dir / 'nonexistent.db'
        
        result = validate_restored_db(
            db_path=non_existent_path,
            app_schema_version='1.0',
            check_invariants=False
        )
        
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        self.assertTrue(any('não encontrado' in error.lower() or 'not found' in error.lower() for error in result.errors))
    
    def test_validation_result_to_dict(self):
        """Testa conversão de ValidationResult para dicionário"""
        result = ValidationResult(
            success=True,
            errors=['erro1'],
            warnings=['warning1']
        )
        
        result_dict = result.to_dict()
        self.assertEqual(result_dict['success'], True)
        self.assertEqual(result_dict['errors'], ['erro1'])
        self.assertEqual(result_dict['warnings'], ['warning1'])
    
    def test_validation_result_bool(self):
        """Testa que ValidationResult pode ser usado como boolean"""
        success_result = ValidationResult(success=True, errors=[], warnings=[])
        fail_result = ValidationResult(success=False, errors=['error'], warnings=[])
        
        self.assertTrue(success_result)
        self.assertFalse(fail_result)


if __name__ == '__main__':
    unittest.main()

