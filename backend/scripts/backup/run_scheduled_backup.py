# -*- coding: utf-8 -*-
"""
Script de Backup Agendado com Janelas Restritas (P0.1)
Executa backup automático dentro de janelas específicas:
- Segunda a Sexta: 07:00 até 18:00 (inclusive)
- Sábado: 07:00 até 14:00 (inclusive)
- Domingo: não executa

Idempotência: não cria backup se já existe um nos últimos 55 minutos
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.utils.backup_helper import create_backup  # noqa: E402


def should_run_backup_now() -> bool:
    """
    Verifica se o backup deve ser executado agora baseado na janela de execução.

    Returns:
        True se deve executar, False caso contrário
    """
    now = datetime.now()
    weekday = now.weekday()  # 0=Segunda, 6=Domingo
    hour = now.hour
    minute = now.minute

    if weekday == 6:  # Domingo
        return False
    elif weekday == 5:  # Sábado
        # Sábado: 07:00 até 14:00 (inclusive)
        if hour < 7:
            return False
        elif hour > 14:
            return False
        elif hour == 14:
            return minute == 0  # Apenas 14:00, não 14:01+
        else:
            return True  # Entre 7 e 13
    else:  # Segunda a Sexta (0-4)
        # Seg-Sex: 07:00 até 18:00 (inclusive)
        if hour < 7:
            return False
        elif hour > 18:
            return False
        elif hour == 18:
            return minute == 0  # Apenas 18:00, não 18:01+
        else:
            return True  # Entre 7 e 17


def get_recent_backup_timestamp(backup_dir: Path, minutes_threshold: int = 55):
    """
    Verifica se existe backup criado nos últimos N minutos.

    Args:
        backup_dir: Diretório de backups
        minutes_threshold: Limite em minutos (padrão: 55)

    Returns:
        Timestamp do backup mais recente ou None se não houver
    """
    if not backup_dir.exists():
        return None

    cutoff_time = datetime.now() - timedelta(minutes=minutes_threshold)
    most_recent_time = None

    # Padrões de arquivos de backup
    patterns = ["database_*.db", "database_*.zip"]

    for pattern in patterns:
        for backup_file in backup_dir.glob(pattern):
            try:
                # Extrair timestamp do nome do arquivo
                # Formato: database_YYYYMMDD_HHMMSS.ext
                match = re.search(r'(\d{8}_\d{6})', backup_file.name)
                if match:
                    timestamp_str = match.group(1)
                    file_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

                    if file_time >= cutoff_time:
                        if most_recent_time is None or file_time > most_recent_time:
                            most_recent_time = file_time
            except (ValueError, AttributeError):
                # Se não conseguir extrair timestamp, usar data de modificação
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time >= cutoff_time:
                        if most_recent_time is None or file_time > most_recent_time:
                            most_recent_time = file_time
                except Exception:
                    continue

    return most_recent_time


def main():
    """Função principal do script agendado"""
    now = datetime.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    # Configurar logging
    backend_dir = Path(__file__).parent.parent.parent
    logs_dir = backend_dir / 'instance' / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / 'scheduled_backup.log'

    def log_message(level: str, message: str):
        """Loga mensagem no arquivo e no console"""
        log_entry = f"{timestamp} | {level} | {message}\n"
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass
        print(f"[{level}] {message}")

    # Verificar janela de execução
    if not should_run_backup_now():
        weekday_name = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][now.weekday()]
        log_message('INFO', f"Fora da janela de execução ({weekday_name} {now.hour:02d}:{now.minute:02d}) - ignorado")
        sys.exit(0)

    # Verificar idempotência
    backup_dir = backend_dir / 'instance' / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)

    recent_backup = get_recent_backup_timestamp(backup_dir, minutes_threshold=55)
    if recent_backup:
        age_minutes = (now - recent_backup).total_seconds() / 60
        log_message('INFO', f"Backup recente encontrado (criado há {age_minutes:.1f} min) - idempotência ativa, ignorado")
        sys.exit(0)

    # Executar backup
    log_message('INFO', "Iniciando backup agendado (motivo: scheduled_hourly)")
    try:
        backup_path = create_backup(reason='scheduled_hourly', compress=True, silent=False)

        if backup_path:
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            log_message('SUCCESS', f"Backup criado com sucesso: {backup_path.name} ({size_mb:.2f} MB)")
            sys.exit(0)
        else:
            log_message('ERROR', "Falha ao criar backup (retornou None)")
            sys.exit(1)

    except Exception as e:
        error_msg = str(e)
        log_message('ERROR', f"Erro ao criar backup: {error_msg}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

