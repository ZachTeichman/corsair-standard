import { useEffect, useMemo, useState } from "react";
import { DashboardShell } from "./components/DashboardShell";
import { LandingPage } from "./components/LandingPage";
import type { AnalyzePayload, AuditHistoryItem } from "./types/api";

const HISTORY_KEY = "corsair-standard:audit-history";

export default function App() {
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

  const enterDashboard = () => {
    document.getElementById("dashboard")?.scrollIntoView({ behavior: "smooth" });
  };

  const dashboard = useMemo(
    () => (
      <DashboardShell
        payload={payload}
        history={history}
        theme={theme}
        onThemeChange={setTheme}
        onAnalyzed={handleAnalyzed}
      />
    ),
    [payload, history, theme],
  );

  return (
    <>
      <LandingPage onEnter={enterDashboard} />
      <div id="dashboard">{dashboard}</div>
    </>
  );
}

