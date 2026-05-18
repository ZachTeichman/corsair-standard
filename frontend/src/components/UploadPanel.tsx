import { FileUp, Loader2 } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { analyzeResume } from "../lib/api";
import type { AnalyzePayload } from "../types/api";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

interface UploadPanelProps {
  onAnalyzed: (payload: AnalyzePayload) => void;
}

export function UploadPanel({ onAnalyzed }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAudit = useCallback(
    async (nextFile = file) => {
      if (!nextFile) return;
      setLoading(true);
      setError(null);
      try {
        const payload = await analyzeResume(nextFile);
        onAnalyzed(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed.");
      } finally {
        setLoading(false);
      }
    },
    [file, onAnalyzed],
  );

  return (
    <Card className="p-5">
      <div className="mb-4">
        <p className="text-xs font-bold uppercase tracking-[0.22em] text-corsair-bronze">Student upload</p>
        <h2 className="mt-2 text-2xl font-semibold text-white light:text-corsair-ink">Check a DOCX resume</h2>
        <p className="mt-2 text-sm leading-6 text-slate-400 light:text-slate-600">
          Deterministic Word formatting checks only. No candidate quality scoring, job matching, or ATS language.
        </p>
      </div>
      <div
        role="button"
        tabIndex={0}
        className="flex cursor-pointer items-center gap-4 rounded-2xl border border-dashed border-corsair-bronze/35 bg-corsair-bronze/[0.045] p-4 transition hover:bg-corsair-bronze/[0.08] light:bg-corsair-bronze/10"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDrop={(event) => {
          event.preventDefault();
          const dropped = event.dataTransfer.files?.[0];
          if (dropped) {
            setFile(dropped);
            void runAudit(dropped);
          }
        }}
        onDragOver={(event) => event.preventDefault()}
      >
        <input
          ref={inputRef}
          className="hidden"
          type="file"
          accept=".docx"
          onClick={(event) => {
            event.currentTarget.value = "";
          }}
          onChange={(event) => {
            const selected = event.currentTarget.files?.[0] ?? null;
            setFile(selected);
            if (selected) {
              void runAudit(selected);
            }
          }}
        />
        <span className="grid h-14 w-14 place-items-center rounded-xl border border-corsair-bronze/30 bg-black/25 text-corsair-gold light:bg-white/70">
          <FileUp className="h-6 w-6" />
        </span>
        <span className="min-w-0">
          <strong className="block truncate text-white light:text-corsair-ink">{file?.name ?? "Choose or drop a .docx file"}</strong>
          <small className="text-slate-400 light:text-slate-600">Office Open XML resumes only. Selecting a file starts the audit.</small>
        </span>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button variant="primary" disabled={!file || loading} onClick={() => void runAudit()}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {loading ? "Auditing..." : "Run format audit"}
        </Button>
        {error ? <p className="text-sm text-red-300">{error}</p> : <p className="text-sm text-slate-500">Ready when the file is selected.</p>}
      </div>
    </Card>
  );
}
