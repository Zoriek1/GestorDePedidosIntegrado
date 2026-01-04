# -*- coding: utf-8 -*-
"""
Script de Migração: Migrar dados do banco antigo (database.db) para o novo (instance/database.db)

Este script migra todos os dados do banco de dados antigo para o novo local,
preservando IDs, relacionamentos e integridade referencial.
"""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app import create_app, db  # noqa: F401
    from app.models import (  # noqa: F401
        Cliente,
        EnderecoCliente,
        FontePedido,
        Pedido,
        RotaOtimizada,
    )

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("[AVISO] SQLAlchemy não disponível, usando SQLite direto")


class DatabaseMigrator:
    """Classe para migrar dados entre bancos SQLite"""

    def __init__(self, old_db_path: Path, new_db_path: Path, overwrite: bool = False):
        self.old_db_path = Path(old_db_path)
        self.new_db_path = Path(new_db_path)
        self.backup_dir = backend_dir / "instance" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.migration_report = []
        self.overwrite = overwrite

    def create_backup(self, db_path: Path, suffix: str = "") -> Path:
        """Cria backup do banco de dados"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{db_path.stem}_{suffix}_{timestamp}.db"
        backup_path = self.backup_dir / backup_name

        print(f"[BACKUP] Criando backup: {backup_path.name}")
        shutil.copy2(db_path, backup_path)
        print(f"[OK] Backup criado: {backup_path}")

        return backup_path

    def get_tables(self, conn: sqlite3.Connection) -> List[str]:
        """Lista todas as tabelas no banco"""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        return tables

    def get_table_columns(self, conn: sqlite3.Connection, table_name: str) -> List[Tuple]:
        """Obtém informações das colunas de uma tabela"""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()

    def get_table_count(self, conn: sqlite3.Connection, table_name: str) -> int:
        """Conta registros em uma tabela"""
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0

    def copy_table_data(
        self,
        old_conn: sqlite3.Connection,
        new_conn: sqlite3.Connection,
        table_name: str,
    ) -> int:
        """Copia dados de uma tabela do banco antigo para o novo"""
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()

        # Verificar se tabela existe no banco novo
        new_tables = self.get_tables(new_conn)
        if table_name not in new_tables:
            print(f"[AVISO] Tabela {table_name} não existe no banco novo, pulando...")
            return 0

        # Obter colunas de ambas as tabelas
        old_columns = self.get_table_columns(old_conn, table_name)
        new_columns = self.get_table_columns(new_conn, table_name)

        # Mapear colunas (nome, tipo)
        old_col_names = [col[1] for col in old_columns]
        new_col_names = [col[1] for col in new_columns]

        # Encontrar colunas comuns
        common_cols = [col for col in old_col_names if col in new_col_names]

        if not common_cols:
            print(f"[AVISO] Nenhuma coluna comum encontrada em {table_name}")
            return 0

        # Verificar se já existem dados no banco novo
        existing_count = self.get_table_count(new_conn, table_name)
        if existing_count > 0:
            print(f"[AVISO] Tabela {table_name} já tem {existing_count} registros no banco novo")
            if not self.overwrite:
                # Tentar input interativo, mas se falhar (modo não-interativo), pular
                try:
                    response = input("  Deseja sobrescrever? (s/n): ").lower()
                    if response != "s":
                        print(f"[INFO] Pulando tabela {table_name}")
                        return 0
                except (EOFError, KeyboardInterrupt):
                    print(
                        f"[INFO] Modo não-interativo: pulando tabela {table_name} (use --overwrite para sobrescrever)"
                    )
                    return 0
            # Limpar tabela se deve sobrescrever
            print(f"[INFO] Limpando tabela {table_name} antes de migrar...")
            new_cursor.execute(f"DELETE FROM {table_name}")
            new_conn.commit()

        # Buscar todos os dados do banco antigo
        cols_str = ", ".join(common_cols)
        old_cursor.execute(f"SELECT {cols_str} FROM {table_name}")
        rows = old_cursor.fetchall()

        if not rows:
            print(f"[INFO] Tabela {table_name} está vazia no banco antigo")
            return 0

        # Preparar INSERT
        placeholders = ", ".join(["?" for _ in common_cols])
        insert_sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"

        # Inserir dados
        count = 0
        for row in rows:
            try:
                new_cursor.execute(insert_sql, row)
                count += 1
            except sqlite3.IntegrityError as e:
                # Se houver erro de integridade (ex: ID duplicado), tentar sem ID
                if "PRIMARY KEY" in str(e) or "UNIQUE" in str(e):
                    # Remover coluna ID da inserção se for chave primária
                    if "id" in common_cols:
                        idx = common_cols.index("id")
                        cols_without_id = [c for c in common_cols if c != "id"]
                        vals_without_id = [v for i, v in enumerate(row) if i != idx]
                        if cols_without_id:
                            cols_str_no_id = ", ".join(cols_without_id)
                            placeholders_no_id = ", ".join(["?" for _ in cols_without_id])
                            insert_sql_no_id = f"INSERT INTO {table_name} ({cols_str_no_id}) VALUES ({placeholders_no_id})"
                            try:
                                new_cursor.execute(insert_sql_no_id, vals_without_id)
                                count += 1
                            except sqlite3.Error:
                                print(f"[ERRO] Falha ao inserir registro em {table_name}: {e}")
                else:
                    print(f"[ERRO] Erro de integridade em {table_name}: {e}")
            except sqlite3.Error as e:
                print(f"[ERRO] Erro ao inserir em {table_name}: {e}")

        new_conn.commit()
        return count

    def migrate(self, tables_to_migrate: List[str] = None) -> Dict[str, int]:
        """Executa a migração completa"""
        print("=" * 60)
        print("MIGRAÇÃO DE DADOS DO BANCO ANTIGO PARA O NOVO")
        print("=" * 60)
        print()

        # Verificar se bancos existem
        if not self.old_db_path.exists():
            print(f"[ERRO] Banco antigo não encontrado: {self.old_db_path}")
            return {}

        if not self.new_db_path.exists():
            print(f"[ERRO] Banco novo não encontrado: {self.new_db_path}")
            print("[INFO] Criando banco novo...")
            self.new_db_path.parent.mkdir(parents=True, exist_ok=True)
            # Criar banco vazio
            conn = sqlite3.connect(str(self.new_db_path))
            conn.close()

        # Criar backups
        print("[1/5] Criando backups...")
        old_backup = self.create_backup(self.old_db_path, "antigo")
        new_backup = self.create_backup(self.new_db_path, "novo")
        print()

        # Conectar aos bancos
        print("[2/5] Conectando aos bancos...")
        old_conn = sqlite3.connect(str(self.old_db_path))
        new_conn = sqlite3.connect(str(self.new_db_path))
        print(f"[OK] Banco antigo: {self.old_db_path}")
        print(f"[OK] Banco novo: {self.new_db_path}")
        print()

        # Listar tabelas
        print("[3/5] Verificando tabelas...")
        old_tables = self.get_tables(old_conn)
        new_tables = self.get_tables(new_conn)

        print(f"Tabelas no banco antigo: {len(old_tables)}")
        for table in old_tables:
            count = self.get_table_count(old_conn, table)
            print(f"  - {table}: {count} registros")

        print(f"\nTabelas no banco novo: {len(new_tables)}")
        for table in new_tables:
            count = self.get_table_count(new_conn, table)
            print(f"  - {table}: {count} registros")
        print()

        # Determinar tabelas para migrar
        if tables_to_migrate is None:
            # Migrar todas as tabelas comuns
            tables_to_migrate = [t for t in old_tables if t in new_tables]

        # Ordem de migração (importante para foreign keys)
        migration_order = [
            "fontes_pedido",
            "clientes",
            "enderecos_clientes",
            "pedidos",
            "rotas_otimizadas",
        ]
        # Adicionar outras tabelas que não estão na ordem
        for table in tables_to_migrate:
            if table not in migration_order:
                migration_order.append(table)

        # Filtrar apenas tabelas que existem em ambos os bancos
        tables_to_migrate = [t for t in migration_order if t in old_tables and t in new_tables]

        print(f"[4/5] Migrando {len(tables_to_migrate)} tabelas...")
        print()

        migration_results = {}
        for table in tables_to_migrate:
            print(f"Migrando {table}...")
            count = self.copy_table_data(old_conn, new_conn, table)
            migration_results[table] = count
            print(f"[OK] {table}: {count} registros migrados")
            print()

        # Validação
        print("[5/5] Validando migração...")
        print()
        for table in tables_to_migrate:
            old_count = self.get_table_count(old_conn, table)
            new_count = self.get_table_count(new_conn, table)
            status = "[OK]" if new_count >= old_count else "[ERRO]"
            print(f"{status} {table}: {old_count} -> {new_count} registros")
            self.migration_report.append(
                {
                    "table": table,
                    "old_count": old_count,
                    "new_count": new_count,
                    "migrated": migration_results.get(table, 0),
                }
            )

        # Fechar conexões
        old_conn.close()
        new_conn.close()

        print()
        print("=" * 60)
        print("MIGRAÇÃO CONCLUÍDA")
        print("=" * 60)
        print("Backups criados:")
        print(f"  - Antigo: {old_backup.name}")
        print(f"  - Novo: {new_backup.name}")
        print()

        return migration_results


def main():
    """Função principal"""
    import argparse

    parser = argparse.ArgumentParser(description="Migra dados do banco antigo para o novo")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescrever dados existentes no banco novo",
    )
    args = parser.parse_args()

    old_db = backend_dir / "database.db"
    new_db = backend_dir / "instance" / "database.db"

    migrator = DatabaseMigrator(old_db, new_db, overwrite=args.overwrite)

    try:
        results = migrator.migrate()

        print("\nResumo da migração:")
        for table, count in results.items():
            print(f"  {table}: {count} registros")

        print("\n[OK] Migração concluída com sucesso!")
        print("\nPróximos passos:")
        print("  1. Reinicie o servidor")
        print("  2. Verifique se a API retorna os pedidos: GET /api/pedidos")
        print("  3. Teste alguns endpoints críticos")

    except Exception as e:
        print(f"\n[ERRO] Falha na migração: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
