"""
corsair/patcher.py

Surgical XML-only patcher for Corsair Standard.

Each fix function receives the DOCX ZIP entries dict
{ filename: bytes } and returns a modified entries dict.

Rules:
  - Never call analyze_docx here. The server re-analyzes after patching.
  - Never use python-docx (Document class). Raw XML only.
  - Never rewrite content — only touch XML properties.
  - Each fixer is a standalone function registered in FIXERS.

Usage (server.py):
    from corsair.patcher import apply_fix, FIXERS

    entries = read_zip(working_path)
    entries = apply_fix(entries, rule_id, paragraph_index)
    write_zip(working_path, entries)
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

ET.register_namespace("w",   W_NS)
ET.register_namespace("r",   "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
ET.register_namespace("mc",  "http://schemas.openxmlformats.org/markup-compatibility/2006")
ET.register_namespace("wpc", "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas")
ET.register_namespace("m",   "http://schemas.openxmlformats.org/officeDocument/2006/math")
ET.register_namespace("o",   "urn:schemas-microsoft-com:office:office")
ET.register_namespace("v",   "urn:schemas-microsoft-com:vml")
ET.register_namespace("wp",  "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing")
ET.register_namespace("w10", "urn:schemas-microsoft-com:office:word")
ET.register_namespace("wne", "http://schemas.microsoft.com/office/word/2006/wordml")
ET.register_namespace("wps", "http://schemas.microsoft.com/office/word/2010/wordprocessingShape")


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _attr(el: ET.Element, name: str, value: str) -> None:
    el.set(_w(name), value)


def _get_or_add(parent: ET.Element, tag: str) -> ET.Element:
    """Find child element by tag or create it."""
    el = parent.find(tag)
    if el is None:
        el = ET.SubElement(parent, tag)
    return el


def _inches_to_twips(inches: float) -> str:
    return str(round(inches * 1440))


def _inches_to_half_points(inches: float) -> str:
    """Font size in half-points (w:sz). 10pt = 20 half-points."""
    return str(round(inches * 144))  # not used directly but kept for reference


def _pt_to_half_points(pt: float) -> str:
    return str(round(pt * 2))


def _parse_zip(entries: Dict[str, bytes], filename: str) -> ET.Element:
    return ET.fromstring(entries[filename])


def _serialise(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _body_paragraphs(doc_root: ET.Element) -> List[ET.Element]:
    body = doc_root.find(_w("body"))
    if body is None:
        return []
    return body.findall(_w("p"))


def _is_blank_paragraph(para: ET.Element) -> bool:
    text = "".join(
        t.text or ""
        for t in para.findall(f".//{_w('t')}")
    ).strip()
    return text == ""


def _get_ppr(para: ET.Element) -> ET.Element:
    ppr = para.find(_w("pPr"))
    if ppr is None:
        ppr = ET.Element(_w("pPr"))
        para.insert(0, ppr)
    return ppr


# ---------------------------------------------------------------------------
# Section detection (mirrors analyzer logic)
# ---------------------------------------------------------------------------

SECTION_RE = re.compile(r"^[A-Z][A-Z &/]{3,}$")


def _paragraph_text(para: ET.Element) -> str:
    return "".join(t.text or "" for t in para.findall(f".//{_w('t')}")).strip()


def _is_section_paragraph(para: ET.Element) -> bool:
    return bool(SECTION_RE.fullmatch(_paragraph_text(para)))


def _section_paragraphs(doc_root: ET.Element) -> List[ET.Element]:
    return [p for p in _body_paragraphs(doc_root) if _is_section_paragraph(p)]


# ---------------------------------------------------------------------------
# Margin fix
# ---------------------------------------------------------------------------

CANONICAL_MARGIN_TWIPS = _inches_to_twips(1.0)  # "10800" → wait, 1.0in = 1440 twips
# 1.0 inch = 1440 twips
CANONICAL_MARGIN_TWIPS = "1440"


def _fix_margin_range(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """Set all page margins to exactly 1.0in (1440 twips)."""
    doc_root = _parse_zip(entries, "word/document.xml")
    body = doc_root.find(_w("body"))
    if body is None:
        return entries

    sect_pr = body.find(_w("sectPr"))
    if sect_pr is None:
        sect_pr = ET.SubElement(body, _w("sectPr"))

    pg_mar = sect_pr.find(_w("pgMar"))
    if pg_mar is None:
        pg_mar = ET.SubElement(sect_pr, _w("pgMar"))

    for side in ("top", "right", "bottom", "left"):
        _attr(pg_mar, side, CANONICAL_MARGIN_TWIPS)

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Font family fix
# ---------------------------------------------------------------------------

CANONICAL_FONT = "Garamond"


def _fix_single_font_family(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """Set w:rFonts on every run to the canonical font family."""
    doc_root = _parse_zip(entries, "word/document.xml")

    for run in doc_root.findall(f".//{_w('r')}"):
        rpr = _get_or_add(run, _w("rPr"))
        rfonts = rpr.find(_w("rFonts"))
        if rfonts is None:
            rfonts = ET.SubElement(rpr, _w("rFonts"))
        _attr(rfonts, "ascii",  CANONICAL_FONT)
        _attr(rfonts, "hAnsi", CANONICAL_FONT)
        _attr(rfonts, "cs",    CANONICAL_FONT)

    # Also patch the Normal style in styles.xml if present
    if "word/styles.xml" in entries:
        styles_root = _parse_zip(entries, "word/styles.xml")
        for rfonts in styles_root.findall(f".//{_w('rFonts')}"):
            _attr(rfonts, "ascii",  CANONICAL_FONT)
            _attr(rfonts, "hAnsi", CANONICAL_FONT)
            _attr(rfonts, "cs",    CANONICAL_FONT)
        entries["word/styles.xml"] = _serialise(styles_root)

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Font size fix
# ---------------------------------------------------------------------------

CANONICAL_BODY_SIZE_HALF_PT = _pt_to_half_points(10.0)  # "20"
BODY_SIZE_MIN_PT = 8.0
BODY_SIZE_MAX_PT = 12.0


def _fix_body_font_size(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """Normalise all body run sizes to 10pt (20 half-points)."""
    doc_root = _parse_zip(entries, "word/document.xml")

    for run in doc_root.findall(f".//{_w('r')}"):
        rpr = run.find(_w("rPr"))
        if rpr is None:
            continue
        sz = rpr.find(_w("sz"))
        if sz is None:
            continue
        val_str = sz.get(_w("val"), "")
        if not val_str.isdigit():
            continue
        val_pt = int(val_str) / 2
        # Only normalise sizes in the body range — leave heading sizes alone
        if BODY_SIZE_MIN_PT <= val_pt <= BODY_SIZE_MAX_PT:
            _attr(sz, "val", CANONICAL_BODY_SIZE_HALF_PT)
            sz_cs = rpr.find(_w("szCs"))
            if sz_cs is not None:
                _attr(sz_cs, "val", CANONICAL_BODY_SIZE_HALF_PT)

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Section headers bold
# ---------------------------------------------------------------------------

def _fix_section_headers_bold(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """Set w:b on all runs inside detected section header paragraphs."""
    doc_root = _parse_zip(entries, "word/document.xml")
    paragraphs = _body_paragraphs(doc_root)

    targets = (
        [paragraphs[paragraph_index]]
        if paragraph_index is not None and paragraph_index < len(paragraphs)
        else _section_paragraphs(doc_root)
    )

    for para in targets:
        for run in para.findall(_w("r")):
            rpr = _get_or_add(run, _w("rPr"))
            if rpr.find(_w("b")) is None:
                ET.SubElement(rpr, _w("b"))
            # Remove explicit b val="0" if present
            b_el = rpr.find(_w("b"))
            if b_el is not None:
                b_el.attrib.pop(_w("val"), None)

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Section labels all caps
# ---------------------------------------------------------------------------

def _fix_section_labels_all_caps(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """Uppercase the text content of section header paragraphs."""
    doc_root = _parse_zip(entries, "word/document.xml")
    paragraphs = _body_paragraphs(doc_root)

    targets = (
        [paragraphs[paragraph_index]]
        if paragraph_index is not None and paragraph_index < len(paragraphs)
        else _section_paragraphs(doc_root)
    )

    for para in targets:
        for t_el in para.findall(f".//{_w('t')}"):
            if t_el.text:
                t_el.text = t_el.text.upper()

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Section divider rule (bottom border)
# ---------------------------------------------------------------------------

def _fix_section_divider_rule(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """Inject a bottom border rule on section header paragraphs."""
    doc_root = _parse_zip(entries, "word/document.xml")
    paragraphs = _body_paragraphs(doc_root)

    targets = (
        [paragraphs[paragraph_index]]
        if paragraph_index is not None and paragraph_index < len(paragraphs)
        else _section_paragraphs(doc_root)
    )

    for para in targets:
        ppr = _get_ppr(para)
        p_bdr = ppr.find(_w("pBdr"))
        if p_bdr is None:
            p_bdr = ET.SubElement(ppr, _w("pBdr"))

        # Remove existing bottom if present to avoid duplicates
        existing = p_bdr.find(_w("bottom"))
        if existing is not None:
            p_bdr.remove(existing)

        bottom = ET.SubElement(p_bdr, _w("bottom"))
        _attr(bottom, "val",   "single")
        _attr(bottom, "sz",    "4")
        _attr(bottom, "space", "1")
        _attr(bottom, "color", "000000")

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Consecutive blank lines
# ---------------------------------------------------------------------------

def _fix_consecutive_blank_lines(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """Remove consecutive blank paragraphs, keeping at most one in a row."""
    doc_root = _parse_zip(entries, "word/document.xml")
    body = doc_root.find(_w("body"))
    if body is None:
        return entries

    children = list(body)
    to_remove: List[ET.Element] = []
    last_was_blank = False

    for child in children:
        if child.tag != _w("p"):
            last_was_blank = False
            continue
        is_blank = _is_blank_paragraph(child)
        if is_blank and last_was_blank:
            to_remove.append(child)
        last_was_blank = is_blank

    for el in to_remove:
        body.remove(el)

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Bullet indent consistency
# ---------------------------------------------------------------------------

# Canonical Corsair bullet indent values (in twips)
CANONICAL_LEFT_INDENT_TWIPS  = "691"   # ~0.48in
CANONICAL_HANGING_INDENT_TWIPS = "331"  # ~0.23in


def _fix_bullet_indent_consistency(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """
    Set w:ind left and hanging to canonical values on all numbered
    (bullet) paragraphs.
    """
    doc_root = _parse_zip(entries, "word/document.xml")

    for para in _body_paragraphs(doc_root):
        ppr = para.find(_w("pPr"))
        if ppr is None:
            continue
        num_pr = ppr.find(_w("numPr"))
        if num_pr is None:
            continue  # not a bullet paragraph

        ind = ppr.find(_w("ind"))
        if ind is None:
            ind = ET.SubElement(ppr, _w("ind"))

        _attr(ind, "left",    CANONICAL_LEFT_INDENT_TWIPS)
        _attr(ind, "hanging", CANONICAL_HANGING_INDENT_TWIPS)

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Right tab consistency
# ---------------------------------------------------------------------------

def _compute_canonical_right_tab(entries: Dict[str, bytes]) -> str:
    """
    Compute the correct right tab position in twips based on actual
    page width and margins rather than hardcoding 10800.

    Standard letter: 12240 twips wide.
    Right tab = page_width - left_margin - right_margin.
    Default: 12240 - 1440 - 1440 = 9360 twips (6.5in).
    Corsair 0.5in margins: 12240 - 720 - 720 = 10800 twips (7.5in).
    """
    PAGE_WIDTH_TWIPS = 12240  # US Letter

    try:
        doc_root = _parse_zip(entries, "word/document.xml")
        body = doc_root.find(_w("body"))
        sect_pr = body.find(_w("sectPr")) if body is not None else None
        pg_mar = sect_pr.find(_w("pgMar")) if sect_pr is not None else None

        if pg_mar is not None:
            left  = int(pg_mar.get(_w("left"),  "1440"))
            right = int(pg_mar.get(_w("right"), "1440"))
        else:
            left = right = 1440

        # Also check page size
        pg_sz = sect_pr.find(_w("pgSz")) if sect_pr is not None else None
        if pg_sz is not None:
            w_val = pg_sz.get(_w("w"))
            if w_val and w_val.isdigit():
                PAGE_WIDTH_TWIPS = int(w_val)

        return str(PAGE_WIDTH_TWIPS - left - right)
    except Exception:
        return "10800"  # safe fallback


def _fix_right_tab_consistency(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """Update all right-aligned tab stops to the computed canonical position."""
    canonical = _compute_canonical_right_tab(entries)
    doc_root = _parse_zip(entries, "word/document.xml")
    paragraphs = _body_paragraphs(doc_root)

    targets = (
        [paragraphs[paragraph_index]]
        if paragraph_index is not None and paragraph_index < len(paragraphs)
        else paragraphs
    )

    for para in targets:
        ppr = para.find(_w("pPr"))
        if ppr is None:
            continue
        tabs = ppr.find(_w("tabs"))
        if tabs is None:
            continue
        for tab in tabs.findall(_w("tab")):
            if tab.get(_w("val")) == "right":
                _attr(tab, "pos", canonical)

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Tab stops required fix
# ---------------------------------------------------------------------------

def _fix_tabs_require_defined_stops(
    entries: Dict[str, bytes],
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """
    For paragraphs that use tab characters but have no defined tab stops,
    inject the canonical right tab stop.
    """
    canonical = _compute_canonical_right_tab(entries)
    doc_root = _parse_zip(entries, "word/document.xml")
    paragraphs = _body_paragraphs(doc_root)

    targets = (
        [paragraphs[paragraph_index]]
        if paragraph_index is not None and paragraph_index < len(paragraphs)
        else paragraphs
    )

    for para in targets:
        # Check if paragraph uses tabs in its runs
        has_tabs = bool(para.findall(f".//{_w('tab')}"))
        if not has_tabs:
            continue

        ppr = _get_ppr(para)
        tabs = ppr.find(_w("tabs"))
        if tabs is not None and tabs.findall(_w("tab")):
            continue  # already has defined stops

        if tabs is None:
            tabs = ET.SubElement(ppr, _w("tabs"))

        new_tab = ET.SubElement(tabs, _w("tab"))
        _attr(new_tab, "val", "right")
        _attr(new_tab, "pos", canonical)

    entries["word/document.xml"] = _serialise(doc_root)
    return entries


# ---------------------------------------------------------------------------
# Fixer registry
# ---------------------------------------------------------------------------

# Maps rule_id → fixer function
# Only rules with a SAFE deterministic fix are registered here.
# Everything else returns 422 from the server endpoint.

FixerFn = Callable[[Dict[str, bytes], Optional[int]], Dict[str, bytes]]

FIXERS: Dict[str, FixerFn] = {
    "document.margin_range":                  _fix_margin_range,
    "typography.single_font_family":          _fix_single_font_family,
    "typography.body_font_size_consistency":  _fix_body_font_size,
    "section.headers_bold":                   _fix_section_headers_bold,
    "section.labels_all_caps":               _fix_section_labels_all_caps,
    "section.divider_rule":                   _fix_section_divider_rule,
    "paragraph.no_consecutive_blank_lines":   _fix_consecutive_blank_lines,
    "bullet.indent_consistency":              _fix_bullet_indent_consistency,
    "paragraph.right_tab_consistency":        _fix_right_tab_consistency,
    "paragraph.tabs_require_defined_stops":   _fix_tabs_require_defined_stops,
}

# Rules that have no safe auto-fix — shown with "Open in Word" + "Ignore" only
MANUAL_ONLY_RULES = {
    "layout.no_tables",
    "layout.no_textboxes",
    "header.name_centered_top_line",
    "header.dual_address",
    "header.contact_single_row",
    "header.contact_spacing_hack",
    "section.corsair_structure_detected",
    "section.required_presence",
    "section.order",
    "entry.date_right_tab",
    "entry.organization_bold",
    "entry.role_italic",
    "entry.location_present",
    "entry.date_alignment_spacing_hack",
    "paragraph.no_leading_spaces",
    "paragraph.no_manual_alignment_spaces",
    "paragraph.tab_space_alignment_hacks",
    "paragraph.excessive_alignment_tabs",
    "paragraph.body_alignment_consistency",
    "paragraph.right_tab_consistency",
    "bullet.no_nested_bullets",
    "bullet.single_line_length",
    "typography.no_unauthorized_inline_emphasis",
    "document.one_page_rendered",
    "header.contact_spacing_hack",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_auto_fixable(rule_id: str) -> bool:
    """Return True if this rule has a registered safe auto-fix."""
    return rule_id in FIXERS


def apply_fix(
    entries: Dict[str, bytes],
    rule_id: str,
    paragraph_index: Optional[int],
) -> Dict[str, bytes]:
    """
    Apply the registered fix for rule_id to the entries dict.

    Raises KeyError if rule_id has no registered fixer.
    The caller should check is_auto_fixable() first and return 422 if False.
    """
    fixer = FIXERS[rule_id]
    return fixer(entries, paragraph_index)


def read_zip_entries(path) -> Dict[str, bytes]:
    """Read a DOCX ZIP into a {filename: bytes} dict."""
    from zipfile import ZipFile
    from pathlib import Path
    with ZipFile(Path(path), "r") as zf:
        return {name: zf.read(name) for name in zf.namelist()}


def write_zip_entries(path, entries: Dict[str, bytes]) -> None:
    """Write a {filename: bytes} dict back to a DOCX ZIP."""
    from zipfile import ZipFile, ZIP_DEFLATED
    from pathlib import Path
    with ZipFile(Path(path), "w", ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
