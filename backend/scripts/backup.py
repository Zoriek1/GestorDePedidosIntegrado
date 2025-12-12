# -*- coding: utf-8 -*-
"""
Sistema de Backup Automático do Banco de Dados
Faz backup do database.db com timestamp e gerencia retenção
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import zipfile

class BackupManager:
    """Gerenciador de backups do banco de dados"""
    
    def __init__(self, db_path=None, backup_dir=None, retention_days=30):
        """
        Inicializa o gerenciador de backups
        
        Args:
            db_path: Caminho para o database.db (padrão: backend/database.db)
            backup_dir: Diretório para salvar backups (padrão: backend/backups)
            retention_days: Número de dias para manter backups
        """
        # Definir diretórios
        self.backend_dir = Path(__file__).parent.parent
        
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self.backend_dir / 'database.db'
        
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = self.backend_dir / 'backups'
        
        self.retention_days = retention_days
        
        # Criar diretório de backups se não existir
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, compress=True):
        """
        Cria um backup do banco de dados
        
        Args:
            compress: Se True, comprime o backup em .zip
        
        Returns:
            Path do arquivo de backup criado ou None em caso de erro
        """
        # Verificar se o banco de dados existe
        if not self.db_path.exists():
            print(f"[ERRO] Banco de dados não encontrado: {self.db_path}")
            return None
        
        # Gerar nome do arquivo de backup com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"database_{timestamp}.db"
        backup_path = self.backup_dir / backup_name
        
        try:
            # Copiar banco de dados
            print(f"[BACKUP] Criando backup: {backup_name}")
            shutil.copy2(self.db_path, backup_path)
            
            # Verificar integridade (tamanho do arquivo)
            original_size = self.db_path.stat().st_size
            backup_size = backup_path.stat().st_size
            
            if original_size != backup_size:
                print(f"[ERRO] Tamanho do backup ({backup_size}) diferente do original ({original_size})")
                backup_path.unlink()
                return None
            
            # Comprimir se solicitado
            if compress:
                zip_path = self.backup_dir / f"database_{timestamp}.zip"
                print(f"[BACKUP] Comprimindo: {zip_path.name}")
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(backup_path, backup_name)
                
                # Remover arquivo .db descomprimido
                backup_path.unlink()
                backup_path = zip_path
            
            backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
            print(f"[BACKUP] ✓ Backup criado: {backup_path.name} ({backup_size_mb:.2f} MB)")
            
            return backup_path
            
        except Exception as e:
            print(f"[ERRO] Erro ao criar backup: {e}")
            # Tentar limpar arquivo de backup parcial
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except:
                    pass
            return None
    
    def cleanup_old_backups(self):
        """
        Remove backups antigos baseado no retention_days
        
        Returns:
            Número de backups removidos
        """
        if self.retention_days <= 0:
            print("[INFO] Retenção ilimitada - nenhum backup será removido")
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        
        print(f"[LIMPEZA] Removendo backups anteriores a {cutoff_date.strftime('%Y-%m-%d')}")
        
        # Listar todos os arquivos de backup
        for backup_file in self.backup_dir.glob('database_*.{db,zip}'):
            try:
                # Obter data de modificação do arquivo
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    print(f"[LIMPEZA] Removendo: {backup_file.name}")
                    backup_file.unlink()
                    removed_count += 1
                    
            except Exception as e:
                print(f"[AVISO] Erro ao processar {backup_file.name}: {e}")
        
        if removed_count > 0:
            print(f"[LIMPEZA] ✓ {removed_count} backup(s) antigo(s) removido(s)")
        else:
            print(f"[LIMPEZA] Nenhum backup antigo para remover")
        
        return removed_count
    
    def list_backups(self):
        """
        Lista todos os backups disponíveis
        
        Returns:
            Lista de tuplas (path, size_mb, date)
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob('database_*.*'), reverse=True):
            try:
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                backups.append((backup_file, size_mb, mod_time))
            except Exception as e:
                print(f"[AVISO] Erro ao processar {backup_file.name}: {e}")
        
        return backups
    
    def get_backup_stats(self):
        """
        Retorna estatísticas dos backups
        
        Returns:
            Dicionário com estatísticas
        """
        backups = self.list_backups()
        
        if not backups:
            return {
                'count': 0,
                'total_size_mb': 0,
                'oldest': None,
                'newest': None
            }
        
        total_size = sum(b[1] for b in backups)
        
        return {
            'count': len(backups),
            'total_size_mb': total_size,
            'oldest': backups[-1][2] if backups else None,
            'newest': backups[0][2] if backups else None
        }


def main():
    """Função principal para executar backup via linha de comando"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema de Backup do Banco de Dados')
    parser.add_argument('--no-compress', action='store_true', help='Não comprimir backup')
    parser.add_argument('--no-cleanup', action='store_true', help='Não remover backups antigos')
    parser.add_argument('--retention', type=int, default=30, help='Dias de retenção (padrão: 30)')
    parser.add_argument('--list', action='store_true', help='Listar backups existentes')
    parser.add_argument('--stats', action='store_true', help='Mostrar estatísticas de backups')
    
    args = parser.parse_args()
    
    # Criar gerenciador de backups
    backup_mgr = BackupManager(retention_days=args.retention)
    
    print("\n" + "="*60)
    print("SISTEMA DE BACKUP - Gestor de Pedidos")
    print("="*60)
    
    # Modo listar
    if args.list:
        backups = backup_mgr.list_backups()
        print(f"\nBackups disponíveis: {len(backups)}")
        print("-"*60)
        for backup_path, size_mb, mod_time in backups:
            print(f"  {backup_path.name}")
            print(f"    Tamanho: {size_mb:.2f} MB")
            print(f"    Data: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        return
    
    # Modo estatísticas
    if args.stats:
        stats = backup_mgr.get_backup_stats()
        print(f"\nEstatísticas de Backups:")
        print("-"*60)
        print(f"  Total de backups: {stats['count']}")
        print(f"  Tamanho total: {stats['total_size_mb']:.2f} MB")
        if stats['oldest']:
            print(f"  Mais antigo: {stats['oldest'].strftime('%Y-%m-%d %H:%M:%S')}")
        if stats['newest']:
            print(f"  Mais recente: {stats['newest'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        return
    
    # Criar backup
    backup_path = backup_mgr.create_backup(compress=not args.no_compress)
    
    if not backup_path:
        print("\n[ERRO] Falha ao criar backup!")
        print("="*60 + "\n")
        sys.exit(1)
    
    # Limpar backups antigos
    if not args.no_cleanup:
        print()
        backup_mgr.cleanup_old_backups()
    
    # Mostrar estatísticas finais
    print()
    stats = backup_mgr.get_backup_stats()
    print(f"[INFO] Total de backups: {stats['count']} ({stats['total_size_mb']:.2f} MB)")
    
    print("="*60 + "\n")
    print("[OK] Backup concluído com sucesso!")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Operação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO] Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

