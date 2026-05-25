# Corsair Standard Context

Use this file first when starting a new Codex chat. It is intentionally short so future work does not spend context rediscovering the app.

## Active App

- Product: deterministic DOCX resume formatting compliance checker.
- Local preview: `http://127.0.0.1:8000/app`.
- Backend: `backend/main.py` exposes the FastAPI API.
- Local shim: `server.py` imports `backend.main:app` and serves the React build plus static legal/resource pages.
- Frontend: `frontend/src` is the active Vite React + TypeScript + Tailwind app.
- Static pages: `web/privacy.html`, `web/terms.html`, `web/security.html`, `web/why.html`, and `web/formatting-guide.html`.
- Core analysis engine: `corsair/`.

## Ignore Unless Asked

- `archived/legacy-vanilla-ui/`: old vanilla home/audit UI kept only for reference.
- `references/`: old prototypes and experimental autofix work.
- `frontend/node_modules/`, `frontend/dist/`, `.venv/`, `.git/`, and `var/`: generated/runtime data.

## Current Product Boundary

The MVP uploads a DOCX, runs deterministic formatting rules, returns scores/issues, creates an annotated DOCX, and offers a clean template. It is not an ATS tool, candidate evaluator, job matcher, content scorer, or resume writer.
