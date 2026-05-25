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
    "document.margin_range": "Page margins are off",
    "layout.no_tables": "This layout uses a table",
    "layout.no_textboxes": "This layout uses a text box",
    "header.name_centered_top_line": "Name looks centered but is fragile to edit",
    "header.dual_address": "Header needs exactly two city/state addresses",
    "header.address_line_integrity": "One header address looks wrong",
    "header.contact_single_row": "Contact line may shift when edited",
    "header.contact_spacing_hack": "Header is lined up with spaces",
    "section.corsair_structure_detected": "Resume sections could not be read clearly",
    "section.required_presence": "Required section missing",
    "section.order": "Sections out of order",
    "section.label_spelling": "Section heading has a typo",
    "section.labels_all_caps": "Section heading needs all caps",
    "section.headers_bold": "Section heading needs bold",
    "section.divider_rule": "Section heading needs an underline",
    "section.reverse_chronological_order": "Entry is out of chronological order",
    "entry.date_right_tab": "Date is not anchored to the right edge",
    "entry.date_range_en_dash": "Date range uses the wrong dash",
    "entry.date_range_valid": "Date range looks wrong",
    "entry.organization_bold": "Organization name needs bold",
    "entry.role_italic": "Role/title needs italics",
    "entry.separator_commas_plain": "Comma has extra styling",
    "entry.location_present": "Entry line missing City, ST location",
    "entry.date_alignment_spacing_hack": "Date is lined up with spaces",
    "paragraph.no_consecutive_blank_lines": "Consecutive blank lines",
    "paragraph.no_leading_spaces": "Line starts with typed spaces",
    "paragraph.no_manual_alignment_spaces": "Text is lined up with the spacebar",
    "paragraph.tab_space_alignment_hacks": "Text looks aligned but uses tabs mixed with spaces",
    "paragraph.excessive_alignment_tabs": "Text is pushed into place with repeated tabs",
    "paragraph.tabs_require_defined_stops": "Tab spacing is not locked in",
    "paragraph.right_tab_consistency": "Dates do not share the same right edge",
    "paragraph.body_alignment_consistency": "Numbered bullet is justified",
    "bullet.indent_consistency": "First-level bullet indent differs from template",
    "typography.single_font_family": "Multiple font families detected",
    "typography.body_font_size_consistency": "Body font size inconsistent",
    "typography.no_unauthorized_inline_emphasis": "Unauthorized bold/italic in bullet",
    "text.spelling_suspected": "Possible spelling issue",
}

FIX_GUIDANCE: dict[str, str] = {
    "document.margin_range": "In Word, set each page margin between 0.5in and 1.0in.",
    "layout.no_tables": "Move the resume text out of the table and into regular paragraphs.",
    "layout.no_textboxes": "Move this text out of the text box and into the normal page body.",
    "header.name_centered_top_line": "Use Word's Center Align button for the name instead of spacing it by hand.",
    "header.dual_address": "Include exactly two city/state addresses in the header contact row.",
    "header.address_line_integrity": "Separate the two locations cleanly so each address stays on its own side of the header.",
    "header.contact_single_row": "Put the contact info on one clean row and use Word alignment, not hand-spaced text.",
    "header.contact_spacing_hack": "Delete the extra spaces and use Word alignment or tabs so the header does not shift.",
    "section.corsair_structure_detected": "Use the clean Corsair template section headings, then rerun the audit.",
    "section.required_presence": "Add the missing required section.",
    "section.order": "Move the sections into the required Corsair order.",
    "section.label_spelling": "Rename the section heading to match the template exactly.",
    "section.labels_all_caps": "Make the whole section heading uppercase.",
    "section.headers_bold": "Select the section heading and turn on Bold.",
    "section.divider_rule": "Add the horizontal line under this section heading.",
    "section.reverse_chronological_order": "Move this entry so dates run newest to oldest within this section. Ongoing Present entries should appear before completed entries.",
    "entry.date_right_tab": "Delete the spacing before the date and use the template's right-aligned date position.",
    "entry.date_range_en_dash": "Replace the dash between dates with an en dash: January 2026 – Present.",
    "entry.date_range_valid": "Correct the date range so the end date is valid and comes after the start date.",
    "entry.organization_bold": "Select the organization or school name at the start of the line and turn on Bold.",
    "entry.role_italic": "Select the role, title, or program name and turn on Italics.",
    "entry.separator_commas_plain": "Select the comma and turn off Bold and Italics.",
    "entry.location_present": "Add the location in City, ST format before the date.",
    "entry.date_alignment_spacing_hack": "Delete the extra spaces before the date and use the template's right-aligned date position.",
    "paragraph.no_consecutive_blank_lines": "Remove the extra blank paragraph. Use paragraph spacing instead.",
    "paragraph.no_leading_spaces": "Delete the typed spaces at the start of the line. Use Word indentation instead.",
    "paragraph.no_manual_alignment_spaces": "Delete the repeated spaces and use Word alignment, tabs, or indentation instead.",
    "paragraph.tab_space_alignment_hacks": "Delete the extra spaces around the tab so the line does not shift later.",
    "paragraph.excessive_alignment_tabs": "Replace the repeated tab presses with the template's normal spacing.",
    "paragraph.tabs_require_defined_stops": "Use the template's saved tab position, or the spacing may move when edited.",
    "paragraph.right_tab_consistency": "Make this date use the same right edge as the other dates.",
    "paragraph.body_alignment_consistency": "Click that bullet paragraph and choose Left Align instead of Justify.",
    "bullet.indent_consistency": "Set first-level bullets to a 0.25in bullet position with text starting at 0.5in.",
    "typography.single_font_family": "Select all text and apply one font throughout.",
    "typography.body_font_size_consistency": "Make the body text one consistent size between 10pt and 12pt.",
    "typography.no_unauthorized_inline_emphasis": "Remove bold or italic from this bullet unless the visual layout intentionally calls for it.",
    "text.spelling_suspected": "Review this word manually before changing it. Names, companies, and industry terms may be intentional.",
}

COMMENT_EXPLANATIONS: dict[str, str] = {
    "annotation.focused_summary": (
        "This copy only marks the most useful examples so the resume does not get flooded with comments."
    ),
    "document.margin_range": "The page margins are outside the template range, so the resume may not fit or line up correctly.",
    "layout.no_tables": "This resume uses a table to place content. Tables can make the resume hard to edit cleanly.",
    "layout.no_textboxes": "This text is inside a floating text box. Text boxes can move around or hide content when edited.",
    "header.name_centered_top_line": (
        "The name may look centered now, but it can move when the header or margins change."
    ),
    "header.dual_address": "The header should show two clean city/state locations.",
    "header.contact_single_row": (
        "The contact line may look fine now, but the pieces can drift when the phone, email, or location changes."
    ),
    "header.address_line_integrity": (
        "One location in the header has extra characters, wraps oddly, or is attached to the wrong side."
    ),
    "header.contact_spacing_hack": (
        "The header is lined up with typed spaces. It can shift when someone edits the contact info."
    ),
    "section.corsair_structure_detected": "The checker cannot clearly read the required resume sections.",
    "section.required_presence": "A required section is missing from the resume.",
    "section.order": "The sections are in a different order than the template expects.",
    "section.label_spelling": (
        "The section is there, but the heading text does not match the template exactly."
    ),
    "section.labels_all_caps": "This section heading should be written in all capital letters.",
    "section.headers_bold": "This section heading should be bold like the others.",
    "section.divider_rule": "This section heading should have the horizontal line underneath it.",
    "paragraph.no_manual_alignment_spaces": (
        "This line is lined up with repeated spaces. It can move around when the text changes."
    ),
    "paragraph.no_leading_spaces": "This line starts with typed spaces instead of Word indentation.",
    "paragraph.tab_space_alignment_hacks": (
        "This line mixes a tab with extra spaces. It may look okay now, but it can shift later."
    ),
    "paragraph.excessive_alignment_tabs": (
        "This line uses several tab presses to push text into place."
    ),
    "paragraph.tabs_require_defined_stops": (
        "This line uses a tab, but Word has not been told exactly where that tab should land."
    ),
    "paragraph.right_tab_consistency": "This date does not land on the same right edge as the other dates.",
    "entry.date_right_tab": (
        "The date may look aligned now, but it is not locked to the same right edge as the other dates."
    ),
    "entry.date_range_en_dash": (
        "Date ranges should use the longer dash, not the short keyboard hyphen."
    ),
    "entry.date_range_valid": (
        "The date range is backwards or has an end date that does not make sense."
    ),
    "entry.date_alignment_spacing_hack": (
        "The date is pushed into place with spaces instead of the template's date alignment."
    ),
    "entry.organization_bold": "The organization or school name should stand out in bold.",
    "entry.role_italic": "The role, title, or program name should be italicized.",
    "entry.separator_commas_plain": "The comma should stay plain. It should not inherit bold or italics from nearby words.",
    "entry.location_present": "This entry needs a City, ST location before the date.",
    "bullet.indent_consistency": "The bullet dot or the text after it starts at a different ruler position than the template.",
    "paragraph.body_alignment_consistency": "This bullet is set to Justify, so Word stretches the text across the line like a newspaper column. The other bullets are normal left-aligned text.",
    "section.reverse_chronological_order": (
        "This entry is below an older entry, but newer items should come first in the same section."
    ),
    "typography.single_font_family": "More than one font is used in the resume.",
    "typography.body_font_size_consistency": "The body text uses more than one font size.",
    "typography.no_unauthorized_inline_emphasis": "This bullet has bold or italic text where the template usually expects plain text.",
    "text.spelling_suspected": "This word may be misspelled. Check it manually before changing names, company terms, or abbreviations.",
}


MAX_DOCX_COMMENTS = 15
FOCUSED_SUMMARY_RULE_ID = "annotation.focused_summary"


def count_docx_comments(path: str | Path) -> int:
    path = Path(path).resolve()
    with ZipFile(path, "r") as archive:
        try:
            comments_xml = archive.read("word/comments.xml")
        except KeyError:
            return 0
    root = ET.fromstring(comments_xml)
    return sum(1 for element in root.iter() if element.tag.split("}")[-1] == "comment")


def _strip_existing_comment_markup(element: ET.Element) -> None:
    for child in list(element):
        if child.tag in {_w("commentRangeStart"), _w("commentRangeEnd")}:
            element.remove(child)
            continue

        _strip_existing_comment_markup(child)

        if child.tag == _w("r"):
            for grandchild in list(child):
                if grandchild.tag == _w("commentReference"):
                    child.remove(grandchild)
            meaningful_children = [grandchild for grandchild in list(child) if grandchild.tag != _w("rPr")]
            if not meaningful_children:
                element.remove(child)


def _rule_comment_cap(violation: dict[str, Any]) -> int:
    category = violation.get("category")
    rule_id = str(violation.get("rule_id") or "")
    if category == "structural":
        return 1
    if rule_id.startswith(("section.", "header.", "layout.", "document.")):
        return 1
    if category == "visual":
        return 3
    return 2


def _comment_priority(violation: dict[str, Any]) -> int:
    severity = violation.get("severity")
    category = violation.get("category")
    if severity == "critical":
        return 0
    if category == "visual":
        return 1
    if severity == "major":
        return 2
    if category == "structural":
        return 3
    return 4


def _focused_summary_violation(
    *,
    total_count: int,
    shown_issue_count: int,
    suppressed_count: int,
    suppressed_by_rule: dict[str, int],
) -> dict[str, Any]:
    return {
        "rule_id": FOCUSED_SUMMARY_RULE_ID,
        "severity": "minor",
        "points": 0,
        "category": "annotation",
        "message": (
            f"Focused annotation shows {shown_issue_count} representative comments. "
            f"{suppressed_count} repeated or lower-priority issues remain in the dashboard."
        ),
        "evidence": {
            "grouped_comment": True,
            "paragraph": {"index": 0},
            "total_count": total_count,
            "shown_issue_count": shown_issue_count,
            "suppressed_count": suppressed_count,
            "suppressed_by_rule": suppressed_by_rule,
        },
}


def _focused_comment_violation(violation: dict[str, Any]) -> dict[str, Any]:
    focused = copy.deepcopy(violation)
    evidence = focused.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
        focused["evidence"] = evidence
    evidence["focused_comment"] = True
    return focused


def curate_docx_comment_violations(
    violations: list[dict[str, Any]],
    *,
    max_comments: int = MAX_DOCX_COMMENTS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select a focused, non-overwhelming set of Word comments.

    The analyzer still returns every violation to the dashboard. This only limits
    the Word-native comments embedded in the annotated DOCX.
    """
    if max_comments < 1:
        max_comments = 1
    if not violations:
        return [], {
            "mode": "focused",
            "total_issues": 0,
            "comment_count": 0,
            "shown_issue_count": 0,
            "suppressed_count": 0,
            "max_comments": max_comments,
            "suppressed_by_rule": {},
        }

    budget = max_comments - 1 if max_comments > 1 else 1
    selected: list[dict[str, Any]] = []
    selected_by_rule: dict[str, int] = {}
    suppressed_by_rule: dict[str, int] = {}

    ordered_violations = [
        violation
        for _, violation in sorted(
            enumerate(violations),
            key=lambda item: (_comment_priority(item[1]), item[0]),
        )
    ]

    for violation in ordered_violations:
        rule_id = str(violation.get("rule_id") or "formatting.issue")
        cap = _rule_comment_cap(violation)
        if selected_by_rule.get(rule_id, 0) >= cap or len(selected) >= budget:
            suppressed_by_rule[rule_id] = suppressed_by_rule.get(rule_id, 0) + 1
            continue
        selected.append(_focused_comment_violation(violation))
        selected_by_rule[rule_id] = selected_by_rule.get(rule_id, 0) + 1

    suppressed_count = len(violations) - len(selected)
    curated = selected
    if suppressed_count > 0:
        summary = _focused_summary_violation(
            total_count=len(violations),
            shown_issue_count=len(selected),
            suppressed_count=suppressed_count,
            suppressed_by_rule=suppressed_by_rule,
        )
        curated = [summary, *selected]

    return curated, {
        "mode": "focused",
        "total_issues": len(violations),
        "comment_count": len(curated),
        "shown_issue_count": len(selected),
        "suppressed_count": suppressed_count,
        "max_comments": max_comments,
        "suppressed_by_rule": suppressed_by_rule,
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

    if rule_id == "paragraph.body_alignment_consistency":
        found = paragraph.get("alignment") or evidence.get("found_alignment")
        expected = paragraph.get("expected_alignment") or evidence.get("expected_alignment")
        if found and expected:
            found_label = "Justify" if found == "both" else str(found).title()
            expected_label = str(expected).title()
            return f"Found: paragraph alignment is {found_label}. Expected: {expected_label}."

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

    if rule_id == "header.address_line_integrity":
        address_issues = evidence.get("address_issues")
        if isinstance(address_issues, list) and address_issues:
            first_issue = address_issues[0]
            if isinstance(first_issue, dict):
                found = first_issue.get("found")
                expected = first_issue.get("expected")
                if found and expected:
                    return f"Found: {found}. Expected: {expected}."

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

    if rule_id == "text.spelling_suspected":
        word = paragraph.get("word")
        suggestion = paragraph.get("suggestion")
        if word and suggestion:
            return f"Found: {word}. Possible: {suggestion}."

    return ""


def _combine_explanation_and_detail(rule_id: str, explanation: str, detail: str) -> str:
    if not detail:
        return explanation
    if rule_id in {
        "bullet.indent_consistency",
        "entry.date_range_valid",
        "paragraph.body_alignment_consistency",
        "section.label_spelling",
        "section.reverse_chronological_order",
        "text.spelling_suspected",
    }:
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
    if rule_id == FOCUSED_SUMMARY_RULE_ID:
        evidence = violation.get("evidence") or {}
        shown = evidence.get("shown_issue_count")
        suppressed = evidence.get("suppressed_count")
        if not isinstance(shown, int):
            shown = 0
        if not isinstance(suppressed, int):
            suppressed = 0
        return [
            "Focused annotation mode",
            "",
            f"This DOCX shows {shown} representative comments and leaves {suppressed} repeated or lower-priority issues summarized in the web dashboard.",
            "",
            "Recommendation:",
            "Use the full issue list on the site for diagnosis. If the structure feels noisy, start from the clean Corsair template and transfer content into it.",
        ]

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


def estimate_docx_comment_count(violations: list[dict[str, Any]]) -> int:
    return sum(len(_paragraph_indices(violation)) for violation in violations)


def _build_paragraph_comment_map(violations: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    mapping: dict[int, list[dict[str, Any]]] = {}
    for violation in violations:
        indices = _paragraph_indices(violation)
        evidence = violation.get("evidence") or {}
        if isinstance(evidence, dict) and evidence.get("focused_comment") is True:
            indices = indices[:1]
        for index in indices:
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

    _strip_existing_comment_markup(document_root)
    comments_root = _ensure_comments_root(None)
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
