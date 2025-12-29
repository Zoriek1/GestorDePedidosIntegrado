# Backup Encriptado para Google Drive

## Visão Geral
- Banco: `C:/Users/<USER>/var/lib/database/database.db`
- Backup: encriptado com AES-256-GCM
- Upload: Google Drive (Service Account)
- Retenção: 90 backups no Drive (configurável)

## Pré-requisitos
1. Python + venv ativado (opcional)
2. Dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Credenciais:
   - `backend/user/config/google_credentials.json` (já usadas no projeto)
   - Opcional: `GDRIVE_BACKUP_FOLDER_ID` para escolher a pasta no Drive
4. Chave de encriptação:
   - Definida em `BACKUP_ENCRYPTION_KEY` no `.env`
   - Se ausente, será gerada automaticamente no primeiro uso

## Como executar backup imediato
```bash
cd backend/scripts/backup
python backup.py --upload-drive --keep-remote 90
```
Opções úteis:
- `--keep-local` mantém o arquivo encriptado local após upload
- `--no-compress` pula compressão antes de encriptar
- `--folder-id <ID>` define a pasta destino no Drive

## Agendar (Windows Task Scheduler)
1) Edite o horário em `scripts/backup/agendar_backup_gdrive.bat` (padrão 02:00).
2) Execute como administrador:
```cmd
cd backend/scripts/backup
agendar_backup_gdrive.bat
```
3) A tarefa criada roda diariamente.

## Restauração (manual)
1. Baixe o arquivo `.enc` do Drive.
2. Desencripte:
```python
from app.utils.encryption import decrypt_file
decrypt_file("downloaded.enc", "restaurado.db")
```
3. Substitua `C:/Users/<USER>/var/lib/database/database.db` (faça backup antes).

## Logs
- `backend/instance/logs/backup_gdrive.log` (execuções agendadas)
- `backend/instance/logs/backup_audit.log` (auditoria geral)

