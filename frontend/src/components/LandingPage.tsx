import { ArrowRight, FileCheck2, ShieldCheck, Sparkles } from "lucide-react";
import { LinkButton } from "./ui/Button";

interface LandingPageProps {
  onEnter: () => void;
}

export function LandingPage({ onEnter }: LandingPageProps) {
  return (
    <section className="relative min-h-dvh overflow-hidden bg-corsair-black text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_28%_22%,rgba(200,169,106,0.20),transparent_32%),radial-gradient(circle_at_78%_18%,rgba(180,29,58,0.12),transparent_28%),linear-gradient(135deg,#050708,#0b1015_55%,#11100d)]" />
      <div className="absolute inset-x-0 bottom-0 h-72 bg-gradient-to-t from-corsair-black to-transparent" />
      <nav className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl border border-corsair-bronze/35 bg-corsair-bronze/10 text-corsair-gold">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div className="font-semibold uppercase tracking-[0.18em]">
            Corsair
            <br />
            <span className="text-corsair-bronze">Standard</span>
          </div>
        </div>
        <button
          onClick={onEnter}
          className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-corsair-bronze/40 hover:text-white"
        >
          Open platform
        </button>
      </nav>
      <div className="relative z-10 mx-auto grid max-w-7xl gap-10 px-6 pb-20 pt-16 lg:grid-cols-[1fr_520px] lg:items-center lg:pt-28">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-corsair-bronze/30 bg-corsair-bronze/10 px-4 py-2 text-sm text-corsair-gold">
            <Sparkles className="h-4 w-4" />
            Deterministic DOCX compliance for finance recruiting resumes
          </div>
          <h1 className="mt-8 max-w-4xl font-display text-6xl leading-[0.95] tracking-tight text-white md:text-7xl lg:text-8xl">
            Format with precision. Submit with confidence.
          </h1>
          <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-300">
            Corsair Standard audits the Word formatting beneath the page: tab stops, spacing,
            margins, bullets, date logic, section structure, and typography. No ATS scoring.
            No candidate ranking. Just formatting compliance.
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            <button
              onClick={onEnter}
              className="inline-flex min-h-12 items-center gap-2 rounded-xl border border-corsair-gold/40 bg-gradient-to-br from-corsair-gold to-corsair-bronze px-5 py-3 text-sm font-bold text-black shadow-bronze transition hover:brightness-110"
            >
              Run compliance audit <ArrowRight className="h-4 w-4" />
            </button>
            <LinkButton href="/api/template/clean-docx">Download clean template</LinkButton>
          </div>
        </div>
        <div className="rounded-[2rem] border border-white/10 bg-white/[0.045] p-4 shadow-corsair backdrop-blur-xl">
          <div className="rounded-[1.5rem] border border-white/10 bg-corsair-panel p-5">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.22em] text-corsair-bronze">Audit preview</p>
                <h2 className="mt-1 text-xl font-semibold">Resume_Annotated.docx</h2>
              </div>
              <div className="rounded-full border border-corsair-bronze/30 px-3 py-1 text-sm text-corsair-gold">87 / 100</div>
            </div>
            <div className="space-y-3 rounded-2xl bg-[#f8f4ed] p-6 text-[#161412] shadow-2xl">
              <div className="mx-auto h-3 w-48 rounded-full bg-slate-800" />
              <div className="pt-4 text-center font-serif text-2xl font-bold">Student Name</div>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <span>Marietta, GA</span>
                <span className="text-center">(678) 200-6585</span>
                <span className="text-right">Athens, GA</span>
              </div>
              <PreviewLine title="EDUCATION" />
              <PreviewLine title="PROFESSIONAL EXPERIENCE" alert="Date tab stop" />
              <PreviewLine title="LEADERSHIP & RELEVANT EXPERIENCE" />
              <div className="rounded-xl border border-amber-300/80 bg-amber-100/60 p-3 text-sm text-amber-950">
                Word-native comments show exactly where formatting needs attention.
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function PreviewLine({ title, alert }: { title: string; alert?: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <strong className="text-sm">{title}</strong>
        <span className="h-px flex-1 bg-slate-800" />
        {alert ? <span className="rounded-full bg-red-100 px-2 py-1 text-xs font-semibold text-red-700">{alert}</span> : null}
      </div>
      <div className="space-y-1 pl-6">
        <div className="h-2 rounded-full bg-slate-300" />
        <div className="h-2 w-4/5 rounded-full bg-slate-300" />
      </div>
    </div>
  );
}

