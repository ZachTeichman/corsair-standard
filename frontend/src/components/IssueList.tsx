import { severityCounts } from "../lib/utils";
import type { AnalyzePayload } from "../types/api";
import { IssueCard } from "./IssueCard";
import { Card } from "./ui/Card";

interface IssueListProps {
  payload: AnalyzePayload | null;
}

export function IssueList({ payload }: IssueListProps) {
  const violations = payload?.result.violations ?? [];
  const counts = severityCounts(violations);

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap gap-2 border-b border-white/10 px-4 py-3">
        <Tab label="All Issues" value={violations.length} active />
        <Tab label="Critical" value={counts.critical} />
        <Tab label="Major" value={counts.major} />
        <Tab label="Minor" value={counts.minor} />
      </div>
      <div className="max-h-[620px] space-y-3 overflow-auto p-4">
        {violations.length ? (
          violations.map((violation, index) => (
            <IssueCard key={`${violation.rule_id}-${index}`} violation={violation} links={payload?.document_links} />
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-sm text-slate-400">
            Upload a DOCX to generate formatting suggestions and Word-native comments.
          </div>
        )}
      </div>
    </Card>
  );
}

function Tab({ label, value, active = false }: { label: string; value: number; active?: boolean }) {
  return (
    <span
      className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
        active ? "bg-corsair-bronze/15 text-corsair-gold" : "bg-white/[0.04] text-slate-400"
      }`}
    >
      {label} <strong className="ml-1">{value}</strong>
    </span>
  );
}

