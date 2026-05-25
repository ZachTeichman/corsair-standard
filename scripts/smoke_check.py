from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch(base_url: str, path: str) -> tuple[int, bytes, dict[str, str]]:
    request = Request(f"{base_url}{path}", headers={"Accept": "application/json,text/html"})
    with urlopen(request, timeout=15) as response:
        return response.status, response.read(), dict(response.headers.items())


def check(base_url: str, path: str, expected_status: int, expected_text: bytes | None = None) -> bool:
    try:
        status, body, headers = fetch(base_url, path)
    except HTTPError as exc:
        status = exc.code
        body = exc.read()
        headers = dict(exc.headers.items())
    except URLError as exc:
        print(f"FAIL {path}: {exc}", file=sys.stderr)
        return False

    if status != expected_status:
        print(f"FAIL {path}: expected HTTP {expected_status}, got {status}", file=sys.stderr)
        return False
    if expected_text is not None and expected_text not in body:
        print(f"FAIL {path}: expected response body to contain {expected_text!r}", file=sys.stderr)
        return False

    missing_headers = [
        header
        for header in [
            "X-Content-Type-Options",
            "Referrer-Policy",
            "X-Frame-Options",
            "Permissions-Policy",
        ]
        if header not in headers
    ]
    if missing_headers:
        print(f"FAIL {path}: missing security headers {', '.join(missing_headers)}", file=sys.stderr)
        return False

    print(f"OK {path}: HTTP {status}")
    return True


def main() -> int:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("PUBLIC_BASE_URL", "")).rstrip("/")
    if not base_url:
        print("Usage: python scripts/smoke_check.py https://your-app.example.com", file=sys.stderr)
        return 2

    ok = True
    ok = check(base_url, "/api/health", 200, b'"status":"ok"') and ok
    ok = check(base_url, "/app", 200, b"<html") and ok
    if ok:
        print(json.dumps({"status": "ok", "base_url": base_url}, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
