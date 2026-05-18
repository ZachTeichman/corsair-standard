import { Download, FileText, History, LayoutDashboard, Moon, Settings, Sun, Workflow } from "lucide-react";
import type { ReactElement } from "react";
import type { AnalyzePayload, AuditHistoryItem } from "../types/api";
import { IssueList } from "./IssueList";
import { OfficePreview } from "./OfficePreview";
import { ScoreRing } from "./ScoreRing";
import { UploadPanel } from "./UploadPanel";

interface DashboardShellProps {
  payload: AnalyzePayload | null;
  history: AuditHistoryItem[];
  theme: "dark" | "light";
  onThemeChange: (theme: "dark" | "light") => void;
  onAnalyzed: (payload: AnalyzePayload) => void;
}

export function DashboardShell({ payload, history, theme, onThemeChange, onAnalyzed }: DashboardShellProps) {
  const issueCount = payload?.result.violations.length ?? 0;
  const filename = payload?.source.filename ?? "No document selected";

  return (
    <div className="min-h-dvh bg-corsair-black text-white light:bg-corsair-ivory light:text-corsair-ink">
      <div className="grid min-h-dvh lg:grid-cols-[280px_1fr]">
        <aside className="border-b border-white/10 bg-black/30 p-5 backdrop-blur-xl light:border-black/10 light:bg-white/70 lg:border-b-0 lg:border-r">
          <div className="flex h-full flex-col">
            <div className="mb-8 flex items-center gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-2xl border border-corsair-bronze/35 bg-corsair-bronze/10 text-corsair-gold">
                <Workflow className="h-6 w-6" />
              </div>
              <div className="font-semibold uppercase tracking-[0.18em]">
                Corsair
                <br />
                <span className="text-corsair-bronze">Standard</span>
              </div>
            </div>
            <nav className="grid gap-2">
              <NavItem icon={<LayoutDashboard />} label="Overview" active />
              <NavItem icon={<FileText />} label="Issues" badge={issueCount} />
              <NavItem icon={<Workflow />} label="Structure" badge="soon" />
              <NavItem icon={<History />} label="Score History" badge={history.length || undefined} />
              <NavItem icon={<Download />} label="Documents" />
              <NavItem icon={<Settings />} label="Settings" disabled />
            </nav>
            <div className="mt-auto space-y-4 pt-8">
              <a
                href="/api/template/clean-docx"
                className="block rounded-2xl border border-corsair-bronze/25 bg-corsair-bronze/[0.08] p-4 text-sm transition hover:border-corsair-bronze/50"
              >
                <strong className="text-corsair-gold">Clean template</strong>
                <span className="mt-1 block text-slate-400 light:text-slate-600">
                  Start from the stable Corsair formatting document.
                </span>
              </a>
              <div className="grid grid-cols-2 gap-2 rounded-2xl border border-white/10 bg-white/[0.04] p-1 light:border-black/10">
                <button
                  onClick={() => onThemeChange("light")}
                  className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm ${theme === "light" ? "bg-white text-corsair-ink" : "text-slate-400"}`}
                >
                  <Sun className="h-4 w-4" /> Light
                </button>
                <button
                  onClick={() => onThemeChange("dark")}
                  className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm ${theme === "dark" ? "bg-black text-corsair-gold" : "text-slate-500"}`}
                >
                  <Moon className="h-4 w-4" /> Dark
                </button>
              </div>
            </div>
          </div>
        </aside>

        <main className="p-4 md:p-6 xl:p-8">
          <header className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.24em] text-corsair-bronze">Deterministic formatting compliance</p>
              <h1 className="mt-2 font-display text-4xl text-white light:text-corsair-ink md:text-5xl">Good evening, Zach.</h1>
              <p className="mt-2 max-w-2xl text-slate-400 light:text-slate-600">
                {payload ? `${filename} has ${issueCount} formatting issue${issueCount === 1 ? "" : "s"} in the current audit.` : "Upload a Word resume to inspect formatting structure and generate an annotated DOCX."}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <a className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm font-semibold text-slate-200 transition hover:bg-white/[0.08] light:border-black/10 light:text-corsair-ink" href="/api/template/clean-docx">
                Download Template
              </a>
              <a className="rounded-xl border border-corsair-gold/40 bg-gradient-to-br from-corsair-gold to-corsair-bronze px-4 py-3 text-sm font-bold text-black shadow-bronze transition hover:brightness-110" href={payload?.document_links?.office_viewer_open ?? "#"} target="_blank" rel="noreferrer">
                Open in Viewer
              </a>
            </div>
          </header>

          <div className="grid gap-5 xl:grid-cols-[minmax(440px,0.9fr)_minmax(560px,1.1fr)]">
            <section className="space-y-5">
              <ScoreRing payload={payload} />
              <UploadPanel onAnalyzed={onAnalyzed} />
              <IssueList payload={payload} />
            </section>
            <section className="space-y-5">
              <OfficePreview payload={payload} />
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-400 light:border-black/10 light:bg-white/70 light:text-slate-600">
                <strong className="text-corsair-gold">Structure View</strong> is staged for future DOCX formatting-mark visualization. The current source of truth is the analyzer output plus Word-native comments.
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}

function NavItem({ icon, label, active, badge, disabled }: { icon: ReactElement; label: string; active?: boolean; badge?: number | string; disabled?: boolean }) {
  return (
    <button
      disabled={disabled}
      className={`flex min-h-12 items-center justify-between rounded-2xl border px-4 text-sm font-semibold transition ${
        active
          ? "border-corsair-bronze/30 bg-corsair-bronze/10 text-corsair-gold"
          : "border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-white light:text-slate-600"
      } disabled:cursor-not-allowed disabled:opacity-40`}
    >
      <span className="flex items-center gap-3">
        {icon}
        {label}
      </span>
      {badge !== undefined ? <span className="rounded-full bg-white/[0.06] px-2 py-1 text-xs">{badge}</span> : null}
    </button>
  );
}
