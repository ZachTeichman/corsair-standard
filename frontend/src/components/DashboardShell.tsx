import { BookOpen, FileQuestion, Moon, Sun, UsersRound, Workflow } from "lucide-react";
import type { ReactNode } from "react";
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
  onHome: () => void;
}

export function DashboardShell({ payload, theme, onThemeChange, onAnalyzed, onHome }: DashboardShellProps) {
  const issueCount = payload?.result.violations.length ?? 0;
  const filename = payload?.source.filename ?? "No document selected";
  const candidateFirstName = payload?.result.document_summary?.candidate_name?.first_name?.trim();
  const greetingName = candidateFirstName || "there";
  const structuralRisk = payload?.result.structural_risk;
  const sourceCommentCount = payload?.annotation_summary?.source_comment_count ?? 0;
  const estimatedCommentCount = payload?.annotation_summary?.estimated_comment_count_without_focus ?? 0;
  const hasCommentOverload = sourceCommentCount > 20 || estimatedCommentCount > 20;
  const shouldRecommendCleanTemplate =
    hasCommentOverload || structuralRisk?.missing_canonical_structure || structuralRisk?.level === "critical";

  return (
    <div className="min-h-dvh bg-corsair-black text-white light:bg-corsair-ivory light:text-corsair-ink">
      <div className="grid min-h-dvh lg:grid-cols-[280px_1fr]">
        <aside className="border-b border-white/10 bg-black/30 p-5 backdrop-blur-xl light:border-black/10 light:bg-white/70 lg:border-b-0 lg:border-r">
          <div className="flex h-full flex-col">
            <button
              type="button"
              onClick={onHome}
              className="mb-8 flex items-center gap-3 text-left transition hover:text-corsair-gold"
              aria-label="Return to homepage"
            >
              <div className="grid h-12 w-12 place-items-center rounded-2xl border border-corsair-bronze/35 bg-corsair-bronze/10 text-corsair-gold">
                <Workflow className="h-6 w-6" />
              </div>
              <div className="font-semibold uppercase tracking-[0.18em]">
                Corsair
                <br />
                <span className="text-corsair-bronze">Standard</span>
              </div>
            </button>
            <nav className="grid gap-2" aria-label="Resource pages">
              <ResourceLink href="/why.html" icon={<FileQuestion className="h-5 w-5" />} label="Why this site" />
              <ResourceLink href="/formatting-guide.html" icon={<BookOpen className="h-5 w-5" />} label="Formatting guide" />
              <ResourceLink href="/club" icon={<UsersRound className="h-5 w-5" />} label="Club version" />
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
              <h1 className="mt-2 font-display text-4xl text-white light:text-corsair-ink md:text-5xl">
                Good evening, {greetingName}.
              </h1>
              <p className="mt-2 max-w-2xl text-slate-400 light:text-slate-600">
                {payload ? `${filename} has ${issueCount} formatting issue${issueCount === 1 ? "" : "s"} in the current audit.` : "Upload a Word resume to inspect formatting structure and generate an annotated DOCX."}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <a className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm font-semibold text-slate-200 transition hover:bg-white/[0.08] light:border-black/10 light:text-corsair-ink" href="/api/template/clean-docx">
                Download Template
              </a>
            </div>
          </header>

          {shouldRecommendCleanTemplate ? (
            <CleanTemplateNotice sourceCommentCount={sourceCommentCount} estimatedCommentCount={estimatedCommentCount} />
          ) : null}

          <div className="grid gap-5 xl:grid-cols-[minmax(440px,0.9fr)_minmax(560px,1.1fr)]">
            <section className="space-y-5">
              <ScoreRing payload={payload} />
              <div id="upload-section">
                <UploadPanel onAnalyzed={onAnalyzed} />
              </div>
              <IssueList payload={payload} />
            </section>
            <section id="dashboard-demo" className="space-y-5">
              <OfficePreview payload={payload} />
            </section>
          </div>
          <FooterLinks />
        </main>
      </div>
    </div>
  );
}

function CleanTemplateNotice({
  sourceCommentCount,
  estimatedCommentCount,
}: {
  sourceCommentCount: number;
  estimatedCommentCount: number;
}) {
  const commentCount = Math.max(sourceCommentCount, estimatedCommentCount);
  return (
    <div className="mb-6 rounded-2xl border border-corsair-bronze/35 bg-corsair-bronze/[0.08] p-4 shadow-bronze light:bg-white/80">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-corsair-bronze">
            Comment overload detected
          </p>
          <h2 className="mt-2 text-xl font-semibold text-white light:text-corsair-ink">
            Switch this resume into the clean Corsair template.
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300 light:text-slate-700">
            This audit would create {commentCount} Word comments without focused annotation. The dashboard still shows every issue,
            but the annotated DOCX only marks representative examples so it does not overload the document.
            The fastest fix is to move the content into the clean template, then run the audit again.
          </p>
        </div>
        <a
          className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-xl border border-corsair-gold/40 bg-gradient-to-br from-corsair-gold to-corsair-bronze px-4 py-2 text-sm font-bold text-black shadow-bronze transition hover:brightness-110"
          href="/api/template/clean-docx"
        >
          Download Clean Template
        </a>
      </div>
    </div>
  );
}

function ResourceLink({ href, icon, label }: { href: string; icon: ReactNode; label: string }) {
  return (
    <a
      href={href}
      className="flex min-h-12 items-center justify-between rounded-2xl border border-transparent px-4 text-sm font-semibold text-slate-400 transition hover:border-white/10 hover:bg-white/[0.04] hover:text-white light:text-slate-600 light:hover:text-corsair-ink"
    >
      <span className="flex items-center gap-3">
        {icon}
        {label}
      </span>
    </a>
  );
}

function FooterLinks() {
  return (
    <footer className="mt-8 flex flex-col gap-3 border-t border-white/10 pt-5 text-sm text-slate-500 light:border-black/10 light:text-slate-600 md:flex-row md:items-center md:justify-between">
      <span>&copy; 2026 Corsair Standard</span>
      <nav className="flex flex-wrap gap-4" aria-label="Legal links">
        <a className="font-semibold transition hover:text-corsair-gold" href="/privacy.html">Privacy</a>
        <a className="font-semibold transition hover:text-corsair-gold" href="/terms.html">Terms</a>
        <a className="font-semibold transition hover:text-corsair-gold" href="/security.html">Security</a>
      </nav>
    </footer>
  );
}
