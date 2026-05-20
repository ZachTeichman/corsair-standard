import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Severity, Violation } from "../types/api";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function severityCounts(violations: Violation[]) {
  return violations.reduce(
    (counts, violation) => {
      counts[violation.severity] += 1;
      return counts;
    },
    { critical: 0, major: 0, minor: 0 } satisfies Record<Severity, number>,
  );
}

export function severityTone(severity: Severity) {
  if (severity === "critical") {
    return "text-red-100 bg-red-500/20 border-red-400/40 light:text-red-800 light:bg-red-50 light:border-red-300";
  }
  if (severity === "major") {
    return "text-amber-100 bg-amber-500/20 border-amber-400/40 light:text-amber-900 light:bg-amber-100 light:border-amber-300";
  }
  return "text-slate-100 bg-slate-500/20 border-slate-300/25 light:text-slate-700 light:bg-slate-100 light:border-slate-300";
}

export function ruleTitle(ruleId: string) {
  const labels: Record<string, string> = {
    "document.margin_range": "Margins out of range",
    "document.one_page_rendered": "Document exceeds one page",
    "layout.no_tables": "Layout tables detected",
    "layout.no_textboxes": "Text boxes detected",
    "header.name_centered_top_line": "Name placement is not stable",
    "header.dual_address": "Header address pattern is incomplete",
    "header.address_line_integrity": "Header address line is malformed",
    "header.contact_single_row": "Contact row is not structurally stable",
    "header.contact_spacing_hack": "Header uses manual spacing",
    "section.corsair_structure_detected": "Corsair structure not detected",
    "section.required_presence": "Required section missing",
    "section.order": "Sections out of order",
    "section.label_spelling": "Section label spelling issue",
    "section.labels_all_caps": "Section label is not all caps",
    "section.headers_bold": "Section header is not bold",
    "section.divider_rule": "Section divider rule missing",
    "section.reverse_chronological_order": "Section entries are out of order",
    "entry.date_right_tab": "Date does not use a right tab",
    "entry.date_range_en_dash": "Date range should use an en dash",
    "entry.date_range_valid": "Date range does not make sense",
    "entry.date_alignment_spacing_hack": "Date alignment uses manual spacing",
    "entry.organization_bold": "Organization name is not bold",
    "entry.role_italic": "Role/title is not italicized",
    "entry.location_present": "Entry location is missing",
    "paragraph.no_consecutive_blank_lines": "Extra blank line",
    "paragraph.no_leading_spaces": "Leading spaces used as indentation",
    "paragraph.no_manual_alignment_spaces": "Manual spaces used for alignment",
    "paragraph.tab_space_alignment_hacks": "Tabs mixed with spaces",
    "paragraph.excessive_alignment_tabs": "Too many alignment tabs",
    "paragraph.tabs_require_defined_stops": "Tab lacks a defined stop",
    "paragraph.right_tab_consistency": "Right tab positions are inconsistent",
    "paragraph.body_alignment_consistency": "Numbered bullet is justified",
    "bullet.indent_consistency": "Bullet indent differs from template",
    "typography.single_font_family": "Font family is inconsistent",
    "typography.body_font_size_consistency": "Body font size inconsistent",
    "typography.no_unauthorized_inline_emphasis": "Unexpected inline emphasis",
  };
  return labels[ruleId] ?? ruleId;
}

export function evidenceSummary(violation: Violation) {
  const evidence = violation.evidence ?? {};
  const paragraph = evidence.paragraph as { index?: number; text?: string } | undefined;
  const paragraphs = evidence.paragraphs as Array<{
    index?: number;
    text?: string;
    bullet_position_inches?: number;
    text_indent_inches?: number;
    alignment?: string | null;
    expected_alignment?: string;
  }> | undefined;
  const first = (paragraph ?? paragraphs?.[0]) as
    | {
        index?: number;
        text?: string;
        bullet_position_inches?: number;
        text_indent_inches?: number;
        alignment?: string | null;
        expected_alignment?: string;
      }
    | undefined;
  if (violation.rule_id === "paragraph.body_alignment_consistency" && first?.index !== undefined) {
    const found = first.alignment === "both" ? "Justify" : (first.alignment ?? "unknown");
    const expected = first.expected_alignment ?? (evidence.expected_alignment as string | undefined) ?? "left";
    return `Paragraph ${first.index}: alignment is ${found}; expected ${expected.charAt(0).toUpperCase()}${expected.slice(1)}`;
  }
  if (violation.rule_id === "bullet.indent_consistency" && first?.index !== undefined) {
    const expected = evidence.expected as { bullet_position_inches?: number; text_indent_inches?: number } | undefined;
    const foundBullet = typeof first.bullet_position_inches === "number" ? `${first.bullet_position_inches.toFixed(2)}in` : "unknown";
    const foundText = typeof first.text_indent_inches === "number" ? `${first.text_indent_inches.toFixed(2)}in` : "unknown";
    const expectedBullet = typeof expected?.bullet_position_inches === "number" ? `${expected.bullet_position_inches.toFixed(2)}in` : "0.25in";
    const expectedText = typeof expected?.text_indent_inches === "number" ? `${expected.text_indent_inches.toFixed(2)}in` : "0.50in";
    return `Paragraph ${first.index}: bullet at ${foundBullet} vs ${expectedBullet}; text starts at ${foundText} vs ${expectedText}`;
  }
  if (first?.index !== undefined) {
    return `Paragraph ${first.index}${first.text ? `: ${first.text.slice(0, 92)}` : ""}`;
  }
  if (Array.isArray(paragraphs) && paragraphs.length > 0) {
    return `${paragraphs.length} paragraphs affected`;
  }
  return "Document-level issue";
}
