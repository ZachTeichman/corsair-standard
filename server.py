"""Local entrypoint.

The deployable FastAPI app now lives in backend/main.py. This shim keeps the
old `uvicorn server:app` workflow working by serving the API plus the React
frontend build.
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
@app.head("/app")
@app.head("/app/")
def serve_react_app() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/club")
@app.get("/club/")
@app.head("/club")
@app.head("/club/")
def serve_club_app() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/styles.css")
@app.head("/styles.css")
def serve_static_page_styles() -> FileResponse:
    return FileResponse(WEB_DIR / "styles.css")


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


@app.get("/why.html")
@app.head("/why.html")
def serve_why() -> FileResponse:
    return FileResponse(WEB_DIR / "why.html")


@app.get("/formatting-guide.html")
@app.head("/formatting-guide.html")
def serve_formatting_guide() -> FileResponse:
    return FileResponse(WEB_DIR / "formatting-guide.html")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
