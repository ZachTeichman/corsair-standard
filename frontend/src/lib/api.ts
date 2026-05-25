import type { AnalyzePayload } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

function errorMessageFromPayload(payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return "The audit request failed.";
  }
  const detail = "detail" in payload ? payload.detail : null;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
          return item.msg;
        }
        return JSON.stringify(item);
      })
      .join(" ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return "The audit request failed.";
}

export async function analyzeResume(file: File): Promise<AnalyzePayload> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
  });
  const payload = (await response.json()) as AnalyzePayload | { detail?: string };
  if (!response.ok) {
    throw new Error(errorMessageFromPayload(payload));
  }
  return payload as AnalyzePayload;
}

export function apiHref(path?: string | null) {
  if (!path) return "#";
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}
