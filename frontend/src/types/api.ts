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
  points?: number;
  message: string;
  evidence?: Record<string, unknown>;
}

export interface DocumentSummary {
  paragraph_count?: number;
  table_count?: number;
  textbox_count?: number;
  page_margins_inches?: Record<string, number>;
  detected_sections?: Array<{ name: string; paragraph_index: number }>;
  render_validation?: Record<string, unknown>;
}

export interface AnalyzeResult {
  rubric_version?: string;
  source_path?: string;
  score: number;
  visual_compliance_score?: number;
  structural_quality_score?: number;
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
}

export interface AnalyzePayload {
  status: string;
  audit_type: string;
  source: {
    filename: string;
    file_type: string;
  };
  result: AnalyzeResult;
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

