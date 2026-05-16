from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, quote_plus
from urllib.request import Request, urlopen

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from corsair.analyzer import analyze_docx
from corsair.annotator import annotate_docx

UPLOAD_DIR = Path("var/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_AUTH_FLOWS: dict[str, dict[str, Any]] = {}
GRAPH_SESSION: dict[str, Any] = {}
GRAPH_SCOPES = "openid profile offline_access User.Read Files.ReadWrite"
GRAPH_ROOT = "https://graph.microsoft.com"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


app = FastAPI(
    title="Corsair Resume Format Compliance API",
    description=(
        "Draft deterministic DOCX formatting checks for Corsair resume layout "
        "compliance. This does not score candidate quality or parse resume semantics."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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


def _json_request(url: str, method: str = "GET", token: str | None = None, body: Any = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request_headers = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=data, method=method, headers=request_headers)
    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail or exc.reason) from exc
    return json.loads(response_body.decode("utf-8")) if response_body else {}


def _token_request(url: str, form: dict[str, str]) -> dict[str, Any]:
    data = urlencode(form).encode("utf-8")
    request = Request(url, data=data, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail or exc.reason) from exc
    return json.loads(response_body.decode("utf-8"))


def _upload_bytes(url: str, token: str, payload: bytes) -> dict[str, Any]:
    request = Request(
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
def analyze_resume(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or ""
    if not filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Only .docx uploads are supported by the current deterministic checker.",
        )

    upload_id = uuid.uuid4().hex
    upload_path = UPLOAD_DIR / f"{upload_id}_original_{Path(filename).name}"
    with upload_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)

    result = analyze_docx(upload_path, render=False)
    annotated_path = UPLOAD_DIR / f"{upload_id}_annotated_{Path(filename).name}"
    try:
        annotate_docx(upload_path, result.get("violations", []), annotated_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not create annotated DOCX: {exc}") from exc

    original_public_url = f"{PUBLIC_BASE_URL}/api/uploads/{upload_id}/original" if PUBLIC_BASE_URL else None
    annotated_public_url = f"{PUBLIC_BASE_URL}/api/uploads/{upload_id}/annotated" if PUBLIC_BASE_URL else None
    office_viewer_url = (
        f"https://view.officeapps.live.com/op/view.aspx?src={quote_plus(annotated_public_url)}"
        if annotated_public_url
        else None
    )
    office_embed_url = (
        f"https://view.officeapps.live.com/op/embed.aspx?src={quote_plus(annotated_public_url)}"
        if annotated_public_url
        else None
    )

    preview: list[dict[str, Any]] = []
    render_preview = {
        "available": False,
        "reason": "DOCX rendering is skipped. Use Microsoft Word or Office Online for high-fidelity preview.",
        "approximate_pdf_preview": False,
    }
    layout = {
        "available": False,
        "reason": "Layout overlays require a Word/Office render and are disabled in this DOCX-only analysis mode.",
        "blocks": [],
        "issues": [],
    }

    return {
        "status": "complete",
        "audit_type": "draft_format_compliance",
        "source": {
            "filename": filename,
            "file_type": "docx",
        },
        "result": result,
        "preview": preview,
        "render_preview": render_preview,
        "layout": layout,
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
        },
    }


app.mount("/", StaticFiles(directory="web", html=True), name="web")
