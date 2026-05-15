from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from zipfile import ZipFile
import xml.etree.ElementTree as ET


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _attr_map(node: Optional[ET.Element]) -> Dict[str, str]:
    if node is None:
        return {}
    return {key.split("}")[-1]: value for key, value in node.attrib.items()}


def _twips_to_inches(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    return round(int(value) / 1440, 3)


def _twips_to_points(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    return round(int(value) / 20, 2)


@dataclass
class RunModel:
    text: str
    font: Optional[str]
    size_pt: Optional[float]
    bold: bool
    italic: bool


@dataclass
class ParagraphModel:
    index: int
    text: str
    style_name: Optional[str]
    alignment: Optional[str]
    is_blank: bool
    has_tabs: bool
    tab_stops: List[Dict[str, str]] = field(default_factory=list)
    borders: Dict[str, Dict[str, str]] = field(default_factory=dict)
    runs: List[RunModel] = field(default_factory=list)
    numbering: bool = False
    numbering_level: Optional[int] = None
    indent: Dict[str, str] = field(default_factory=dict)
    spacing: Dict[str, str] = field(default_factory=dict)
    leading_spaces: int = 0
    repeated_spaces: bool = False
    raw_repeated_spaces: bool = False
    tab_space_padding: bool = False

    @property
    def left_indent_pt(self) -> Optional[float]:
        return _twips_to_points(self.indent.get("left"))

    @property
    def hanging_indent_pt(self) -> Optional[float]:
        return _twips_to_points(self.indent.get("hanging"))

    @property
    def has_bottom_border(self) -> bool:
        bottom = self.borders.get("bottom", {})
        return bool(bottom and bottom.get("val") not in {None, "nil", "none"})

    @property
    def tab_count(self) -> int:
        return self.text.count("\t")

    @property
    def visible_runs(self) -> List[RunModel]:
        return [run for run in self.runs if run.text.strip()]


@dataclass
class DocumentModel:
    source_path: str
    paragraph_count: int
    table_count: int
    textbox_count: int
    page_margins: Dict[str, Optional[float]]
    paragraphs: List[ParagraphModel]


def parse_docx(path: str | Path) -> DocumentModel:
    docx_path = Path(path)
    with ZipFile(docx_path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    body_paragraphs = root.findall(".//w:body/w:p", NS)

    page_margins: Dict[str, Optional[float]] = {}
    sect = root.find(".//w:body/w:sectPr", NS)
    if sect is not None:
        margins = sect.find("./w:pgMar", NS)
        margin_attrs = _attr_map(margins)
        page_margins = {
            side: _twips_to_inches(margin_attrs.get(side))
            for side in ("top", "right", "bottom", "left")
        }

    document_text = document_xml.decode("utf-8", errors="ignore")
    paragraphs: List[ParagraphModel] = []

    for index, para in enumerate(body_paragraphs):
        text_parts: List[str] = []
        runs: List[RunModel] = []
        for run in para.findall("./w:r", NS):
            run_text_parts: List[str] = []
            for node in run:
                tag = node.tag.split("}")[-1]
                if tag == "t":
                    value = node.text or ""
                    text_parts.append(value)
                    run_text_parts.append(value)
                elif tag == "tab":
                    text_parts.append("\t")
                    run_text_parts.append("\t")
            run_text = "".join(run_text_parts)
            if run_text:
                rpr = run.find("./w:rPr", NS)
                rfonts = run.find("./w:rPr/w:rFonts", NS)
                size = run.find("./w:rPr/w:sz", NS)
                font_attrs = _attr_map(rfonts)
                size_attrs = _attr_map(size)
                runs.append(
                    RunModel(
                        text=run_text,
                        font=font_attrs.get("ascii") or font_attrs.get("hAnsi") or font_attrs.get("cs"),
                        size_pt=(
                            round(int(size_attrs["val"]) / 2, 2)
                            if size_attrs.get("val") and size_attrs["val"].isdigit()
                            else None
                        ),
                        bold=rpr is not None and rpr.find("./w:b", NS) is not None,
                        italic=rpr is not None and rpr.find("./w:i", NS) is not None,
                    )
                )
        text = "".join(text_parts)
        normalized_for_spacing = re.sub(r" *\t *", "\t", text)
        stripped = text.lstrip(" ")
        leading_spaces = len(text) - len(stripped)
        raw_repeated_spaces = bool(re.search(r" {2,}", text))
        tab_space_padding = bool(re.search(r"(?: {2,}\t|\t {2,})", text))
        paragraph_tabs = para.findall("./w:pPr/w:tabs/w:tab", NS)
        tab_stops = [_attr_map(tab) for tab in paragraph_tabs]
        p_style = para.find("./w:pPr/w:pStyle", NS)
        style_name = _attr_map(p_style).get("val")
        p_jc = para.find("./w:pPr/w:jc", NS)
        p_ind = para.find("./w:pPr/w:ind", NS)
        p_spacing = para.find("./w:pPr/w:spacing", NS)
        p_num = para.find("./w:pPr/w:numPr", NS)
        p_ilvl = para.find("./w:pPr/w:numPr/w:ilvl", NS)
        p_borders = para.findall("./w:pPr/w:pBdr/*", NS)
        borders = {node.tag.split("}")[-1]: _attr_map(node) for node in p_borders}

        paragraphs.append(
            ParagraphModel(
                index=index,
                text=text,
                style_name=style_name,
                alignment=_attr_map(p_jc).get("val"),
                is_blank=text.strip() == "",
                has_tabs=bool(para.findall("./w:r/w:tab", NS)),
                tab_stops=tab_stops,
                borders=borders,
                runs=runs,
                numbering=(
                    p_num is not None
                    or "list" in (style_name or "").lower()
                    or text.lstrip().startswith(("• ", "● "))
                ),
                numbering_level=(
                    int(_attr_map(p_ilvl).get("val"))
                    if _attr_map(p_ilvl).get("val", "").isdigit()
                    else None
                ),
                indent=_attr_map(p_ind),
                spacing=_attr_map(p_spacing),
                leading_spaces=leading_spaces,
                repeated_spaces="  " in normalized_for_spacing.strip(),
                raw_repeated_spaces=raw_repeated_spaces,
                tab_space_padding=tab_space_padding,
            )
        )

    return DocumentModel(
        source_path=str(docx_path),
        paragraph_count=len(paragraphs),
        table_count=document_text.count("<w:tbl"),
        textbox_count=document_text.count("txbxContent"),
        page_margins=page_margins,
        paragraphs=paragraphs,
    )
