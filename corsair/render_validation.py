from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import Any, Dict


WORD_APP_PATH = Path("/Applications/Microsoft Word.app")


def get_render_validation_status() -> Dict[str, Any]:
    osascript_path = which("osascript")
    if WORD_APP_PATH.exists() and osascript_path:
        return {
            "available": True,
            "engine": "microsoft_word",
            "binary_path": osascript_path,
            "notes": "Rendered page-count validation is available through Microsoft Word.",
        }

    return {
        "available": False,
        "engine": "microsoft_word",
        "binary_path": None,
        "notes": "Microsoft Word is required for high-fidelity Office 365-compatible rendering.",
    }


def _export_with_word(docx_path: Path, pdf_path: Path, osascript_path: str) -> subprocess.CompletedProcess[str]:
    script_lines = [
        f'set sourcePath to "{docx_path}"',
        f'set outputPath to "{pdf_path}"',
        'tell application id "com.microsoft.Word"',
        "set visible to false",
        "open file name sourcePath",
        "set activeDoc to active document",
        "save as activeDoc file name outputPath file format format PDF",
        "close activeDoc saving no",
        "end tell",
    ]
    command = [osascript_path]
    for line in script_lines:
        command.extend(["-e", line])
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def validate_rendered_page_count(docx_path: str | Path) -> Dict[str, Any]:
    status = get_render_validation_status()
    if not status["available"]:
        return {**status, "page_count": None, "ok": False}

    try:
        import fitz
    except Exception as exc:
        return {
            **status,
            "page_count": None,
            "ok": False,
            "notes": f"PyMuPDF is unavailable, so rendered page-count validation failed: {exc}",
        }

    source = Path(docx_path).resolve()
    with TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        pdf_path = tmp_dir_path / f"{source.stem}.pdf"
        try:
            completed = _export_with_word(source, pdf_path, status["binary_path"])
        except subprocess.TimeoutExpired:
            return {
                **status,
                "page_count": None,
                "ok": False,
                "notes": f"{status['engine']} conversion timed out.",
            }

        if completed.returncode != 0:
            return {
                **status,
                "page_count": None,
                "ok": False,
                "notes": completed.stderr.strip() or completed.stdout.strip() or f"{status['engine']} conversion failed.",
            }

        if not pdf_path.exists():
            pdf_candidates = list(tmp_dir_path.glob("*.pdf"))
            pdf_path = pdf_candidates[0] if pdf_candidates else pdf_path
        if not pdf_path.exists():
            return {
                **status,
                "page_count": None,
                "ok": False,
                "notes": f"{status['engine']} did not produce a PDF output file.",
            }

        pdf_doc = fitz.open(str(pdf_path))
        page_count = pdf_doc.page_count
        pdf_doc.close()

    return {
        **status,
        "page_count": page_count,
        "ok": page_count == 1,
        "notes": "Rendered page-count validation completed.",
    }
