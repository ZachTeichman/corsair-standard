from __future__ import annotations

import base64
import asyncio
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from contextlib import suppress
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import slowapi.extension as slowapi_extension
from slowapi.util import get_remote_address

# SlowAPI wraps the route before FastAPI resolves postponed annotations.
# Make these names available in the wrapper module so UploadFile stays valid.
slowapi_extension.UploadFile = UploadFile
slowapi_extension.Any = Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_local_env() -> None:
    env_path = ROOT_DIR / "backend" / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()

from corsair.analyzer import analyze_docx
from corsair.annotator import (
    annotate_docx,
    count_docx_comments,
    curate_docx_comment_violations,
    estimate_docx_comment_count,
)
from backend.drive_storage import (
    DriveStorageUnavailable,
    cleanup_expired,
    drive_configured,
    drive_folder_id,
    friendly_drive_error,
    retention_hours,
    upload_docx,
    verify_folder,
)

UPLOAD_DIR = ROOT_DIR / "var" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_PATH = ROOT_DIR / "templates" / "corsair_clean_format_template.docx"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
LOCAL_UPLOAD_RETENTION_SECONDS = 24 * 60 * 60
LOCAL_CLEANUP_INTERVAL_SECONDS = 5 * 60
GRAPH_AUTH_FLOWS: dict[str, dict[str, Any]] = {}
GRAPH_SESSION: dict[str, Any] = {}
GRAPH_SCOPES = "openid profile offline_access User.Read Files.ReadWrite"
GRAPH_ROOT = "https://graph.microsoft.com"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


def _drive_docx_title(filename: str, label: str) -> str:
    source = Path(filename).name
    stem = Path(source).stem or "resume"
    return f"{stem} - {label}.docx"


def cleanup_local_uploads() -> dict[str, Any]:
    cutoff = time.time() - LOCAL_UPLOAD_RETENTION_SECONDS
    deleted: list[str] = []
    for path in UPLOAD_DIR.glob("*.docx"):
        try:
            expired = path.stat().st_mtime < cutoff
        except FileNotFoundError:
            continue
        if not expired:
            continue
        path.unlink(missing_ok=True)
        deleted.append(path.name)
    return {
        "deleted": deleted,
        "count": len(deleted),
        "retention_seconds": LOCAL_UPLOAD_RETENTION_SECONDS,
    }


async def _local_upload_cleanup_loop() -> None:
    while True:
        cleanup_local_uploads()
        await asyncio.sleep(LOCAL_CLEANUP_INTERVAL_SECONDS)

app = FastAPI(
    title="Corsair Resume Format Compliance API",
    description=(
        "Draft deterministic DOCX formatting checks for Corsair resume layout "
        "compliance. This does not score candidate quality or parse resume semantics."
    ),
    version="0.1.0",
)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def start_local_upload_cleanup() -> None:
    cleanup_local_uploads()
    app.state.local_upload_cleanup_task = asyncio.create_task(_local_upload_cleanup_loop())


@app.on_event("shutdown")
async def stop_local_upload_cleanup() -> None:
    task = getattr(app.state, "local_upload_cleanup_task", None)
    if not task:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/storage/status")
def storage_status() -> dict[str, Any]:
    local_cleanup = cleanup_local_uploads()
    status: dict[str, Any] = {
        "provider": "google_drive",
        "configured": drive_configured(),
        "folder_id": drive_folder_id(),
        "retention_hours": retention_hours(),
        "local_upload_retention_hours": LOCAL_UPLOAD_RETENTION_SECONDS // 3600,
        "local_cleanup": local_cleanup,
        "available": False,
    }
    if not drive_configured():
        return status
    try:
        folder = verify_folder()
    except DriveStorageUnavailable as exc:
        status["error"] = str(exc)
    except Exception as exc:
        status["error"] = f"Google Drive storage check failed: {exc}"
    else:
        status["available"] = True
        status["folder"] = {
            "id": folder.get("id"),
            "name": folder.get("name"),
            "url": folder.get("webViewLink"),
        }
    return status


@app.post("/api/storage/cleanup")
def cleanup_storage() -> dict[str, Any]:
    local_cleanup = cleanup_local_uploads()
    if not drive_configured():
        return {"local_uploads": local_cleanup, "google_drive": {"configured": False, "deleted": [], "count": 0}}
    try:
        return {"local_uploads": local_cleanup, "google_drive": cleanup_expired()}
    except DriveStorageUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/template/clean-docx")
def download_clean_template() -> FileResponse:
    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=404, detail="Clean template DOCX not found.")
    return FileResponse(
        TEMPLATE_PATH,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="Corsair-Clean-Formatting-Template.docx",
    )


def _graph_config() -> dict[str, str | None]:
    return {
        "client_id": os.getenv("MS_GRAPH_CLIENT_ID"),
        "tenant": os.getenv("MS_GRAPH_TENANT", "organizations"),
        "redirect_uri": os.getenv("MS_GRAPH_REDIRECT_URI", "http://127.0.0.1:8000/api/office/callback"),
    }


def _require_graph_client_id() -> str:
    client_id = _graph_config()["client_id"]
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail="Set MS_GRAPH_CLIENT_ID to enable Microsoft 365 preview.",
        )
    return client_id


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("ascii").rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def _json_request(
    url: str,
    method: str = "GET",
    token: str | None = None,
    body: Any = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request_headers = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    request = UrlRequest(url, data=data, method=method, headers=request_headers)
    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail or exc.reason) from exc
    return json.loads(response_body.decode("utf-8")) if response_body else {}


def _token_request(url: str, form: dict[str, str]) -> dict[str, Any]:
    data = urlencode(form).encode("utf-8")
    request = UrlRequest(url, data=data, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail or exc.reason) from exc
    return json.loads(response_body.decode("utf-8"))


def _upload_bytes(url: str, token: str, payload: bytes) -> dict[str, Any]:
    request = UrlRequest(
        url,
        data=payload,
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail or exc.reason) from exc


def _access_token() -> str:
    token = GRAPH_SESSION.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Connect Microsoft 365 before requesting Office preview.")
    if GRAPH_SESSION.get("expires_at", 0) <= time.time() + 60:
        raise HTTPException(status_code=401, detail="Microsoft 365 session expired. Connect again.")
    return str(token)


@app.get("/api/office/status")
def office_status() -> dict[str, Any]:
    config = _graph_config()
    return {
        "configured": bool(config["client_id"]),
        "connected": bool(GRAPH_SESSION.get("access_token") and GRAPH_SESSION.get("expires_at", 0) > time.time() + 60),
        "tenant": config["tenant"],
        "redirect_uri": config["redirect_uri"],
        "scopes": GRAPH_SCOPES,
        "public_base_url": PUBLIC_BASE_URL or None,
    }


@app.get("/api/office/connect")
def office_connect() -> dict[str, str]:
    config = _graph_config()
    client_id = _require_graph_client_id()
    verifier, challenge = _pkce_pair()
    state = uuid.uuid4().hex
    GRAPH_AUTH_FLOWS[state] = {"verifier": verifier, "created_at": time.time()}
    auth_url = (
        f"https://login.microsoftonline.com/{config['tenant']}/oauth2/v2.0/authorize?"
        + urlencode(
            {
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": config["redirect_uri"],
                "response_mode": "query",
                "scope": GRAPH_SCOPES,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
    )
    return {"auth_url": auth_url}


@app.get("/api/office/callback")
def office_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
) -> str:
    if error:
        raise HTTPException(status_code=400, detail=error_description or error)
    if not code or not state or state not in GRAPH_AUTH_FLOWS:
        raise HTTPException(status_code=400, detail="Invalid Microsoft 365 auth callback.")

    config = _graph_config()
    flow = GRAPH_AUTH_FLOWS.pop(state)
    token_url = f"https://login.microsoftonline.com/{config['tenant']}/oauth2/v2.0/token"
    token_response = _token_request(
        token_url,
        {
            "client_id": _require_graph_client_id(),
            "scope": GRAPH_SCOPES,
            "code": code,
            "redirect_uri": str(config["redirect_uri"]),
            "grant_type": "authorization_code",
            "code_verifier": flow["verifier"],
        },
    )
    GRAPH_SESSION.clear()
    GRAPH_SESSION.update(token_response)
    GRAPH_SESSION["expires_at"] = time.time() + int(token_response.get("expires_in", 3600))
    return "Microsoft 365 connected. You can return to the Corsair checker tab."


@app.get("/api/uploads/{upload_id}/original")
def download_original(upload_id: str) -> FileResponse:
    cleanup_local_uploads()
    matches = list(UPLOAD_DIR.glob(f"{upload_id}_original_*.docx"))
    if not matches:
        raise HTTPException(status_code=404, detail="Uploaded DOCX not found.")
    path = matches[0]
    original_name = path.name.split("_original_", 1)[1]
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=original_name,
    )


@app.get("/api/uploads/{upload_id}/annotated")
def download_annotated(upload_id: str) -> FileResponse:
    cleanup_local_uploads()
    matches = list(UPLOAD_DIR.glob(f"{upload_id}_annotated_*.docx"))
    if not matches:
        raise HTTPException(status_code=404, detail="Annotated DOCX not found.")
    path = matches[0]
    original_name = path.name.split("_annotated_", 1)[1]
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"annotated-{original_name}",
    )


def _uploaded_docx(upload_id: str) -> tuple[Path, str]:
    cleanup_local_uploads()
    matches = list(UPLOAD_DIR.glob(f"{upload_id}_original_*.docx"))
    if not matches:
        raise HTTPException(status_code=404, detail="Uploaded DOCX not found.")
    path = matches[0]
    return path, path.name.split("_original_", 1)[1]


@app.post("/api/uploads/{upload_id}/office-preview")
def create_office_preview(upload_id: str) -> dict[str, Any]:
    path, original_name = _uploaded_docx(upload_id)
    payload = path.read_bytes()
    if len(payload) >= 4 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="This prototype supports Microsoft Graph simple upload for DOCX files under 4 MB.")

    token = _access_token()
    graph_name = f"corsair-{upload_id}-{original_name}"
    upload_url = f"{GRAPH_ROOT}/v1.0/me/drive/root:/{quote(graph_name)}:/content"
    item = _upload_bytes(upload_url, token, payload)
    item_id = item.get("id")
    if not item_id:
        raise HTTPException(status_code=502, detail="Microsoft Graph did not return an uploaded drive item id.")

    preview = _json_request(
        f"{GRAPH_ROOT}/beta/me/drive/items/{quote(item_id)}/preview",
        method="POST",
        token=token,
        body={"viewer": "office", "chromeless": False, "allowEdit": False},
    )
    return {
        "status": "ready",
        "provider": "microsoft_graph",
        "uploaded_item": {
            "id": item_id,
            "name": item.get("name"),
            "web_url": item.get("webUrl"),
        },
        "preview": {
            "get_url": preview.get("getUrl"),
            "post_url": preview.get("postUrl"),
            "post_parameters": preview.get("postParameters"),
        },
    }


@app.post("/api/analyze")
@limiter.limit("10/hour")
def analyze_resume(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    cleanup_local_uploads()
    filename = file.filename or ""
    lower_filename = filename.lower()
    if lower_filename.endswith(".docm"):
        raise HTTPException(status_code=400, detail="DOCM files with macros are not accepted.")
    if not lower_filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx uploads are supported.")
    if file.size and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10MB limit.")

    upload_id = uuid.uuid4().hex
    upload_path = UPLOAD_DIR / f"{upload_id}_original_{Path(filename).name}"
    with upload_path.open("wb") as handle:
        total_bytes = 0
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                handle.close()
                upload_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File exceeds 10MB limit.")
            handle.write(chunk)

    result = analyze_docx(upload_path, render=False)
    annotated_path = UPLOAD_DIR / f"{upload_id}_annotated_{Path(filename).name}"
    comment_violations, annotation_summary = curate_docx_comment_violations(result.get("violations", []))
    annotation_summary["source_comment_count"] = count_docx_comments(upload_path)
    annotation_summary["estimated_comment_count_without_focus"] = estimate_docx_comment_count(result.get("violations", []))
    try:
        annotate_docx(upload_path, comment_violations, annotated_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not create annotated DOCX: {exc}") from exc

    drive_links: dict[str, Any] | None = None
    if drive_configured():
        try:
            cleanup_expired()
            original_drive = upload_docx(
                upload_path,
                title=_drive_docx_title(filename, "Original"),
                upload_id=upload_id,
                role="original",
            )
            annotated_drive = upload_docx(
                annotated_path,
                title=_drive_docx_title(filename, "Annotated"),
                upload_id=upload_id,
                role="annotated",
            )
            drive_links = {
                "provider": "google_drive",
                "folder_id": drive_folder_id(),
                "retention_hours": retention_hours(),
                "original": {
                    "id": original_drive.get("id"),
                    "name": original_drive.get("name"),
                    "web_view_link": original_drive.get("webViewLink"),
                    "web_content_link": original_drive.get("webContentLink"),
                    "expires_at": original_drive.get("expires_at"),
                },
                "annotated": {
                    "id": annotated_drive.get("id"),
                    "name": annotated_drive.get("name"),
                    "web_view_link": annotated_drive.get("webViewLink"),
                    "web_content_link": annotated_drive.get("webContentLink"),
                    "expires_at": annotated_drive.get("expires_at"),
                },
            }
        except Exception as exc:
            drive_links = {
                "provider": "google_drive",
                "folder_id": drive_folder_id(),
                "retention_hours": retention_hours(),
                "error": friendly_drive_error(exc),
            }

    original_public_url = f"{PUBLIC_BASE_URL}/api/uploads/{upload_id}/original" if PUBLIC_BASE_URL else None
    annotated_public_url = f"{PUBLIC_BASE_URL}/api/uploads/{upload_id}/annotated" if PUBLIC_BASE_URL else None
    office_viewer_url = (
        f"https://view.officeapps.live.com/op/view.aspx?src={quote(annotated_public_url, safe='')}"
        if annotated_public_url
        else None
    )
    office_embed_url = (
        f"https://view.officeapps.live.com/op/embed.aspx?src={quote(annotated_public_url, safe='')}&action=embedview&wdStartOn=1"
        if annotated_public_url
        else None
    )

    return {
        "status": "complete",
        "audit_type": "draft_format_compliance",
        "source": {
            "filename": filename,
            "file_type": "docx",
        },
        "result": result,
        "annotation_summary": annotation_summary,
        "preview": [],
        "render_preview": {
            "available": False,
            "reason": "DOCX rendering is skipped. Use Microsoft Word or Office Online for high-fidelity preview.",
            "approximate_pdf_preview": False,
        },
        "layout": {
            "available": False,
            "reason": "Layout overlays require a Word/Office render and are disabled in this DOCX-only analysis mode.",
            "blocks": [],
            "issues": [],
        },
        "document_links": {
            "upload_id": upload_id,
            "original_docx": f"/api/uploads/{upload_id}/original",
            "annotated_docx": f"/api/uploads/{upload_id}/annotated",
            "original_public_url": original_public_url,
            "annotated_public_url": annotated_public_url,
            "open_in_word": None,
            "office_online": None,
            "office_viewer_embed": office_embed_url,
            "office_viewer_open": office_viewer_url,
            "office_viewer_source": "annotated_docx",
            "google_drive": drive_links,
        },
    }
