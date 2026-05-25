from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    token = os.getenv("ADMIN_CLEANUP_TOKEN", "").strip()
    if not base_url:
        print("PUBLIC_BASE_URL is required.", file=sys.stderr)
        return 2
    if not token:
        print("ADMIN_CLEANUP_TOKEN is required.", file=sys.stderr)
        return 2

    request = Request(
        f"{base_url}/api/storage/cleanup",
        data=b"",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Cleanup failed: HTTP {exc.code} {detail}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Cleanup failed: {exc}", file=sys.stderr)
        return 1

    if payload:
        print(json.dumps(json.loads(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
