"""Legacy local entrypoint.

The deployable FastAPI app now lives in backend/main.py. This shim keeps the
old `uvicorn server:app` workflow working by serving the API plus the legacy
vanilla prototype from /web.
"""

from fastapi.staticfiles import StaticFiles

from backend.main import app

app.mount("/", StaticFiles(directory="web", html=True), name="web")
