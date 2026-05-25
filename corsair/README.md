# Corsair Standard

Deterministic formatting compliance platform for Microsoft Word DOCX resumes used in UGA/Corsair-style business recruiting.

**This is not an AI resume writer, semantic parser, or candidate scorer.**

It analyzes formatting compliance only — margins, tab stops, spacing, font consistency, section structure, bullet indentation, date alignment, and typography hierarchy. Every check is deterministic, derived directly from the DOCX Office Open XML structure.

---

## What it does

1. Upload a `.docx` resume
2. The engine parses the raw XML and runs ~30 formatting compliance rules
3. You get a compliance score, categorized issue list, and plain-English guidance
4. An annotated copy of the DOCX is generated with Word-native comments at each violation
5. Open the annotated copy in Microsoft Word or Office Online to see every issue flagged in context

---

## Stack

- **Backend**: Python, FastAPI, pure XML analysis via `xml.etree.ElementTree`
- **Frontend**: React, TypeScript, Vite, and Tailwind in `frontend/src`
- **DOCX parsing**: Direct Office Open XML (no python-docx for analysis)
- **Preview**: Microsoft Office Online Viewer via Cloudflare tunnel

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/ZachTeichman/corsair-standard.git
cd corsair-standard
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
uvicorn server:app --reload
```

The app runs at `http://127.0.0.1:8000`.

---

## Office Viewer preview (optional)

The Microsoft Office Online Viewer requires a publicly accessible URL for the DOCX file. On localhost you need a Cloudflare tunnel.

### Install cloudflared

```bash
brew install cloudflare/cloudflare/cloudflared   # macOS
# or download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
```

### Start a tunnel

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Cloudflare will print a public URL like:
```
https://some-random-words.trycloudflare.com
```

### Start the server with that URL

```bash
PUBLIC_BASE_URL=https://some-random-words.trycloudflare.com uvicorn server:app --reload
```

The Office Viewer preview will now work. Note: the tunnel URL changes every time you restart `cloudflared`. Update `PUBLIC_BASE_URL` accordingly.

For a stable URL during development:

```bash
cloudflared tunnel create corsair-dev
cloudflared tunnel route dns corsair-dev dev.yourdomain.com
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `PUBLIC_BASE_URL` | For preview | Public tunnel URL, e.g. `https://xxx.trycloudflare.com` |
| `MS_GRAPH_CLIENT_ID` | Optional | Azure app client ID for Microsoft Graph Office preview |
| `MS_GRAPH_TENANT` | Optional | Azure tenant, defaults to `organizations` |
| `MS_GRAPH_REDIRECT_URI` | Optional | OAuth callback URI |

For basic use (upload + analyze + download annotated DOCX) no environment variables are needed.

---

## Project structure

```
corsair/
  analyzer.py        # Core rule engine — reads DOCX XML, runs compliance checks
  docx_parser.py     # Parses word/document.xml into structured Python models
  annotator.py       # Injects Word-native comments into DOCX at violation locations
  patcher.py         # Archived experimental patcher; not part of MVP flow
  compiler.py        # Archived experimental reformatter; not part of MVP flow
  rubric.py          # Rule definitions, point values, and scoring weights
  normalize.py       # Text normalization utilities
  render_validation.py  # Page count validation via Word/LibreOffice (macOS only)

frontend/src/
  App.tsx            # Active React app shell
  components/        # Landing page, dashboard, upload, score, issue, and preview UI

web/
  privacy.html       # Static legal page
  terms.html         # Static legal page
  security.html      # Static security page
  why.html           # Static resource page
  formatting-guide.html # Static resource page
  styles.css         # Shared static-page styles

server.py            # FastAPI server — upload, analyze, annotate, template endpoints
var/uploads/         # Uploaded and working DOCX files (gitignored)
templates/           # Canonical Corsair DOCX template
rubrics/             # Rubric JSON definitions
archived/legacy-vanilla-ui/ # Old vanilla UI, retained only as reference
references/          # Historical prototypes and experiments
```

---

## Formatting rules checked

### Document / Layout
- Margins within 0.5–1.0in range
- No layout tables
- No floating text boxes
- One-page compliance (requires render validation)

### Header
- Name centered on first line
- Exactly two city/state addresses
- Contact info on one tab-separated row
- No manual spacing hacks in header

### Sections
- Required sections present (Education, Experience, etc.)
- Sections in correct Corsair order
- Section labels all caps and bold
- Section divider rules present
- Correct spelling of section labels
- Reverse chronological order within sections

### Entry lines
- Dates right-aligned via tab stop, not manual spaces
- Date ranges use en dash, not hyphen
- Date ranges are logically valid
- Organization name bold
- Role/title italicized
- City, ST location present before date

### Paragraph / Spacing
- No consecutive blank paragraphs
- No leading spaces for fake indentation
- No repeated spaces for manual alignment
- No tab+space padding hacks
- Tab characters have defined tab stops

### Bullets
- Consistent indent (0.25in bullet, 0.5in text start)
- No nested bullet levels

### Typography
- Single font family throughout
- Consistent body font size (10–12pt)
- No unauthorized bold/italic in bullets

---

## Scoring

Compliance score is weighted 65% visual / 35% structural:

- **Visual issues** (recruiter sees immediately): font family, missing bold/italic, section caps, divider rules, name centering — higher point values
- **Structural issues** (invisible but fragile): manual spaces, tab hacks, undefined tab stops — lower point values

---

## Known limitations

- Style inheritance from `word/styles.xml` is not yet fully resolved — some bold/italic/font detections may produce false positives on documents that apply formatting through named styles rather than inline runs
- Page count validation requires Microsoft Word on macOS or LibreOffice on Linux
- Office Viewer preview requires a public URL (Cloudflare tunnel for local dev)
- Auto-fix is intentionally out of scope for the MVP. The app should explain and annotate issues, not mutate resume content automatically.

---

## License

MIT
