from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
COMMENTS_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
COMMENTS_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"

ET.register_namespace("w", W_NS)
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")


RULE_LABELS: dict[str, str] = {
    "document.margin_range": "Margins out of range",
    "layout.no_tables": "Layout tables not allowed",
    "layout.no_textboxes": "Text boxes not allowed",
    "header.name_centered_top_line": "Name must be centered on top line",
    "header.dual_address": "Header needs exactly two city/state addresses",
    "header.contact_single_row": "Contact info must be on one tab-separated row",
    "header.contact_spacing_hack": "Header uses spacing hacks instead of tab stops",
    "section.corsair_structure_detected": "Corsair section structure not detected",
    "section.required_presence": "Required section missing",
    "section.order": "Sections out of order",
    "section.labels_all_caps": "Section label must be all caps",
    "section.headers_bold": "Section header must be bold",
    "section.divider_rule": "Section header missing bottom border rule",
    "entry.date_right_tab": "Entry date must use right-aligned tab stop",
    "entry.organization_bold": "Organization name must be bold",
    "entry.role_italic": "Role/title must be italicized",
    "entry.location_present": "Entry line missing City, ST location",
    "entry.date_alignment_spacing_hack": "Date aligned with spaces instead of tab stop",
    "paragraph.no_consecutive_blank_lines": "Consecutive blank lines",
    "paragraph.no_leading_spaces": "Leading spaces used instead of indent",
    "paragraph.no_manual_alignment_spaces": "Repeated spaces used for alignment",
    "paragraph.tab_space_alignment_hacks": "Tabs and spaces mixed for alignment",
    "paragraph.excessive_alignment_tabs": "Multiple tabs used as keyboard alignment",
    "paragraph.tabs_require_defined_stops": "Tab used without a defined tab stop",
    "paragraph.right_tab_consistency": "Right tab stop position inconsistent",
    "paragraph.body_alignment_consistency": "Bullet alignment inconsistent",
    "bullet.indent_consistency": "Bullet indentation inconsistent",
    "bullet.no_nested_bullets": "Nested bullets not allowed",
    "bullet.single_line_length": "Bullet may exceed one line",
    "typography.single_font_family": "Multiple font families detected",
    "typography.body_font_size_consistency": "Body font size inconsistent",
    "typography.no_unauthorized_inline_emphasis": "Unauthorized bold/italic in bullet",
}

FIX_GUIDANCE: dict[str, str] = {
    "document.margin_range": "Set all page margins to between 0.5in and 1.0in.",
    "layout.no_tables": "Remove layout tables and rebuild content as normal paragraphs.",
    "layout.no_textboxes": "Move text box content into regular document paragraphs.",
    "header.name_centered_top_line": "Place your name on the first line, centered, using the canonical header style.",
    "header.dual_address": "Include exactly two city/state addresses in the header contact row.",
    "header.contact_single_row": "Put phone, email, and both locations on one tab-separated row with a right tab stop.",
    "header.contact_spacing_hack": "Rebuild the header contact row using defined tab stops, not space padding.",
    "section.corsair_structure_detected": "Restore canonical Corsair section headers.",
    "section.required_presence": "Add the missing required section.",
    "section.order": "Reorder sections to match the required Corsair sequence.",
    "section.labels_all_caps": "Make the section label fully uppercase.",
    "section.headers_bold": "Apply bold formatting to this section header.",
    "section.divider_rule": "Add a bottom border rule directly beneath this section header.",
    "entry.date_right_tab": "Use a single right-aligned tab stop for the date. Delete manual spaces.",
    "entry.organization_bold": "Bold the organization or institution name at the start of the entry line.",
    "entry.role_italic": "Italicize the role, title, or program descriptor before the date tab.",
    "entry.location_present": "Add City, ST before the date on this entry line.",
    "entry.date_alignment_spacing_hack": "Replace space/tab padding with a clean right-aligned tab stop for the date.",
    "paragraph.no_consecutive_blank_lines": "Remove the extra blank paragraph. Use paragraph spacing instead.",
    "paragraph.no_leading_spaces": "Delete the leading spaces. Use paragraph indent settings instead.",
    "paragraph.no_manual_alignment_spaces": "Replace repeated spaces with a tab stop or paragraph indent.",
    "paragraph.tab_space_alignment_hacks": "Remove space padding around tabs. Use defined tab stops only.",
    "paragraph.excessive_alignment_tabs": "Replace multiple tab characters with one tab and a defined tab stop.",
    "paragraph.tabs_require_defined_stops": "Define a tab stop for this paragraph before using a tab character.",
    "paragraph.right_tab_consistency": "Use the same right tab stop position on all date-aligned lines.",
    "paragraph.body_alignment_consistency": "Set all bullet paragraphs to the same alignment.",
    "bullet.indent_consistency": "Use one consistent bullet indent and hanging indent throughout.",
    "bullet.no_nested_bullets": "Flatten this to the standard single-level Corsair bullet.",
    "bullet.single_line_length": "Tighten this bullet or adjust margins so it fits on one line.",
    "typography.single_font_family": "Select all text and apply one font family throughout.",
    "typography.body_font_size_consistency": "Normalize all body text to one size between 10pt and 12pt.",
    "typography.no_unauthorized_inline_emphasis": "Remove bold or italic from this bullet unless it is part of the template hierarchy.",
}

SEVERITY_PREFIX = {
    "critical": "Critical",
    "major": "Major",
    "minor": "Minor",
}


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _rel(tag: str) -> str:
    return f"{{{REL_NS}}}{tag}"


def _ct(tag: str) -> str:
    return f"{{{CT_NS}}}{tag}"


def _attr(element: ET.Element, name: str, value: str) -> None:
    element.set(_w(name), value)


def _comment_lines(violation: dict[str, Any]) -> list[str]:
    rule_id = str(violation.get("rule_id") or "formatting.issue")
    severity = str(violation.get("severity") or "minor")
    label = RULE_LABELS.get(rule_id, rule_id)
    message = str(violation.get("message") or "Formatting issue detected.")
    guidance = FIX_GUIDANCE.get(rule_id, "Review and correct this formatting issue.")
    prefix = SEVERITY_PREFIX.get(severity, "Issue")
    return [
        f"{prefix}: {label}",
        message,
        "",
        f"Fix: {guidance}",
    ]


def _make_comment(comment_id: int, violation: dict[str, Any], author: str, date_str: str) -> ET.Element:
    comment = ET.Element(_w("comment"))
    _attr(comment, "id", str(comment_id))
    _attr(comment, "author", author)
    _attr(comment, "date", date_str)
    _attr(comment, "initials", "CS")

    for line in _comment_lines(violation):
        paragraph = ET.SubElement(comment, _w("p"))
        run = ET.SubElement(paragraph, _w("r"))
        text = ET.SubElement(run, _w("t"))
        text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        text.text = line
    return comment


def _comment_range_start(comment_id: int) -> ET.Element:
    element = ET.Element(_w("commentRangeStart"))
    _attr(element, "id", str(comment_id))
    return element


def _comment_range_end(comment_id: int) -> ET.Element:
    element = ET.Element(_w("commentRangeEnd"))
    _attr(element, "id", str(comment_id))
    return element


def _comment_reference(comment_id: int) -> ET.Element:
    run = ET.Element(_w("r"))
    rpr = ET.SubElement(run, _w("rPr"))
    rstyle = ET.SubElement(rpr, _w("rStyle"))
    _attr(rstyle, "val", "CommentReference")
    reference = ET.SubElement(run, _w("commentReference"))
    _attr(reference, "id", str(comment_id))
    return run


def _paragraph_indices(violation: dict[str, Any]) -> list[int]:
    evidence = violation.get("evidence") or {}
    indices: list[int] = []

    paragraphs = evidence.get("paragraphs")
    if isinstance(paragraphs, list):
        for paragraph in paragraphs:
            if isinstance(paragraph, dict) and isinstance(paragraph.get("index"), int):
                indices.append(paragraph["index"])

    paragraph = evidence.get("paragraph")
    if isinstance(paragraph, dict) and isinstance(paragraph.get("index"), int):
        indices.append(paragraph["index"])

    if not indices:
        indices.append(0)

    deduped: list[int] = []
    for index in indices:
        if index not in deduped:
            deduped.append(index)
    return deduped


def _build_paragraph_comment_map(violations: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    mapping: dict[int, list[dict[str, Any]]] = {}
    for violation in violations:
        for index in _paragraph_indices(violation):
            mapping.setdefault(index, []).append(violation)
    return mapping


def _next_comment_id(comments_root: ET.Element) -> int:
    ids: list[int] = []
    for comment in comments_root.findall(_w("comment")):
        value = comment.get(_w("id"))
        if value and value.isdigit():
            ids.append(int(value))
    return max(ids, default=-1) + 1


def _ensure_comments_root(existing_xml: bytes | None) -> ET.Element:
    if existing_xml:
        return ET.fromstring(existing_xml)
    return ET.Element(_w("comments"))


def _ensure_comments_relationship(rels_xml: bytes) -> bytes:
    rels_root = ET.fromstring(rels_xml)
    for relationship in rels_root.findall(_rel("Relationship")):
        if relationship.get("Type") == COMMENTS_REL_TYPE:
            relationship.set("Target", "comments.xml")
            return ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)

    existing_ids = {relationship.get("Id") for relationship in rels_root.findall(_rel("Relationship"))}
    next_id = 1
    while f"rId{next_id}" in existing_ids:
        next_id += 1

    ET.SubElement(
        rels_root,
        _rel("Relationship"),
        {"Id": f"rId{next_id}", "Type": COMMENTS_REL_TYPE, "Target": "comments.xml"},
    )
    return ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)


def _ensure_comments_content_type(content_types_xml: bytes) -> bytes:
    content_root = ET.fromstring(content_types_xml)
    for override in content_root.findall(_ct("Override")):
        if override.get("PartName") == "/word/comments.xml":
            override.set("ContentType", COMMENTS_CONTENT_TYPE)
            return ET.tostring(content_root, encoding="utf-8", xml_declaration=True)

    ET.SubElement(
        content_root,
        _ct("Override"),
        {"PartName": "/word/comments.xml", "ContentType": COMMENTS_CONTENT_TYPE},
    )
    return ET.tostring(content_root, encoding="utf-8", xml_declaration=True)


def annotate_docx(
    input_path: str | Path,
    violations: list[dict[str, Any]],
    output_path: str | Path,
    author: str = "Corsair Standard",
) -> Path:
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not violations:
        shutil.copy2(input_path, output_path)
        return output_path

    with ZipFile(input_path, "r") as source:
        entries = {item.filename: source.read(item.filename) for item in source.infolist()}

    document_root = ET.fromstring(entries["word/document.xml"])
    body_paragraphs = document_root.findall(".//" + _w("body") + "/" + _w("p"))
    if not body_paragraphs:
        raise ValueError("word/document.xml has no body paragraphs.")

    comments_root = _ensure_comments_root(entries.get("word/comments.xml"))
    next_id = _next_comment_id(comments_root)
    date_str = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    paragraph_map = _build_paragraph_comment_map(violations)

    for paragraph_index, paragraph in enumerate(body_paragraphs):
        paragraph_violations = paragraph_map.get(paragraph_index, [])
        if not paragraph_violations:
            continue

        ppr = paragraph.find(_w("pPr"))
        insert_pos = 1 if ppr is not None else 0
        for violation in paragraph_violations:
            comment_id = next_id
            next_id += 1
            comments_root.append(_make_comment(comment_id, violation, author, date_str))
            paragraph.insert(insert_pos, _comment_range_start(comment_id))
            insert_pos += 1
            paragraph.append(_comment_range_end(comment_id))
            paragraph.append(_comment_reference(comment_id))

    entries["word/document.xml"] = ET.tostring(document_root, encoding="utf-8", xml_declaration=True)
    entries["word/comments.xml"] = ET.tostring(comments_root, encoding="utf-8", xml_declaration=True)
    entries["word/_rels/document.xml.rels"] = _ensure_comments_relationship(entries["word/_rels/document.xml.rels"])
    entries["[Content_Types].xml"] = _ensure_comments_content_type(entries["[Content_Types].xml"])

    with ZipFile(output_path, "w", ZIP_DEFLATED) as target:
        for name, data in entries.items():
            target.writestr(name, data)

    return output_path
