from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from .docx_parser import DocumentModel, ParagraphModel, parse_docx
from .render_validation import get_render_validation_status, validate_rendered_page_count
from .rubric import load_rubric


SECTION_PATTERN = re.compile(r"^[A-Z][A-Z &/]{3,}$")
CITY_STATE_PATTERN = re.compile(r"\b[A-Z][A-Za-z .'-]+,?\s+[A-Z]{2}(?:\s+\d{5})?\b")
HEADER_CITY_STATE_PATTERN = re.compile(
    r"[A-Z][A-Za-z .'-]+,?\s+[A-Z]{2}(?:\s+\d{5})?"
)
DATE_PATTERN = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}"
    r"(?:\s*[-–]\s*(?:Present|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{4}))?\b"
)
DATE_RANGE_WITH_WRONG_DASH_PATTERN = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}"
    r"\s*(?:-|—)\s*"
    r"(?:Present|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{4})\b"
)
MONTH_NAMES = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
MONTH_YEAR_PATTERN = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\b"
)
DATE_RANGE_PARTS_PATTERN = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})"
    r"\s*[-–—]\s*"
    r"(Present|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b"
)
DATE_RANGE_START_PATTERN = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})"
    r"\s*[-–—]\s*([A-Za-z0-9 ]+)"
)
TWIPS_PER_INCH = 1440
TWIPS_PER_POINT = 20
TWIP_TOLERANCE = 20
VISUAL_SCORE_WEIGHT = 0.65
STRUCTURAL_SCORE_WEIGHT = 0.35


def _make_violation(
    rule_id: str,
    severity: str,
    points: int,
    message: str,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "points": points,
        "category": "visual",
        "message": message,
        "evidence": evidence or {},
    }


def _rule_lookup(rubric: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {rule["id"]: rule for rule in rubric.get("rules", []) if "id" in rule}


def _apply_rubric_to_violations(
    violations: List[Dict[str, Any]],
    rules_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for violation in violations:
        rule = rules_by_id.get(violation["rule_id"], {})
        item = dict(violation)
        item["severity"] = rule.get("severity", item.get("severity", "minor"))
        item["points"] = int(rule.get("points", item.get("points", 0)))
        item["category"] = rule.get("category", item.get("category", "visual"))
        item["fixable"] = rule.get("fixable", item.get("fixable", False))
        normalized.append(item)
    return normalized


def _detect_sections(document: DocumentModel, allowed_sections: set[str]) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if text in allowed_sections and SECTION_PATTERN.fullmatch(text):
            sections.append({"name": text, "paragraph_index": para.index})
    return sections


def _suspected_section_heading_typos(
    document: DocumentModel,
    missing_sections: List[str],
    detected_sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    detected_indices = {section["paragraph_index"] for section in detected_sections}
    candidates: List[Dict[str, Any]] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if paragraph.index in detected_indices or not SECTION_PATTERN.fullmatch(text):
            continue
        for missing in missing_sections:
            similarity = SequenceMatcher(None, text, missing).ratio()
            if similarity >= 0.78 or missing in text or text in missing:
                candidates.append({"paragraph": paragraph, "expected": missing, "found": text})
                break
    return candidates


def _paragraph_summary(
    paragraph: ParagraphModel,
    target_ranges: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    space_runs = [len(match.group(0)) for match in re.finditer(r" {2,}", paragraph.text)]
    summary = {
        "index": paragraph.index,
        "text": paragraph.text[:160].replace("\t", "\\t"),
        "alignment": paragraph.alignment,
        "style_name": paragraph.style_name,
        "tab_count": paragraph.tab_count,
        "tab_stop_count": len(paragraph.tab_stops),
        "space_run_count": len(space_runs),
        "max_consecutive_spaces": max(space_runs, default=0),
        "has_raw_repeated_spaces": paragraph.raw_repeated_spaces,
        "has_tab_space_padding": paragraph.tab_space_padding,
        "numbering_level": paragraph.numbering_level,
        "left_indent_pt": paragraph.left_indent_pt,
        "hanging_indent_pt": paragraph.hanging_indent_pt,
    }
    if target_ranges:
        summary["target_ranges"] = target_ranges
    left = _int_twips(paragraph.indent.get("left"))
    hanging = _int_twips(paragraph.indent.get("hanging"))
    if left is not None and hanging is not None:
        summary["bullet_position_inches"] = round((left - hanging) / TWIPS_PER_INCH, 3)
        summary["text_indent_inches"] = round(left / TWIPS_PER_INCH, 3)
    return summary


def _unique_paragraphs(paragraphs: List[ParagraphModel]) -> List[ParagraphModel]:
    seen: set[int] = set()
    unique: List[ParagraphModel] = []
    for paragraph in paragraphs:
        if paragraph.index in seen:
            continue
        seen.add(paragraph.index)
        unique.append(paragraph)
    return unique


def _header_indices(document: DocumentModel, detected_sections: List[Dict[str, Any]]) -> set[int]:
    first_section_index = min(
        (section["paragraph_index"] for section in detected_sections),
        default=min((paragraph.index for paragraph in document.paragraphs), default=0),
    )
    return {
        paragraph.index
        for paragraph in document.paragraphs
        if paragraph.index < first_section_index and not paragraph.is_blank
    }


def _contact_paragraph(document: DocumentModel, header_indices: set[int]) -> Optional[ParagraphModel]:
    header_paragraphs = [paragraph for paragraph in document.paragraphs if paragraph.index in header_indices]
    with_email = [paragraph for paragraph in header_paragraphs if "@" in paragraph.text]
    candidates = with_email or header_paragraphs
    if not candidates:
        return None
    return max(candidates, key=lambda paragraph: (len(_header_city_state_matches(paragraph.text)), paragraph.tab_count))


def _header_city_state_matches(text: str) -> List[str]:
    matches: List[str] = []
    for match in HEADER_CITY_STATE_PATTERN.finditer(text):
        value = match.group(0).strip()
        prefix = re.search(r"([A-Z][A-Za-z .'-]+,\s+[A-Z]{2}(?:\s+\d{5})?)$", value)
        if prefix:
            value = prefix.group(1)
        matches.append(value)
    return matches


def _header_address_paragraphs(document: DocumentModel, header_indices: set[int]) -> List[ParagraphModel]:
    return [
        paragraph
        for paragraph in document.paragraphs
        if paragraph.index in header_indices and _header_city_state_matches(paragraph.text)
    ]


def _looks_like_manual_layout(paragraph: ParagraphModel) -> bool:
    if paragraph.is_blank:
        return False
    if paragraph.leading_spaces >= 2 or paragraph.tab_space_padding:
        return True
    if paragraph.raw_repeated_spaces and (paragraph.has_tabs or paragraph.index <= 4 or DATE_PATTERN.search(paragraph.text)):
        return True
    if paragraph.tab_count >= 3 and len(paragraph.tab_stops) == 0:
        return True
    return False


def _expected_right_tab_position(document: DocumentModel) -> Optional[int]:
    page_width = document.page_size_twips.get("w")
    left_margin = document.page_margins_twips.get("left")
    right_margin = document.page_margins_twips.get("right")
    if page_width is None or left_margin is None or right_margin is None:
        return None
    return page_width - left_margin - right_margin


def _int_twips(value: Optional[str]) -> Optional[int]:
    if value is None or not str(value).lstrip("-").isdigit():
        return None
    return int(value)


def _close_twips(actual: Optional[int], expected: int, tolerance: int = TWIP_TOLERANCE) -> bool:
    return actual is not None and abs(actual - expected) <= tolerance


def _right_tab_positions(paragraph: ParagraphModel) -> set[int]:
    positions = set()
    for tab in paragraph.tab_stops:
        pos = tab.get("pos")
        if tab.get("val") == "right" and pos and pos.lstrip("-").isdigit():
            positions.add(int(pos))
    return positions


def _has_expected_right_tab(paragraph: ParagraphModel, expected_position: Optional[int], tolerance: int = 72) -> bool:
    positions = _right_tab_positions(paragraph)
    if not positions:
        return False
    if expected_position is None:
        return True
    return any(abs(position - expected_position) <= tolerance for position in positions)


def _has_center_tab(paragraph: ParagraphModel) -> bool:
    return any(tab.get("val") == "center" for tab in paragraph.tab_stops)


def _is_stably_centered_name(paragraph: ParagraphModel) -> bool:
    if paragraph.leading_spaces or paragraph.raw_repeated_spaces or paragraph.tab_space_padding:
        return False
    if paragraph.alignment == "center" and paragraph.tab_count == 0:
        return True
    return _has_center_tab(paragraph) and paragraph.tab_count == 1


def _all_visible_runs_bold(paragraph: ParagraphModel) -> bool:
    visible = paragraph.visible_runs
    return bool(visible) and all(run.bold for run in visible)


def _first_visible_run_bold(paragraph: ParagraphModel) -> bool:
    visible = paragraph.visible_runs
    return bool(visible) and visible[0].bold


def _expects_italic_role(paragraph: ParagraphModel) -> bool:
    before_date = paragraph.text.split("\t", 1)[0]
    # Canonical entry lines with an organization + role + location still have
    # one comma break after removing the trailing City, ST location. Education
    # or high-school lines can be just institution + location and should not be
    # punished as if they were job entries.
    without_location = CITY_STATE_PATTERN.sub("", before_date).rstrip(" ,")
    return without_location.count(",") >= 1


def _role_text_span(paragraph: ParagraphModel) -> Optional[tuple[int, int]]:
    before_date = paragraph.text.split("\t", 1)[0]
    first_comma = before_date.find(",")
    if first_comma < 0:
        return None

    start = first_comma + 1
    while start < len(before_date) and before_date[start] == " ":
        start += 1

    locations = list(CITY_STATE_PATTERN.finditer(before_date))
    end = locations[-1].start() if locations else len(before_date)
    while end > start and before_date[end - 1] in {" ", ","}:
        end -= 1

    if start >= end:
        return None
    return start, end


def _role_italic_target_ranges(paragraph: ParagraphModel) -> List[Dict[str, Any]]:
    span = _role_text_span(paragraph)
    if span is None:
        return []

    role_start, role_end = span
    ranges: List[Dict[str, Any]] = []
    cursor = 0
    for run in paragraph.runs:
        run_start = cursor
        run_end = cursor + len(run.text)
        cursor = run_end
        if run_end <= role_start or run_start >= role_end or run.italic:
            continue

        start = max(run_start, role_start)
        end = min(run_end, role_end)
        while start < end and paragraph.text[start].isspace():
            start += 1
        while end > start and paragraph.text[end - 1].isspace():
            end -= 1
        if start < end:
            ranges.append({"start": start, "end": end, "text": paragraph.text[start:end]})

    return ranges


def _wrong_date_dash_target_ranges(paragraph: ParagraphModel) -> List[Dict[str, Any]]:
    ranges: List[Dict[str, Any]] = []
    for match in DATE_RANGE_WITH_WRONG_DASH_PATTERN.finditer(paragraph.text):
        matched_text = match.group(0)
        dash_offset = matched_text.find("-")
        if dash_offset < 0:
            dash_offset = matched_text.find("—")
        if dash_offset >= 0:
            start = match.start() + dash_offset
            ranges.append({"start": start, "end": start + 1, "text": paragraph.text[start:start + 1]})
    return ranges


def _date_target_ranges(paragraph: ParagraphModel) -> List[Dict[str, Any]]:
    ranges: List[Dict[str, Any]] = []
    for match in DATE_PATTERN.finditer(paragraph.text):
        ranges.append({"start": match.start(), "end": match.end(), "text": match.group(0)})
    return ranges


def _month_year_value(month: str, year: str) -> int:
    return int(year) * 12 + MONTH_NAMES[month.lower()]


def _parse_date_value(text: str) -> Optional[int]:
    match = MONTH_YEAR_PATTERN.fullmatch(text.strip())
    if not match:
        return None
    return _month_year_value(match.group(1), match.group(2))


def _date_info(paragraph: ParagraphModel) -> Optional[Dict[str, Any]]:
    range_match = DATE_RANGE_PARTS_PATTERN.search(paragraph.text)
    if range_match:
        start_value = _month_year_value(range_match.group(1), range_match.group(2))
        end_text = range_match.group(3)
        is_present = end_text.lower() == "present"
        end_value = None if is_present else _parse_date_value(end_text)
        return {
            "date_text": range_match.group(0),
            "start_value": start_value,
            "end_value": end_value,
            "is_present": is_present,
            "sort_value": start_value if is_present else (end_value or start_value),
            "target_ranges": [{"start": range_match.start(), "end": range_match.end(), "text": range_match.group(0)}],
        }

    malformed_range = DATE_RANGE_START_PATTERN.search(paragraph.text)
    if malformed_range:
        start_value = _month_year_value(malformed_range.group(1), malformed_range.group(2))
        date_text = malformed_range.group(0).strip()
        return {
            "date_text": date_text,
            "start_value": start_value,
            "end_value": None,
            "is_present": False,
            "sort_value": start_value,
            "malformed": True,
            "target_ranges": [{"start": malformed_range.start(), "end": malformed_range.end(), "text": date_text}],
        }

    matches = list(MONTH_YEAR_PATTERN.finditer(paragraph.text))
    if not matches:
        return None
    match = matches[-1]
    value = _month_year_value(match.group(1), match.group(2))
    return {
        "date_text": match.group(0),
        "start_value": value,
        "end_value": value,
        "is_present": False,
        "sort_value": value,
        "target_ranges": [{"start": match.start(), "end": match.end(), "text": match.group(0)}],
    }


def _section_ranges(document: DocumentModel, detected_sections: List[Dict[str, Any]]) -> Dict[str, range]:
    allowed_detected = {section["paragraph_index"]: section["name"] for section in detected_sections}
    detected_names = set(allowed_detected.values())
    heading_boundaries: List[Dict[str, Any]] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if paragraph.index in allowed_detected:
            heading_boundaries.append({"name": allowed_detected[paragraph.index], "paragraph_index": paragraph.index})
        elif SECTION_PATTERN.fullmatch(text):
            heading_boundaries.append({"name": text, "paragraph_index": paragraph.index})
    sorted_sections = sorted(heading_boundaries, key=lambda section: section["paragraph_index"])
    ranges: Dict[str, range] = {}
    for index, section in enumerate(sorted_sections):
        if section["name"] not in detected_names:
            continue
        start = section["paragraph_index"] + 1
        end = (
            sorted_sections[index + 1]["paragraph_index"]
            if index + 1 < len(sorted_sections)
            else len(document.paragraphs)
        )
        ranges[section["name"]] = range(start, end)
    return ranges


def _section_date_entries(
    document: DocumentModel,
    detected_sections: List[Dict[str, Any]],
    section_indices: set[int],
    header_indices: set[int],
) -> Dict[str, List[Dict[str, Any]]]:
    checked_sections = {"EDUCATION", "PROFESSIONAL EXPERIENCE", "LEADERSHIP & RELEVANT EXPERIENCE"}
    ranges = _section_ranges(document, detected_sections)
    entries_by_section: Dict[str, List[Dict[str, Any]]] = {}
    for section_name, section_range in ranges.items():
        if section_name not in checked_sections:
            continue
        entries: List[Dict[str, Any]] = []
        for para in document.paragraphs:
            if para.index not in section_range:
                continue
            if para.index in section_indices or para.index in header_indices or para.numbering or para.is_blank:
                continue
            info = _date_info(para)
            if info:
                entries.append({"paragraph": para, **info})
        entries_by_section[section_name] = entries
    return entries_by_section


def _entry_paragraphs(document: DocumentModel, section_indices: set[int], header_indices: set[int]) -> List[ParagraphModel]:
    entries: List[ParagraphModel] = []
    for para in document.paragraphs:
        if para.index in section_indices or para.index in header_indices or para.numbering or para.is_blank:
            continue
        if para.has_tabs and DATE_PATTERN.search(para.text):
            entries.append(para)
    return entries


def _font_size_summary(document: DocumentModel) -> Dict[str, Any]:
    fonts = Counter()
    sizes = Counter()
    for para in document.paragraphs:
        for run in para.visible_runs:
            if run.font:
                fonts[run.font] += len(run.text.strip())
            if run.size_pt and run.size_pt > 2:
                sizes[run.size_pt] += len(run.text.strip())
    return {
        "fonts": dict(fonts),
        "sizes_pt": dict(sizes),
    }


def analyze_docx(path: str | Path, render: bool = False) -> Dict[str, Any]:
    rubric = load_rubric()
    rules_by_id = _rule_lookup(rubric)
    document = parse_docx(path)
    violations: List[Dict[str, Any]] = []
    expected_sections = rubric["section_order"]["required_sections"]
    allowed_sections = set(expected_sections) | set(rubric["section_order"].get("optional_sections", []))
    detected_sections = _detect_sections(document, allowed_sections)
    section_indices = {section["paragraph_index"] for section in detected_sections}
    header_indices = _header_indices(document, detected_sections)
    expected_right_tab_position = _expected_right_tab_position(document)

    for side, value in document.page_margins.items():
        if value is None:
            continue
        if not 0.5 <= value <= 1.0:
            violations.append(
                _make_violation(
                    "document.margin_range",
                    "major",
                    4,
                    f"{side} margin is {value}in, outside the allowed 0.5in to 1.0in range.",
                    {"side": side, "value_inches": value},
                )
            )

    if document.table_count:
        violations.append(
            _make_violation(
                "layout.no_tables",
                "critical",
                10,
                "Document uses tables for layout, which is disallowed in corsair_v1.",
                {"table_count": document.table_count},
            )
        )

    if document.textbox_count:
        violations.append(
            _make_violation(
                "layout.no_textboxes",
                "critical",
                10,
                "Document uses text boxes or floating content, which is disallowed in corsair_v1.",
                {"textbox_count": document.textbox_count},
            )
        )

    render_validation = validate_rendered_page_count(path) if render else get_render_validation_status()
    if render and render_validation.get("page_count") is not None and render_validation["page_count"] != 1:
        violations.append(
            _make_violation(
                "document.one_page_rendered",
                "critical",
                10,
                "Rendered document is not exactly one page.",
                {"page_count": render_validation["page_count"]},
            )
        )

    blank_runs = 0
    max_blank_run = 0
    repeated_space_paragraphs: List[ParagraphModel] = []
    manual_indent_paragraphs: List[ParagraphModel] = []
    tab_space_hack_paragraphs: List[ParagraphModel] = []
    excessive_tab_paragraphs: List[ParagraphModel] = []
    header_spacing_hack_paragraphs: List[ParagraphModel] = []
    date_spacing_hack_paragraphs: List[ParagraphModel] = []
    justified_numbered: List[ParagraphModel] = []
    tab_without_stop: List[ParagraphModel] = []
    irregular_right_tab: List[ParagraphModel] = []
    bullet_paragraphs: List[ParagraphModel] = []
    top_level_bullet_outliers: List[ParagraphModel] = []

    for para in document.paragraphs:
        if para.is_blank:
            blank_runs += 1
            max_blank_run = max(max_blank_run, blank_runs)
        else:
            blank_runs = 0

        if para.leading_spaces >= 2:
            manual_indent_paragraphs.append(para)

        if para.repeated_spaces and not para.is_blank:
            repeated_space_paragraphs.append(para)

        has_tab_space_hack = para.tab_space_padding or (
            para.raw_repeated_spaces
            and para.has_tabs
            and not para.tab_stops
            and not para.is_blank
        )
        if has_tab_space_hack:
            tab_space_hack_paragraphs.append(para)
        elif para.tab_count >= 3 and not para.tab_stops and not para.is_blank:
            excessive_tab_paragraphs.append(para)
        elif para.has_tabs and not para.tab_stops:
            tab_without_stop.append(para)

        if para.index in header_indices and _looks_like_manual_layout(para):
            header_spacing_hack_paragraphs.append(para)

        if DATE_PATTERN.search(para.text) and _looks_like_manual_layout(para):
            date_spacing_hack_paragraphs.append(para)

        if para.numbering:
            bullet_paragraphs.append(para)
            if para.numbering_level in {None, 0}:
                expected_indent = rubric["canonical_layout"].get("default_bullet_indent_twips", {})
                expected_left = int(expected_indent.get("left", 720))
                expected_hanging = int(expected_indent.get("hanging", 360))
                actual_left = _int_twips(para.indent.get("left"))
                actual_hanging = _int_twips(para.indent.get("hanging"))
                bullet_position = actual_left - actual_hanging if actual_left is not None and actual_hanging is not None else None
                expected_bullet_position = expected_left - expected_hanging
                if (
                    not _close_twips(actual_left, expected_left)
                    or not _close_twips(actual_hanging, expected_hanging)
                    or not _close_twips(bullet_position, expected_bullet_position)
                ):
                    top_level_bullet_outliers.append(para)

        if para.alignment == "both" and para.numbering:
            justified_numbered.append(para)

        right_tabs = [tab for tab in para.tab_stops if tab.get("val") == "right"]
        if right_tabs:
            if not _has_expected_right_tab(para, expected_right_tab_position):
                irregular_right_tab.append(para)

    tab_space_indices = {paragraph.index for paragraph in tab_space_hack_paragraphs}
    excessive_tab_indices = {paragraph.index for paragraph in excessive_tab_paragraphs}
    specific_manual_indices = tab_space_indices | {paragraph.index for paragraph in header_spacing_hack_paragraphs + date_spacing_hack_paragraphs}
    repeated_space_paragraphs = [
        paragraph for paragraph in repeated_space_paragraphs if paragraph.index not in specific_manual_indices
    ]
    tab_without_stop = [
        paragraph
        for paragraph in tab_without_stop
        if paragraph.index not in tab_space_indices and paragraph.index not in excessive_tab_indices
    ]

    if max_blank_run > 1:
        violations.append(
            _make_violation(
                "paragraph.no_consecutive_blank_lines",
                "minor",
                1,
                "Document contains consecutive blank paragraphs.",
                {"max_consecutive_blank_paragraphs": max_blank_run},
            )
        )

    if manual_indent_paragraphs:
        violations.append(
            _make_violation(
                "paragraph.no_leading_spaces",
                "major",
                4,
                "One or more paragraphs use literal leading spaces instead of paragraph indentation.",
                {"paragraphs": [_paragraph_summary(p) for p in manual_indent_paragraphs[:8]]},
            )
        )

    if repeated_space_paragraphs:
        violations.append(
                _make_violation(
                    "paragraph.no_manual_alignment_spaces",
                    "major",
                    4,
                    "One or more lines are positioned with repeated spaces instead of stable Word formatting.",
                    {"paragraphs": [_paragraph_summary(p) for p in repeated_space_paragraphs[:8]]},
                )
            )

    if tab_space_hack_paragraphs:
        violations.append(
                _make_violation(
                    "paragraph.tab_space_alignment_hacks",
                    "major",
                    6,
                    "Some lines look aligned because tabs and extra spaces are mixed together.",
                    {"paragraphs": [_paragraph_summary(p) for p in _unique_paragraphs(tab_space_hack_paragraphs)[:8]]},
                )
            )

    if excessive_tab_paragraphs:
        violations.append(
                _make_violation(
                    "paragraph.excessive_alignment_tabs",
                    "major",
                    4,
                    "Some lines are pushed into place with repeated tab presses instead of saved tab stops.",
                    {"paragraphs": [_paragraph_summary(p) for p in _unique_paragraphs(excessive_tab_paragraphs)[:8]]},
                )
            )

    if tab_without_stop:
        violations.append(
                _make_violation(
                    "paragraph.tabs_require_defined_stops",
                    "major",
                    4,
                    "Some tabs are used without saved tab stops, so Word decides the spacing automatically.",
                    {"paragraphs": [_paragraph_summary(p) for p in tab_without_stop[:8]]},
                )
            )

    if header_spacing_hack_paragraphs:
        violations.append(
                _make_violation(
                    "header.contact_spacing_hack",
                    "major",
                    6,
                    "The header may look aligned, but it is built with manual spacing that can break during editing.",
                    {"paragraphs": [_paragraph_summary(p) for p in _unique_paragraphs(header_spacing_hack_paragraphs)[:8]]},
                )
            )

    if date_spacing_hack_paragraphs:
        violations.append(
                _make_violation(
                    "entry.date_alignment_spacing_hack",
                    "major",
                    6,
                    "Some dates may look aligned, but they are positioned with spaces or mixed tab spacing.",
                    {"paragraphs": [_paragraph_summary(p) for p in _unique_paragraphs(date_spacing_hack_paragraphs)[:8]]},
                )
            )

    if irregular_right_tab:
        violations.append(
            _make_violation(
                "paragraph.right_tab_consistency",
                "minor",
                1,
                "Some right-aligned tab stops differ from the expected position for the document page width and margins.",
                {
                    "expected_position_twips": expected_right_tab_position,
                    "paragraphs": [_paragraph_summary(p) for p in irregular_right_tab[:8]],
                },
            )
        )

    if justified_numbered:
        violations.append(
            _make_violation(
                "paragraph.body_alignment_consistency",
                "minor",
                1,
                "Some numbered bullet paragraphs use full justification while peers do not.",
                {"paragraphs": [_paragraph_summary(p) for p in justified_numbered[:8]]},
            )
        )

    if top_level_bullet_outliers:
        expected_indent = rubric["canonical_layout"].get("default_bullet_indent_twips", {})
        expected_left = int(expected_indent.get("left", 720))
        expected_hanging = int(expected_indent.get("hanging", 360))
        expected_bullet_position = expected_left - expected_hanging
        violations.append(
            _make_violation(
                "bullet.indent_consistency",
                "major",
                4,
                "First-level bullets must use the 0.25in bullet position and 0.5in text indent.",
                {
                    "expected": {
                        "bullet_position_inches": round(expected_bullet_position / TWIPS_PER_INCH, 3),
                        "text_indent_inches": round(expected_left / TWIPS_PER_INCH, 3),
                        "hanging_indent_inches": round(expected_hanging / TWIPS_PER_INCH, 3),
                    },
                    "grouped_comment": True,
                    "paragraphs": [_paragraph_summary(p) for p in top_level_bullet_outliers[:8]],
                },
            )
        )

    entries_by_section = _section_date_entries(document, detected_sections, section_indices, header_indices)
    invalid_date_entries: List[Dict[str, Any]] = []
    chronological_outliers: List[Dict[str, Any]] = []
    for section_name, entries in entries_by_section.items():
        previous_key: Optional[tuple[int, int]] = None
        previous_entry: Optional[Dict[str, Any]] = None
        for entry in entries:
            if entry.get("malformed") or (entry["end_value"] is not None and entry["end_value"] < entry["start_value"]):
                invalid_date_entries.append({**entry, "section": section_name})
                continue

            key = (1 if entry["is_present"] else 0, entry["sort_value"])
            if previous_key is not None and key > previous_key:
                chronological_outliers.append(
                    {
                        **entry,
                        "section": section_name,
                        "previous_date_text": previous_entry["date_text"] if previous_entry else None,
                    }
                )
            previous_key = key
            previous_entry = entry

    if invalid_date_entries:
        violations.append(
            _make_violation(
                "entry.date_range_valid",
                "major",
                5,
                "One or more date ranges are impossible or malformed.",
                {
                    "paragraphs": [
                        _paragraph_summary(item["paragraph"], item["target_ranges"])
                        | {"section": item["section"], "date_text": item["date_text"]}
                        for item in invalid_date_entries[:8]
                    ]
                },
            )
        )

    if chronological_outliers:
        violations.append(
            _make_violation(
                "section.reverse_chronological_order",
                "major",
                4,
                "Entries should be reverse chronological within each section.",
                {
                    "paragraphs": [
                        _paragraph_summary(item["paragraph"], item["target_ranges"])
                        | {
                            "section": item["section"],
                            "date_text": item["date_text"],
                            "previous_date_text": item.get("previous_date_text"),
                        }
                        for item in chronological_outliers[:8]
                    ]
                },
            )
        )

    section_names = [section["name"] for section in detected_sections]

    nonblank = [paragraph for paragraph in document.paragraphs if not paragraph.is_blank]
    if nonblank:
        first = nonblank[0]
        if first.index != 0 or not _is_stably_centered_name(first):
            violations.append(
                _make_violation(
                    "header.name_centered_top_line",
                    "critical",
                    5,
                    "The name may look centered, but it is built in a way that can shift during editing.",
                    {"paragraph": _paragraph_summary(first)},
                )
            )

    header_address_paragraphs = _header_address_paragraphs(document, header_indices)
    header_address_matches = [
        address
        for paragraph in header_address_paragraphs
        for address in _header_city_state_matches(paragraph.text)
    ]
    if header_indices and len(header_address_matches) != 2:
        evidence: Dict[str, Any] = {"detected_addresses": header_address_matches}
        if header_address_paragraphs:
            evidence["paragraphs"] = [_paragraph_summary(p) for p in header_address_paragraphs[:4]]
        violations.append(
            _make_violation(
                "header.dual_address",
                "critical",
                10,
                "Header must contain exactly two city/state addresses before the Education section.",
                evidence,
            )
        )

    contact = _contact_paragraph(document, header_indices)
    if contact:
        if contact.tab_count < 2 or not _has_expected_right_tab(contact, expected_right_tab_position):
            violations.append(
                _make_violation(
                    "header.contact_single_row",
                    "major",
                    5,
                    "Header contact information must sit on one tab-separated row with a right tab stop.",
                    {
                        "paragraph": _paragraph_summary(contact),
                        "tab_stops": contact.tab_stops,
                        "expected_position_twips": expected_right_tab_position,
                    },
                )
            )

    missing_sections = [name for name in expected_sections if name not in section_names]
    suspected_section_typos = _suspected_section_heading_typos(
        document,
        missing_sections,
        detected_sections,
    )
    typo_expected_sections = {item["expected"] for item in suspected_section_typos}
    if suspected_section_typos:
        violations.append(
            _make_violation(
                "section.label_spelling",
                "critical",
                5,
                "One or more required section headings are present but misspelled.",
                {
                    "paragraphs": [
                        _paragraph_summary(
                            item["paragraph"],
                            [{"start": 0, "end": len(item["paragraph"].text), "text": item["paragraph"].text}],
                        )
                        | {"found": item["found"], "expected": item["expected"]}
                        for item in suspected_section_typos[:8]
                    ]
                },
            )
        )
    missing_sections = [name for name in missing_sections if name not in typo_expected_sections]
    if missing_sections:
        evidence: Dict[str, Any] = {"missing_sections": missing_sections, "detected_sections": section_names}
        violations.append(
            _make_violation(
                "section.required_presence",
                "critical",
                10,
                "Document is missing one or more required sections.",
                evidence,
            )
        )

    if len(detected_sections) < 2:
        violations.append(
            _make_violation(
                "section.corsair_structure_detected",
                "critical",
                10,
                "Document does not expose enough canonical Corsair section structure to audit reliably.",
                {"detected_sections": section_names},
            )
        )

    filtered_detected = [name for name in section_names if name in expected_sections]
    expected_filtered = [name for name in expected_sections if name in filtered_detected]
    if filtered_detected and filtered_detected != expected_filtered:
        violations.append(
            _make_violation(
                "section.order",
                "major",
                4,
                "Section order does not match the canonical Corsair sequence.",
                {
                    "expected_order": expected_sections,
                    "detected_order": filtered_detected,
                },
            )
        )

    malformed_sections = []
    unbold_sections = []
    missing_section_rules = []
    for section in detected_sections:
        para = document.paragraphs[section["paragraph_index"]]
        if para.text.strip() != para.text.strip().upper():
            malformed_sections.append(para)
        if not _all_visible_runs_bold(para):
            unbold_sections.append(para)
        if not para.has_bottom_border:
            missing_section_rules.append(para)

    if malformed_sections:
        violations.append(
            _make_violation(
                "section.labels_all_caps",
                "critical",
                5,
                "All section labels must be fully capitalized.",
                {"paragraphs": [_paragraph_summary(p) for p in malformed_sections[:8]]},
            )
        )

    if unbold_sections:
        violations.append(
            _make_violation(
                "section.headers_bold",
                "major",
                5,
                "All section labels must be bold.",
                {"paragraphs": [_paragraph_summary(p) for p in unbold_sections[:8]]},
            )
        )

    if missing_section_rules:
        violations.append(
            _make_violation(
                "section.divider_rule",
                "major",
                5,
                "Each section header must include a bottom divider rule.",
                {"paragraphs": [_paragraph_summary(p) for p in missing_section_rules[:8]]},
            )
        )

    entries = _entry_paragraphs(document, section_indices, header_indices)
    missing_right_tabs = []
    wrong_date_dashes: List[tuple[ParagraphModel, List[Dict[str, Any]]]] = []
    unbold_orgs = []
    missing_italic_roles: List[tuple[ParagraphModel, List[Dict[str, Any]]]] = []
    missing_locations = []
    for entry in entries:
        if entry.tab_count != 1 or not _has_expected_right_tab(entry, expected_right_tab_position):
            missing_right_tabs.append(entry)
        dash_targets = _wrong_date_dash_target_ranges(entry)
        if dash_targets:
            wrong_date_dashes.append((entry, dash_targets))
        if not _first_visible_run_bold(entry):
            unbold_orgs.append(entry)
        role_targets = _role_italic_target_ranges(entry) if _expects_italic_role(entry) else []
        if role_targets:
            missing_italic_roles.append((entry, role_targets))
        before_date = entry.text.split("\t", 1)[0]
        if not CITY_STATE_PATTERN.search(before_date):
            missing_locations.append(entry)

    if missing_right_tabs:
        violations.append(
            _make_violation(
                "entry.date_right_tab",
                "major",
                5,
                "Entry dates must be right-aligned with one canonical right tab stop.",
                {
                    "expected_position_twips": expected_right_tab_position,
                    "paragraphs": [_paragraph_summary(p) for p in missing_right_tabs[:8]],
                },
            )
        )

    if wrong_date_dashes:
        violations.append(
            _make_violation(
                "entry.date_range_en_dash",
                "minor",
                1,
                "Date ranges must use an en dash (–), not a hyphen or em dash.",
                {
                    "paragraphs": [
                        _paragraph_summary(paragraph, target_ranges=target_ranges)
                        for paragraph, target_ranges in wrong_date_dashes[:8]
                    ],
                    "expected_dash": "–",
                },
            )
        )

    if unbold_orgs:
        violations.append(
            _make_violation(
                "entry.organization_bold",
                "major",
                5,
                "Organization or institution name must start each entry line in bold.",
                {"paragraphs": [_paragraph_summary(p) for p in unbold_orgs[:8]]},
            )
        )

    if missing_italic_roles:
        violations.append(
            _make_violation(
                "entry.role_italic",
                "major",
                5,
                "Role, title, or program descriptor must be italicized before the date tab.",
                {
                    "paragraphs": [
                        _paragraph_summary(paragraph, target_ranges=target_ranges)
                        for paragraph, target_ranges in missing_italic_roles[:8]
                    ]
                },
            )
        )

    if missing_locations:
        violations.append(
            _make_violation(
                "entry.location_present",
                "minor",
                1,
                "Entry lines must include City, ST before the date tab.",
                {"paragraphs": [_paragraph_summary(p) for p in missing_locations[:8]]},
            )
        )

    type_summary = _font_size_summary(document)
    meaningful_fonts = {
        font: weight
        for font, weight in type_summary["fonts"].items()
        if weight >= 3
    }
    if len(meaningful_fonts) > 1:
        violations.append(
            _make_violation(
                "typography.single_font_family",
                "critical",
                5,
                "Document must use a single font family throughout.",
                {"fonts": meaningful_fonts},
            )
        )

    body_sizes = [
        size
        for size, weight in type_summary["sizes_pt"].items()
        if 8 <= float(size) <= 12 and weight >= 3
    ]
    if len(body_sizes) > 1 and max(body_sizes) - min(body_sizes) > 0.5:
        violations.append(
            _make_violation(
                "typography.body_font_size_consistency",
                "major",
                5,
                "Body text must use a consistent font size without drift.",
                {"body_sizes_pt": sorted(body_sizes)},
            )
        )

    unauthorized_emphasis = []
    for para in bullet_paragraphs:
        if any(run.italic for run in para.visible_runs):
            unauthorized_emphasis.append(para)
    if unauthorized_emphasis:
        violations.append(
            _make_violation(
                "typography.no_unauthorized_inline_emphasis",
                "minor",
                1,
                "Bold or italic emphasis in bullets must only be used for canonical labels such as GPA or Honors.",
                {"paragraphs": [_paragraph_summary(p) for p in unauthorized_emphasis[:8]]},
            )
        )

    violations = _apply_rubric_to_violations(violations, rules_by_id)
    structural_penalty = sum(item["points"] for item in violations if item.get("category") == "structural")
    visual_penalty = sum(item["points"] for item in violations if item.get("category") == "visual")
    total_penalty = structural_penalty + visual_penalty
    visual_compliance_score = max(0, 100 - visual_penalty)
    structural_quality_score = max(0, 100 - structural_penalty)
    score = round(
        (visual_compliance_score * VISUAL_SCORE_WEIGHT)
        + (structural_quality_score * STRUCTURAL_SCORE_WEIGHT)
    )

    return {
        "rubric_version": rubric["rubric_version"],
        "source_path": str(path),
        "score": score,
        "overall_score": score,
        "visual_compliance_score": visual_compliance_score,
        "structural_quality_score": structural_quality_score,
        "total_penalty": total_penalty,
        "visual_penalty": visual_penalty,
        "structural_penalty": structural_penalty,
        "score_weights": {
            "visual": VISUAL_SCORE_WEIGHT,
            "structural": STRUCTURAL_SCORE_WEIGHT,
        },
        "document_summary": {
            "paragraph_count": document.paragraph_count,
            "table_count": document.table_count,
            "textbox_count": document.textbox_count,
            "page_margins_inches": document.page_margins,
            "detected_sections": detected_sections,
            "render_validation": render_validation,
        },
        "violations": violations,
    }
