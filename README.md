# Corsair Standard

Corsair Standard is a deterministic DOCX formatting compliance platform for UGA/Corsair-style business recruiting resumes.

It is not an ATS keyword tool, AI resume evaluator, candidate quality scorer, job matcher, or bullet rewriter. The product checks formatting structure: margins, spacing, tab stops, bullets, typography, date alignment, section structure, one-page compliance, and Word-native construction quality.

## Repository Structure

```text
/frontend   Vite React + TypeScript + Tailwind interface
/backend    FastAPI API entrypoint for deployment/runtime
/corsair    Python DOCX parser, analyzer, annotator, and formatting rules
/rubrics    JSON rubric configuration
/templates  Clean Corsair DOCX template download
/web        Static legal and resource pages
/archived   Historical prototypes not used by the active app
```

## Local Development

Run the backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Vite proxies `/api/*` to `http://127.0.0.1:8000`.

For the bundled local preview used in Codex, run `uvicorn server:app --reload`
from the repo root and open `http://127.0.0.1:8000/app`.

## Office Viewer Preview

The analyzer always returns downloadable original and annotated DOCX links. The embedded Microsoft Office Viewer preview requires the uploaded DOCX to be reachable from a public URL.

For local testing, start the backend with `PUBLIC_BASE_URL` pointed at a tunnel URL:

```bash
PUBLIC_BASE_URL=https://your-tunnel.trycloudflare.com uvicorn main:app --reload
```

Without `PUBLIC_BASE_URL`, the React UI still works, but the Office iframe shows a preview-pending state and the annotated DOCX can be downloaded locally.

## Deployment Notes

Frontend:

- Deploy `/frontend` to Vercel.
- Set `VITE_API_BASE_URL` to the deployed backend URL if the backend is on another domain.

Backend:

- Deploy `/backend` to Railway, Render, or another Python host.
- Keep `/corsair`, `/rubrics`, and `/templates` available in the deployed project root.
- Set `PUBLIC_BASE_URL` to the backend's public URL so Office Viewer can load annotated DOCX files.

## Current Product Boundary

The MVP is:

- Upload DOCX
- Analyze with deterministic Python rules
- Generate annotated DOCX comments
- Show visual score, structural score, issue cards, and Word preview links
- Offer a clean formatting template

Out of scope for now:

- Auto-fix/session patching
- ATS scoring
- candidate quality scoring
- skill extraction
- semantic resume parsing
- job matching
- grammar checking

## Context Hygiene For Codex

Start future chats by reading `AGENTS.md`. The archived vanilla UI and
experimental references are not part of the active product unless explicitly
requested.
