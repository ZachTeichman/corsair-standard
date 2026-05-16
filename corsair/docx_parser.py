from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from zipfile import ZipFile
import xml.etree.ElementTree as ET


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W_NS = NS["w"]


def _attr_map(node: Optional[ET.Element]) -> Dict[str, str]:
    if node is None:
        return {}
    return {key.split("}")[-1]: value for key, value in node.attrib.items()}


def _local_name(node: ET.Element) -> str:
    return node.tag.split("}")[-1]


def _is_on_off(node: Optional[ET.Element]) -> Optional[bool]:
    if node is None:
        return None
    value = _attr_map(node).get("val")
    if value is None:
        return True
    return value.lower() not in {"0", "false", "off", "no"}


def _merge_dict(base: Dict[str, str], override: Dict[str, str]) -> Dict[str, str]:
    merged = dict(base)
    merged.update({key: value for key, value in override.items() if value is not None})
    return merged


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
    numbering_type: str = "none"
    numbering_id: Optional[str] = None
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
    page_size_twips: Dict[str, Optional[int]]
    page_margins: Dict[str, Optional[float]]
    page_margins_twips: Dict[str, Optional[int]]
    paragraphs: List[ParagraphModel]


def _rpr_props(rpr: Optional[ET.Element]) -> Dict[str, Any]:
    if rpr is None:
        return {}
    rfonts = rpr.find("./w:rFonts", NS)
    size = rpr.find("./w:sz", NS)
    font_attrs = _attr_map(rfonts)
    size_attrs = _attr_map(size)
    props: Dict[str, Any] = {}
    font = font_attrs.get("ascii") or font_attrs.get("hAnsi") or font_attrs.get("cs")
    if font:
        props["font"] = font
    if size_attrs.get("val", "").isdigit():
        props["size_pt"] = round(int(size_attrs["val"]) / 2, 2)
    bold = _is_on_off(rpr.find("./w:b", NS))
    italic = _is_on_off(rpr.find("./w:i", NS))
    if bold is not None:
        props["bold"] = bold
    if italic is not None:
        props["italic"] = italic
    return props


def _ppr_props(ppr: Optional[ET.Element]) -> Dict[str, Any]:
    if ppr is None:
        return {"alignment": None, "tab_stops": [], "indent": {}, "spacing": {}, "borders": {}, "numbering": {}}
    p_jc = ppr.find("./w:jc", NS)
    p_ind = ppr.find("./w:ind", NS)
    p_spacing = ppr.find("./w:spacing", NS)
    tabs = ppr.findall("./w:tabs/w:tab", NS)
    borders = ppr.findall("./w:pBdr/*", NS)
    p_num = ppr.find("./w:numPr", NS)
    p_ilvl = ppr.find("./w:numPr/w:ilvl", NS)
    p_num_id = ppr.find("./w:numPr/w:numId", NS)
    return {
        "alignment": _attr_map(p_jc).get("val"),
        "tab_stops": [_attr_map(tab) for tab in tabs],
        "indent": _attr_map(p_ind),
        "spacing": _attr_map(p_spacing),
        "borders": {node.tag.split("}")[-1]: _attr_map(node) for node in borders},
        "numbering": {
            "ilvl": _attr_map(p_ilvl).get("val"),
            "numId": _attr_map(p_num_id).get("val"),
        }
        if p_num is not None
        else {},
    }


def _merge_ppr(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "alignment": override.get("alignment") or base.get("alignment"),
        "tab_stops": override.get("tab_stops") or base.get("tab_stops", []),
        "indent": _merge_dict(base.get("indent", {}), override.get("indent", {})),
        "spacing": _merge_dict(base.get("spacing", {}), override.get("spacing", {})),
        "borders": {**base.get("borders", {}), **override.get("borders", {})},
        "numbering": _merge_dict(base.get("numbering", {}), override.get("numbering", {})),
    }


def _parse_styles(archive: ZipFile) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    defaults = {
        "ppr": {"alignment": None, "tab_stops": [], "indent": {}, "spacing": {}, "borders": {}, "numbering": {}},
        "rpr": {},
    }
    styles: Dict[str, Dict[str, Any]] = {}
    try:
        styles_root = ET.fromstring(archive.read("word/styles.xml"))
    except KeyError:
        return defaults, styles

    defaults["ppr"] = _ppr_props(styles_root.find("./w:docDefaults/w:pPrDefault/w:pPr", NS))
    defaults["rpr"] = _rpr_props(styles_root.find("./w:docDefaults/w:rPrDefault/w:rPr", NS))

    for style in styles_root.findall("./w:style", NS):
        attrs = _attr_map(style)
        style_id = attrs.get("styleId")
        if not style_id:
            continue
        based_on = _attr_map(style.find("./w:basedOn", NS)).get("val")
        styles[style_id] = {
            "style_id": style_id,
            "type": attrs.get("type"),
            "based_on": based_on,
            "ppr": _ppr_props(style.find("./w:pPr", NS)),
            "rpr": _rpr_props(style.find("./w:rPr", NS)),
        }
    return defaults, styles


def _style_chain(styles: Dict[str, Dict[str, Any]], style_id: Optional[str]) -> List[Dict[str, Any]]:
    chain: List[Dict[str, Any]] = []
    seen: set[str] = set()
    current = style_id
    while current and current not in seen and current in styles:
        seen.add(current)
        style = styles[current]
        chain.append(style)
        current = style.get("based_on")
    return list(reversed(chain))


def _effective_style_props(
    defaults: Dict[str, Any],
    styles: Dict[str, Dict[str, Any]],
    style_id: Optional[str],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    ppr = defaults["ppr"]
    rpr = dict(defaults["rpr"])
    for style in _style_chain(styles, style_id):
        ppr = _merge_ppr(ppr, style["ppr"])
        rpr.update(style["rpr"])
    return ppr, rpr


def _parse_numbering(archive: ZipFile) -> Dict[tuple[str, str], Dict[str, str]]:
    try:
        numbering_root = ET.fromstring(archive.read("word/numbering.xml"))
    except KeyError:
        return {}

    abstract_num_ids: Dict[str, str] = {}
    for num in numbering_root.findall("./w:num", NS):
        num_id = _attr_map(num).get("numId")
        abstract_id = _attr_map(num.find("./w:abstractNumId", NS)).get("val")
        if num_id and abstract_id:
            abstract_num_ids[num_id] = abstract_id

    indents: Dict[tuple[str, str], Dict[str, str]] = {}
    for abstract in numbering_root.findall("./w:abstractNum", NS):
        abstract_id = _attr_map(abstract).get("abstractNumId")
        if not abstract_id:
            continue
        for level in abstract.findall("./w:lvl", NS):
            ilvl = _attr_map(level).get("ilvl", "0")
            ind = _attr_map(level.find("./w:pPr/w:ind", NS))
            if ind:
                for num_id, mapped_abstract_id in abstract_num_ids.items():
                    if mapped_abstract_id == abstract_id:
                        indents[(num_id, ilvl)] = ind
    return indents


def _xml_count(root: ET.Element, local_name: str) -> int:
    return sum(1 for node in root.iter() if _local_name(node) == local_name)


def parse_docx(path: str | Path) -> DocumentModel:
    docx_path = Path(path)
    with ZipFile(docx_path) as archive:
        document_xml = archive.read("word/document.xml")
        defaults, styles = _parse_styles(archive)
        numbering_indents = _parse_numbering(archive)
    root = ET.fromstring(document_xml)
    body_paragraphs = root.findall(".//w:body/w:p", NS)

    page_size_twips: Dict[str, Optional[int]] = {}
    page_margins: Dict[str, Optional[float]] = {}
    page_margins_twips: Dict[str, Optional[int]] = {}
    sect = root.find(".//w:body/w:sectPr", NS)
    if sect is not None:
        page_size = sect.find("./w:pgSz", NS)
        page_size_attrs = _attr_map(page_size)
        page_size_twips = {
            side: int(page_size_attrs[side]) if page_size_attrs.get(side, "").isdigit() else None
            for side in ("w", "h")
        }
        margins = sect.find("./w:pgMar", NS)
        margin_attrs = _attr_map(margins)
        page_margins_twips = {
            side: int(margin_attrs[side]) if margin_attrs.get(side, "").isdigit() else None
            for side in ("top", "right", "bottom", "left")
        }
        page_margins = {
            side: _twips_to_inches(margin_attrs.get(side))
            for side in ("top", "right", "bottom", "left")
        }

    paragraphs: List[ParagraphModel] = []

    for index, para in enumerate(body_paragraphs):
        ppr_node = para.find("./w:pPr", NS)
        p_style = para.find("./w:pPr/w:pStyle", NS)
        style_name = _attr_map(p_style).get("val")
        style_ppr, style_rpr = _effective_style_props(defaults, styles, style_name)
        inline_ppr = _ppr_props(ppr_node)
        effective_ppr = _merge_ppr(style_ppr, inline_ppr)
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
                run_props = dict(style_rpr)
                paragraph_rpr = _rpr_props(para.find("./w:pPr/w:rPr", NS))
                run_props.update(paragraph_rpr)
                run_props.update(_rpr_props(rpr))
                runs.append(
                    RunModel(
                        text=run_text,
                        font=run_props.get("font"),
                        size_pt=run_props.get("size_pt"),
                        bold=bool(run_props.get("bold", False)),
                        italic=bool(run_props.get("italic", False)),
                    )
                )
        text = "".join(text_parts)
        normalized_for_spacing = re.sub(r" *\t *", "\t", text)
        stripped = text.lstrip(" ")
        leading_spaces = len(text) - len(stripped)
        raw_repeated_spaces = bool(re.search(r" {2,}", text))
        tab_space_padding = bool(re.search(r"(?: {2,}\t|\t {2,})", text))
        numbering = effective_ppr.get("numbering", {})
        numbering_id = numbering.get("numId")
        numbering_level_text = numbering.get("ilvl") or ("0" if numbering_id else None)
        numbering_level = (
            int(numbering_level_text)
            if numbering_level_text is not None and str(numbering_level_text).isdigit()
            else None
        )
        effective_indent = dict(effective_ppr.get("indent", {}))
        if numbering_id and numbering_level_text:
            effective_indent = _merge_dict(
                numbering_indents.get((numbering_id, numbering_level_text), {}),
                effective_indent,
            )
        has_ooxml_numbering = bool(numbering_id)
        has_unicode_bullet = text.lstrip().startswith(("• ", "● "))
        has_list_style = "list" in (style_name or "").lower()
        if has_ooxml_numbering:
            numbering_type = "ooxml"
        elif has_unicode_bullet:
            numbering_type = "unicode"
        elif has_list_style:
            numbering_type = "style"
        else:
            numbering_type = "none"

        paragraphs.append(
            ParagraphModel(
                index=index,
                text=text,
                style_name=style_name,
                alignment=effective_ppr.get("alignment"),
                is_blank=text.strip() == "",
                has_tabs=bool(para.findall("./w:r/w:tab", NS)),
                tab_stops=effective_ppr.get("tab_stops", []),
                borders=effective_ppr.get("borders", {}),
                runs=runs,
                numbering=numbering_type != "none",
                numbering_type=numbering_type,
                numbering_id=numbering_id,
                numbering_level=numbering_level,
                indent=effective_indent,
                spacing=effective_ppr.get("spacing", {}),
                leading_spaces=leading_spaces,
                repeated_spaces="  " in normalized_for_spacing.strip(),
                raw_repeated_spaces=raw_repeated_spaces,
                tab_space_padding=tab_space_padding,
            )
        )

    return DocumentModel(
        source_path=str(docx_path),
        paragraph_count=len(paragraphs),
        table_count=_xml_count(root, "tbl"),
        textbox_count=_xml_count(root, "txbxContent"),
        page_size_twips=page_size_twips,
        page_margins=page_margins,
        page_margins_twips=page_margins_twips,
        paragraphs=paragraphs,
    )
