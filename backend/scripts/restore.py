# -*- coding: utf-8 -*-
"""
Sistema de Restauração de Backups
Restaura o banco de dados a partir de um backup
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import zipfile

class RestoreManager:
    """Gerenciador de restauração de backups"""
    
    def __init__(self, db_path=None, backup_dir=None):
        """
        Inicializa o gerenciador de restauração
        
        Args:
            db_path: Caminho para o database.db (padrão: backend/database.db)
            backup_dir: Diretório com os backups (padrão: backend/backups)
        """
        self.backend_dir = Path(__file__).parent.parent
        
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self.backend_dir / 'database.db'
        
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = self.backend_dir / 'backups'
    
    def list_backups(self):
        """
        Lista todos os backups disponíveis ordenados por data (mais recente primeiro)
        
        Returns:
            Lista de tuplas (index, path, size_mb, date)
        """
        if not self.backup_dir.exists():
            return []
        
        backups = []
        backup_files = sorted(
            self.backup_dir.glob('database_*.*'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for idx, backup_file in enumerate(backup_files, 1):
            try:
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                backups.append((idx, backup_file, size_mb, mod_time))
            except Exception as e:
                print(f"[AVISO] Erro ao processar {backup_file.name}: {e}")
        
        return backups
    
    def create_backup_before_restore(self):
        """
        Cria um backup do banco atual antes de restaurar
        
        Returns:
            Path do backup criado ou None
        """
        if not self.db_path.exists():
            print("[INFO] Banco de dados atual não existe, pulando backup preventivo")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"database_pre_restore_{timestamp}.db"
        backup_path = self.backup_dir / backup_name
        
        try:
            print(f"[BACKUP] Criando backup preventivo: {backup_name}")
            shutil.copy2(self.db_path, backup_path)
            print(f"[BACKUP] ✓ Backup preventivo criado")
            return backup_path
        except Exception as e:
            print(f"[ERRO] Erro ao criar backup preventivo: {e}")
            return None
    
    def restore_backup(self, backup_path, create_backup_first=True):
        """
        Restaura o banco de dados a partir de um backup
        
        Args:
            backup_path: Caminho do arquivo de backup
            create_backup_first: Se True, cria backup do banco atual primeiro
        
        Returns:
            True se restaurado com sucesso, False caso contrário
        """
        backup_path = Path(backup_path)
        
        # Verificar se o arquivo de backup existe
        if not backup_path.exists():
            print(f"[ERRO] Arquivo de backup não encontrado: {backup_path}")
            return False
        
        # Criar backup preventivo
        if create_backup_first and self.db_path.exists():
            preventive_backup = self.create_backup_before_restore()
            if not preventive_backup:
                resposta = input("\n[AVISO] Não foi possível criar backup preventivo. Continuar? (s/n): ")
                if resposta.lower() != 's':
                    print("[INFO] Restauração cancelada.")
                    return False
        
        try:
            # Se o backup é um arquivo .zip, extrair primeiro
            if backup_path.suffix == '.zip':
                print(f"[RESTORE] Extraindo arquivo comprimido: {backup_path.name}")
                
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    # Listar arquivos no zip
                    files = zipf.namelist()
                    db_files = [f for f in files if f.endswith('.db')]
                    
                    if not db_files:
                        print("[ERRO] Nenhum arquivo .db encontrado no backup comprimido")
                        return False
                    
                    # Extrair para arquivo temporário
                    temp_dir = self.backup_dir / 'temp_restore'
                    temp_dir.mkdir(exist_ok=True)
                    
                    db_file = db_files[0]
                    zipf.extract(db_file, temp_dir)
                    
                    extracted_path = temp_dir / db_file
                    
                    # Copiar para o local do banco de dados
                    print(f"[RESTORE] Restaurando: {self.db_path.name}")
                    shutil.copy2(extracted_path, self.db_path)
                    
                    # Limpar arquivo temporário
                    extracted_path.unlink()
                    temp_dir.rmdir()
            
            else:
                # Backup não comprimido, copiar diretamente
                print(f"[RESTORE] Restaurando: {backup_path.name} → {self.db_path.name}")
                shutil.copy2(backup_path, self.db_path)
            
            # Verificar integridade básica
            restored_size = self.db_path.stat().st_size
            
            if restored_size == 0:
                print("[ERRO] Banco de dados restaurado está vazio!")
                return False
            
            print(f"[RESTORE] ✓ Banco de dados restaurado com sucesso!")
            print(f"[RESTORE]   Tamanho: {restored_size / (1024 * 1024):.2f} MB")
            
            return True
            
        except Exception as e:
            print(f"[ERRO] Erro ao restaurar backup: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Função principal para executar restauração via linha de comando"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema de Restauração de Backups')
    parser.add_argument('--backup', type=str, help='Caminho do backup a restaurar')
    parser.add_argument('--no-backup', action='store_true', help='Não criar backup preventivo')
    parser.add_argument('--list', action='store_true', help='Listar backups disponíveis')
    
    args = parser.parse_args()
    
    # Criar gerenciador de restauração
    restore_mgr = RestoreManager()
    
    print("\n" + "="*60)
    print("SISTEMA DE RESTAURAÇÃO - Gestor de Pedidos")
    print("="*60)
    
    # Listar backups disponíveis
    backups = restore_mgr.list_backups()
    
    if not backups:
        print("\n[ERRO] Nenhum backup encontrado!")
        print(f"[INFO] Diretório de backups: {restore_mgr.backup_dir}")
        print("\n" + "="*60 + "\n")
        sys.exit(1)
    
    # Modo listar apenas
    if args.list:
        print(f"\nBackups disponíveis: {len(backups)}")
        print("-"*60)
        for idx, backup_path, size_mb, mod_time in backups:
            print(f"  [{idx}] {backup_path.name}")
            print(f"      Tamanho: {size_mb:.2f} MB")
            print(f"      Data: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        print("="*60 + "\n")
        return
    
    # Se especificou arquivo via --backup
    if args.backup:
        backup_to_restore = Path(args.backup)
    else:
        # Modo interativo: mostrar lista e solicitar escolha
        print(f"\nBackups disponíveis: {len(backups)}")
        print("-"*60)
        for idx, backup_path, size_mb, mod_time in backups:
            print(f"  [{idx}] {backup_path.name}")
            print(f"      Tamanho: {size_mb:.2f} MB")
            print(f"      Data: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        
        print("-"*60)
        
        try:
            escolha = input("\nEscolha o número do backup a restaurar (ou 'q' para sair): ").strip()
            
            if escolha.lower() == 'q':
                print("[INFO] Operação cancelada.")
                sys.exit(0)
            
            escolha_num = int(escolha)
            
            if escolha_num < 1 or escolha_num > len(backups):
                print(f"[ERRO] Escolha inválida! Digite um número entre 1 e {len(backups)}")
                sys.exit(1)
            
            # Obter backup escolhido
            backup_to_restore = backups[escolha_num - 1][1]
            
        except ValueError:
            print("[ERRO] Entrada inválida! Digite um número.")
            sys.exit(1)
    
    # Confirmação
    print("\n" + "="*60)
    print("ATENÇÃO: Restauração de Backup")
    print("="*60)
    print(f"\nBackup selecionado: {backup_to_restore.name}")
    print(f"Banco atual será SUBSTITUÍDO: {restore_mgr.db_path}")
    
    if not args.no_backup and restore_mgr.db_path.exists():
        print(f"\nUm backup preventivo será criado antes da restauração.")
    
    print("\n" + "="*60)
    confirmacao = input("\nTem certeza que deseja continuar? (digite 'SIM' em maiúsculas): ").strip()
    
    if confirmacao != 'SIM':
        print("\n[INFO] Restauração cancelada.")
        sys.exit(0)
    
    # Executar restauração
    print()
    sucesso = restore_mgr.restore_backup(
        backup_to_restore,
        create_backup_first=not args.no_backup
    )
    
    print("="*60)
    
    if sucesso:
        print("\n[OK] Restauração concluída com sucesso!")
        print("\n[PRÓXIMO PASSO] Reinicie o servidor Flask para usar o banco restaurado.")
    else:
        print("\n[ERRO] Falha na restauração!")
        sys.exit(1)
    
    print("\n" + "="*60 + "\n")


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

