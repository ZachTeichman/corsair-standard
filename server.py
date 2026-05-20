"""Legacy local entrypoint.

The deployable FastAPI app now lives in backend/main.py. This shim keeps the
old `uvicorn server:app` workflow working by serving the API plus the current
React frontend build when available.
"""

from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.main import app

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
WEB_DIR = ROOT_DIR / "web"
STATIC_DIR = FRONTEND_DIST if (FRONTEND_DIST / "index.html").exists() else ROOT_DIR / "web"


@app.get("/app")
@app.get("/app/")
def serve_react_app() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/index.html")
@app.head("/index.html")
def serve_legacy_home() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/audit.html")
@app.head("/audit.html")
def serve_legacy_audit() -> FileResponse:
    return FileResponse(WEB_DIR / "audit.html")


@app.get("/styles.css")
@app.head("/styles.css")
def serve_legacy_styles() -> FileResponse:
    return FileResponse(WEB_DIR / "styles.css")


@app.get("/app.js")
@app.head("/app.js")
def serve_legacy_app_js() -> FileResponse:
    return FileResponse(WEB_DIR / "app.js")


@app.get("/privacy.html")
@app.head("/privacy.html")
def serve_privacy() -> FileResponse:
    return FileResponse(WEB_DIR / "privacy.html")


@app.get("/terms.html")
@app.head("/terms.html")
def serve_terms() -> FileResponse:
    return FileResponse(WEB_DIR / "terms.html")


@app.get("/security.html")
@app.head("/security.html")
def serve_security() -> FileResponse:
    return FileResponse(WEB_DIR / "security.html")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
