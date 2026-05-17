"""
Session management routes for Corsair Standard.

Paste this into server.py after the existing imports and before app.mount().

Required additional imports for server.py:
    import time
    from corsair.patcher import apply_fix, is_auto_fixable, read_zip_entries, write_zip_entries
"""

# ---------------------------------------------------------------------------
# Paste these imports at the top of server.py alongside existing imports
# ---------------------------------------------------------------------------
# import time                                                   # already likely present
# from corsair.patcher import (
#     apply_fix, is_auto_fixable, read_zip_entries, write_zip_entries
# )

# ---------------------------------------------------------------------------
# Paste this session store near the top of server.py, after UPLOAD_DIR
# ---------------------------------------------------------------------------

"""
SESSIONS: dict[str, dict] = {}
SESSION_TTL_SECONDS = 2 * 60 * 60  # 2 hours

def _expire_sessions() -> None:
    now = time.time()
    expired = [uid for uid, session in SESSIONS.items() if now - session["created_at"] > SESSION_TTL_SECONDS]
    for uid in expired:
        SESSIONS.pop(uid, None)
"""

# ---------------------------------------------------------------------------
# Replace /api/analyze with this version (adds session creation)
# ---------------------------------------------------------------------------

from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

# These will already exist in server.py — shown here for reference
# from corsair.analyzer import analyze_docx
# from corsair.annotator import annotate_docx
# from corsair.patcher import apply_fix, is_auto_fixable, read_zip_entries, write_zip_entries


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class FixRequest(BaseModel):
    rule_id: str
    paragraph_index: Optional[int] = None


class IgnoreRequest(BaseModel):
    rule_id: str
    paragraph_index: Optional[int] = None


# ---------------------------------------------------------------------------
# Score helpers
# ---------------------------------------------------------------------------

def _active_violations(session: dict) -> list[dict[str, Any]]:
    """Return violations not yet fixed or ignored."""
    ignored_keys = {
        (item["rule_id"], item.get("paragraph_index"))
        for item in session["ignored"]
    }
    fixed_keys = {
        (item["rule_id"], item.get("paragraph_index"))
        for item in session["history"]
    }
    return [
        v for v in session["analysis"].get("violations", [])
        if (v["rule_id"], None) not in ignored_keys
        and (v["rule_id"], None) not in fixed_keys
    ]


def _score_from_violations(violations: list[dict[str, Any]], full_analysis: dict) -> int:
    """
    Recalculate score excluding ignored/fixed violations.
    Mirrors analyzer.py scoring: sum penalties, subtract from 100.
    """
    from corsair.analyzer import STRUCTURAL_QUALITY_RULES
    structural_penalty = sum(v["points"] for v in violations if v["rule_id"] in STRUCTURAL_QUALITY_RULES)
    visual_penalty     = sum(v["points"] for v in violations if v["rule_id"] not in STRUCTURAL_QUALITY_RULES)
    visual_score       = max(0, 100 - visual_penalty)
    structural_score   = max(0, 100 - structural_penalty)
    return round((visual_score + structural_score) / 2)


def _session_response(session: dict, fixed_rule_id: str | None = None, duration_ms: float = 0) -> dict[str, Any]:
    """Build the standard session state response."""
    active = _active_violations(session)
    score  = _score_from_violations(active, session["analysis"])

    # Annotate each violation with fixability so frontend can render correct buttons
    for v in active:
        v["auto_fixable"] = is_auto_fixable(v["rule_id"])

    return {
        "score":          score,
        "violations":     active,
        "fixed_rule_id":  fixed_rule_id,
        "history":        session["history"],
        "ignored_count":  len(session["ignored"]),
        "duration_ms":    round(duration_ms, 1),
    }


# ---------------------------------------------------------------------------
# Updated /api/analyze endpoint
# (Replace the existing one in server.py with this version)
# ---------------------------------------------------------------------------

def make_analyze_endpoint(
    app,
    UPLOAD_DIR: Path,
    SESSIONS: dict,
    PUBLIC_BASE_URL: str,
    analyze_docx,
    annotate_docx,
    apply_fix,
    is_auto_fixable,
    read_zip_entries,
    write_zip_entries,
):
    """
    Call this function after defining app in server.py to register
    the updated analyze endpoint with session support.

    Or simply inline the route directly into server.py.
    """

    @app.post("/api/analyze")
    def analyze_resume(file: UploadFile = File(...)) -> dict[str, Any]:
        from corsair.analyzer import analyze_docx as _analyze
        from corsair.annotator import annotate_docx as _annotate

        _expire_sessions()

        filename = file.filename or ""
        if not filename.lower().endswith(".docx"):
            raise HTTPException(
                status_code=400,
                detail="Only .docx uploads are supported.",
            )

        t0 = time.time()
        upload_id   = uuid.uuid4().hex
        safe_name   = Path(filename).name
        orig_path   = UPLOAD_DIR / f"{upload_id}_original_{safe_name}"
        working_path = UPLOAD_DIR / f"{upload_id}_working_{safe_name}"

        with orig_path.open("wb") as fh:
            shutil.copyfileobj(file.file, fh)
        shutil.copy2(orig_path, working_path)

        try:
            analysis = _analyze(working_path, render=False)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

        # Annotate violations with fixability
        for v in analysis.get("violations", []):
            v["auto_fixable"] = is_auto_fixable(v["rule_id"])

        SESSIONS[upload_id] = {
            "original":       orig_path,
            "working":        working_path,
            "analysis":       analysis,
            "history":        [],
            "ignored":        [],
            "annotated_cache": None,
            "created_at":     time.time(),
        }

        duration_ms = (time.time() - t0) * 1000

        # Build viewer URLs
        annotated_public_url = (
            f"{PUBLIC_BASE_URL}/api/sessions/{upload_id}/annotated-public"
            if PUBLIC_BASE_URL else None
        )
        office_embed_url = (
            f"https://view.officeapps.live.com/op/embed.aspx?src={quote(annotated_public_url, safe='')}&action=embedview"
            if annotated_public_url else None
        )
        office_viewer_url = (
            f"https://view.officeapps.live.com/op/view.aspx?src={quote(annotated_public_url, safe='')}"
            if annotated_public_url else None
        )

        active = _active_violations(SESSIONS[upload_id])
        score  = _score_from_violations(active, analysis)

        return {
            "status":     "complete",
            "audit_type": "draft_format_compliance",
            "source":     {"filename": filename, "file_type": "docx"},
            "upload_id":  upload_id,
            "score":      score,
            "violations": active,
            "result":     {**analysis, "score": score},
            "document_links": {
                "upload_id":          upload_id,
                "original_docx":      f"/api/sessions/{upload_id}/download?version=original",
                "annotated_docx":     f"/api/sessions/{upload_id}/download",
                "office_viewer_embed": office_embed_url,
                "office_viewer_open":  office_viewer_url,
            },
            "duration_ms": round(duration_ms, 1),
        }


# ---------------------------------------------------------------------------
# Session endpoints — paste these directly into server.py
# ---------------------------------------------------------------------------

# @app.post("/api/sessions/{upload_id}/fix")
def session_fix_route(app, SESSIONS, analyze_docx, apply_fix, is_auto_fixable, read_zip_entries, write_zip_entries):

    @app.post("/api/sessions/{upload_id}/fix")
    def session_fix(upload_id: str, body: FixRequest) -> dict[str, Any]:
        session = SESSIONS.get(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired.")

        if not is_auto_fixable(body.rule_id):
            raise HTTPException(
                status_code=422,
                detail=f"No safe auto-fix available for rule '{body.rule_id}'.",
            )

        t0 = time.time()

        # Read working DOCX as ZIP entries
        entries = read_zip_entries(session["working"])

        # Apply the single targeted fix
        try:
            entries = apply_fix(entries, body.rule_id, body.paragraph_index)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Patch failed: {exc}") from exc

        # Write patched working DOCX back to disk
        write_zip_entries(session["working"], entries)

        # Invalidate annotated cache — viewer must regenerate on next request
        session["annotated_cache"] = None

        # Re-analyze
        try:
            session["analysis"] = analyze_docx(session["working"], render=False)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Re-analysis failed: {exc}") from exc

        # Record fix in history
        session["history"].append({
            "rule_id":         body.rule_id,
            "paragraph_index": body.paragraph_index,
            "fixed_at":        time.time(),
        })

        duration_ms = (time.time() - t0) * 1000
        return _session_response(session, fixed_rule_id=body.rule_id, duration_ms=duration_ms)


# @app.post("/api/sessions/{upload_id}/ignore")
def session_ignore_route(app, SESSIONS):

    @app.post("/api/sessions/{upload_id}/ignore")
    def session_ignore(upload_id: str, body: IgnoreRequest) -> dict[str, Any]:
        session = SESSIONS.get(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired.")

        t0 = time.time()

        # Add to ignored list (avoid duplicates)
        key = {"rule_id": body.rule_id, "paragraph_index": body.paragraph_index}
        if key not in session["ignored"]:
            session["ignored"].append(key)

        duration_ms = (time.time() - t0) * 1000
        return _session_response(session, duration_ms=duration_ms)


# @app.post("/api/sessions/{upload_id}/undo-ignore")
def session_undo_ignore_route(app, SESSIONS):

    @app.post("/api/sessions/{upload_id}/undo-ignore")
    def session_undo_ignore(upload_id: str, body: IgnoreRequest) -> dict[str, Any]:
        session = SESSIONS.get(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired.")

        t0 = time.time()
        key = {"rule_id": body.rule_id, "paragraph_index": body.paragraph_index}
        session["ignored"] = [i for i in session["ignored"] if i != key]

        duration_ms = (time.time() - t0) * 1000
        return _session_response(session, duration_ms=duration_ms)


# @app.post("/api/sessions/{upload_id}/reset")
def session_reset_route(app, SESSIONS, analyze_docx):

    @app.post("/api/sessions/{upload_id}/reset")
    def session_reset(upload_id: str) -> dict[str, Any]:
        session = SESSIONS.get(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired.")

        t0 = time.time()

        # Restore working copy from original
        shutil.copy2(session["original"], session["working"])

        # Clear state
        session["history"]          = []
        session["ignored"]          = []
        session["annotated_cache"]  = None

        # Re-analyze
        try:
            session["analysis"] = analyze_docx(session["working"], render=False)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Re-analysis failed: {exc}") from exc

        duration_ms = (time.time() - t0) * 1000
        return _session_response(session, duration_ms=duration_ms)


# @app.get("/api/sessions/{upload_id}/download")
def session_download_route(app, SESSIONS):

    @app.get("/api/sessions/{upload_id}/download")
    def session_download(upload_id: str, version: str = "working") -> FileResponse:
        session = SESSIONS.get(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired.")

        path = session["original"] if version == "original" else session["working"]
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found.")

        stem = path.name.split("_working_", 1)[-1].split("_original_", 1)[-1]
        download_name = f"corsair-{'original' if version == 'original' else 'fixed'}-{stem}"

        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=download_name,
        )


# @app.get("/api/sessions/{upload_id}/viewer")
def session_viewer_route(app, SESSIONS, UPLOAD_DIR, PUBLIC_BASE_URL, annotate_docx):

    @app.get("/api/sessions/{upload_id}/viewer")
    def session_viewer(upload_id: str) -> dict[str, Any]:
        """
        Generate (or return cached) annotated DOCX viewer URL.
        Regenerates annotated DOCX only when annotated_cache is None
        (i.e. after a fix, reset, or first request).
        """
        session = SESSIONS.get(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired.")

        if session["annotated_cache"] is None:
            # Regenerate annotated DOCX from current working copy
            violations = session["analysis"].get("violations", [])
            safe_stem  = session["working"].name.split("_working_", 1)[-1]
            annotated_path = UPLOAD_DIR / f"{upload_id}_annotated_{safe_stem}"
            try:
                annotate_docx(session["working"], violations, annotated_path)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Annotation failed: {exc}") from exc
            session["annotated_cache"] = annotated_path

        if not PUBLIC_BASE_URL:
            return {
                "ready": False,
                "reason": "PUBLIC_BASE_URL is not set. Start the Cloudflare tunnel and restart with PUBLIC_BASE_URL.",
                "download_url": f"/api/sessions/{upload_id}/download",
            }

        annotated_public = f"{PUBLIC_BASE_URL}/api/sessions/{upload_id}/annotated-public"
        viewer_url  = f"https://view.officeapps.live.com/op/view.aspx?src={quote(annotated_public, safe='')}"
        embed_url   = f"https://view.officeapps.live.com/op/embed.aspx?src={quote(annotated_public, safe='')}&action=embedview"

        return {
            "ready":       True,
            "viewer_url":  viewer_url,
            "embed_url":   embed_url,
            "download_url": f"/api/sessions/{upload_id}/download",
        }


# @app.get("/api/sessions/{upload_id}/annotated-public")
def session_annotated_public_route(app, SESSIONS, UPLOAD_DIR, annotate_docx):

    @app.get("/api/sessions/{upload_id}/annotated-public")
    def session_annotated_public(upload_id: str) -> FileResponse:
        """
        Serve the annotated DOCX at a stable public URL for Office Viewer.
        This is what the Office Viewer iframe fetches.
        Regenerates if cache is invalidated.
        """
        session = SESSIONS.get(upload_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired.")

        if session["annotated_cache"] is None:
            violations = session["analysis"].get("violations", [])
            safe_stem  = session["working"].name.split("_working_", 1)[-1]
            annotated_path = UPLOAD_DIR / f"{upload_id}_annotated_{safe_stem}"
            try:
                annotate_docx(session["working"], violations, annotated_path)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Annotation failed: {exc}") from exc
            session["annotated_cache"] = annotated_path

        path = session["annotated_cache"]
        if not path.exists():
            raise HTTPException(status_code=404, detail="Annotated file not found.")

        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


# ---------------------------------------------------------------------------
# TTL cleanup (call this at the top of /api/analyze)
# ---------------------------------------------------------------------------

def _expire_sessions() -> None:
    """Remove sessions older than SESSION_TTL_SECONDS."""
    SESSION_TTL_SECONDS = 2 * 60 * 60
    now     = time.time()
    expired = [
        uid for uid, s in SESSIONS.items()
        if now - s["created_at"] > SESSION_TTL_SECONDS
    ]
    for uid in expired:
        session = SESSIONS.pop(uid, None)
        if session:
            # Clean up files
            for key in ("original", "working", "annotated_cache"):
                path = session.get(key)
                if path and isinstance(path, Path) and path.exists():
                    try:
                        path.unlink()
                    except OSError:
                        pass
