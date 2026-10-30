import {
  FileAudio,
  Loader2,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/Card";
import { Button, buttonClass } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { api, ApiError } from "@/lib/api";
import {
  fileStem,
  formatDate,
  formatDuration,
  languageLabel,
  relativeTime,
} from "@/lib/format";
import type { ProcessingStatus, RecordingSummary } from "@/lib/types";
import { useWorkspace } from "@/lib/workspace";

type FilterStatus = "all" | ProcessingStatus;

export function FilesPage() {
  const { recordings, total, loading, refresh, setSelectedId, selectedId } = useWorkspace();
  const { push } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [statusFilter, setStatusFilter] = useState<FilterStatus>("all");
  const [langFilter, setLangFilter] = useState<"all" | "fa" | "en">("all");
  const [deleting, setDeleting] = useState<RecordingSummary | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [batchBusy, setBatchBusy] = useState(false);

  useEffect(() => {
    const fromUrl = searchParams.get("q");
    if (fromUrl !== null) setQuery(fromUrl);
  }, [searchParams]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return recordings.filter((recording) => {
      if (statusFilter !== "all" && recording.processing_status !== statusFilter) return false;
      if (langFilter !== "all") {
        const code = (recording.language ?? "fa").toLowerCase();
        if (langFilter === "fa" && !code.startsWith("fa") && code !== "auto") return false;
        if (langFilter === "en" && !code.startsWith("en")) return false;
      }
      if (!needle) return true;
      return (
        recording.original_filename.toLowerCase().includes(needle) ||
        (recording.language ?? "").toLowerCase().includes(needle) ||
        recording.id.toLowerCase().includes(needle)
      );
    });
  }, [recordings, query, statusFilter, langFilter]);

  const completedCount = useMemo(
    () => recordings.filter((r) => r.processing_status === "completed").length,
    [recordings],
  );
  const failedList = useMemo(
    () => recordings.filter((r) => r.processing_status === "failed"),
    [recordings],
  );
  const inFlightList = useMemo(
    () =>
      recordings.filter((r) =>
        ["processing", "pending"].includes(r.processing_status),
      ),
    [recordings],
  );

  async function handleClearFailed() {
    if (failedList.length === 0) return;
    setBatchBusy(true);
    try {
      await Promise.allSettled(failedList.map((r) => api.deleteRecording(r.id)));
      if (selectedId && failedList.some((r) => r.id === selectedId)) {
        setSelectedId(null);
      }
      await refresh();
      push(`Removed ${failedList.length} failed recordings.`, "success");
    } finally {
      setBatchBusy(false);
    }
  }

  async function handleCancelAllPending() {
    if (inFlightList.length === 0) return;
    setBatchBusy(true);
    try {
      await Promise.allSettled(inFlightList.map((r) => api.deleteRecording(r.id)));
      if (selectedId && inFlightList.some((r) => r.id === selectedId)) {
        setSelectedId(null);
      }
      await refresh();
      push(`Canceled and removed ${inFlightList.length} pending/processing recordings.`, "info");
    } finally {
      setBatchBusy(false);
    }
  }

  async function handleDownload(rec: RecordingSummary) {
    try {
      const result = await api.export(rec.id, "json");
      const blob = new Blob([result.content], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = result.filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      push(`Downloaded ${result.filename}`, "success");
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Download failed.", "error");
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await api.deleteRecording(deleting.id);
      if (selectedId === deleting.id) setSelectedId(null);
      setDeleting(null);
      await refresh();
      push("Recording and its derived data were removed.", "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Delete failed.";
      setDeleteError(message);
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        crumb="WORKSPACE / FILES"
        title="My Files"
        subtitle="Manage and review your uploaded audio files."
        actions={
          <>
            {inFlightList.length > 0 && (
              <Button
                variant="ghost"
                onClick={() => void handleCancelAllPending()}
                disabled={batchBusy || loading}
              >
                <XCircle className="size-4" />
                Cancel Pending ({inFlightList.length})
              </Button>
            )}
            {failedList.length > 0 && (
              <Button
                variant="danger"
                onClick={() => void handleClearFailed()}
                disabled={batchBusy || loading}
              >
                <Trash2 className="size-4" />
                Clear Failed ({failedList.length})
              </Button>
            )}
            <Button variant="ghost" onClick={() => void refresh()} disabled={loading}>
              <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Link to="/upload" className={buttonClass({ size: "md" })}>
              <Upload className="size-4" />
              Upload Audio
            </Link>
          </>
        }
      />

      {/* Search and Filters */}
      <Card className="p-5">
        <h2 className="text-[13px] font-semibold text-ink">Search and Filters</h2>
        <div className="mt-3.5 flex flex-wrap items-center gap-4">
          <div className="relative min-w-[220px] flex-1 max-w-[360px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-mute" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search files..."
              aria-label="Search files"
              className="h-9 w-full rounded-[9px] border border-navy-600 bg-navy-800 pl-8 pr-3 text-[11.5px] text-ink outline-none placeholder:text-mute focus:border-violet-900"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as FilterStatus)}
            aria-label="Filter by status"
            className="h-9 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[11.5px] text-mute2 outline-none focus:border-violet-900"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>

          <select
            value={langFilter}
            onChange={(e) => setLangFilter(e.target.value as "all" | "fa" | "en")}
            aria-label="Filter by language"
            className="h-9 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[11.5px] text-mute2 outline-none focus:border-violet-900"
          >
            <option value="all">All Languages</option>
            <option value="fa">Persian</option>
            <option value="en">English</option>
          </select>
        </div>
      </Card>

      {/* Audio Library */}
      <Card className="p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-ink">Audio Library</h2>
          <span className="text-[11px] text-mute">
            {visible.length} of {total} files
          </span>
        </div>

        {loading && recordings.length === 0 ? (
          <div className="flex items-center gap-2 py-10 text-[12px] text-mute">
            <Loader2 className="size-4 animate-spin" />
            Loading audio library…
          </div>
        ) : visible.length === 0 ? (
          <div className="py-12 text-center">
            <div className="mx-auto grid size-11 place-items-center rounded-full bg-navy-800 text-mute">
              <FileAudio className="size-5" />
            </div>
            <p className="mt-3 text-[13px] font-semibold text-ink">
              {recordings.length === 0 ? "Your audio library is empty" : "No files match your filter"}
            </p>
            <p className="mt-1 text-[11px] text-mute">
              {recordings.length === 0
                ? "Upload a Persian or English audio file to get started."
                : "Try clearing the search query or status filter."}
            </p>
          </div>
        ) : (
          <div className="mt-4 divide-y divide-navy-600/60">
            {visible.map((rec) => {
              const isInFlight =
                rec.processing_status === "pending" || rec.processing_status === "processing";
              return (
                <div
                  key={rec.id}
                  className="grid grid-cols-1 items-center gap-3 py-3.5 sm:grid-cols-[minmax(0,1.4fr)_140px_180px_auto]"
                >
                  <div className="min-w-0">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedId(rec.id);
                        navigate("/");
                      }}
                      className="block max-w-full truncate text-left text-[12.5px] font-medium text-ink transition hover:text-violet-300"
                    >
                      {rec.original_filename}
                    </button>
                    <p className="mt-0.5 text-[10px] text-mute">
                      {formatDuration(rec.duration_seconds)} · {languageLabel(rec.language)} ·{" "}
                      {relativeTime(rec.created_at)}
                    </p>
                  </div>

                  <div>
                    <StatusBadge status={rec.processing_status} />
                    {rec.error_message && (
                      <p
                        className="mt-0.5 truncate text-[10px] text-rose-300"
                        title={rec.error_message}
                      >
                        {rec.error_message}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-[11.5px] text-mute2">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedId(rec.id);
                        navigate("/");
                      }}
                      className="font-medium text-ink transition hover:text-violet-300"
                    >
                      Open
                    </button>
                    <span className="text-mute">·</span>
                    <button
                      type="button"
                      onClick={() => void handleDownload(rec)}
                      className="transition hover:text-ink"
                    >
                      Download
                    </button>
                    <span className="text-mute">·</span>
                    <button
                      type="button"
                      onClick={() => {
                        setDeleteError(null);
                        setDeleting(rec);
                      }}
                      className="text-rose-300/90 transition hover:text-rose-200"
                    >
                      {isInFlight ? "Cancel" : "Delete"}
                    </button>
                  </div>

                  <div className="hidden text-right text-[10px] text-mute sm:block">
                    {formatDate(rec.created_at)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Storage Overview */}
      <Card className="p-5">
        <h2 className="text-[13px] font-semibold text-ink">Storage Overview</h2>
        <p className="mt-2 text-[11.5px] text-mute2">
          {total} files &nbsp;·&nbsp; {completedCount} completed &nbsp;·&nbsp; {inFlightList.length} in queue &nbsp;·&nbsp; {failedList.length} failed
        </p>
      </Card>

      <Modal
        open={Boolean(deleting)}
        title={
          deleting &&
          (deleting.processing_status === "pending" ||
            deleting.processing_status === "processing")
            ? "Cancel and remove this upload?"
            : "Delete this recording?"
        }
        description="The audio file, job, transcript, analysis, and derived vector index are permanently removed."
        onClose={() => {
          if (!deleteBusy) setDeleting(null);
        }}
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleting(null)} disabled={deleteBusy}>
              Keep
            </Button>
            <Button variant="danger" onClick={() => void confirmDelete()} disabled={deleteBusy}>
              {deleteBusy ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Trash2 className="size-4" />
              )}
              {deleting &&
              (deleting.processing_status === "pending" ||
                deleting.processing_status === "processing")
                ? "Cancel & Remove"
                : "Delete permanently"}
            </Button>
          </>
        }
      >
        <div className="rounded-[10px] border border-navy-600 bg-navy-800 px-3 py-2">
          <p className="truncate text-[12px] font-medium text-ink">
            {deleting ? fileStem(deleting.original_filename) : ""}
          </p>
          <p className="mt-0.5 text-[10px] text-mute">
            {deleting ? formatDate(deleting.created_at) : ""}
          </p>
        </div>
        {deleteError && <p className="mt-2 text-[11px] text-rose-300">{deleteError}</p>}
      </Modal>
    </div>
  );
}
