from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DRIVE_MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveStorageUnavailable(RuntimeError):
    pass


def friendly_drive_error(exc: Exception) -> str:
    content = str(exc)
    if "storageQuotaExceeded" in content or "Service Accounts do not have storage quota" in content:
        return (
            "Google Drive rejected the upload because service accounts do not have storage quota "
            "in a normal My Drive folder. Use OAuth for resumeformatter6@gmail.com, or upload into "
            "a Google Shared Drive instead."
        )
    if "File not found" in content:
        return "Google Drive could not see the configured folder. Confirm the folder is shared with the active credential."
    return f"Google Drive storage failed: {exc}"


def drive_configured() -> bool:
    return bool(os.getenv("GOOGLE_DRIVE_FOLDER_ID"))


def drive_folder_id() -> str | None:
    return os.getenv("GOOGLE_DRIVE_FOLDER_ID")


def retention_hours() -> int:
    raw = os.getenv("GOOGLE_DRIVE_RETENTION_HOURS", "24")
    try:
        hours = int(raw)
    except ValueError:
        return 24
    return max(1, hours)


def _load_drive_modules() -> tuple[Any, Any, Any, Any, Any]:
    try:
        from google.oauth2.credentials import Credentials
        from google.oauth2.service_account import Credentials as ServiceAccountCredentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise DriveStorageUnavailable(
            "Install google-api-python-client, google-auth, and google-auth-oauthlib to enable Google Drive storage."
        ) from exc
    return Credentials, ServiceAccountCredentials, InstalledAppFlow, build, MediaFileUpload


def _credentials() -> Any:
    Credentials, ServiceAccountCredentials, InstalledAppFlow, _, _ = _load_drive_modules()
    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_file:
        return ServiceAccountCredentials.from_service_account_file(service_account_file, scopes=DRIVE_SCOPES)

    token_path = Path(os.getenv("GOOGLE_DRIVE_TOKEN_FILE", "var/google-drive-token.json"))
    client_secret_path = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET_FILE")
    if token_path.exists():
        return Credentials.from_authorized_user_file(str(token_path), DRIVE_SCOPES)
    if client_secret_path:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, DRIVE_SCOPES)
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    raise DriveStorageUnavailable(
        "Set GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_APPLICATION_CREDENTIALS, or GOOGLE_DRIVE_CLIENT_SECRET_FILE to enable Google Drive storage."
    )


def _service() -> Any:
    _, _, _, build, _ = _load_drive_modules()
    return build("drive", "v3", credentials=_credentials(), cache_discovery=False)


def verify_folder() -> dict[str, Any]:
    folder_id = drive_folder_id()
    if not folder_id:
        raise DriveStorageUnavailable("GOOGLE_DRIVE_FOLDER_ID is not set.")
    service = _service()
    folder = (
        service.files()
        .get(fileId=folder_id, fields="id,name,mimeType,trashed,webViewLink", supportsAllDrives=True)
        .execute()
    )
    if folder.get("mimeType") != DRIVE_FOLDER_MIME or folder.get("trashed"):
        raise DriveStorageUnavailable("GOOGLE_DRIVE_FOLDER_ID does not point to an active Drive folder.")
    return folder


def upload_docx(path: Path, *, title: str, upload_id: str, role: str) -> dict[str, Any]:
    folder_id = drive_folder_id()
    if not folder_id:
        raise DriveStorageUnavailable("GOOGLE_DRIVE_FOLDER_ID is not set.")
    _, _, _, _, MediaFileUpload = _load_drive_modules()
    service = _service()
    expires_at = int(time.time() + retention_hours() * 3600)
    metadata = {
        "name": title,
        "parents": [folder_id],
        "mimeType": DRIVE_MIME_DOCX,
        "appProperties": {
            "corsairUploadId": upload_id,
            "corsairRole": role,
            "corsairExpiresAt": str(expires_at),
        },
    }
    media = MediaFileUpload(str(path), mimetype=DRIVE_MIME_DOCX, resumable=False)
    item = (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id,name,mimeType,webViewLink,webContentLink,createdTime,appProperties",
            supportsAllDrives=True,
        )
        .execute()
    )
    item["expires_at"] = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
    return item


def cleanup_expired() -> dict[str, Any]:
    folder_id = drive_folder_id()
    if not folder_id:
        raise DriveStorageUnavailable("GOOGLE_DRIVE_FOLDER_ID is not set.")
    service = _service()
    now = int(time.time())
    query = f"'{folder_id}' in parents and trashed = false"
    response = (
        service.files()
        .list(
            q=query,
            fields="files(id,name,appProperties)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=1000,
        )
        .execute()
    )
    deleted: list[dict[str, str]] = []
    for item in response.get("files", []):
        expires_at = item.get("appProperties", {}).get("corsairExpiresAt")
        if not expires_at:
            continue
        try:
            expired = int(expires_at) < now
        except ValueError:
            expired = False
        if not expired:
            continue
        service.files().delete(fileId=item["id"], supportsAllDrives=True).execute()
        deleted.append({"id": item["id"], "name": item.get("name", "")})
    return {"deleted": deleted, "count": len(deleted)}
