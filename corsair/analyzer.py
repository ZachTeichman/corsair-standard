from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from .docx_parser import DocumentModel, ParagraphModel, parse_docx
from .render_validation import get_render_validation_status, validate_rendered_page_count
from .rubric import load_rubric


SECTION_PATTERN = re.compile(r"^[A-Z][A-Z &/]{3,}$")
CITY_STATE_PATTERN = re.compile(r"\b[A-Z][A-Za-z .'-]+,?\s+[A-Z]{2}(?:\s+\d{5})?\b")
DATE_PATTERN = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}"
    r"(?:\s*[-–]\s*(?:Present|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{4}))?\b"
)
STRUCTURAL_QUALITY_RULES = {
    "paragraph.no_leading_spaces",
    "paragraph.no_manual_alignment_spaces",
    "paragraph.tabs_require_defined_stops",
    "paragraph.tab_space_alignment_hacks",
    "paragraph.excessive_alignment_tabs",
    "header.contact_spacing_hack",
    "entry.date_alignment_spacing_hack",
}


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
        "message": message,
        "evidence": evidence or {},
    }


def _detect_sections(document: DocumentModel, allowed_sections: set[str]) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if text in allowed_sections and SECTION_PATTERN.fullmatch(text):
            sections.append({"name": text, "paragraph_index": para.index})
    return sections


def _paragraph_summary(paragraph: ParagraphModel) -> Dict[str, Any]:
    return {
        "index": paragraph.index,
        "text": paragraph.text[:160].replace("\t", "\\t"),
        "alignment": paragraph.alignment,
        "style_name": paragraph.style_name,
        "tab_count": paragraph.tab_count,
        "tab_stop_count": len(paragraph.tab_stops),
        "has_raw_repeated_spaces": paragraph.raw_repeated_spaces,
        "has_tab_space_padding": paragraph.tab_space_padding,
    }


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
    return max(candidates, key=lambda paragraph: (len(CITY_STATE_PATTERN.findall(paragraph.text)), paragraph.tab_count))


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


def _all_visible_runs_bold(paragraph: ParagraphModel) -> bool:
    visible = paragraph.visible_runs
    return bool(visible) and all(run.bold for run in visible)


def _first_visible_run_bold(paragraph: ParagraphModel) -> bool:
    visible = paragraph.visible_runs
    return bool(visible) and visible[0].bold


def _has_italic_before_first_tab(paragraph: ParagraphModel) -> bool:
    seen_text = ""
    for run in paragraph.runs:
        if "\t" in run.text:
            return False
        seen_text += run.text
        if run.italic and run.text.strip():
            return True
    return False


def _expects_italic_role(paragraph: ParagraphModel) -> bool:
    before_date = paragraph.text.split("\t", 1)[0]
    # Canonical entry lines with an organization + role + location still have
    # one comma break after removing the trailing City, ST location. Education
    # or high-school lines can be just institution + location and should not be
    # punished as if they were job entries.
    without_location = CITY_STATE_PATTERN.sub("", before_date).rstrip(" ,")
    return without_location.count(",") >= 1


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
    bullet_signature_counter: Counter = Counter()
    bullet_paragraphs: List[ParagraphModel] = []
    left_equivalent_alignments = {None, "left"}

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
            bullet_signature_counter[
                (
                    para.left_indent_pt,
                    para.hanging_indent_pt,
                    None if para.alignment in left_equivalent_alignments else para.alignment,
                )
            ] += 1

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

    if bullet_signature_counter:
        dominant_signature, _ = bullet_signature_counter.most_common(1)[0]
        outliers = [
            para
            for para in bullet_paragraphs
            if (
                para.left_indent_pt,
                para.hanging_indent_pt,
                None if para.alignment in left_equivalent_alignments else para.alignment,
            ) != dominant_signature
        ]
        if outliers:
            violations.append(
                _make_violation(
                    "bullet.indent_consistency",
                    "major",
                    4,
                    "Bullet indentation is inconsistent across the document.",
                    {
                        "dominant_signature": {
                            "left_indent_pt": dominant_signature[0],
                            "hanging_indent_pt": dominant_signature[1],
                            "alignment": dominant_signature[2],
                        },
                        "paragraphs": [_paragraph_summary(p) for p in outliers[:8]],
                    },
                )
            )

    section_names = [section["name"] for section in detected_sections]

    nonblank = [paragraph for paragraph in document.paragraphs if not paragraph.is_blank]
    if nonblank:
        first = nonblank[0]
        if first.index != 0 or not _has_center_tab(first) or first.tab_count != 1:
            violations.append(
                _make_violation(
                    "header.name_centered_top_line",
                    "critical",
                    5,
                    "The name may look centered, but it is built in a way that can shift during editing.",
                    {"paragraph": _paragraph_summary(first)},
                )
            )

    contact = _contact_paragraph(document, header_indices)
    if contact:
        city_state_matches = CITY_STATE_PATTERN.findall(contact.text)
        if len(city_state_matches) != 2:
            violations.append(
                _make_violation(
                    "header.dual_address",
                    "critical",
                    10,
                    "Header contact line must contain exactly two city/state addresses.",
                    {"paragraph": _paragraph_summary(contact), "detected_addresses": city_state_matches},
                )
            )
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
    if missing_sections:
        violations.append(
            _make_violation(
                "section.required_presence",
                "critical",
                10,
                "Document is missing one or more required sections.",
                {"missing_sections": missing_sections, "detected_sections": section_names},
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
    unbold_orgs = []
    missing_italic_roles = []
    missing_locations = []
    for entry in entries:
        if entry.tab_count != 1 or not _has_expected_right_tab(entry, expected_right_tab_position):
            missing_right_tabs.append(entry)
        if not _first_visible_run_bold(entry):
            unbold_orgs.append(entry)
        if _expects_italic_role(entry) and not _has_italic_before_first_tab(entry):
            missing_italic_roles.append(entry)
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
                {"paragraphs": [_paragraph_summary(p) for p in missing_italic_roles[:8]]},
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

    nested_bullets = [
        para
        for para in bullet_paragraphs
        if para.numbering_level is not None and para.numbering_level > 0
    ]
    if nested_bullets:
        violations.append(
            _make_violation(
                "bullet.no_nested_bullets",
                "critical",
                5,
                "Corsair bullets must be flat; nested bullet levels are not allowed.",
                {"paragraphs": [_paragraph_summary(p) for p in nested_bullets[:8]]},
            )
        )

    long_bullets = [
        para
        for para in bullet_paragraphs
        if len(para.text.strip()) > rubric["canonical_layout"].get("max_single_line_bullet_chars", 140)
    ]
    if long_bullets:
        violations.append(
            _make_violation(
                "bullet.single_line_length",
                "minor",
                1,
                "One or more bullet points are likely longer than one rendered line.",
                {
                    "max_chars": rubric["canonical_layout"].get("max_single_line_bullet_chars", 115),
                    "paragraphs": [_paragraph_summary(p) for p in long_bullets[:8]],
                },
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
    if body_sizes and (min(body_sizes) < 10 or max(body_sizes) > 12 or max(body_sizes) - min(body_sizes) > 0.5):
        violations.append(
            _make_violation(
                "typography.body_font_size_consistency",
                "major",
                5,
                "Body text must use a consistent 10-12pt size range without drift.",
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

    structural_penalty = sum(item["points"] for item in violations if item["rule_id"] in STRUCTURAL_QUALITY_RULES)
    visual_penalty = sum(item["points"] for item in violations if item["rule_id"] not in STRUCTURAL_QUALITY_RULES)
    total_penalty = structural_penalty + visual_penalty
    visual_compliance_score = max(0, 100 - visual_penalty)
    structural_quality_score = max(0, 100 - structural_penalty)
    score = round((visual_compliance_score + structural_quality_score) / 2)

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
