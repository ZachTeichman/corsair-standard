import { BarChart3, FileArchive, LockKeyhole, ShieldCheck } from "lucide-react";

const clubFeatures = [
  {
    icon: <FileArchive className="h-5 w-5" />,
    title: "Batch PDF intake",
    body: "Designed for resume books and club review rounds where members submit PDFs instead of editable DOCX files.",
  },
  {
    icon: <BarChart3 className="h-5 w-5" />,
    title: "Visual score only",
    body: "A separate scoring mode focused on page polish, density, alignment, and visual consistency without candidate ranking.",
  },
  {
    icon: <LockKeyhole className="h-5 w-5" />,
    title: "Private club access",
    body: "The club portal will be gated so review tools are available only to approved organizations.",
  },
];

interface ClubComingSoonProps {
  onHome?: () => void;
  onAudit?: () => void;
  theme: "dark" | "light";
  onThemeChange: (theme: "dark" | "light") => void;
}

export function ClubComingSoon({ onHome, onAudit, theme, onThemeChange }: ClubComingSoonProps) {
  return (
    <main className="min-h-dvh bg-corsair-black text-white light:bg-corsair-ivory light:text-corsair-ink">
      <header className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-5 md:flex-row md:items-center md:justify-between md:px-8">
        <button
          type="button"
          onClick={onHome}
          className="text-left text-sm font-bold uppercase tracking-[0.2em] text-corsair-gold transition hover:text-corsair-bronze"
        >
          Corsair Standard
        </button>
        <nav className="flex flex-wrap items-center gap-3 text-sm font-semibold text-slate-400 light:text-slate-600">
          <button type="button" onClick={onAudit} className="transition hover:text-corsair-gold">
            Individual audit
          </button>
          <a className="transition hover:text-corsair-gold" href="/formatting-guide.html">
            Formatting guide
          </a>
          <div className="grid grid-cols-2 gap-1 rounded-full border border-white/10 bg-white/[0.04] p-1 light:border-black/10 light:bg-white/70">
            <button
              type="button"
              onClick={() => onThemeChange("light")}
              className={`rounded-full px-3 py-1.5 text-xs ${theme === "light" ? "bg-white text-corsair-ink shadow-sm" : ""}`}
            >
              Light
            </button>
            <button
              type="button"
              onClick={() => onThemeChange("dark")}
              className={`rounded-full px-3 py-1.5 text-xs ${theme === "dark" ? "bg-black text-corsair-gold shadow-sm" : ""}`}
            >
              Dark
            </button>
          </div>
        </nav>
      </header>

      <section className="mx-auto grid max-w-6xl gap-10 px-5 pb-16 pt-10 md:px-8 md:pb-24 md:pt-16 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-corsair-bronze/30 bg-corsair-bronze/[0.08] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.18em] text-corsair-gold light:text-corsair-bronze">
            <ShieldCheck className="h-4 w-4" />
            Club portal coming soon
          </div>
          <h1 className="mt-6 font-display text-5xl font-semibold leading-[0.95] text-white light:text-corsair-ink md:text-7xl">
            Batch visual scoring for recruiting clubs.
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-slate-400 light:text-slate-700 md:text-lg">
            This will be a private club workflow for uploading batches of PDF resumes and reviewing visual-only score summaries.
            It is separate from the individual DOCX compliance audit.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              disabled
              className="min-h-11 cursor-not-allowed rounded-xl border border-corsair-gold/35 bg-corsair-gold/20 px-5 py-2.5 text-sm font-bold text-corsair-gold opacity-80 light:text-corsair-bronze"
            >
              Club access not open yet
            </button>
            <button
              type="button"
              onClick={onAudit}
              className="inline-flex min-h-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] px-5 py-2.5 text-sm font-semibold text-slate-200 transition hover:bg-white/[0.08] light:border-black/10 light:bg-white/70 light:text-corsair-ink"
            >
              Use individual DOCX audit
            </button>
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-white/[0.035] p-4 light:border-black/10 light:bg-white/70 md:p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-corsair-bronze">Preview workflow</p>
              <h2 className="mt-1 text-xl font-semibold text-white light:text-corsair-ink">Private batch review lane</h2>
            </div>
            <span className="rounded-full border border-corsair-bronze/25 px-3 py-1 text-xs font-bold uppercase tracking-[0.12em] text-corsair-gold light:text-corsair-bronze">
              Locked
            </span>
          </div>
          <div className="grid gap-3">
          {clubFeatures.map((feature) => (
            <article
              key={feature.title}
              className="rounded-lg border border-white/10 bg-black/20 p-5 light:border-black/10 light:bg-white/80"
            >
              <div className="flex gap-4">
                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-corsair-bronze/25 bg-corsair-bronze/[0.08] text-corsair-gold light:text-corsair-bronze">
                  {feature.icon}
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white light:text-corsair-ink">{feature.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-400 light:text-slate-700">{feature.body}</p>
                </div>
              </div>
            </article>
          ))}
          </div>
        </div>
      </section>
    </main>
  );
}
