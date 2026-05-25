import { ChevronDown, ExternalLink } from "lucide-react";
import { apiHref } from "../lib/api";
import { evidenceSummary, ruleTitle, severityTone } from "../lib/utils";
import type { DocumentLinks, Violation } from "../types/api";
import { LinkButton } from "./ui/Button";

interface IssueCardProps {
  violation: Violation;
  links?: DocumentLinks;
}

export function IssueCard({ violation, links }: IssueCardProps) {
  return (
    <article className="group rounded-2xl border border-white/10 bg-white/[0.035] p-4 transition hover:border-corsair-bronze/40 hover:bg-corsair-bronze/[0.06] light:border-black/10 light:bg-white/70">
      <div className="flex items-start gap-4">
        <span className={`mt-1 rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] ${severityTone(violation.severity)}`}>
          {violation.severity}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-white light:text-corsair-ink">{ruleTitle(violation.rule_id)}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-300 light:text-slate-700">{violation.message}</p>
          <p className="mt-2 text-xs text-slate-500 light:text-slate-500">{evidenceSummary(violation)}</p>
        </div>
        <ChevronDown className="mt-1 h-4 w-4 text-slate-500 transition group-hover:text-corsair-bronze" />
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-white/10 pt-3">
        <LinkButton
          href={apiHref(links?.office_viewer_open ?? links?.annotated_docx)}
          target="_blank"
          rel="noreferrer"
          className="min-h-9 rounded-lg px-3 py-1.5 text-xs"
        >
          Open in Viewer <ExternalLink className="h-3.5 w-3.5" />
        </LinkButton>
        <span className="text-xs text-slate-500">
          {(violation.points ?? 0) === 0 ? "Review only" : `${violation.points ?? 0} point impact`}
        </span>
      </div>
    </article>
  );
}
