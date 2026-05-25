# Deployment

Corsair Standard is a FastAPI backend plus a Vite React frontend. The simplest
deployment shape is to build the React app into `frontend/dist`, then run the
root `server.py` app so one process serves both `/api/*` and `/app`.

## Runtime Shape

- API entrypoint: `backend/main.py`
- Combined local/production shim: `server.py`
- Built frontend assets: `frontend/dist`
- Static legal/resource pages: `web/privacy.html`, `web/terms.html`,
  `web/security.html`, `web/why.html`, and `web/formatting-guide.html`
- Runtime upload scratch space: `var/uploads`

Keep `backend/`, `corsair/`, `rubrics/`, `templates/`, `web/`, `server.py`, and
the built `frontend/dist` directory available in the deployed project root.

## Environment Variables

Copy `backend/.env.example` for local development. In production, set variables
through the hosting platform secret/config system.

| Variable | Required | Notes |
| --- | --- | --- |
| `APP_ENV` | Production required | Set to `production` in production. Startup fails fast unless `PUBLIC_BASE_URL`, `ADMIN_CLEANUP_TOKEN`, and `ALLOWED_HOSTS` are configured. Defaults to `development`. |
| `PUBLIC_BASE_URL` | Recommended | Public origin for the running backend, with no trailing slash. Required for Microsoft Office iframe preview URLs. Downloads still work without it. |
| `LOG_LEVEL` | Optional | Python logging level. Defaults to `INFO`. |
| `CORS_ALLOWED_ORIGINS` | Split frontend only | Comma-separated browser origins allowed to call the API, for example `https://app.example.com`. Local dev origins are allowed by default. |
| `ALLOWED_HOSTS` | Production recommended | Comma-separated hostnames accepted by the API, for example `corsair.example.com,www.corsair.example.com`. Leave unset for local development. |
| `ADMIN_CLEANUP_TOKEN` | Recommended | Enables `POST /api/storage/cleanup` when set. If unset, the endpoint returns `404` and cannot be used. |
| `GOOGLE_DRIVE_FOLDER_ID` | Optional | Enables Google Drive upload storage when set. |
| `GOOGLE_DRIVE_RETENTION_HOURS` | Optional | Retention window for Drive files. Defaults to `24`; values below 1 are treated as 1 hour. |
| `GOOGLE_DRIVE_UPLOAD_MODE` | Optional | `background`, `sync`, or `disabled`. Defaults to `background` so audit responses do not wait on Drive upload. Use `sync` only if the response must include Drive preview links immediately. |
| `GOOGLE_DRIVE_TOKEN_JSON` | Optional | OAuth authorized-user token JSON for cloud hosts like Railway where local token files are unavailable. Store as a secret. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Optional | Service account JSON for cloud hosts. Store as a secret. Use only when Drive folder/storage permissions are configured for the service account. |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Optional | Path to a Google service account JSON file. Alternative to OAuth credentials. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Optional | Standard Google credentials path. Alternative to `GOOGLE_SERVICE_ACCOUNT_FILE`. |
| `GOOGLE_DRIVE_CLIENT_SECRET_FILE` | Optional | Path to an OAuth client secret JSON file. Used with `GOOGLE_DRIVE_TOKEN_FILE`. |
| `GOOGLE_DRIVE_TOKEN_FILE` | Optional | OAuth token cache path. Defaults to `var/google-drive-token.json`. |
| `MS_GRAPH_CLIENT_ID` | Optional | Enables Microsoft Graph Office preview connection. If missing, `/api/office/connect` returns a setup message. |
| `MS_GRAPH_TENANT` | Optional | Microsoft tenant for OAuth. Defaults to `organizations`. |
| `MS_GRAPH_REDIRECT_URI` | Optional | OAuth callback URI. Defaults to `http://127.0.0.1:8000/api/office/callback`; set this to the deployed `/api/office/callback` URL when Graph preview is enabled. |
| `VITE_API_BASE_URL` | Split frontend only | Set when the Vite frontend is hosted separately from the API. Leave unset for the combined `server.py` deployment. |

For the combined deployment, `PUBLIC_BASE_URL` should point at the same public
origin that serves `server.py`, for example `https://corsair.example.com`.

## Build And Start

Install Python dependencies from the project root:

```bash
python -m pip install -r requirements.txt
```

Build the frontend:

```bash
cd frontend
npm ci
npm run build
```

Start the combined app from the project root:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

For local development, `127.0.0.1` is fine:

```bash
.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Open the app at:

```text
http://127.0.0.1:8000/app
```

## Docker

Build the image from the project root:

```bash
docker build -t corsair-standard:local .
```

Run the container:

```bash
docker run --rm -p 8000:8000 \
  -e APP_ENV=development \
  -e PUBLIC_BASE_URL=http://127.0.0.1:8000 \
  -e LOG_LEVEL=INFO \
  -e ADMIN_CLEANUP_TOKEN=change-me \
  corsair-standard:local
```

The image builds `frontend/dist` in a Node stage, installs Python runtime
dependencies in a Python 3.11 slim stage, runs as a non-root `corsair` user, and
serves `uvicorn server:app`. It includes a Docker healthcheck against
`/api/health`.

For production, mount or provide credentials through the platform secret system
instead of baking them into the image. If local-only storage is used, make sure
the container filesystem or mounted volume keeps `var/uploads` writable for the
server process.

## Production Checks

Run these checks before promoting a build:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m unittest discover -s tests
cd frontend
npm ci
npm run build
```

After the service starts, verify:

- `GET /api/health` returns `{"status":"ok"}`
- `GET /app` returns the React app
- Uploading a valid DOCX below 1MB succeeds
- Uploading a DOCM, fake DOCX, or file over 1MB is rejected
- If `ADMIN_CLEANUP_TOKEN` is set, `POST /api/storage/cleanup` requires
  `Authorization: Bearer <ADMIN_CLEANUP_TOKEN>`
- If `ADMIN_CLEANUP_TOKEN` is unset, `POST /api/storage/cleanup` returns `404`

You can run the basic HTTP smoke check with:

```bash
python scripts/smoke_check.py https://corsair.example.com
```

The GitHub Actions workflow in `.github/workflows/ci.yml` runs Python tests and
the frontend build on push and pull request.

## Storage Expectations

The app writes temporary local DOCX artifacts under `var/uploads`. That
directory must be writable by the server process.

Local upload artifacts are retained for 24 hours and cleaned by the FastAPI
startup cleanup loop. The cleanup loop runs every 5 minutes while the process is
alive.

Google Drive storage is optional. When `GOOGLE_DRIVE_FOLDER_ID` and credentials
are configured, uploaded original and annotated DOCX files are copied to Drive
with an expiration timestamp. Drive cleanup is performed by
`POST /api/storage/cleanup`, which should be called by a protected scheduler
with the admin bearer token.

Use the cleanup helper from a platform scheduler or cron job:

```bash
PUBLIC_BASE_URL=https://corsair.example.com \
ADMIN_CLEANUP_TOKEN=your-secret-token \
python scripts/cleanup_storage.py
```

A daily schedule is enough for the default 24-hour retention window. Hourly is
also safe if the hosting platform supports it.

If Google Drive is not configured, the app still supports upload, analysis, and
local DOCX downloads from `var/uploads` while the local artifacts exist.

## Logging Policy

Logs must stay privacy-safe. Do not log:

- Resume text
- Candidate names
- Phone numbers
- Email addresses
- Filenames
- Extracted resume content

Structured logs may include operational metadata such as:

- Request id
- File extension
- Byte count
- Cleanup count
- Analysis duration
- Score
- Violation count
- Annotation comment count
- Suppressed comment count

When adding logs, keep them diagnostic and content-free.

## Deployment Notes

- Keep upload limits aligned with the backend constant: 1MB DOCX maximum.
- Configure any reverse proxy to allow at least 1MB request bodies plus normal
  multipart overhead.
- A practical proxy/body cap is `2m` or `2MB`. For nginx, use
  `client_max_body_size 2m;`.
- Use HTTPS in production, especially for Microsoft Graph OAuth callbacks and
  Office preview URLs.
- If hosting frontend and backend separately, set `CORS_ALLOWED_ORIGINS` to the
  deployed frontend origin.
- Set `ALLOWED_HOSTS` to the deployed hostname before public launch.
- Do not commit production secrets, OAuth tokens, service account JSON, or
  generated files in `var/`.

## Next Hardening Step

The next deployment task should be platform-specific deploy configuration for
the selected host, including secret wiring, persistent upload storage if needed,
and a protected scheduler for `POST /api/storage/cleanup`.
