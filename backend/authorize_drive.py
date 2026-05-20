from __future__ import annotations

import os
from urllib.parse import parse_qs
from pathlib import Path
from wsgiref.simple_server import make_server

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / "backend" / ".env"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    load_env()
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    client_secret = os.environ["GOOGLE_DRIVE_CLIENT_SECRET_FILE"]
    token_file = Path(os.environ.get("GOOGLE_DRIVE_TOKEN_FILE", ROOT_DIR / "var" / "google-drive-token.json"))
    token_file.parent.mkdir(parents=True, exist_ok=True)

    flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
    flow.redirect_uri = "http://127.0.0.1:8765/"
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    print("Open this URL in the browser and approve Drive access:", flush=True)
    print(authorization_url, flush=True)

    callback: dict[str, str] = {}

    def app(environ, start_response):
        query = parse_qs(environ.get("QUERY_STRING", ""))
        if "error" in query:
            callback["error"] = query["error"][0]
        if "code" in query:
            callback["url"] = "http://127.0.0.1:8765/?" + environ.get("QUERY_STRING", "")
        body = b"Google Drive authorization complete. You can close this tab."
        start_response("200 OK", [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))])
        return [body]

    with make_server("127.0.0.1", 8765, app) as server:
        while "url" not in callback and "error" not in callback:
            server.handle_request()

    if "error" in callback:
        raise SystemExit(f"Google OAuth failed: {callback['error']}")

    flow.fetch_token(authorization_response=callback["url"])
    credentials = flow.credentials
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    print(f"Saved Google Drive token to {token_file}")


if __name__ == "__main__":
    main()
