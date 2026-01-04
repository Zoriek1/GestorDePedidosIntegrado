"""
Integração simples com Google Drive para backups encriptados.
Requer credenciais de Service Account em JSON (já usadas no projeto).
"""
import os
from pathlib import Path
from typing import List, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from app.config import Config

SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

DEFAULT_CREDENTIAL_PATHS = [
    Config.BASE_DIR / "user" / "config" / "google_credentials.json",
    Config.BASE_DIR / "config" / "google_credentials.json",
]


class GoogleDriveBackupError(Exception):
    """Erro genérico para operações no Google Drive."""


class GoogleDriveBackup:
    def __init__(self, folder_id: Optional[str] = None, credentials_path: Optional[Path] = None):
        self.folder_id = folder_id or os.environ.get("GDRIVE_BACKUP_FOLDER_ID")
        self.credentials_path = self._resolve_credentials(credentials_path)
        self.service = self._build_service()

    def _resolve_credentials(self, credentials_path: Optional[Path]) -> Path:
        candidates: List[Path] = []
        if credentials_path:
            candidates.append(Path(credentials_path))
        env_path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
        if env_path:
            candidates.append(Path(env_path))
        candidates.extend(DEFAULT_CREDENTIAL_PATHS)

        for path in candidates:
            if path and path.exists():
                return path
        raise GoogleDriveBackupError(
            f"Credenciais do Google não encontradas. Procurei em: {', '.join(str(p) for p in candidates)}"
        )

    def _build_service(self):
        try:
            creds = Credentials.from_service_account_file(str(self.credentials_path), scopes=SCOPES)
            return build("drive", "v3", credentials=creds)
        except Exception as exc:
            raise GoogleDriveBackupError(f"Falha ao inicializar cliente do Google Drive: {exc}") from exc

    def upload_backup(self, file_path: Path, mime_type: str = "application/octet-stream") -> str:
        file_path = Path(file_path)
        if not file_path.exists():
            raise GoogleDriveBackupError(f"Arquivo para upload não encontrado: {file_path}")

        metadata = {"name": file_path.name}
        if self.folder_id:
            metadata["parents"] = [self.folder_id]

        media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
        try:
            created = (
                self.service.files()
                .create(
                    body=metadata,
                    media_body=media,
                    fields="id, name, size, createdTime",
                    supportsAllDrives=True,
                )
                .execute()
            )
            file_id = created.get("id")

            # Transferir propriedade para o dono da pasta (se folder_id foi fornecido)
            # Isso evita problemas de quota da service account
            if self.folder_id:
                try:
                    # Busca o email do proprietário da pasta
                    pasta_info = self.service.files().get(
                        fileId=self.folder_id,
                        fields="owners",
                        supportsAllDrives=True
                    ).execute()

                    owner_email = pasta_info.get("owners", [{}])[0].get("emailAddress")

                    if owner_email:
                        # Transfere propriedade
                        self.service.permissions().create(
                            fileId=file_id,
                            body={
                                "type": "user",
                                "role": "owner",
                                "emailAddress": owner_email
                            },
                            transferOwnership=True,
                            supportsAllDrives=True
                        ).execute()
                        print(f"[GDRIVE] Propriedade transferida para: {owner_email}")
                except Exception as e:
                    # Não falha o upload se a transferência der erro
                    print(f"[AVISO] Não foi possível transferir propriedade: {e}")

            return file_id
        except HttpError as exc:
            raise GoogleDriveBackupError(f"Erro ao fazer upload para o Drive: {exc}") from exc

    def list_backups(self, prefix: str = "database_") -> List[dict]:
        query_parts = ["trashed=false"]
        if prefix:
            query_parts.append(f"name contains '{prefix}'")
        if self.folder_id:
            query_parts.append(f"'{self.folder_id}' in parents")
        query = " and ".join(query_parts)

        try:
            response = (
                self.service.files()
                .list(
                    q=query,
                    fields="files(id, name, createdTime, size)",
                    orderBy="createdTime desc",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            return response.get("files", [])
        except HttpError as exc:
            raise GoogleDriveBackupError(f"Erro ao listar backups no Drive: {exc}") from exc

    def delete_old_backups(self, keep_count: int = 90, prefix: str = "database_") -> int:
        files = self.list_backups(prefix=prefix)
        if len(files) <= keep_count:
            return 0

        to_delete = files[keep_count:]
        deleted = 0
        for f in to_delete:
            try:
                self.service.files().delete(fileId=f["id"], supportsAllDrives=True).execute()
                deleted += 1
            except HttpError:
                # Continua tentando os demais
                continue
        return deleted

    def download_backup(self, file_id: str, dst: Path) -> Path:
        import io

        from googleapiclient.http import MediaIoBaseDownload

        dst = Path(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)

        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        fh = io.FileIO(str(dst), "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        try:
            while not done:
                status, done = downloader.next_chunk()
            return dst
        except HttpError as exc:
            raise GoogleDriveBackupError(f"Erro ao baixar backup do Drive: {exc}") from exc

