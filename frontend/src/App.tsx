import { useEffect, useMemo, useState } from "react";
import { ClubComingSoon } from "./components/ClubComingSoon";
import { DashboardShell } from "./components/DashboardShell";
import { LandingPage } from "./components/LandingPage";
import type { AnalyzePayload, AuditHistoryItem } from "./types/api";

const HISTORY_KEY = "corsair-standard:audit-history";
type AppView = "home" | "app" | "club";

function getViewFromLocation(): AppView {
  if (window.location.pathname.startsWith("/club")) return "club";
  return window.location.pathname.startsWith("/app") ? "app" : "home";
}

export default function App() {
  const [view, setView] = useState<AppView>(() => getViewFromLocation());
  const [pendingScrollTarget, setPendingScrollTarget] = useState<string | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const saved = window.localStorage.getItem("corsair-standard:theme");
    return saved === "light" ? "light" : "dark";
  });
  const [payload, setPayload] = useState<AnalyzePayload | null>(null);
  const [history, setHistory] = useState<AuditHistoryItem[]>(() => {
    try {
      return JSON.parse(window.localStorage.getItem(HISTORY_KEY) ?? "[]") as AuditHistoryItem[];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    const handlePopState = () => setView(getViewFromLocation());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem("corsair-standard:theme", theme);
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 25)));
  }, [history]);

  const handleAnalyzed = (nextPayload: AnalyzePayload) => {
    setPayload(nextPayload);
    const item: AuditHistoryItem = {
      id: nextPayload.document_links?.upload_id ?? crypto.randomUUID(),
      filename: nextPayload.source.filename,
      createdAt: new Date().toISOString(),
      score: nextPayload.result.score,
      visualScore: nextPayload.result.visual_compliance_score,
      structuralScore: nextPayload.result.structural_quality_score,
      violations: nextPayload.result.violations,
    };
    setHistory((current) => [item, ...current.filter((entry) => entry.id !== item.id)].slice(0, 25));
  };

  const openApp = (targetId?: string) => {
    if (!window.location.pathname.startsWith("/app")) {
      window.history.pushState({}, "", "/app");
    }
    setView("app");
    setPendingScrollTarget(targetId ?? null);
  };

  const openHome = () => {
    if (window.location.pathname !== "/") {
      window.history.pushState({}, "", "/");
    }
    setView("home");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    if (view !== "app" || !pendingScrollTarget) return;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById(pendingScrollTarget)?.scrollIntoView({
        behavior: "smooth",
        block: pendingScrollTarget === "upload-section" ? "center" : "start",
      });
      setPendingScrollTarget(null);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [pendingScrollTarget, view]);

  const openAudit = () => {
    openApp("upload-section");
  };

  const dashboard = useMemo(
    () => (
      <DashboardShell
        payload={payload}
        history={history}
        theme={theme}
        onThemeChange={setTheme}
        onAnalyzed={handleAnalyzed}
        onHome={openHome}
      />
    ),
    [payload, history, theme],
  );

  if (view === "home") {
    return <LandingPage onRunAudit={openAudit} theme={theme} onThemeChange={setTheme} />;
  }

  if (view === "club") {
    return <ClubComingSoon onHome={openHome} onAudit={openAudit} theme={theme} onThemeChange={setTheme} />;
  }

  return <div id="dashboard">{dashboard}</div>;
}
