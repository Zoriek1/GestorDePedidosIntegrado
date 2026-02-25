# -*- coding: utf-8 -*-
"""
Módulo de Validação de Banco de Dados Restaurado (P1.1)
Validação padronizada usada por restore real e restore-smoke-test
"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class ValidationResult:
    """Resultado de validação de banco de dados"""

    success: bool
    errors: List[str]
    warnings: List[str]

    def __bool__(self):
        return self.success

    def to_dict(self):
        """Converte para dicionário (para logging/serialização)"""
        return {
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_restored_db(
    db_path: Path,
    app_schema_version: Optional[str] = None,
    check_invariants: bool = False,
    verbose: bool = False,
) -> ValidationResult:
    """
    Valida banco de dados restaurado com checks obrigatórios

    Args:
        db_path: Caminho do arquivo de banco de dados
        app_schema_version: Versão do schema esperada (ex: '1.0')
        check_invariants: Se True, verifica invariantes (foreign keys, etc)
        verbose: Se True, inclui mais detalhes nos erros

    Returns:
        ValidationResult com success, errors e warnings
    """
    errors = []
    warnings = []

    if not db_path.exists():
        return ValidationResult(
            success=False,
            errors=[f"Arquivo de banco não encontrado: {db_path}"],
            warnings=[],
        )

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 1. PRAGMA integrity_check (OBRIGATÓRIO)
        try:
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if not result or result[0] != "ok":
                error_msg = result[0] if result else "unknown error"
                errors.append(f"Integrity check falhou: {error_msg}")
                conn.close()
                return ValidationResult(success=False, errors=errors, warnings=warnings)
        except Exception as e:
            errors.append(f"Erro ao executar integrity_check: {str(e)}")
            if verbose:
                import traceback

                errors.append(traceback.format_exc())
            conn.close()
            return ValidationResult(success=False, errors=errors, warnings=warnings)

        # 2. Verificação de schema_version
        if app_schema_version:
            schema_ok, schema_errors, schema_warnings = _validate_schema_version(
                cursor, app_schema_version, verbose
            )
            errors.extend(schema_errors)
            warnings.extend(schema_warnings)

        # 3. Sanity checks (tabelas essenciais, queries básicas)
        sanity_ok, sanity_errors, sanity_warnings = _run_sanity_checks(cursor, verbose)
        errors.extend(sanity_errors)
        warnings.extend(sanity_warnings)

        # 4. Invariantes (opcional)
        if check_invariants:
            invariants_ok, invariants_errors, invariants_warnings = _check_invariants(
                cursor, verbose
            )
            errors.extend(invariants_errors)
            warnings.extend(invariants_warnings)

        conn.close()

        # Se houver erros, validação falhou
        success = len(errors) == 0
        return ValidationResult(success=success, errors=errors, warnings=warnings)

    except Exception as e:
        error_msg = f"Erro ao validar banco de dados: {str(e)}"
        errors.append(error_msg)
        if verbose:
            import traceback

            errors.append(traceback.format_exc())
        return ValidationResult(success=False, errors=errors, warnings=warnings)


def _validate_schema_version(
    cursor: sqlite3.Cursor, app_schema_version: str, verbose: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """
    Valida schema_version do banco

    Returns:
        (success, errors, warnings)
    """
    errors = []
    warnings = []

    try:
        # Verificar se existe tabela schema_version (legado)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        has_schema_version_table = cursor.fetchone() is not None

        # Verificar se existe tabela app_meta (novo padrão)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_meta'")
        has_app_meta_table = cursor.fetchone() is not None

        db_schema_version = None

        if has_schema_version_table:
            # Tabela schema_version legada
            try:
                cursor.execute("SELECT version FROM schema_version LIMIT 1")
                result = cursor.fetchone()
                if result:
                    db_schema_version = result[0]
            except Exception as e:
                warnings.append(f"Não foi possível ler schema_version: {str(e)}")

        if has_app_meta_table and not db_schema_version:
            # Tabela app_meta (novo padrão)
            try:
                cursor.execute("SELECT value FROM app_meta WHERE key='schema_version' LIMIT 1")
                result = cursor.fetchone()
                if result:
                    db_schema_version = result[0]
            except Exception as e:
                warnings.append(f"Não foi possível ler schema_version de app_meta: {str(e)}")

        if db_schema_version:
            # Validar compatibilidade (versão deve ser igual ou compatível)
            if db_schema_version != app_schema_version:
                errors.append(
                    f"Incompatibilidade de schema_version: banco={db_schema_version}, app={app_schema_version}"
                )
                return (False, errors, warnings)
        else:
            # Sem schema_version no banco - apenas warning (não bloqueia)
            warnings.append(
                f"Banco não possui schema_version registrado. Esperado: {app_schema_version}"
            )

        return (len(errors) == 0, errors, warnings)

    except Exception as e:
        errors.append(f"Erro ao validar schema_version: {str(e)}")
        if verbose:
            import traceback

            errors.append(traceback.format_exc())
        return (False, errors, warnings)


def _run_sanity_checks(
    cursor: sqlite3.Cursor, verbose: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """
    Executa sanity checks básicos

    Returns:
        (success, errors, warnings)
    """
    errors = []
    warnings = []

    try:
        # 1. Verificar se tabelas essenciais existem
        essential_tables = ["pedidos", "clientes", "fonte_pedido"]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}

        for table in essential_tables:
            if table not in existing_tables:
                errors.append(f"Tabela essencial '{table}' não encontrada")

        # 2. Verificar que queries básicas funcionam (COUNT(*))
        if "pedidos" in existing_tables:
            try:
                cursor.execute("SELECT COUNT(*) FROM pedidos")
                count_pedidos = cursor.fetchone()[0]
                if count_pedidos < 0:
                    errors.append(f"Contagem de pedidos inválida: {count_pedidos}")
            except Exception as e:
                errors.append(f"Erro ao contar pedidos: {str(e)}")
                if verbose:
                    import traceback

                    errors.append(traceback.format_exc())

        if "clientes" in existing_tables:
            try:
                cursor.execute("SELECT COUNT(*) FROM clientes")
                count_clientes = cursor.fetchone()[0]
                if count_clientes < 0:
                    errors.append(f"Contagem de clientes inválida: {count_clientes}")
            except Exception as e:
                errors.append(f"Erro ao contar clientes: {str(e)}")
                if verbose:
                    import traceback

                    errors.append(traceback.format_exc())

        if "fonte_pedido" in existing_tables:
            try:
                cursor.execute("SELECT COUNT(*) FROM fonte_pedido")
                count_fontes = cursor.fetchone()[0]
                if count_fontes < 0:
                    errors.append(f"Contagem de fontes inválida: {count_fontes}")
            except Exception as e:
                # fonte_pedido pode não existir em bancos antigos - warning apenas
                warnings.append(f"Não foi possível contar fontes: {str(e)}")

        return (len(errors) == 0, errors, warnings)

    except Exception as e:
        errors.append(f"Erro ao executar sanity checks: {str(e)}")
        if verbose:
            import traceback

            errors.append(traceback.format_exc())
        return (False, errors, warnings)


def _check_invariants(
    cursor: sqlite3.Cursor, verbose: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """
    Verifica invariantes básicas (foreign keys, etc)

    Returns:
        (success, errors, warnings)
    """
    errors = []
    warnings = []

    try:
        # Verificar foreign keys se habilitadas
        cursor.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()

        if fk_violations:
            # Agrupar violações para não spam excessivo
            violations_count = len(fk_violations)
            if violations_count > 10:
                errors.append(
                    f"Encontradas {violations_count} violações de foreign key (mostrando primeiras 10)"
                )
                for violation in fk_violations[:10]:
                    errors.append(f"FK violation: {violation}")
            else:
                errors.append(f"Encontradas {violations_count} violações de foreign key")
                for violation in fk_violations:
                    errors.append(f"FK violation: {violation}")

        return (len(errors) == 0, errors, warnings)

    except Exception as e:
        # Foreign keys podem não estar habilitadas - warning apenas
        warnings.append(f"Não foi possível verificar foreign keys: {str(e)}")
        return (True, errors, warnings)
