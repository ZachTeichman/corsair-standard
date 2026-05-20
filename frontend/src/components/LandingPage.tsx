import PaperStackHero from "./PaperStackHero";

interface LandingPageProps {
  onRunAudit: () => void;
  theme: "dark" | "light";
  onThemeChange: (theme: "dark" | "light") => void;
}

export function LandingPage({ onRunAudit, theme, onThemeChange }: LandingPageProps) {
  return <PaperStackHero onRunAudit={onRunAudit} theme={theme} onThemeChange={onThemeChange} />;
}
