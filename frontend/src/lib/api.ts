import type { AnalyzePayload } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export async function analyzeResume(file: File): Promise<AnalyzePayload> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
  });
  const payload = (await response.json()) as AnalyzePayload | { detail?: string };
  if (!response.ok) {
    throw new Error("detail" in payload ? payload.detail ?? "The audit request failed." : "The audit request failed.");
  }
  return payload as AnalyzePayload;
}

export function apiHref(path?: string | null) {
  if (!path) return "#";
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}
