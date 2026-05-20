export type Severity = "critical" | "major" | "minor";

export interface EvidenceParagraph {
  index?: number;
  text?: string;
  alignment?: string | null;
  style_name?: string | null;
}

export interface Violation {
  rule_id: string;
  severity: Severity;
  category?: string;
  points?: number;
  message: string;
  evidence?: Record<string, unknown>;
}

export interface DocumentSummary {
  paragraph_count?: number;
  table_count?: number;
  textbox_count?: number;
  page_margins_inches?: Record<string, number>;
  candidate_name?: {
    full_name: string;
    first_name: string;
  } | null;
  detected_sections?: Array<{ name: string; paragraph_index: number }>;
  render_validation?: Record<string, unknown>;
}

export interface AnalyzeResult {
  rubric_version?: string;
  source_path?: string;
  score: number;
  visual_compliance_score?: number;
  structural_quality_score?: number;
  structural_penalty?: number;
  visual_penalty?: number;
  structural_risk?: {
    level: "ok" | "notice" | "warning" | "critical";
    title: string;
    message: string;
    legacy_template_detected: boolean;
    missing_canonical_structure: boolean;
    structural_issue_count: number;
    legacy_rule_hits: string[];
  };
  total_penalty?: number;
  document_summary?: DocumentSummary;
  violations: Violation[];
}

export interface DocumentLinks {
  upload_id?: string;
  original_docx?: string;
  annotated_docx?: string;
  original_public_url?: string | null;
  annotated_public_url?: string | null;
  office_viewer_embed?: string | null;
  office_viewer_open?: string | null;
  office_viewer_source?: string;
  google_drive?: {
    provider: "google_drive";
    folder_id?: string | null;
    retention_hours?: number;
    error?: string;
    original?: {
      id?: string;
      name?: string;
      web_view_link?: string;
      web_content_link?: string;
      expires_at?: string;
    };
    annotated?: {
      id?: string;
      name?: string;
      web_view_link?: string;
      web_content_link?: string;
      expires_at?: string;
    };
  } | null;
}

export interface AnalyzePayload {
  status: string;
  audit_type: string;
  source: {
    filename: string;
    file_type: string;
  };
  result: AnalyzeResult;
  annotation_summary?: {
    mode: "focused";
    total_issues: number;
    comment_count: number;
    shown_issue_count: number;
    suppressed_count: number;
    max_comments: number;
    source_comment_count?: number;
    estimated_comment_count_without_focus?: number;
    suppressed_by_rule?: Record<string, number>;
  };
  document_links?: DocumentLinks;
}

export interface AuditHistoryItem {
  id: string;
  filename: string;
  createdAt: string;
  score: number;
  visualScore?: number;
  structuralScore?: number;
  violations: Violation[];
}
