from __future__ import annotations

import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from .analyzer import analyze_docx
from .docx_parser import NS, _attr_map
from .rubric import load_rubric


RIGHT_TAB_TWIPS = "10800"
DEFAULT_LEFT_TWIPS = "720"
DEFAULT_HANGING_TWIPS = "360"


def _cleanup_text_value(text: str, is_first: bool, is_last: bool) -> str:
    if is_first:
        text = text.lstrip(" ")
    if is_last:
        text = text.rstrip(" ")
    text = re.sub(r" {2,}", " ", text)
    return text


def _cleanup_tab_paragraph_text_value(text: str) -> str:
    if text.isspace():
        return ""
    if len(text) > len(text.lstrip(" ")) + 10:
        compact = text.strip(" ")
        if len(compact) <= 2:
            return ""
    return text.strip(" ")


def _remove_consecutive_blank_paragraphs(body: ET.Element) -> int:
    removed = 0
    previous_blank = False
    for para in list(body.findall("./w:p", NS)):
        text = "".join((node.text or "") for node in para.findall(".//w:t", NS))
        current_blank = text.strip() == ""
        if current_blank and previous_blank:
            body.remove(para)
            removed += 1
            continue
        previous_blank = current_blank
    return removed


def _ensure_tab_stops(ppr: ET.Element, has_tabs: bool) -> bool:
    if not has_tabs:
        return False

    changed = False
    tabs_node = ppr.find("./w:tabs", NS)
    if tabs_node is None:
        tabs_node = ET.SubElement(ppr, f"{{{NS['w']}}}tabs")
        changed = True

    right_tabs = [tab for tab in tabs_node.findall("./w:tab", NS) if _attr_map(tab).get("val") == "right"]
    if not right_tabs:
        ET.SubElement(
            tabs_node,
            f"{{{NS['w']}}}tab",
            {
                f"{{{NS['w']}}}val": "right",
                f"{{{NS['w']}}}pos": RIGHT_TAB_TWIPS,
            },
        )
        return True

    for tab in right_tabs:
        attrs = _attr_map(tab)
        if attrs.get("pos") != RIGHT_TAB_TWIPS:
            tab.set(f"{{{NS['w']}}}pos", RIGHT_TAB_TWIPS)
            changed = True
    return changed


def _normalize_bullet_indent(ppr: ET.Element, is_numbered: bool) -> bool:
    if not is_numbered:
        return False

    ind = ppr.find("./w:ind", NS)
    if ind is None:
        ind = ET.SubElement(ppr, f"{{{NS['w']}}}ind")

    changed = False
    if ind.get(f"{{{NS['w']}}}left") != DEFAULT_LEFT_TWIPS:
        ind.set(f"{{{NS['w']}}}left", DEFAULT_LEFT_TWIPS)
        changed = True
    if ind.get(f"{{{NS['w']}}}hanging") != DEFAULT_HANGING_TWIPS:
        ind.set(f"{{{NS['w']}}}hanging", DEFAULT_HANGING_TWIPS)
        changed = True
    return changed


def _normalize_alignment(ppr: ET.Element, is_numbered: bool) -> bool:
    if not is_numbered:
        return False
    jc = ppr.find("./w:jc", NS)
    if jc is None:
        return False
    if _attr_map(jc).get("val") == "both":
        jc.set(f"{{{NS['w']}}}val", "left")
        return True
    return False


def _trim_section_header_spaces(text_nodes: List[ET.Element], aggregate_text: str) -> bool:
    if not re.fullmatch(r"[A-Z][A-Z &/ ]*", aggregate_text.strip()):
        return False
    changed = False
    for i, node in enumerate(text_nodes):
        original = node.text or ""
        cleaned = original.strip(" ")
        if cleaned != original:
            node.text = cleaned
            changed = True
    return changed


def normalize_docx(input_path: str | Path, output_path: str | Path) -> Dict[str, Any]:
    rubric = load_rubric()
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    modifications: Dict[str, int] = {
        "trimmed_text_nodes": 0,
        "normalized_tab_stops": 0,
        "normalized_bullet_indents": 0,
        "normalized_bullet_alignment": 0,
        "removed_blank_paragraphs": 0,
        "trimmed_section_headers": 0,
    }

    with TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        with ZipFile(input_path) as src:
            src.extractall(tmp_dir_path)

        document_xml_path = tmp_dir_path / "word" / "document.xml"
        root = ET.fromstring(document_xml_path.read_bytes())
        body = root.find(".//w:body", NS)
        if body is None:
            raise ValueError("DOCX body not found.")

        modifications["removed_blank_paragraphs"] = _remove_consecutive_blank_paragraphs(body)

        for para in body.findall("./w:p", NS):
            ppr = para.find("./w:pPr", NS)
            if ppr is None:
                ppr = ET.SubElement(para, f"{{{NS['w']}}}pPr")

            text_nodes = para.findall(".//w:t", NS)
            texts = [(node.text or "") for node in text_nodes]
            aggregate_text = "".join(texts)
            has_tabs = bool(para.findall(".//w:tab", NS))
            is_numbered = ppr.find("./w:numPr", NS) is not None

            if _trim_section_header_spaces(text_nodes, aggregate_text):
                modifications["trimmed_section_headers"] += 1

            for index, node in enumerate(text_nodes):
                original = node.text or ""
                if has_tabs:
                    cleaned = _cleanup_tab_paragraph_text_value(original)
                else:
                    cleaned = _cleanup_text_value(
                        original,
                        is_first=index == 0,
                        is_last=index == len(text_nodes) - 1,
                    )
                if cleaned != original:
                    node.text = cleaned
                    modifications["trimmed_text_nodes"] += 1

            if _ensure_tab_stops(ppr, has_tabs):
                modifications["normalized_tab_stops"] += 1

            if _normalize_bullet_indent(ppr, is_numbered):
                modifications["normalized_bullet_indents"] += 1

            if _normalize_alignment(ppr, is_numbered):
                modifications["normalized_bullet_alignment"] += 1

        document_xml_path.write_bytes(
            ET.tostring(root, encoding="utf-8", xml_declaration=True)
        )

        with ZipFile(output_path, "w", ZIP_DEFLATED) as dest:
            for file_path in sorted(tmp_dir_path.rglob("*")):
                if file_path.is_file():
                    dest.write(file_path, file_path.relative_to(tmp_dir_path))

    before = analyze_docx(input_path)
    after = analyze_docx(output_path)

    return {
        "rubric_version": rubric["rubric_version"],
        "input_path": str(input_path),
        "output_path": str(output_path),
        "modifications": modifications,
        "before": {
            "score": before["score"],
            "total_penalty": before["total_penalty"],
            "violation_count": len(before["violations"]),
        },
        "after": {
            "score": after["score"],
            "total_penalty": after["total_penalty"],
            "violation_count": len(after["violations"]),
        },
    }
