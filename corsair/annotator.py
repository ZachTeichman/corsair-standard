from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
COMMENTS_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
COMMENTS_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
DATE_PATTERN = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}"
    r"(?:\s*[-–]\s*(?:Present|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{4}))?\b"
)

ET.register_namespace("w", W_NS)
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")


RULE_LABELS: dict[str, str] = {
    "document.margin_range": "Margins out of range",
    "layout.no_tables": "Layout tables not allowed",
    "layout.no_textboxes": "Text boxes not allowed",
    "header.name_centered_top_line": "Name looks centered but is fragile to edit",
    "header.dual_address": "Header needs exactly two city/state addresses",
    "header.contact_single_row": "Contact info must be on one tab-separated row",
    "header.contact_spacing_hack": "Header looks aligned but is built with manual spacing",
    "section.corsair_structure_detected": "Corsair section structure not detected",
    "section.required_presence": "Required section missing",
    "section.order": "Sections out of order",
    "section.label_spelling": "Section heading has a typo",
    "section.labels_all_caps": "Section label must be all caps",
    "section.headers_bold": "Section header must be bold",
    "section.divider_rule": "Section header missing bottom border rule",
    "section.reverse_chronological_order": "Entry is out of chronological order",
    "entry.date_right_tab": "Date looks aligned but is fragile to edit",
    "entry.date_range_en_dash": "Date range uses the wrong dash",
    "entry.date_range_valid": "Date range does not make sense",
    "entry.organization_bold": "Organization name must be bold",
    "entry.role_italic": "Role/title must be italicized",
    "entry.location_present": "Entry line missing City, ST location",
    "entry.date_alignment_spacing_hack": "Date alignment is being faked with spaces",
    "paragraph.no_consecutive_blank_lines": "Consecutive blank lines",
    "paragraph.no_leading_spaces": "Leading spaces used instead of indent",
    "paragraph.no_manual_alignment_spaces": "Text is lined up with the spacebar",
    "paragraph.tab_space_alignment_hacks": "Text looks aligned but uses tabs mixed with spaces",
    "paragraph.excessive_alignment_tabs": "Text is pushed into place with repeated tabs",
    "paragraph.tabs_require_defined_stops": "Tab was used without a saved tab stop",
    "paragraph.right_tab_consistency": "Right tab stop position inconsistent",
    "paragraph.body_alignment_consistency": "Bullet alignment inconsistent",
    "bullet.indent_consistency": "First-level bullet indent is off",
    "typography.single_font_family": "Multiple font families detected",
    "typography.body_font_size_consistency": "Body font size inconsistent",
    "typography.no_unauthorized_inline_emphasis": "Unauthorized bold/italic in bullet",
}

FIX_GUIDANCE: dict[str, str] = {
    "document.margin_range": "Set all page margins to between 0.5in and 1.0in.",
    "layout.no_tables": "Remove layout tables and rebuild content as normal paragraphs.",
    "layout.no_textboxes": "Move text box content into regular document paragraphs.",
    "header.name_centered_top_line": "Keep the name visually centered, but center it with Word's paragraph alignment or a saved center tab stop instead of manual spacing.",
    "header.dual_address": "Include exactly two city/state addresses in the header contact row.",
    "header.contact_single_row": "Keep the same visual layout, but use Word tab stops or paragraph alignment for the left, center, and right contact fields instead of lining things up by eye.",
    "header.contact_spacing_hack": "Delete the extra spaces between contact fields and use Word tab stops or paragraph alignment to keep the same visual layout.",
    "section.corsair_structure_detected": "Restore canonical Corsair section headers.",
    "section.required_presence": "Add the missing required section.",
    "section.order": "Reorder sections to match the required Corsair sequence.",
    "section.label_spelling": "Fix the section heading text so it exactly matches the required heading.",
    "section.labels_all_caps": "Make the section label fully uppercase.",
    "section.headers_bold": "Apply bold formatting to this section header.",
    "section.divider_rule": "Add a bottom border rule directly beneath this section header.",
    "section.reverse_chronological_order": "Move this entry so dates run newest to oldest within this section. Ongoing Present entries should appear before completed entries.",
    "entry.date_right_tab": "Delete the spaces before the date and use a right-aligned tab stop so all dates snap to the same right edge.",
    "entry.date_range_en_dash": "Replace the dash between dates with an en dash: January 2026 – Present.",
    "entry.date_range_valid": "Correct the date range so the end date is valid and comes after the start date.",
    "entry.organization_bold": "Bold the organization or institution name at the start of the entry line.",
    "entry.role_italic": "Italicize the role, title, or program descriptor before the date tab.",
    "entry.location_present": "Add City, ST before the date on this entry line.",
    "entry.date_alignment_spacing_hack": "Delete the space padding before the date and use a right-aligned tab stop.",
    "paragraph.no_consecutive_blank_lines": "Remove the extra blank paragraph. Use paragraph spacing instead.",
    "paragraph.no_leading_spaces": "Delete the leading spaces. Use paragraph indent settings instead.",
    "paragraph.no_manual_alignment_spaces": "Delete the repeated spaces. If the text needs to align, use Word's tab stops, paragraph alignment, or indentation instead.",
    "paragraph.tab_space_alignment_hacks": "Delete the spaces around the tabs. Use one tab with a saved tab stop so the line stays aligned after edits.",
    "paragraph.excessive_alignment_tabs": "Replace the repeated tab presses with one tab and a saved tab stop.",
    "paragraph.tabs_require_defined_stops": "If this tab is meant to align text, add a tab stop in Word's ruler or paragraph settings. Otherwise Word may shift the text unpredictably.",
    "paragraph.right_tab_consistency": "Use the same right tab stop position on all date-aligned lines.",
    "paragraph.body_alignment_consistency": "Set all bullet paragraphs to the same alignment.",
    "bullet.indent_consistency": "Set first-level bullets to a 0.25in bullet position with text starting at 0.5in.",
    "typography.single_font_family": "Select all text and apply one font family throughout.",
    "typography.body_font_size_consistency": "Normalize all body text to one size between 10pt and 12pt.",
    "typography.no_unauthorized_inline_emphasis": "Remove bold or italic from this bullet unless the visual layout intentionally calls for it.",
}

COMMENT_EXPLANATIONS: dict[str, str] = {
    "header.name_centered_top_line": (
        "It may look centered now, but it can shift when header text or margins change."
    ),
    "header.contact_single_row": (
        "The contact line may look close visually, but the fields can drift when phone, email, or location text changes."
    ),
    "header.contact_spacing_hack": (
        "The header may look aligned now, but extra spaces can break when you edit phone, email, or location text."
    ),
    "section.label_spelling": (
        "The section is present, but the heading text does not exactly match the required wording."
    ),
    "paragraph.no_manual_alignment_spaces": (
        "This line is using repeated spaces to position text, which can break when the line changes."
    ),
    "paragraph.tab_space_alignment_hacks": (
        "This line mixes tabs with extra spaces to make text appear aligned."
    ),
    "paragraph.excessive_alignment_tabs": (
        "This line uses repeated tab presses to push text into place."
    ),
    "paragraph.tabs_require_defined_stops": (
        "This line uses a tab, but Word has not been told exactly where that tab should land."
    ),
    "entry.date_right_tab": (
        "The date may look aligned now, but it is not attached to a stable right edge."
    ),
    "entry.date_range_en_dash": (
        "Date ranges should use the longer en dash character, not a regular keyboard hyphen."
    ),
    "entry.date_range_valid": (
        "The date range is either backwards or uses an invalid end date."
    ),
    "entry.date_alignment_spacing_hack": (
        "The date is being pushed into position with spaces or mixed tab spacing."
    ),
    "bullet.indent_consistency": (
        "The bullet dot or the text after it is not using the expected first-level bullet indent."
    ),
    "section.reverse_chronological_order": (
        "This entry appears below an older entry even though its date should place it higher in the same section."
    ),
}


def _first_evidence_paragraph(violation: dict[str, Any]) -> dict[str, Any]:
    evidence = violation.get("evidence") or {}
    paragraph = evidence.get("paragraph")
    if isinstance(paragraph, dict):
        return paragraph
    paragraphs = evidence.get("paragraphs")
    if isinstance(paragraphs, list):
        for item in paragraphs:
            if isinstance(item, dict):
                return item
    return {}


def _format_inches(value: Any) -> str | None:
    if isinstance(value, (int, float)):
        return f"{value:.2f}in"
    return None


def _evidence_detail(violation: dict[str, Any]) -> str:
    rule_id = str(violation.get("rule_id") or "")
    evidence = violation.get("evidence") or {}
    paragraph = _first_evidence_paragraph(violation)

    if rule_id == "bullet.indent_consistency":
        expected = evidence.get("expected") if isinstance(evidence.get("expected"), dict) else {}
        found_bullet = _format_inches(paragraph.get("bullet_position_inches"))
        found_text = _format_inches(paragraph.get("text_indent_inches"))
        expected_bullet = _format_inches(expected.get("bullet_position_inches"))
        expected_text = _format_inches(expected.get("text_indent_inches"))
        details = []
        if found_bullet and expected_bullet:
            details.append(f"bullet position is {found_bullet}, expected {expected_bullet}")
        if found_text and expected_text:
            details.append(f"text starts at {found_text}, expected {expected_text}")
        if details:
            return "Found: " + "; ".join(details) + "."

    if rule_id in {
        "paragraph.tab_space_alignment_hacks",
        "entry.date_alignment_spacing_hack",
        "header.contact_spacing_hack",
    }:
        tab_count = paragraph.get("tab_count")
        max_spaces = paragraph.get("max_consecutive_spaces")
        space_runs = paragraph.get("space_run_count")
        pieces = []
        if isinstance(tab_count, int):
            pieces.append(f"{tab_count} tab{'s' if tab_count != 1 else ''}")
        if isinstance(space_runs, int) and isinstance(max_spaces, int) and max_spaces > 1:
            pieces.append(
                f"{space_runs} repeated-space run{'s' if space_runs != 1 else ''}, longest is {max_spaces} spaces"
            )
        if pieces:
            return "Found: " + " plus ".join(pieces) + "."

    if rule_id == "paragraph.no_manual_alignment_spaces":
        max_spaces = paragraph.get("max_consecutive_spaces")
        space_runs = paragraph.get("space_run_count")
        if isinstance(space_runs, int) and isinstance(max_spaces, int) and max_spaces > 1:
            return f"Found: {space_runs} repeated-space run{'s' if space_runs != 1 else ''}; longest is {max_spaces} spaces."

    if rule_id in {"paragraph.tabs_require_defined_stops", "paragraph.excessive_alignment_tabs"}:
        tab_count = paragraph.get("tab_count")
        tab_stop_count = paragraph.get("tab_stop_count")
        if isinstance(tab_count, int) and isinstance(tab_stop_count, int):
            return f"Found: {tab_count} tab{'s' if tab_count != 1 else ''}, but {tab_stop_count} saved tab stop{'s' if tab_stop_count != 1 else ''}."

    if rule_id in {"entry.date_right_tab", "paragraph.right_tab_consistency"}:
        expected = evidence.get("expected_position_twips")
        tab_stops = evidence.get("tab_stops")
        if expected is not None:
            expected_inches = f"{int(expected) / 1440:.2f}in"
            if isinstance(tab_stops, list):
                positions = [
                    f"{int(tab.get('pos')) / 1440:.2f}in"
                    for tab in tab_stops
                    if isinstance(tab, dict) and str(tab.get("pos", "")).lstrip("-").isdigit()
                ]
                if positions:
                    return f"Found tab stop at {', '.join(positions)}; expected right tab at {expected_inches}."
            return f"Expected right tab at {expected_inches}."

    if rule_id == "entry.date_range_valid":
        date_text = paragraph.get("date_text")
        section = paragraph.get("section")
        if isinstance(date_text, str) and date_text.endswith("Presents"):
            return f"Found: {date_text}. Expected: {date_text[:-1]}."
        if date_text and section:
            return f"Found: {date_text} in {section}."
        if date_text:
            return f"Found: {date_text}."

    if rule_id == "section.label_spelling":
        found = paragraph.get("found")
        expected = paragraph.get("expected")
        if found and expected:
            return f"Found: {found}. Expected: {expected}."

    if rule_id == "section.reverse_chronological_order":
        date_text = paragraph.get("date_text")
        previous = paragraph.get("previous_date_text")
        section = paragraph.get("section")
        if date_text and previous and section:
            return f"Found: {date_text} appears after {previous} in {section}."
        if date_text and section:
            return f"Found: {date_text} is out of order in {section}."

    return ""


def _combine_explanation_and_detail(rule_id: str, explanation: str, detail: str) -> str:
    if not detail:
        return explanation
    if rule_id in {"entry.date_range_valid", "section.label_spelling", "section.reverse_chronological_order"}:
        return f"{explanation} {detail}"
    clean_detail = detail
    if clean_detail.startswith("Found: "):
        clean_detail = clean_detail[len("Found: "):]
    clean_detail = clean_detail[:1].lower() + clean_detail[1:]
    return f"{explanation} It used {clean_detail}"


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
    label = RULE_LABELS.get(rule_id, rule_id)
    explanation = COMMENT_EXPLANATIONS.get(rule_id, str(violation.get("message") or "Formatting issue detected."))
    guidance = FIX_GUIDANCE.get(rule_id, "Review and correct this formatting issue.")
    detail = _evidence_detail(violation)
    return [
        label,
        "",
        _combine_explanation_and_detail(rule_id, explanation, detail),
        "",
        "Fix:",
        guidance,
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


def _text_element(value: str) -> ET.Element:
    text = ET.Element(_w("t"))
    text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text.text = value
    return text


def _run_text(run: ET.Element) -> str:
    parts: list[str] = []
    for child in run:
        if child.tag == _w("t"):
            parts.append(child.text or "")
        elif child.tag == _w("tab"):
            parts.append("\t")
    return "".join(parts)


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join(_run_text(run) for run in paragraph.findall(_w("r")))


def _clone_run_with_text(run: ET.Element, value: str) -> ET.Element:
    clone = ET.Element(_w("r"))
    rpr = run.find(_w("rPr"))
    if rpr is not None:
        clone.append(copy.deepcopy(rpr))

    buffer: list[str] = []
    for char in value:
        if char == "\t":
            if buffer:
                clone.append(_text_element("".join(buffer)))
                buffer = []
            clone.append(ET.Element(_w("tab")))
        else:
            buffer.append(char)
    if buffer:
        clone.append(_text_element("".join(buffer)))
    return clone


def _merge_ranges(ranges: list[dict[str, Any]], text_length: int) -> list[tuple[int, int]]:
    normalized: list[tuple[int, int]] = []
    for item in ranges:
        start = item.get("start")
        end = item.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        start = max(0, min(start, text_length))
        end = max(0, min(end, text_length))
        if start < end:
            normalized.append((start, end))

    merged: list[tuple[int, int]] = []
    for start, end in sorted(normalized):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
    return merged


def _fallback_target_ranges(rule_id: str, text: str) -> list[dict[str, int]]:
    if not text:
        return []

    if rule_id == "paragraph.no_leading_spaces":
        leading = len(text) - len(text.lstrip(" "))
        return [{"start": 0, "end": leading}] if leading else []

    if rule_id in {
        "paragraph.no_manual_alignment_spaces",
        "paragraph.tab_space_alignment_hacks",
        "paragraph.excessive_alignment_tabs",
        "paragraph.tabs_require_defined_stops",
        "header.contact_spacing_hack",
        "header.contact_single_row",
    }:
        ranges = [
            {"start": match.start(), "end": match.end()}
            for match in re.finditer(r"(?: {2,}|\t+)", text)
        ]
        return ranges[:6]

    if rule_id in {
        "entry.date_right_tab",
        "entry.date_alignment_spacing_hack",
        "entry.date_range_valid",
        "section.reverse_chronological_order",
    }:
        match = DATE_PATTERN.search(text)
        if match:
            return [{"start": match.start(), "end": match.end()}]
        tab_index = text.find("\t")
        if tab_index >= 0:
            return [{"start": tab_index, "end": min(len(text), tab_index + 1)}]

    if rule_id == "entry.organization_bold":
        end = text.find(",")
        if end > 0:
            return [{"start": 0, "end": end}]

    if rule_id == "bullet.indent_consistency":
        match = re.search(r"\S", text)
        if match:
            return [{"start": match.start(), "end": min(len(text), match.start() + 1)}]

    return []


def _target_ranges_for_violation(violation: dict[str, Any], paragraph_index: int, text: str) -> list[tuple[int, int]]:
    evidence = violation.get("evidence") or {}
    collected: list[dict[str, Any]] = []
    paragraphs = evidence.get("paragraphs")
    if isinstance(paragraphs, list):
        for paragraph in paragraphs:
            if not isinstance(paragraph, dict) or paragraph.get("index") != paragraph_index:
                continue
            ranges = paragraph.get("target_ranges")
            if isinstance(ranges, list):
                collected.extend(item for item in ranges if isinstance(item, dict))

    paragraph = evidence.get("paragraph")
    if isinstance(paragraph, dict) and paragraph.get("index") == paragraph_index:
        ranges = paragraph.get("target_ranges")
        if isinstance(ranges, list):
            collected.extend(item for item in ranges if isinstance(item, dict))

    if not collected:
        rule_id = str(violation.get("rule_id") or "")
        collected = _fallback_target_ranges(rule_id, text)

    # One Word comment range should have one start/end pair. For grouped
    # spacing issues, anchor the bubble to the first concrete problem spot
    # rather than marking the whole paragraph.
    return _merge_ranges(collected, len(text))[:1]


def _insert_comment_on_ranges(paragraph: ET.Element, comment_id: int, ranges: list[tuple[int, int]]) -> bool:
    if not ranges:
        return False

    target_start, target_end = ranges[0]
    original_children = list(paragraph)
    new_children: list[ET.Element] = []
    cursor = 0
    opened = False
    closed = False

    for child in original_children:
        if child.tag != _w("r"):
            new_children.append(child)
            continue

        run_text = _run_text(child)
        if not run_text:
            new_children.append(child)
            continue

        run_start = cursor
        run_end = cursor + len(run_text)
        cursor = run_end

        if run_end <= target_start or run_start >= target_end:
            new_children.append(child)
            continue

        before_end = max(0, min(len(run_text), target_start - run_start))
        highlight_start = max(0, min(len(run_text), target_start - run_start))
        highlight_end = max(0, min(len(run_text), target_end - run_start))

        if before_end > 0:
            new_children.append(_clone_run_with_text(child, run_text[:before_end]))
        if highlight_start < highlight_end:
            if not opened:
                new_children.append(_comment_range_start(comment_id))
                opened = True
            new_children.append(_clone_run_with_text(child, run_text[highlight_start:highlight_end]))
            if target_end <= run_end and not closed:
                new_children.append(_comment_range_end(comment_id))
                closed = True
        if highlight_end < len(run_text):
            new_children.append(_clone_run_with_text(child, run_text[highlight_end:]))

    if opened and not closed:
        new_children.append(_comment_range_end(comment_id))
    if not opened:
        return False
    new_children.append(_comment_reference(comment_id))
    paragraph[:] = new_children
    return True


def _paragraph_indices(violation: dict[str, Any]) -> list[int]:
    evidence = violation.get("evidence") or {}
    indices: list[int] = []
    rule_id = str(violation.get("rule_id") or "")

    if evidence.get("grouped_comment") is True:
        paragraphs = evidence.get("paragraphs")
        if isinstance(paragraphs, list):
            for paragraph in paragraphs:
                if isinstance(paragraph, dict) and isinstance(paragraph.get("index"), int):
                    return [paragraph["index"]]
        paragraph = evidence.get("paragraph")
        if isinstance(paragraph, dict) and isinstance(paragraph.get("index"), int):
            return [paragraph["index"]]
        return [0]

    paragraphs = evidence.get("paragraphs")
    if isinstance(paragraphs, list):
        for paragraph in paragraphs:
            if isinstance(paragraph, dict) and isinstance(paragraph.get("index"), int):
                indices.append(paragraph["index"])

    paragraph = evidence.get("paragraph")
    if isinstance(paragraph, dict) and isinstance(paragraph.get("index"), int):
        indices.append(paragraph["index"])

    if not indices and rule_id in {
        "section.required_presence",
        "typography.single_font_family",
        "typography.body_font_size_consistency",
    }:
        return []

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
    body = document_root.find(".//" + _w("body"))
    if body is None:
        raise ValueError("word/document.xml has no <w:body> element.")
    body_paragraphs = body.findall(_w("p"))
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
            ranges = _target_ranges_for_violation(violation, paragraph_index, _paragraph_text(paragraph))
            if not _insert_comment_on_ranges(paragraph, comment_id, ranges):
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
