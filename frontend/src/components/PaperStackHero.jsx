import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useAnimation } from "framer-motion";

function Sk({ w = "100%", h = 7, dark = false, gold = false, mb = 6 }) {
  return (
    <div
      style={{
        height: h,
        width: w,
        borderRadius: 3,
        marginBottom: mb,
        flexShrink: 0,
        background: gold
          ? "rgba(180,130,50,0.42)"
          : dark
            ? "rgba(0,0,0,0.28)"
            : "rgba(0,0,0,0.13)",
      }}
    />
  );
}

function SkRow({ left, right }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
      <div style={{ height: 8, width: left, borderRadius: 3, background: "rgba(0,0,0,0.24)" }} />
      <div style={{ height: 8, width: right, borderRadius: 3, background: "rgba(0,0,0,0.13)" }} />
    </div>
  );
}

function SkRule() {
  return <div style={{ height: 1, background: "rgba(0,0,0,0.16)", margin: "10px 0 9px" }} />;
}

function SkSection() {
  return <div style={{ height: 8, width: "36%", borderRadius: 3, background: "rgba(120,80,30,0.48)", marginBottom: 9 }} />;
}

function ResumeContent() {
  return (
    <>
      <Sk w="42%" h={13} dark mb={14} />
      <Sk w="60%" gold mb={10} />
      <SkRule />
      <SkSection />
      <SkRow left="60%" right="22%" />
      <Sk w="100%" mb={5} />
      <Sk w="88%" mb={5} />
      <Sk w="74%" mb={5} />
      <Sk w="92%" mb={5} />
      <SkRule />
      <SkSection />
      <SkRow left="56%" right="24%" />
      <Sk w="100%" mb={5} />
      <Sk w="80%" mb={5} />
      <Sk w="94%" mb={5} />
      <Sk w="68%" mb={5} />
      <SkRule />
      <SkSection />
      <Sk w="100%" mb={5} />
      <Sk w="84%" mb={5} />
      <Sk w="58%" mb={0} />
    </>
  );
}

function Paper({ ctrl, initialState, zIndex, bg, glowActive = false, children }) {
  return (
    <motion.div
      animate={ctrl}
      initial={initialState}
      className="paper-stack-hero__paper"
      style={{
        position: "absolute",
        borderRadius: 5,
        background: bg,
        zIndex,
        boxShadow: glowActive
          ? "0 0 0 2.5px rgba(215,168,94,0.95), 0 0 40px rgba(215,168,94,0.4), 0 12px 50px rgba(0,0,0,0.5)"
          : "0 10px 50px rgba(0,0,0,0.55), 0 3px 10px rgba(0,0,0,0.35)",
        transition: "box-shadow 0.45s ease",
      }}
    >
      <ResumeContent />
      {children}
    </motion.div>
  );
}

function GridLines({ visible }) {
  const hLines = [
    { top: "20%", label: "R1" },
    { top: "44%", label: "R2" },
    { top: "68%", label: "R3" },
  ];
  const vLines = [{ left: "10%" }, { left: "90%" }];

  return (
    <AnimatePresence>
      {visible && (
        <>
          {hLines.map((l, i) => (
            <motion.div
              key={`h${i}`}
              initial={{ opacity: 0, scaleX: 0 }}
              animate={{ opacity: 1, scaleX: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18, delay: i * 0.04, ease: "easeOut" }}
              style={{
                position: "absolute",
                height: 1,
                width: "100%",
                left: 0,
                top: l.top,
                background: "rgba(215,168,94,0.6)",
                transformOrigin: "left center",
                zIndex: 20,
                pointerEvents: "none",
              }}
            >
              <span
                style={{
                  position: "absolute",
                  right: 6,
                  top: -14,
                  fontSize: 9,
                  color: "rgba(215,168,94,0.85)",
                  fontFamily: "ui-monospace, monospace",
                  letterSpacing: "0.04em",
                }}
              >
                {l.label}
              </span>
            </motion.div>
          ))}
          {vLines.map((l, i) => (
            <motion.div
              key={`v${i}`}
              initial={{ opacity: 0, scaleY: 0 }}
              animate={{ opacity: 1, scaleY: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18, delay: 0.08 + i * 0.04, ease: "easeOut" }}
              style={{
                position: "absolute",
                width: 1,
                height: "100%",
                top: 0,
                left: l.left,
                background: "rgba(215,168,94,0.45)",
                transformOrigin: "center top",
                zIndex: 20,
                pointerEvents: "none",
              }}
            />
          ))}
        </>
      )}
    </AnimatePresence>
  );
}

function CheckBadge({ visible }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ scale: 0.3, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.3, opacity: 0 }}
          transition={{ duration: 0.42, ease: [0.34, 1.56, 0.64, 1] }}
          style={{
            position: "absolute",
            top: -22,
            right: -22,
            width: 52,
            height: 52,
            borderRadius: "50%",
            background: "linear-gradient(135deg,#f0bd6d,#aa6f2c)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 24px rgba(215,168,94,0.65)",
            zIndex: 40,
          }}
        >
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
            <motion.path
              d="M4 11.5L9 16.5L18 6.5"
              stroke="#140e07"
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.38, delay: 0.18, ease: "easeOut" }}
            />
          </svg>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function StageLabel({ label }) {
  return (
    <AnimatePresence mode="wait">
      <motion.span
        key={label}
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.28 }}
        style={{
          position: "absolute",
          bottom: -32,
          left: 0,
          fontSize: 10,
          color: "rgba(215,168,94,0.5)",
          fontFamily: "ui-monospace, monospace",
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </motion.span>
    </AnimatePresence>
  );
}

const FAN = [
  { x: 0, y: 0, r: 0, s: 1 },
  { x: 44, y: -36, r: 14, s: 0.97 },
  { x: -52, y: -24, r: -17, s: 0.95 },
  { x: 80, y: 14, r: 24, s: 0.93 },
  { x: -88, y: 22, r: -26, s: 0.91 },
];

const STAGES = {
  idle: "01  Incoming resumes",
  spread: "02  Analyzing structure",
  grid: "03  Aligning formatting",
  converge: "04  Resolving inconsistencies",
  final: "05  Compliance achieved",
  glow: "06  Ready to submit",
};

export default function PaperStackHero({ onRunAudit, theme = "dark", onThemeChange }) {
  const [phase, setPhase] = useState("idle");
  const [gridOn, setGridOn] = useState(false);
  const [checkOn, setCheckOn] = useState(false);
  const [glow, setGlow] = useState(false);
  const cancelRef = useRef(false);
  const isLight = theme === "light";

  const [c1, c2, c3, c4, c5] = [useAnimation(), useAnimation(), useAnimation(), useAnimation(), useAnimation()];
  const ctrls = [c1, c2, c3, c4, c5];

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  const snap = (i, extra = {}) =>
    ctrls[i].start({
      x: FAN[i].x,
      y: FAN[i].y,
      rotate: FAN[i].r,
      scale: FAN[i].s,
      opacity: 1,
      transition: { duration: 0.01 },
      ...extra,
    });

  const go = async () => {
    cancelRef.current = false;

    setPhase("idle");
    const floatLoop = (ctrl, baseY, amp, period, offset) => {
      let running = true;
      const loop = async () => {
        await wait(offset);
        while (running && !cancelRef.current) {
          await ctrl.start({ y: baseY - amp, transition: { duration: period / 2, ease: "easeInOut" } });
          if (!running || cancelRef.current) break;
          await ctrl.start({ y: baseY + amp, transition: { duration: period / 2, ease: "easeInOut" } });
        }
      };
      void loop();
      return () => {
        running = false;
      };
    };
    const stops = [
      floatLoop(c1, FAN[0].y, 5, 2.6, 0),
      floatLoop(c2, FAN[1].y, 4, 2.9, 320),
      floatLoop(c3, FAN[2].y, 6, 2.4, 640),
      floatLoop(c4, FAN[3].y, 4, 3.1, 180),
      floatLoop(c5, FAN[4].y, 5, 2.7, 500),
    ];

    await wait(1800);
    cancelRef.current = true;
    stops.forEach((s) => s());
    await wait(150);
    cancelRef.current = false;

    setPhase("spread");
    await Promise.all([
      c1.start({ x: 0, y: 12, rotate: 0, scale: 1, opacity: 1, transition: { duration: 0.44, ease: [0.4, 0, 0.6, 1] } }),
      c2.start({ x: 90, y: -56, rotate: 20, scale: 0.96, opacity: 1, transition: { duration: 0.46, ease: [0.4, 0, 0.6, 1] } }),
      c3.start({ x: -100, y: -34, rotate: -22, scale: 0.94, opacity: 1, transition: { duration: 0.48, ease: [0.4, 0, 0.6, 1] } }),
      c4.start({ x: 140, y: 22, rotate: 30, scale: 0.92, opacity: 1, transition: { duration: 0.5, ease: [0.4, 0, 0.6, 1] } }),
      c5.start({ x: -150, y: 34, rotate: -32, scale: 0.9, opacity: 1, transition: { duration: 0.52, ease: [0.4, 0, 0.6, 1] } }),
    ]);
    await wait(260);

    setPhase("grid");
    setGridOn(true);
    await Promise.all([
      c1.start({ x: 0, y: 2, rotate: 0, transition: { duration: 0.34, ease: [0.4, 0, 0.6, 1] } }),
      c2.start({ x: 22, y: -16, rotate: 5, transition: { duration: 0.34, ease: [0.4, 0, 0.6, 1] } }),
      c3.start({ x: -24, y: -10, rotate: -6, transition: { duration: 0.36, ease: [0.4, 0, 0.6, 1] } }),
      c4.start({ x: 38, y: 8, rotate: 8, transition: { duration: 0.38, ease: [0.4, 0, 0.6, 1] } }),
      c5.start({ x: -40, y: 12, rotate: -9, transition: { duration: 0.4, ease: [0.4, 0, 0.6, 1] } }),
    ]);
    await wait(80);
    setGridOn(false);

    setPhase("converge");
    await Promise.all([
      c1.start({ x: 0, y: 0, rotate: 0, scale: 1, transition: { duration: 0.38, ease: [0.34, 1.56, 0.64, 1] } }),
      c2.start({ x: 3, y: 4, rotate: 1.5, scale: 0.98, transition: { duration: 0.38, ease: [0.34, 1.56, 0.64, 1] } }),
      c3.start({ x: -3, y: 6, rotate: -1.5, scale: 0.97, transition: { duration: 0.4, ease: [0.34, 1.56, 0.64, 1] } }),
      c4.start({ x: 5, y: 8, rotate: 2, scale: 0.96, transition: { duration: 0.42, ease: [0.34, 1.56, 0.64, 1] } }),
      c5.start({ x: -5, y: 10, rotate: -2, scale: 0.95, transition: { duration: 0.44, ease: [0.34, 1.56, 0.64, 1] } }),
    ]);
    await wait(180);

    setPhase("final");
    await Promise.all([
      c2.start({ opacity: 0, y: -10, scale: 0.96, transition: { duration: 0.24, ease: "easeIn" } }),
      c3.start({ opacity: 0, y: -14, scale: 0.94, transition: { duration: 0.24, ease: "easeIn" } }),
      c4.start({ opacity: 0, y: -18, scale: 0.93, transition: { duration: 0.26, ease: "easeIn" } }),
      c5.start({ opacity: 0, y: -22, scale: 0.91, transition: { duration: 0.26, ease: "easeIn" } }),
    ]);
    await c1.start({ scale: 1.018, transition: { duration: 0.15, ease: "easeOut" } });
    await c1.start({ scale: 1, transition: { duration: 0.16, ease: "easeOut" } });
    setCheckOn(true);
    await wait(550);

    setPhase("glow");
    setGlow(true);
    cancelRef.current = false;
    while (!cancelRef.current) {
      await c1.start({ y: -7, transition: { duration: 2.5, ease: "easeInOut" } });
      if (cancelRef.current) break;
      await c1.start({ y: 0, transition: { duration: 2.5, ease: "easeInOut" } });
    }
  };

  const reset = async () => {
    cancelRef.current = true;
    await wait(120);
    setCheckOn(false);
    setGlow(false);
    setGridOn(false);
    await Promise.all(FAN.map((_, i) => snap(i)));
    await wait(400);
    void go();
  };

  useEffect(() => {
    FAN.forEach((f, i) => ctrls[i].set({ x: f.x, y: f.y, rotate: f.r, scale: f.s, opacity: 1 }));
    void go();
    const t = setTimeout(reset, 8000);
    return () => {
      cancelRef.current = true;
      clearTimeout(t);
    };
  }, []);

  return (
    <section className={`paper-stack-hero ${isLight ? "is-light" : "is-dark"}`} aria-label="Corsair Standard homepage hero">
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          background: isLight
            ? "radial-gradient(ellipse 58% 52% at 18% 52%, rgba(196,141,61,0.18), transparent), radial-gradient(ellipse 42% 52% at 86% 20%, rgba(30,44,56,0.09), transparent)"
            : "radial-gradient(ellipse 60% 55% at 18% 52%, rgba(159,113,59,0.15), transparent), radial-gradient(ellipse 45% 60% at 84% 24%, rgba(55,77,95,0.11), transparent)",
        }}
      />

      <div className="paper-stack-hero__theme-toggle" aria-label="Homepage color theme">
        <button
          type="button"
          onClick={() => onThemeChange?.("light")}
          className={isLight ? "is-active" : ""}
        >
          Light
        </button>
        <button
          type="button"
          onClick={() => onThemeChange?.("dark")}
          className={!isLight ? "is-active" : ""}
        >
          Dark
        </button>
      </div>

      <div className="paper-stack-hero__copy">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "5px 13px",
            border: isLight ? "1px solid rgba(128,82,31,0.24)" : "1px solid rgba(215,168,94,0.28)",
            borderRadius: 999,
            background: isLight ? "rgba(128,82,31,0.08)" : "rgba(215,168,94,0.07)",
            color: isLight ? "#6f4319" : "#f6d7a3",
            fontSize: 11,
            fontWeight: 500,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            marginBottom: 28,
          }}
        >
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: isLight ? "#9d6424" : "#ffd28a", boxShadow: "0 0 10px rgba(184,124,44,0.55)" }} />
          Deterministic DOCX compliance for finance recruiting resumes
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.65, ease: [0.4, 0, 0.2, 1] }}
          className="paper-stack-hero__title"
        >
          <span className="paper-stack-hero__title-accent">
            Format with
            <br />
            precision.
          </span>
          <br />
          Submit with
          <br />
          confidence.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.38, duration: 0.65 }}
          style={{ maxWidth: 420, color: isLight ? "rgba(38,30,22,0.68)" : "rgba(246,242,234,0.56)", fontSize: 15, lineHeight: 1.68, marginBottom: 34 }}
        >
          Corsair Standard audits the Word formatting beneath the page: tab stops, spacing,
          margins, bullets, date logic, section structure, and typography. No ATS scoring.
          No candidate ranking. Just formatting compliance.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.52, duration: 0.65 }}
          className="paper-stack-hero__actions"
        >
          <motion.button
            type="button"
            onClick={onRunAudit}
            animate={{ background: "linear-gradient(135deg,#f0bd6d,#aa6f2c)", color: "#140e07" }}
            transition={{ duration: 0.3 }}
            aria-label="Run compliance audit"
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48,
              padding: "13px 22px",
              borderRadius: 8,
              border: "1px solid rgba(255,210,138,0.52)",
              fontSize: 14,
              fontWeight: 600,
              textDecoration: "none",
              whiteSpace: "nowrap",
              cursor: "pointer",
            }}
          >
            Run compliance audit &rarr;
          </motion.button>
          <a
            href="/api/template/clean-docx"
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 48,
              padding: "13px 20px",
              borderRadius: 8,
              border: isLight ? "1px solid rgba(110,71,29,0.18)" : "1px solid rgba(215,168,94,0.18)",
              background: isLight ? "rgba(255,255,255,0.62)" : "rgba(255,255,255,0.04)",
              color: isLight ? "#21170f" : "#f6f2ea",
              fontSize: 14,
              fontWeight: 400,
              textDecoration: "none",
              cursor: "pointer",
            }}
          >
            Download clean template
          </a>
          <a
            href="/club"
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 48,
              padding: "13px 20px",
              borderRadius: 8,
              border: isLight ? "1px solid rgba(110,71,29,0.18)" : "1px solid rgba(215,168,94,0.18)",
              background: isLight ? "rgba(255,255,255,0.42)" : "rgba(255,255,255,0.025)",
              color: isLight ? "#4b321e" : "#d9c7aa",
              fontSize: 14,
              fontWeight: 400,
              textDecoration: "none",
              cursor: "pointer",
            }}
          >
            Club batch scoring
          </a>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.28, duration: 0.8 }}
        className="paper-stack-hero__visual"
      >
        <div className="paper-stack-hero__stage">
          <GridLines visible={gridOn} />

          <Paper ctrl={c5} initialState={{ x: FAN[4].x, y: FAN[4].y, rotate: FAN[4].r, scale: FAN[4].s, opacity: 1 }} zIndex={1} bg="#d8d3c8" />
          <Paper ctrl={c4} initialState={{ x: FAN[3].x, y: FAN[3].y, rotate: FAN[3].r, scale: FAN[3].s, opacity: 1 }} zIndex={2} bg="#e0dace" />
          <Paper ctrl={c3} initialState={{ x: FAN[2].x, y: FAN[2].y, rotate: FAN[2].r, scale: FAN[2].s, opacity: 1 }} zIndex={3} bg="#e9e3d8" />
          <Paper ctrl={c2} initialState={{ x: FAN[1].x, y: FAN[1].y, rotate: FAN[1].r, scale: FAN[1].s, opacity: 1 }} zIndex={4} bg="#f0ebe2" />
          <Paper ctrl={c1} initialState={{ x: FAN[0].x, y: FAN[0].y, rotate: 0, scale: 1, opacity: 1 }} zIndex={5} bg="#f5f0e8" glowActive={glow}>
            <CheckBadge visible={checkOn} />
          </Paper>

          <StageLabel label={STAGES[phase] || STAGES.idle} />
        </div>
      </motion.div>
      <footer className="paper-stack-hero__footer">
        <span>&copy; 2026 Corsair Standard</span>
        <nav aria-label="Legal links">
          <a href="/privacy.html">Privacy</a>
          <a href="/terms.html">Terms</a>
          <a href="/security.html">Security</a>
        </nav>
      </footer>
    </section>
  );
}
