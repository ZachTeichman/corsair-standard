import { AlertTriangle, CircleCheck, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { severityCounts } from "../lib/utils";
import type { AnalyzePayload } from "../types/api";
import { Card } from "./ui/Card";

interface ScoreRingProps {
  payload: AnalyzePayload | null;
}

export function ScoreRing({ payload }: ScoreRingProps) {
  const result = payload?.result;
  const score = result?.score ?? 0;
  const counts = severityCounts(result?.violations ?? []);
  const structuralRisk = result?.structural_risk;
  const showStructuralWarning = structuralRisk && structuralRisk.level !== "ok";
  const status = !payload
    ? "No audit yet"
    : structuralRisk?.level === "critical"
      ? "Structural failure."
      : structuralRisk?.level === "warning" && structuralRisk.legacy_template_detected
        ? "Legacy template risk."
        : structuralRisk?.level === "warning"
          ? "Structure risk."
        : score >= 90
          ? "Strong foundation."
          : score >= 75
            ? "Needs focused cleanup."
            : "High-priority formatting risk.";

  return (
    <Card className="p-5 md:p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-corsair-bronze">Compliance score</p>
          <h2 className="mt-2 text-2xl font-semibold text-white light:text-corsair-ink">{status}</h2>
        </div>
        {showStructuralWarning ? (
          <AlertTriangle className="h-6 w-6 text-amber-300" />
        ) : score >= 90 ? (
          <CircleCheck className="h-6 w-6 text-emerald-300" />
        ) : (
          <ShieldCheck className="h-6 w-6 text-corsair-bronze" />
        )}
      </div>
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <div
          className="relative mx-auto grid h-48 w-48 place-items-center rounded-full"
          style={{
            background: `conic-gradient(#f1bd68 ${score * 3.6}deg, rgba(255,255,255,0.08) 0deg)`,
          }}
        >
          <div className="absolute inset-4 rounded-full bg-corsair-panel light:bg-corsair-ivory" />
          <div className="relative text-center">
            <div className="font-display text-6xl text-white light:text-corsair-ink">{payload ? score : "--"}</div>
            <div className="text-sm text-slate-400">/100</div>
          </div>
        </div>
        <div className="grid content-center gap-3">
          <Metric label="Visual" value={result?.visual_compliance_score ?? "--"} />
          <Metric label="Structure" value={result?.structural_quality_score ?? "--"} />
          {showStructuralWarning ? (
            <div className="rounded-2xl border border-amber-400/25 bg-amber-500/10 p-4 text-sm light:border-amber-700/25 light:bg-amber-100/70">
              <p className="font-semibold text-amber-100 light:text-amber-900">{structuralRisk.title}</p>
              <p className="mt-1 leading-6 text-amber-100/80 light:text-amber-950/75">{structuralRisk.message}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.16em] text-amber-200/80 light:text-amber-800">
                {structuralRisk.structural_issue_count} structural issue{structuralRisk.structural_issue_count === 1 ? "" : "s"}
                {result?.structural_penalty !== undefined ? ` / ${result.structural_penalty} point structure penalty` : ""}
              </p>
            </div>
          ) : null}
          <div className="mt-2 grid gap-2 rounded-2xl border border-white/10 bg-black/20 p-4 light:border-black/10 light:bg-black/[0.035]">
            <Severity icon={<AlertTriangle className="h-4 w-4" />} label="Critical" value={counts.critical} tone="bg-red-400" />
            <Severity label="Major" value={counts.major} tone="bg-amber-400" />
            <Severity label="Minor" value={counts.minor} tone="bg-slate-300" />
          </div>
        </div>
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.035] px-4 py-3 text-sm light:border-black/10 light:bg-white/80">
      <span className="text-slate-400 light:text-slate-600">{label} score</span>
      <strong className="font-mono text-lg text-white light:text-corsair-ink">{value}</strong>
    </div>
  );
}

function Severity({ icon, label, value, tone }: { icon?: ReactNode; label: string; value: number; tone: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="flex items-center gap-2 text-slate-300 light:text-slate-700">
        {icon ?? <span className={`h-2.5 w-2.5 rounded-full ${tone}`} />}
        {label}
      </span>
      <strong className="font-mono text-white light:text-corsair-ink">{value}</strong>
    </div>
  );
}
