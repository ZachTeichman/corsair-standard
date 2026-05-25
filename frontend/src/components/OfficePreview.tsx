import { Download, ExternalLink, Eye } from "lucide-react";
import { apiHref } from "../lib/api";
import type { AnalyzePayload } from "../types/api";
import { Button, LinkButton } from "./ui/Button";
import { Card } from "./ui/Card";

interface OfficePreviewProps {
  payload: AnalyzePayload | null;
}

export function OfficePreview({ payload }: OfficePreviewProps) {
  const annotated = payload?.document_links?.annotated_docx;
  const drive = payload?.document_links?.google_drive;
  const driveAnnotated = drive?.annotated?.web_view_link;
  const driveAnnotatedId = drive?.annotated?.id;
  const drivePreview = driveAnnotatedId ? `https://drive.google.com/file/d/${driveAnnotatedId}/preview` : null;
  const embed = payload?.document_links?.office_viewer_embed ?? drivePreview;
  const microsoftPreview = payload?.document_links?.office_viewer_open;
  const filename = payload?.source.filename ?? "Annotated DOCX";
  const annotation = payload?.annotation_summary;

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3 light:border-black/10">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-corsair-bronze">Word preview</p>
          <h2 className="mt-1 truncate text-lg font-semibold text-white light:text-corsair-ink">{filename}</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {driveAnnotated ? (
            <LinkButton href={driveAnnotated} target="_blank" rel="noreferrer" variant="primary" className="min-h-9 rounded-lg px-3 py-1.5 text-xs">
              <ExternalLink className="h-4 w-4" /> Open in Google Drive
            </LinkButton>
          ) : (
            <Button disabled className="min-h-9 rounded-lg px-3 py-1.5 text-xs">
              <ExternalLink className="h-4 w-4" /> Open in Google Drive
            </Button>
          )}
          {microsoftPreview ? (
            <LinkButton href={microsoftPreview} target="_blank" rel="noreferrer" className="min-h-9 rounded-lg px-3 py-1.5 text-xs">
              <Eye className="h-4 w-4" /> Preview in Microsoft Office
            </LinkButton>
          ) : (
            <Button disabled className="min-h-9 rounded-lg px-3 py-1.5 text-xs">
              <Eye className="h-4 w-4" /> Preview in Microsoft Office
            </Button>
          )}
          <LinkButton href={apiHref(annotated)} className="min-h-9 rounded-lg px-3 py-1.5 text-xs">
            <Download className="h-4 w-4" /> Download annotated DOCX
          </LinkButton>
        </div>
      </div>
      {drive?.error ? (
        <div className="border-b border-amber-400/20 bg-amber-500/10 px-4 py-2 text-xs text-amber-200 light:text-amber-800">
          Google Drive storage is configured but not active yet: {drive.error}
        </div>
      ) : drive?.status === "pending" ? (
        <div className="border-b border-corsair-bronze/20 bg-corsair-bronze/[0.08] px-4 py-2 text-xs text-corsair-gold light:text-corsair-bronze">
          Audit complete. Google Drive storage is finishing in the background; local DOCX downloads are ready now.
        </div>
      ) : drive?.status === "disabled" ? (
        <div className="border-b border-white/10 bg-white/[0.04] px-4 py-2 text-xs text-slate-400 light:border-black/10 light:text-slate-600">
          Google Drive storage is disabled for this environment. Local DOCX downloads are ready.
        </div>
      ) : driveAnnotated ? (
        <div className="border-b border-corsair-bronze/20 bg-corsair-bronze/[0.08] px-4 py-2 text-xs text-corsair-gold light:text-corsair-bronze">
          Stored in Google Drive for {drive?.retention_hours ?? 24} hours.
        </div>
      ) : null}
      {annotation && annotation.suppressed_count > 0 ? (
        <div className="border-b border-corsair-bronze/20 bg-corsair-bronze/[0.08] px-4 py-2 text-xs leading-5 text-slate-300 light:text-slate-700">
          Focused annotation: showing {annotation.shown_issue_count} representative DOCX comments and summarizing{" "}
          {annotation.suppressed_count} repeated issues in the dashboard. For noisy structure problems, the clean template is the fastest reset.
        </div>
      ) : null}
      <div className="bg-black/35 p-3 light:bg-corsair-ivory/70">
        {embed ? (
          <iframe
            title={drivePreview ? "Google Drive annotated resume preview" : "Microsoft Office annotated resume preview"}
            className="h-[72vh] min-h-[620px] w-full rounded-xl border border-white/10 bg-white"
            src={embed}
          />
        ) : (
          <div className="grid h-[620px] place-items-center rounded-xl border border-dashed border-white/10 bg-corsair-black/70 p-8 text-center light:border-black/10 light:bg-white/70">
            <div className="max-w-sm">
              <p className="text-xs font-bold uppercase tracking-[0.22em] text-corsair-bronze">Preview pending</p>
              <h3 className="mt-3 text-3xl font-semibold text-white light:text-corsair-ink">Upload a DOCX</h3>
              <p className="mt-3 text-sm leading-6 text-slate-400 light:text-slate-600">
                The preview uses Google Drive storage when available, then Microsoft Office Viewer when
                the backend has a public URL. The annotated DOCX still downloads locally.
              </p>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
