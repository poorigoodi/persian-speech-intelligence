import {
  AlertTriangle,
  ArrowUp,
  CheckCircle2,
  FileAudio,
  Loader2,
  RotateCcw,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { StatusPill } from "@/components/ui/StatusPill";
import { useToast } from "@/components/ui/Toast";
import { useJobStatus } from "@/hooks/useRecordingData";
import { api, ApiError } from "@/lib/api";
import { formatBytes, formatDuration, relativeTime } from "@/lib/format";
import { useWorkspace } from "@/lib/workspace";

const ACCEPTED = [".wav", ".mp3", ".m4a", ".flac", ".ogg"];
const ACCEPTED_LABEL = "MP3, WAV, M4A, FLAC, OGG";
const MAX_MB = 100;

function validateFile(file: File): string | null {
  const ext = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
  if (!ACCEPTED.includes(ext)) {
    return `Unsupported format "${ext}". Use ${ACCEPTED_LABEL}.`;
  }
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_MB * 1024 * 1024) {
    return `File is larger than ${MAX_MB} MB.`;
  }
  return null;
}

export function UploadPage() {
  const {
    refresh,
    rememberBlob,
    setSelectedId,
    selectedId,
    recordings,
    settings,
    setSettings,
    uploadSession,
    setUploadSession,
  } = useWorkspace();
  const { push } = useToast();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const announcedRef = useRef<string | null>(null);

  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [canceling, setCanceling] = useState(false);

  const { recordingId, fileName, fileSize, error, outputLang } = uploadSession;
  const setRecordingId = (id: string | null) =>
    setUploadSession((prev) => ({ ...prev, recordingId: id }));
  const setFileName = (name: string | null) =>
    setUploadSession((prev) => ({ ...prev, fileName: name }));
  const setFileSize = (size: number | null) =>
    setUploadSession((prev) => ({ ...prev, fileSize: size }));
  const setError = (err: string | null) =>
    setUploadSession((prev) => ({ ...prev, error: err }));
  const setOutputLang = (lang: "fa" | "en") =>
    setUploadSession((prev) => ({ ...prev, outputLang: lang }));

  const { status, error: statusError } = useJobStatus(recordingId);

  const failedList = useMemo(
    () => recordings.filter((r) => r.processing_status === "failed"),
    [recordings],
  );
  const inFlightList = useMemo(
    () => recordings.filter((r) => ["pending", "processing"].includes(r.processing_status)),
    [recordings],
  );

  useEffect(() => {
    if (status?.status === "completed" && announcedRef.current !== status.recording_id) {
      announcedRef.current = status.recording_id;
      push("Processing complete. Transcript and analysis are ready.", "success");
      void refresh();
    }
  }, [status, push, refresh]);

  async function handleFile(file: File) {
    const problem = validateFile(file);
    if (problem) {
      setError(problem);
      push(problem, "error");
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setError(null);
    setUploading(true);
    setRecordingId(null);
    setFileName(file.name);
    setFileSize(file.size);
    announcedRef.current = null;

    try {
      const result = await api.upload(file, controller.signal);
      rememberBlob(result.recording_id, file);
      setSelectedId(result.recording_id);
      setRecordingId(result.recording_id);
      push("Upload complete. Transcription is queued.", "success");
      await refresh();
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setFileName(null);
        setFileSize(null);
        push("Upload canceled.", "info");
        return;
      }
      const message =
        err instanceof ApiError ? err.message : "Upload failed. Is the backend running?";
      setError(message);
      push(message, "error");
    } finally {
      setUploading(false);
      abortRef.current = null;
    }
  }

  async function handleCancelActive() {
    if (uploading && abortRef.current) {
      abortRef.current.abort();
      return;
    }
    if (!recordingId) {
      setFileName(null);
      setFileSize(null);
      setError(null);
      return;
    }
    setCanceling(true);
    try {
      await api.deleteRecording(recordingId);
      if (selectedId === recordingId) setSelectedId(null);
      setRecordingId(null);
      setFileName(null);
      setFileSize(null);
      setError(null);
      await refresh();
      push("Upload and processing job canceled.", "info");
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Could not cancel job.", "error");
    } finally {
      setCanceling(false);
    }
  }

  async function handleClearFailed() {
    if (failedList.length === 0) return;
    setCanceling(true);
    try {
      await Promise.allSettled(failedList.map((r) => api.deleteRecording(r.id)));
      if (selectedId && failedList.some((r) => r.id === selectedId)) setSelectedId(null);
      await refresh();
      push(`Removed ${failedList.length} failed recordings.`, "success");
    } finally {
      setCanceling(false);
    }
  }

  async function handleCancelAllPending() {
    if (inFlightList.length === 0) return;
    setCanceling(true);
    try {
      await Promise.allSettled(inFlightList.map((r) => api.deleteRecording(r.id)));
      if (recordingId && inFlightList.some((r) => r.id === recordingId)) {
        setRecordingId(null);
        setFileName(null);
        setFileSize(null);
      }
      if (selectedId && inFlightList.some((r) => r.id === selectedId)) setSelectedId(null);
      await refresh();
      push(`Canceled and removed ${inFlightList.length} pending/processing items.`, "info");
    } finally {
      setCanceling(false);
    }
  }

  function onDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  }

  const progress = status?.progress ?? 0;

  return (
    <div className="space-y-4">
      <PageHeader
        crumb="WORKSPACE / UPLOAD"
        title="Upload Audio"
        subtitle="Upload Persian or English audio files for transcription and AI analysis."
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
        {/* Dropzone Card */}
        <Card className="p-5">
          <h2 className="text-[13px] font-semibold text-ink">Drop your audio here</h2>

          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`mt-3.5 flex min-h-[230px] flex-col items-center justify-center rounded-[13px] border border-dashed px-6 py-9 text-center transition ${
              dragging
                ? "border-violet-500 bg-violet-500/10"
                : "border-navy-600 bg-navy-800/35 hover:border-violet-900"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED.join(",")}
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void handleFile(file);
                event.target.value = "";
              }}
            />

            <div className="grid size-12 place-items-center rounded-full bg-violet-600/15 text-violet-400">
              {uploading ? (
                <Loader2 className="size-6 animate-spin" />
              ) : (
                <ArrowUp className="size-6 stroke-[2.2]" />
              )}
            </div>

            <h3 className="mt-4 text-[15px] font-semibold text-ink">
              {dragging ? "Drop to upload" : "Drag and drop audio files"}
            </h3>
            <p className="mt-1.5 text-[11px] text-mute">
              {ACCEPTED_LABEL} up to {MAX_MB}MB
            </p>

            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <Button onClick={() => inputRef.current?.click()} disabled={uploading}>
                Select File
              </Button>
              {uploading && (
                <Button variant="danger" onClick={() => void handleCancelActive()}>
                  <XCircle className="size-4" />
                  Cancel Upload
                </Button>
              )}
            </div>
          </div>

          {error && (
            <div className="mt-3 flex items-start gap-2 rounded-[10px] border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-200">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {(fileName || uploading) && (
            <div className="mt-4 rounded-[12px] border border-navy-600 bg-navy-800/60 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-[9px] bg-violet-500/15 text-violet-300">
                    <FileAudio className="size-4" />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-[12px] font-semibold text-ink">{fileName}</p>
                    <p className="text-[10px] text-mute">
                      {formatBytes(fileSize)}
                      {status?.current_step ? ` · ${status.current_step}` : ""}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {status ? (
                    <StatusPill status={status.status} />
                  ) : (
                    <StatusPill status="processing" />
                  )}
                  {status?.status !== "completed" && (
                    <Button
                      size="sm"
                      variant="danger"
                      disabled={canceling}
                      onClick={() => void handleCancelActive()}
                    >
                      <XCircle className="size-3.5" />
                      Cancel
                    </Button>
                  )}
                </div>
              </div>

              <div className="mt-3">
                <div className="flex items-center justify-between text-[10px] text-mute">
                  <span>{status?.current_step ? `Step: ${status.current_step}` : "Queued…"}</span>
                  <span className="tabular-nums">
                    {status?.status === "completed" ? 100 : progress}%
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-navy-900">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-600 to-electric transition-all duration-500"
                    style={{ width: `${status?.status === "completed" ? 100 : progress}%` }}
                  />
                </div>
              </div>

              {status?.status === "failed" && (
                <p className="mt-2 text-[11px] text-rose-300">
                  {status.error_message || statusError || "Processing failed."}
                </p>
              )}

              <div className="mt-3 flex flex-wrap gap-2">
                {status?.status === "completed" && (
                  <>
                    <Button size="sm" onClick={() => navigate("/")}>
                      <CheckCircle2 className="size-3.5" />
                      Open Workspace
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => navigate("/analysis")}>
                      <Sparkles className="size-3.5" />
                      Speech Analysis
                    </Button>
                  </>
                )}
                {(status?.status === "failed" || error) && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setRecordingId(null);
                      setFileName(null);
                      setFileSize(null);
                      setError(null);
                    }}
                  >
                    <RotateCcw className="size-3.5" />
                    Reset
                  </Button>
                )}
              </div>
            </div>
          )}
        </Card>

        {/* Processing Options Card */}
        <Card className="flex flex-col justify-between p-5">
          <div>
            <h2 className="text-[13px] font-semibold text-ink">Processing Options</h2>

            <div className="mt-5 space-y-4">
              <div className="flex items-center justify-between gap-3 border-b border-navy-600/60 pb-3.5">
                <span className="text-[12px] text-mute2">Source Language</span>
                <select
                  value={settings.defaultLanguage}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      defaultLanguage: e.target.value as "auto" | "fa" | "en",
                    })
                  }
                  aria-label="Source Language"
                  className="h-8 rounded-[8px] border border-navy-600 bg-navy-800 px-2.5 text-[11.5px] font-semibold text-ink outline-none focus:border-violet-900"
                >
                  <option value="auto">Auto Detect</option>
                  <option value="fa">Persian (Farsi)</option>
                  <option value="en">English</option>
                </select>
              </div>

              <div className="flex items-center justify-between gap-3 border-b border-navy-600/60 pb-3.5">
                <span className="text-[12px] text-mute2">Output Language</span>
                <select
                  value={outputLang}
                  onChange={(e) => setOutputLang(e.target.value as "fa" | "en")}
                  aria-label="Output Language"
                  className="h-8 rounded-[8px] border border-navy-600 bg-navy-800 px-2.5 text-[11.5px] font-semibold text-ink outline-none focus:border-violet-900"
                >
                  <option value="fa">Persian</option>
                  <option value="en">English</option>
                </select>
              </div>

              <div className="flex items-center justify-between gap-3 pb-1">
                <span className="text-[12px] text-mute2">Transcription Mode</span>
                <span className="text-[11.5px] font-semibold capitalize text-ink">
                  {settings.transcriptionMode}
                </span>
              </div>
            </div>
          </div>

          <p className="mt-6 rounded-[10px] border border-navy-600/80 bg-navy-800/50 px-3 py-2.5 text-[10px] leading-relaxed text-mute">
            Placeholder note: Language and model options are saved locally. Backend upload (`POST /api/v1/recordings`) uses the server’s configured Whisper and Qwen models automatically.
          </p>
        </Card>
      </div>

      {/* Recent Uploads Card */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[13px] font-semibold text-ink">Recent Uploads</h2>

          <div className="flex flex-wrap items-center gap-2">
            {inFlightList.length > 0 && (
              <Button
                size="sm"
                variant="ghost"
                disabled={canceling}
                onClick={() => void handleCancelAllPending()}
              >
                <XCircle className="size-3.5" />
                Cancel Pending ({inFlightList.length})
              </Button>
            )}
            {failedList.length > 0 && (
              <Button
                size="sm"
                variant="danger"
                disabled={canceling}
                onClick={() => void handleClearFailed()}
              >
                <Trash2 className="size-3.5" />
                Clear Failed ({failedList.length})
              </Button>
            )}
          </div>
        </div>

        {recordings.length === 0 ? (
          <p className="mt-4 text-[12px] text-mute">No recordings have been uploaded yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-navy-600/60">
            {recordings.slice(0, 6).map((rec) => (
              <li
                key={rec.id}
                className="flex items-center justify-between gap-4 py-3 first:pt-1 last:pb-0"
              >
                <button
                  type="button"
                  onClick={() => {
                    setSelectedId(rec.id);
                    navigate("/");
                  }}
                  className="min-w-0 flex-1 truncate text-left text-[12px] font-medium text-ink transition hover:text-violet-300"
                >
                  {rec.original_filename}
                </button>
                <div className="flex shrink-0 items-center gap-4">
                  <span className="hidden text-[11px] tabular-nums text-mute sm:inline">
                    {formatDuration(rec.duration_seconds)} · {relativeTime(rec.created_at)}
                  </span>
                  <StatusBadge status={rec.processing_status} />
                  <button
                    type="button"
                    disabled={canceling}
                    onClick={async () => {
                      setCanceling(true);
                      try {
                        await api.deleteRecording(rec.id);
                        if (selectedId === rec.id) setSelectedId(null);
                        if (recordingId === rec.id) {
                          setRecordingId(null);
                          setFileName(null);
                          setFileSize(null);
                        }
                        await refresh();
                        push(
                          rec.processing_status === "pending" ||
                            rec.processing_status === "processing"
                            ? "Upload canceled."
                            : "Recording deleted.",
                          "info",
                        );
                      } finally {
                        setCanceling(false);
                      }
                    }}
                    className="text-[11px] font-medium text-mute transition hover:text-rose-300"
                  >
                    {rec.processing_status === "pending" || rec.processing_status === "processing"
                      ? "Cancel"
                      : "Delete"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
