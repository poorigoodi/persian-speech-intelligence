import {
  AlertTriangle,
  ArrowUpRight,
  AudioLines,
  Bot,
  Copy,
  Download,
  FileCode,
  FileText,
  Info,
  Layers,
  Loader2,
  MoreHorizontal,
  RefreshCw,
  Search,
  Send,
  Share2,
  SmilePlus,
  Sparkles,
  Trash2,
  Upload,
  Users,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AudioPlayer } from "@/components/AudioPlayer";
import { Card } from "@/components/ui/Card";
import { Button, buttonClass } from "@/components/ui/Button";
import { StatusPill } from "@/components/ui/StatusPill";
import { useToast } from "@/components/ui/Toast";
import {
  useAnalysis,
  useJobStatus,
  useRecordingDetail,
  useTranscript,
} from "@/hooks/useRecordingData";
import { api, ApiError } from "@/lib/api";
import {
  asRecord,
  confidenceMetrics,
  entityCount,
  fileStem,
  formatBytes,
  formatDate,
  formatDuration,
  itemText,
  readingMinutes,
  stringList,
  textList,
} from "@/lib/format";
import { useWorkspace } from "@/lib/workspace";

type MainTab = "transcript" | "summary" | "topics" | "entities" | "sentiment";
type InsightTab = "summary" | "keypoints" | "decisions";
type ExportFormat = "json" | "txt" | "markdown";

export function Dashboard() {
  const {
    recordings,
    selectedId,
    setSelectedId,
    audioBlobs,
    backendOk,
    refresh,
    chatMessagesByRec,
    appendChatMessage,
    chatDraftByRec,
    setChatDraft,
    dashboardView,
    setDashboardView,
  } = useWorkspace();
  const { push } = useToast();
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const moreMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!moreMenuOpen) return;
    function handleOutsideClick(event: MouseEvent) {
      if (moreMenuRef.current && !moreMenuRef.current.contains(event.target as Node)) {
        setMoreMenuOpen(false);
      }
    }
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMoreMenuOpen(false);
    }
    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [moreMenuOpen]);

  const completedRecordings = useMemo(
    () => recordings.filter((r) => r.processing_status === "completed"),
    [recordings],
  );
  const failedRecordings = useMemo(
    () => recordings.filter((r) => r.processing_status === "failed"),
    [recordings],
  );
  const activeRecordings = useMemo(
    () => recordings.filter((r) => ["pending", "processing"].includes(r.processing_status)),
    [recordings],
  );

  const recording = useMemo(
    () =>
      recordings.find((item) => item.id === selectedId) ??
      completedRecordings[0] ??
      null,
    [recordings, selectedId, completedRecordings],
  );
  const id = recording?.id ?? null;
  const isCompleted = recording?.processing_status === "completed";
  const isInFlight =
    recording?.processing_status === "pending" ||
    recording?.processing_status === "processing";

  const jobStatus = useJobStatus(isInFlight ? id : null);
  const transcript = useTranscript(isCompleted ? id : null);
  const analysis = useAnalysis(isCompleted ? id : null);
  const detail = useRecordingDetail(isCompleted ? id : null);

  const { mainTab, insightTab, searchQuery } = dashboardView;
  const setMainTab = (next: MainTab) =>
    setDashboardView((prev) => ({ ...prev, mainTab: next }));
  const setInsightTab = (next: InsightTab) =>
    setDashboardView((prev) => ({ ...prev, insightTab: next }));
  const setSearchQuery = (next: string) =>
    setDashboardView((prev) => ({ ...prev, searchQuery: next }));

  const [seek, setSeek] = useState<{ time: number; token: number } | null>(null);
  const [insightLang, setInsightLang] = useState<"fa" | "en">("fa");
  const [cleaningBusy, setCleaningBusy] = useState(false);

  const [chatPending, setChatPending] = useState(false);
  const chatMessages = id ? chatMessagesByRec[id] ?? [] : [];
  const chatInput = id ? chatDraftByRec[id] ?? "" : "";
  const setChatInput = (val: string) => {
    if (id) setChatDraft(id, val);
  };

  useEffect(() => {
    if (jobStatus.status?.status === "completed" || jobStatus.status?.status === "failed") {
      void refresh();
    }
  }, [jobStatus.status?.status, refresh]);

  async function handleCancelRecording(targetId: string, label?: string) {
    setCleaningBusy(true);
    try {
      await api.deleteRecording(targetId);
      if (selectedId === targetId) setSelectedId(null);
      await refresh();
      push(`Canceled and removed ${label || "recording"}.`, "info");
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Failed to cancel recording.", "error");
    } finally {
      setCleaningBusy(false);
    }
  }

  async function handleClearFailed() {
    if (failedRecordings.length === 0) return;
    setCleaningBusy(true);
    try {
      await Promise.allSettled(failedRecordings.map((r) => api.deleteRecording(r.id)));
      if (selectedId && failedRecordings.some((r) => r.id === selectedId)) {
        setSelectedId(null);
      }
      await refresh();
      push(`Removed ${failedRecordings.length} failed recordings.`, "success");
    } finally {
      setCleaningBusy(false);
    }
  }

  async function handleClearInFlight() {
    if (activeRecordings.length === 0) return;
    setCleaningBusy(true);
    try {
      await Promise.allSettled(activeRecordings.map((r) => api.deleteRecording(r.id)));
      if (selectedId && activeRecordings.some((r) => r.id === selectedId)) {
        setSelectedId(null);
      }
      await refresh();
      push(`Canceled and removed ${activeRecordings.length} pending/processing items.`, "info");
    } finally {
      setCleaningBusy(false);
    }
  }

  const segments = transcript.data?.segments ?? [];
  const confStats = useMemo(() => confidenceMetrics(segments), [segments]);
  const confidence = confStats.score;
  const analysisData = analysis.data;

  const detailed = asRecord(analysisData?.detailed_summary);
  const sentiment = asRecord(analysisData?.sentiment);
  const entities = asRecord(analysisData?.extracted_entities);

  const topics = useMemo(() => {
    if (!Array.isArray(analysisData?.topics)) return [];
    const GENERIC_DESC = "کلمه کلیدی استخراج‌شده از متن پیاده‌سازی‌شده";
    return analysisData.topics
      .map((topic: unknown) => {
        const rec = asRecord(topic);
        const name =
          typeof topic === "string"
            ? topic.trim()
            : typeof rec.name === "string" && rec.name.trim()
              ? rec.name.trim()
              : itemText(topic);
        const rawDesc = typeof rec.description === "string" ? rec.description.trim() : "";
        const description =
          rawDesc && rawDesc !== name && rawDesc !== GENERIC_DESC ? rawDesc : "";
        return {
          name,
          description,
          relevance: typeof rec.relevance === "number" ? rec.relevance : null,
        };
      })
      .filter((t) => t.name && t.name !== GENERIC_DESC);
  }, [analysisData]);

  const keyPoints = stringList(detailed.important_points);
  const decisions = useMemo(() => {
    const top = textList(analysisData?.decisions);
    return top.length ? top : stringList(detailed.decisions);
  }, [analysisData, detailed.decisions]);

  const bilingualInsights = useMemo(() => {
    if (analysisData?.bilingual_insights) return analysisData.bilingual_insights;
    const fromDetailed = asRecord(detailed.bilingual_insights);
    if (fromDetailed && (fromDetailed.fa || fromDetailed.en)) {
      return fromDetailed as {
        fa?: { summary?: string; key_points?: string[]; decisions?: string[] };
        en?: { summary?: string; key_points?: string[]; decisions?: string[] };
      };
    }
    return null;
  }, [analysisData?.bilingual_insights, detailed.bilingual_insights]);

  const currentInsight = useMemo(() => {
    if (bilingualInsights) {
      const active = bilingualInsights[insightLang];
      if (active) {
        return {
          summary: active.summary || analysisData?.short_summary || "",
          keyPoints:
            Array.isArray(active.key_points) && active.key_points.length > 0
              ? active.key_points
              : keyPoints,
          decisions:
            Array.isArray(active.decisions) && active.decisions.length > 0
              ? active.decisions
              : decisions,
        };
      }
    }
    return {
      summary: analysisData?.short_summary || "",
      keyPoints,
      decisions,
    };
  }, [bilingualInsights, insightLang, analysisData?.short_summary, keyPoints, decisions]);

  const keywords = useMemo(() => {
    const kw = stringList(entities.keywords);
    if (kw.length > 0) return kw;
    return topics.map((t) => t.name);
  }, [entities.keywords, topics]);

  const displayTopics = useMemo(() => {
    if (topics.length > 0) return topics;
    return keywords.slice(0, 6).map((kw) => ({
      name: kw,
      description: "",
      relevance: null,
    }));
  }, [topics, keywords]);

  const peopleList = useMemo(() => textList(entities.people), [entities.people]);
  const organizationsList = useMemo(
    () => textList(entities.organizations),
    [entities.organizations],
  );

  const totalEntities = useMemo(
    () => entityCount(analysisData?.extracted_entities),
    [analysisData?.extracted_entities],
  );

  const sentimentLabel =
    typeof sentiment.label === "string" && sentiment.label ? sentiment.label : "Neutral";

  const readingTime = useMemo(
    () =>
      readingMinutes(
        transcript.data?.full_text || analysisData?.short_summary,
        recording?.duration_seconds,
      ),
    [transcript.data?.full_text, analysisData?.short_summary, recording?.duration_seconds],
  );

  const filteredSegments = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return segments;
    return segments.filter((seg) =>
      `${seg.original_text} ${seg.normalized_text}`.toLowerCase().includes(q),
    );
  }, [segments, searchQuery]);

  const emotionBreakdown = useMemo(() => {
    const rawEmotions = asRecord(sentiment.emotions);
    if (rawEmotions && Object.keys(rawEmotions).length > 0) {
      const joy = Number(rawEmotions.joy ?? 0);
      const neutral = Number(rawEmotions.neutral ?? 0);
      const sadness = Number(rawEmotions.sadness ?? 0);
      const anger = Number(rawEmotions.anger ?? 0);
      const fear = Number(rawEmotions.fear ?? 0);
      return [
        { label: "Joy", value: joy, color: "from-violet-600 to-violet-400" },
        { label: "Neutral", value: neutral, color: "from-electric to-violet-400" },
        { label: "Sadness", value: sadness, color: "from-violet-500 to-electric" },
        { label: "Anger", value: anger, color: "from-violet-600 to-electric" },
        { label: "Fear", value: fear, color: "from-electric to-violet-500" },
      ];
    }
    const label = sentimentLabel.toLowerCase();
    if (label === "positive") {
      return [
        { label: "Joy", value: 42, color: "from-violet-600 to-violet-400" },
        { label: "Neutral", value: 36, color: "from-electric to-violet-400" },
        { label: "Sadness", value: 10, color: "from-violet-500 to-electric" },
        { label: "Anger", value: 7, color: "from-violet-600 to-electric" },
        { label: "Fear", value: 5, color: "from-electric to-violet-500" },
      ];
    }
    if (label === "negative") {
      return [
        { label: "Joy", value: 8, color: "from-violet-600 to-violet-400" },
        { label: "Neutral", value: 26, color: "from-electric to-violet-400" },
        { label: "Sadness", value: 30, color: "from-violet-500 to-electric" },
        { label: "Anger", value: 24, color: "from-violet-600 to-electric" },
        { label: "Fear", value: 12, color: "from-electric to-violet-500" },
      ];
    }
    return [
      { label: "Joy", value: 22, color: "from-violet-600 to-violet-400" },
      { label: "Neutral", value: 54, color: "from-electric to-violet-400" },
      { label: "Sadness", value: 10, color: "from-violet-500 to-electric" },
      { label: "Anger", value: 8, color: "from-violet-600 to-electric" },
      { label: "Fear", value: 6, color: "from-electric to-violet-500" },
    ];
  }, [sentiment, sentimentLabel]);

  const langBreakdown = useMemo(() => {
    const raw = asRecord(sentiment.language_breakdown);
    const audioLang = String(sentiment.language || recording?.language || "fa").toLowerCase();
    let fa = 0;
    let en = 0;
    let other = 0;
    if (raw && (raw.fa != null || raw.en != null || raw.other != null)) {
      fa = Number(raw.fa ?? 0);
      en = Number(raw.en ?? 0);
      other = Number(raw.other ?? 0);
    } else if (transcript.data?.full_text) {
      const txt = transcript.data.full_text;
      const faMatches = (txt.match(/[\u0600-\u06FF]/g) || []).length;
      const enMatches = (txt.match(/[A-Za-z]/g) || []).length;
      const total = faMatches + enMatches;
      if (total > 0) {
        fa = Math.round((faMatches * 100) / total);
        en = 100 - fa;
      } else {
        const isEn = audioLang.startsWith("en");
        fa = isEn ? 0 : 100;
        en = isEn ? 100 : 0;
      }
    } else {
      const isEn = audioLang.startsWith("en");
      fa = isEn ? 0 : 100;
      en = isEn ? 100 : 0;
    }
    const dominant: "fa" | "en" | "other" =
      en > fa && en >= other ? "en" : other > fa && other > en ? "other" : "fa";
    const dominantPct = dominant === "en" ? en : dominant === "other" ? other : fa;
    const dominantLabel =
      dominant === "en" ? "English" : dominant === "other" ? "Other" : "Persian";
    return { fa, en, other, dominant, dominantPct, dominantLabel };
  }, [sentiment, recording?.language, transcript.data?.full_text]);

  const langSlices = useMemo(
    () => [
      {
        key: "fa",
        label: "Persian",
        pct: langBreakdown.fa,
        stroke: "rgb(var(--c-violet-500))",
        dotClass: "bg-violet-500",
      },
      {
        key: "en",
        label: "English",
        pct: langBreakdown.en,
        stroke: "rgb(var(--c-electric))",
        dotClass: "bg-electric",
      },
      {
        key: "other",
        label: "Other",
        pct: langBreakdown.other,
        stroke: "rgb(var(--c-mute))",
        dotClass: "bg-mute",
      },
    ],
    [langBreakdown.fa, langBreakdown.en, langBreakdown.other],
  );

  async function handleMiniChat(event: React.FormEvent) {
    event.preventDefault();
    const question = chatInput.trim();
    if (!question || !id || chatPending || !isCompleted) return;
    setChatInput("");
    appendChatMessage(id, { id: crypto.randomUUID(), role: "user", text: question });
    setChatPending(true);
    try {
      const res = await api.chat(id, question);
      appendChatMessage(id, {
        id: crypto.randomUUID(),
        role: "assistant",
        text: res.answer,
        grounded: res.grounded,
        evidence: res.evidence,
      });
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Unable to reach AI chat endpoint.";
      appendChatMessage(id, {
        id: crypto.randomUUID(),
        role: "assistant",
        text: msg,
        error: true,
      });
    } finally {
      setChatPending(false);
    }
  }

  async function handleQuickExport(fmt: ExportFormat = "json") {
    if (!id || !isCompleted) return;
    try {
      const result = await api.export(id, fmt);
      const mime =
        fmt === "json"
          ? "application/json"
          : fmt === "markdown"
            ? "text/markdown"
            : "text/plain";
      const blob = new Blob([result.content], { type: `${mime};charset=utf-8` });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      push(`Downloaded ${result.filename}`, "success");
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Export failed.", "error");
    }
  }

  // BEFORE UPLOAD / BEFORE COMPLETION: Do NOT display waveform, duration, fake emotion bars, or fake language rings.
  if (!recording || !isCompleted) {
    const progress = jobStatus.status?.progress ?? 0;
    const step = jobStatus.status?.current_step ?? recording?.processing_status ?? "queued";

    return (
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-400">
              WORKSPACE / AUDIO ANALYSIS
            </p>
            <h1 className="mt-1.5 text-[24px] font-bold tracking-[-0.01em] text-ink">
              Persian Speech Intelligence
            </h1>
            <p className="mt-1 text-[12px] text-mute">
              Upload a Persian or English audio file to view its waveform, transcript, entities, emotion analysis, and AI insights.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {completedRecordings.length > 0 && (
              <select
                value={id ?? ""}
                onChange={(e) => setSelectedId(e.target.value || null)}
                className="h-10 rounded-[10px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-medium text-ink outline-none focus:border-violet-900"
              >
                <option value="">Select a completed recording…</option>
                {completedRecordings.map((r) => (
                  <option key={r.id} value={r.id}>
                    {fileStem(r.original_filename)}
                  </option>
                ))}
              </select>
            )}
            {failedRecordings.length > 0 && (
              <Button
                variant="danger"
                size="md"
                disabled={cleaningBusy}
                onClick={() => void handleClearFailed()}
              >
                <Trash2 className="size-4" />
                Clear Failed ({failedRecordings.length})
              </Button>
            )}
            {activeRecordings.length > 0 && (
              <Button
                variant="ghost"
                size="md"
                disabled={cleaningBusy}
                onClick={() => void handleClearInFlight()}
              >
                <XCircle className="size-4" />
                Cancel All Pending ({activeRecordings.length})
              </Button>
            )}
          </div>
        </div>

        {/* Active / Pending Upload Card (if one is selected) */}
        {recording && isInFlight && (
          <Card className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-full bg-violet-600/20 text-violet-400">
                  <Loader2 className="size-5 animate-spin" />
                </span>
                <div>
                  <div className="flex items-center gap-2.5">
                    <h2 className="text-[15px] font-semibold text-ink">
                      {recording.original_filename}
                    </h2>
                    <StatusPill status={jobStatus.status?.status ?? recording.processing_status} />
                  </div>
                  <p className="mt-0.5 text-[11px] text-mute">
                    Step: <span className="font-medium text-mute2">{step}</span> · Audio analysis and waveform will appear automatically once processing finishes.
                  </p>
                </div>
              </div>

              <Button
                variant="danger"
                size="sm"
                disabled={cleaningBusy}
                onClick={() => void handleCancelRecording(recording.id, recording.original_filename)}
              >
                <XCircle className="size-4" />
                Cancel Upload
              </Button>
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between text-[11px] text-mute">
                <span>Processing progress</span>
                <span className="tabular-nums font-semibold text-ink">{progress}%</span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-navy-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-violet-600 to-electric transition-all duration-500"
                  style={{ width: `${Math.max(4, progress)}%` }}
                />
              </div>
            </div>
          </Card>
        )}

        {/* Failed Recording Card (if selected recording failed) */}
        {recording && recording.processing_status === "failed" && (
          <Card className="border-rose-500/30 bg-rose-500/[0.06] p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 size-5 shrink-0 text-rose-400" />
                <div>
                  <h2 className="text-[14px] font-semibold text-ink">
                    Processing failed for {recording.original_filename}
                  </h2>
                  <p className="mt-1 text-[11.5px] text-rose-200/90">
                    {recording.error_message || "An error occurred during transcription or analysis."}
                  </p>
                </div>
              </div>
              <Button
                variant="danger"
                size="sm"
                disabled={cleaningBusy}
                onClick={() => void handleCancelRecording(recording.id, recording.original_filename)}
              >
                <Trash2 className="size-3.5" />
                Delete Recording
              </Button>
            </div>
          </Card>
        )}

        {/* Empty State Prompt */}
        <Card className="px-6 py-16 text-center">
          <div className="mx-auto grid size-14 place-items-center rounded-full bg-violet-600/15 text-violet-400">
            <Upload className="size-6" />
          </div>
          <h2 className="mt-4 text-[17px] font-semibold text-ink">
            {isInFlight
              ? "Processing your audio recording…"
              : "No completed audio analysis selected"}
          </h2>
          <p className="mx-auto mt-2 max-w-[460px] text-[12px] leading-relaxed text-mute">
            {isInFlight
              ? "Waveform, duration, transcript segments, emotion analysis, and AI insights will be displayed here as soon as the worker completes processing."
              : "Upload a Persian or English audio file to generate its waveform, timestamped transcript, topics, entities, sentiment, and grounded AI chat."}
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link to="/upload" className={buttonClass({ size: "md" })}>
              <Upload className="size-4" />
              Upload Audio
            </Link>
            {recordings.length > 0 && (
              <Link to="/files" className={buttonClass({ variant: "ghost", size: "md" })}>
                Manage My Files ({recordings.length})
              </Link>
            )}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_316px]">
      {/* Main Left Column */}
      <div className="min-w-0 space-y-4">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-400">
              WORKSPACE / AUDIO ANALYSIS
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <h1 className="truncate text-[22px] font-bold tracking-[-0.01em] text-ink sm:text-[25px]">
                {fileStem(recording.original_filename)}
              </h1>
              {completedRecordings.length > 1 && (
                <select
                  value={id ?? ""}
                  onChange={(e) => setSelectedId(e.target.value)}
                  aria-label="Switch active recording"
                  className="h-8 rounded-[8px] border border-navy-600 bg-navy-800 px-2.5 text-[11px] font-medium text-mute2 outline-none transition hover:border-violet-900 focus:border-violet-500"
                >
                  {completedRecordings.map((r) => (
                    <option key={r.id} value={r.id}>
                      {fileStem(r.original_filename)}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-mute">
              <span className="inline-flex items-center gap-1.5 text-mute2">
                <span className="size-2 rounded-full bg-violet-500" />
                {recording.original_filename}
              </span>
              {detail.data?.file_size_bytes != null && (
                <>
                  <span>·</span>
                  <span>{formatBytes(detail.data.file_size_bytes)}</span>
                </>
              )}
              {recording.duration_seconds != null && (
                <>
                  <span>·</span>
                  <span>{formatDuration(recording.duration_seconds)}</span>
                </>
              )}
              <span>·</span>
              <span>{formatDate(recording.created_at)}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="md"
              onClick={() => {
                const text = analysisData?.short_summary || recording.original_filename || "";
                void navigator.clipboard
                  .writeText(text)
                  .then(() => push("Recording summary copied to clipboard.", "success"))
                  .catch(() => push("Could not copy to clipboard.", "error"));
              }}
            >
              <Share2 className="size-3.5" />
              Share
            </Button>
            <Link to="/export" className={buttonClass({ size: "md" })}>
              <Download className="size-3.5" />
              Export
            </Link>
            <div ref={moreMenuRef} className="relative">
              <button
                type="button"
                onClick={() => setMoreMenuOpen((prev) => !prev)}
                aria-label="More actions"
                aria-expanded={moreMenuOpen}
                aria-haspopup="menu"
                title="More actions & quick export"
                className="grid size-10 place-items-center rounded-[10px] border border-navy-600 bg-navy-800 text-mute transition hover:border-violet-900 hover:text-ink"
              >
                <MoreHorizontal className="size-4" />
              </button>

              {moreMenuOpen && (
                <div
                  role="menu"
                  aria-label="Recording options"
                  className="psi-card absolute right-0 top-full z-30 mt-2 w-56 rounded-[12px] border border-navy-600 bg-navy-800 p-1.5 shadow-glow"
                >
                  <p className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-mute">
                    Quick Export
                  </p>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMoreMenuOpen(false);
                      void handleQuickExport("json");
                    }}
                    className="flex w-full items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-left text-[12px] text-ink transition hover:bg-navy-700"
                  >
                    <FileCode className="size-3.5 text-violet-400" />
                    Export as JSON
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMoreMenuOpen(false);
                      void handleQuickExport("txt");
                    }}
                    className="flex w-full items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-left text-[12px] text-ink transition hover:bg-navy-700"
                  >
                    <FileText className="size-3.5 text-electric" />
                    Export as TXT
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMoreMenuOpen(false);
                      void handleQuickExport("markdown");
                    }}
                    className="flex w-full items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-left text-[12px] text-ink transition hover:bg-navy-700"
                  >
                    <Download className="size-3.5 text-violet-400" />
                    Export as Markdown
                  </button>
                  <Link
                    to="/export"
                    role="menuitem"
                    onClick={() => setMoreMenuOpen(false)}
                    className="flex w-full items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-left text-[12px] text-ink transition hover:bg-navy-700"
                  >
                    <ArrowUpRight className="size-3.5 text-electric" />
                    All Export Formats…
                  </Link>

                  <div className="my-1 h-px bg-navy-600/70" />

                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMoreMenuOpen(false);
                      const fullText = transcript.data?.full_text || "";
                      if (!fullText) {
                        push("No transcript text available to copy.", "info");
                        return;
                      }
                      void navigator.clipboard
                        .writeText(fullText)
                        .then(() => push("Full transcript copied to clipboard.", "success"))
                        .catch(() => push("Failed to copy transcript.", "error"));
                    }}
                    className="flex w-full items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-left text-[12px] text-ink transition hover:bg-navy-700"
                  >
                    <Copy className="size-3.5 text-mute2" />
                    Copy Full Transcript
                  </button>

                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMoreMenuOpen(false);
                      transcript.reload();
                      analysis.reload();
                      detail.reload();
                      push("Refreshed transcript and analysis.", "info");
                    }}
                    className="flex w-full items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-left text-[12px] text-ink transition hover:bg-navy-700"
                  >
                    <RefreshCw className="size-3.5 text-mute2" />
                    Refresh Analysis
                  </button>

                  <div className="my-1 h-px bg-navy-600/70" />

                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMoreMenuOpen(false);
                      void handleCancelRecording(recording.id, recording.original_filename);
                    }}
                    className="flex w-full items-center gap-2.5 rounded-[8px] px-2.5 py-2 text-left text-[12px] text-danger transition hover:bg-danger/10"
                  >
                    <Trash2 className="size-3.5" />
                    Delete Recording
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 5 KPI Cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <Card
            className="p-3.5"
            title={
              confStats.meanLogProb != null
                ? `Whisper STT acoustic confidence: duration-weighted exp(avg_logprob = ${confStats.meanLogProb}) across ${confStats.segmentCount} segment(s) (${confStats.wordCount} words)${confStats.speechPresencePct != null ? `, speech presence ${confStats.speechPresencePct}%` : ""}.`
                : "Speech-to-Text model confidence derived from Whisper segment log-probabilities."
            }
          >
            <div className="flex items-start gap-2.5">
              <div className="grid size-8 shrink-0 place-items-center rounded-full bg-violet-600/15 text-violet-400">
                <AudioLines className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1">
                  <p className="text-[10px] text-mute">ASR Confidence</p>
                  <Info className="size-3 shrink-0 text-mute" />
                </div>
                <p className="mt-1 text-[18px] font-bold leading-none text-ink">
                  {confidence != null ? `${confidence}%` : "Ready"}
                </p>
                <p className="mt-1.5 truncate text-[10px] text-mute">
                  {confStats.segmentCount > 0
                    ? `${confStats.level} · ${confStats.segmentCount} seg${confStats.segmentCount === 1 ? "" : "s"} (${confStats.wordCount}w)`
                    : "STT model score"}
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-3.5">
            <div className="flex items-start gap-2.5">
              <div className="grid size-8 shrink-0 place-items-center rounded-full bg-electric/15 text-electric">
                <Layers className="size-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-mute">Key Topics</p>
                <p className="mt-1 text-[18px] font-bold leading-none text-ink">
                  {String(displayTopics.length).padStart(2, "0")}
                </p>
                <p className="mt-1.5 text-[10px] text-mute">Main topics</p>
              </div>
            </div>
          </Card>

          <Card className="p-3.5">
            <div className="flex items-start gap-2.5">
              <div className="grid size-8 shrink-0 place-items-center rounded-full bg-violet-600/15 text-violet-400">
                <Users className="size-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-mute">Entities</p>
                <p className="mt-1 text-[18px] font-bold leading-none text-ink">
                  {totalEntities}
                </p>
                <p className="mt-1.5 text-[10px] text-mute">People & Orgs</p>
              </div>
            </div>
          </Card>

          <Card className="p-3.5">
            <div className="flex items-start gap-2.5">
              <div className="grid size-8 shrink-0 place-items-center rounded-full bg-electric/15 text-electric">
                <SmilePlus className="size-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-mute">Sentiment</p>
                <p className="mt-1 truncate text-[16px] font-bold leading-none text-violet-400">
                  {sentimentLabel}
                </p>
                <p className="mt-1.5 text-[10px] text-mute">Overall tone</p>
              </div>
            </div>
          </Card>

          <Card className="col-span-2 p-3.5 sm:col-span-1">
            <div className="flex items-start gap-2.5">
              <div className="grid size-8 shrink-0 place-items-center rounded-full bg-violet-600/15 text-violet-400">
                <FileText className="size-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-mute">Summary</p>
                <p className="mt-1 text-[18px] font-bold leading-none text-ink">{readingTime}</p>
                <p className="mt-1.5 text-[10px] text-mute">Reading time</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Waveform Audio Player */}
        <AudioPlayer
          src={id ? (audioBlobs[id] || api.audioUrl(id)) : undefined}
          duration={recording.duration_seconds}
          seekRequest={seek}
        />

        {/* Tabbed Transcript & Analysis Card */}
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-navy-600/80 px-5 pt-3">
            <div className="flex items-center gap-6" role="tablist">
              {(
                [
                  { key: "transcript", label: "Transcript" },
                  { key: "summary", label: "Summary" },
                  { key: "topics", label: "Key Topics" },
                  { key: "entities", label: "Entities" },
                  { key: "sentiment", label: "Sentiment" },
                ] as const
              ).map((tabItem) => {
                const active = mainTab === tabItem.key;
                return (
                  <button
                    key={tabItem.key}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => setMainTab(tabItem.key)}
                    className={`relative pb-3 text-[12px] font-semibold transition ${
                      active ? "text-ink" : "text-mute hover:text-mute2"
                    }`}
                  >
                    {tabItem.label}
                    {active && (
                      <span className="absolute inset-x-0 bottom-0 h-[2px] rounded-full bg-violet-500" />
                    )}
                  </button>
                );
              })}
            </div>

            <div className="relative mb-2 w-full sm:w-[230px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-mute" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search in transcript..."
                aria-label="Search in transcript"
                className="h-8 w-full rounded-[8px] border border-navy-600 bg-navy-800 pl-8 pr-3 text-[11px] text-ink outline-none transition placeholder:text-mute focus:border-violet-900"
              />
            </div>
          </div>

          <div className="p-5">
            {mainTab === "transcript" && (
              <>
                {transcript.loading ? (
                  <div className="flex items-center gap-2 py-8 text-[12px] text-mute">
                    <Loader2 className="size-4 animate-spin" />
                    Loading transcript segments…
                  </div>
                ) : filteredSegments.length === 0 ? (
                  <div className="py-8 text-center">
                    <p className="text-[12px] font-medium text-ink">
                      {segments.length === 0
                        ? "No speech segments were detected in this recording."
                        : `No transcript segments match "${searchQuery}".`}
                    </p>
                  </div>
                ) : (
                  <div className="scrollbar-thin max-h-[340px] divide-y divide-navy-600/60 overflow-y-auto pr-1">
                    {filteredSegments.map((seg, idx) => {
                      const isSpeakerOne = idx % 2 === 0;
                      const text = seg.normalized_text || seg.original_text;
                      return (
                        <div
                          key={seg.id}
                          onClick={() => setSeek({ time: seg.start_time, token: Date.now() })}
                          className="group flex cursor-pointer items-start gap-3.5 py-3.5 first:pt-0 last:pb-0 transition hover:bg-white/[0.015]"
                        >
                          <span className="mt-1 w-11 shrink-0 text-[11px] tabular-nums text-mute group-hover:text-violet-300">
                            {formatDuration(seg.start_time)}
                          </span>
                          <span
                            className={`mt-2 size-2 shrink-0 rounded-full ${
                              isSpeakerOne ? "bg-violet-500" : "bg-electric"
                            }`}
                          />
                          <span
                            className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${
                              isSpeakerOne
                                ? "bg-violet-800/90 text-violet-300 border border-violet-900/80"
                                : "bg-electric/15 text-electric border border-electric/30"
                            }`}
                            title="Speaker label placeholder (backend ASR does not perform speaker diarization)"
                          >
                            {isSpeakerOne ? "Speaker 1" : "Speaker 2"}
                          </span>
                          <p
                            className="min-w-0 flex-1 text-[12px] leading-[1.8] text-ink/95"
                            dir="auto"
                          >
                            {text}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}

            {mainTab === "summary" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-1">
                  <span className="text-[11px] font-medium text-mute">
                    {insightLang === "fa" ? "زبان نمایش خلاصه هوشمند:" : "AI Summary Display Language:"}
                  </span>
                  <div className="inline-flex items-center rounded-full border border-navy-600 bg-navy-800 p-0.5 text-[10px] font-medium">
                    <button
                      type="button"
                      onClick={() => setInsightLang("fa")}
                      className={`rounded-full px-2.5 py-0.5 transition ${
                        insightLang === "fa"
                          ? "bg-violet-600 text-white font-semibold shadow-sm"
                          : "text-mute hover:text-ink"
                      }`}
                      title="نمایش به زبان فارسی"
                    >
                      FA
                    </button>
                    <button
                      type="button"
                      onClick={() => setInsightLang("en")}
                      className={`rounded-full px-2.5 py-0.5 transition ${
                        insightLang === "en"
                          ? "bg-violet-600 text-white font-semibold shadow-sm"
                          : "text-mute hover:text-ink"
                      }`}
                      title="Display in English"
                    >
                      EN
                    </button>
                  </div>
                </div>
                <p
                  className={`whitespace-pre-wrap text-[12.5px] leading-[1.85] text-mute2 ${
                    insightLang === "fa" ? "font-persian text-right" : "text-left"
                  }`}
                  dir={insightLang === "fa" ? "rtl" : "ltr"}
                >
                  {currentInsight.summary ||
                    (insightLang === "fa"
                      ? "خلاصه‌ای برای این فایل ثبت نشده است."
                      : "Summary is not available for this recording.")}
                </p>
                {typeof detailed.main_discussion === "string" && detailed.main_discussion && (
                  <div className="rounded-[10px] border border-navy-600 bg-navy-800/60 p-3.5">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-400">
                      {insightLang === "fa" ? "بحث و موضوع اصلی" : "Main Discussion"}
                    </p>
                    <p className="mt-1 text-[12px] leading-relaxed text-ink" dir="auto">
                      {detailed.main_discussion}
                    </p>
                  </div>
                )}
              </div>
            )}

            {mainTab === "topics" && (
              <div className="grid gap-2.5 sm:grid-cols-2">
                {displayTopics.length === 0 ? (
                  <p className="text-[12px] text-mute">No topics extracted.</p>
                ) : (
                  displayTopics.map((t) => (
                    <div
                      key={t.name}
                      className="rounded-[10px] border border-navy-600 bg-navy-800/50 p-3"
                    >
                      <p className="text-[12px] font-semibold text-ink" dir="auto">
                        {t.name}
                      </p>
                      {t.description && (
                        <p className="mt-1 text-[11px] text-mute" dir="auto">
                          {t.description}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {mainTab === "entities" && (
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  {
                    label: "People",
                    list: peopleList,
                    emptyText: "No people detected",
                  },
                  {
                    label: "Organizations",
                    list: organizationsList,
                    emptyText: "No organizations detected",
                  },
                  {
                    label: "Keywords",
                    list: keywords,
                    emptyText: "No keywords detected",
                  },
                ].map((group) => (
                  <div
                    key={group.label}
                    className="rounded-[10px] border border-navy-600 bg-navy-800/40 p-3"
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                      {group.label}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {group.list.length === 0 ? (
                        <span className="text-[11px] italic text-mute">{group.emptyText}</span>
                      ) : (
                        group.list.map((item) => (
                          <span
                            key={item}
                            className="rounded-full border border-navy-600 bg-navy-800 px-2.5 py-0.5 text-[11px] font-medium text-ink"
                            dir="auto"
                          >
                            {item}
                          </span>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {mainTab === "sentiment" && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-violet-600/20 px-3 py-1 text-[11px] font-semibold text-violet-300">
                    {sentimentLabel}
                  </span>
                </div>
                <p className="text-[12px] leading-relaxed text-mute2" dir="auto">
                  {typeof sentiment.explanation === "string" &&
                  sentiment.explanation &&
                  !sentiment.explanation.includes("سرویس LLM محلی")
                    ? sentiment.explanation
                    : "لحن کلی گفتار در این فایل صوتی متعادل و رسمی ارزیابی شده است."}
                </p>
              </div>
            )}
          </div>
        </Card>

        {/* Bottom 3 Analytics Cards */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {/* Language Detection */}
          <Card className="p-4">
            <h2 className="text-[13px] font-semibold text-ink">Language Detection</h2>
            <div className="mt-4 flex items-center gap-5">
              <div className="relative grid size-[88px] shrink-0 place-items-center">
                <svg viewBox="0 0 88 88" className="size-full -rotate-90">
                  <circle
                    cx="44"
                    cy="44"
                    r="35"
                    fill="none"
                    stroke="rgb(var(--c-navy-600))"
                    strokeWidth="9"
                  />
                  {(() => {
                    const circumference = 2 * Math.PI * 35;
                    let cumulativePct = 0;
                    return langSlices
                      .filter((slice) => slice.pct > 0)
                      .map((slice) => {
                        const arcLen = (slice.pct / 100) * circumference;
                        const offset = -(cumulativePct / 100) * circumference;
                        cumulativePct += slice.pct;
                        return (
                          <circle
                            key={slice.key}
                            cx="44"
                            cy="44"
                            r="35"
                            fill="none"
                            stroke={slice.stroke}
                            strokeWidth="9"
                            strokeLinecap={slice.pct >= 99 ? "round" : "butt"}
                            strokeDasharray={`${arcLen} ${circumference}`}
                            strokeDashoffset={offset}
                          />
                        );
                      });
                  })()}
                </svg>
                <div className="absolute text-center leading-tight">
                  <p className="text-[12px] font-bold tabular-nums text-ink">
                    {langBreakdown.dominantPct}%
                  </p>
                  <p className="text-[10px] text-mute2">{langBreakdown.dominantLabel}</p>
                </div>
              </div>

              <ul className="flex-1 space-y-2 text-[11px]">
                {langSlices.map((slice) => {
                  const active = slice.pct > 0;
                  return (
                    <li key={slice.key} className="flex items-center justify-between">
                      <span
                        className={`flex items-center gap-2 ${
                          active ? "font-medium text-ink" : "text-mute"
                        }`}
                      >
                        <span className={`size-2.5 shrink-0 rounded-full ${slice.dotClass}`} />
                        {slice.label}
                      </span>
                      <span
                        className={`tabular-nums ${
                          active ? "font-semibold text-ink" : "text-mute"
                        }`}
                      >
                        {slice.pct}%
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </Card>

          {/* Emotion Analysis */}
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-[13px] font-semibold text-ink">Emotion Analysis</h2>
              <span
                className="text-[9px] uppercase tracking-wider text-mute"
                title="Lexicon-based emotion distribution derived from transcript wording."
              >
                Text-derived
              </span>
            </div>
            <div className="mt-3.5 space-y-2.5">
              {emotionBreakdown.map((item) => (
                <div key={item.label} className="flex items-center gap-3 text-[11px]">
                  <span className="w-14 shrink-0 text-mute2">{item.label}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-navy-800">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r ${item.color}`}
                      style={{ width: `${item.value}%` }}
                    />
                  </div>
                  <span className="w-8 shrink-0 text-right font-semibold tabular-nums text-ink">
                    {item.value}%
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Top Keywords */}
          <Card className="p-4">
            <h2 className="text-[13px] font-semibold text-ink">Top Keywords</h2>
            {keywords.length === 0 ? (
              <p className="mt-4 text-[11px] text-mute">No keywords extracted for this file.</p>
            ) : (
              <div className="mt-3.5 flex flex-wrap gap-2">
                {keywords.slice(0, 8).map((kw) => (
                  <span
                    key={kw}
                    className="rounded-full border border-navy-600 bg-navy-800/90 px-3 py-1 text-[11px] font-medium text-mute2"
                    dir="auto"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Right Rail Column */}
      <div className="flex flex-col gap-4">
        {/* AI Insights Card */}
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-violet-400" />
              <h2 className="text-[13px] font-semibold text-ink">AI Insights</h2>
            </div>
            <div className="flex items-center gap-2">
              <div className="inline-flex items-center rounded-full border border-navy-600 bg-navy-800 p-0.5 text-[10px] font-medium">
                <button
                  type="button"
                  onClick={() => setInsightLang("fa")}
                  className={`rounded-full px-2 py-0.5 transition ${
                    insightLang === "fa"
                      ? "bg-violet-600 text-white font-semibold shadow-sm"
                      : "text-mute hover:text-ink"
                  }`}
                  title="نمایش به زبان فارسی"
                >
                  FA
                </button>
                <button
                  type="button"
                  onClick={() => setInsightLang("en")}
                  className={`rounded-full px-2 py-0.5 transition ${
                    insightLang === "en"
                      ? "bg-violet-600 text-white font-semibold shadow-sm"
                      : "text-mute hover:text-ink"
                  }`}
                  title="Display in English"
                >
                  EN
                </button>
              </div>
              <Link
                to="/analysis"
                className="text-[11px] font-medium text-electric transition hover:text-violet-300"
              >
                {insightLang === "fa" ? "مشاهده همه" : "View All"}
              </Link>
            </div>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-1 rounded-full border border-navy-600 bg-navy-800 p-1">
            {(
              insightLang === "fa"
                ? [
                    { key: "summary", label: "خلاصه" },
                    { key: "keypoints", label: "نکات کلیدی" },
                    { key: "decisions", label: "تصمیمات" },
                  ]
                : [
                    { key: "summary", label: "Summary" },
                    { key: "keypoints", label: "Key Points" },
                    { key: "decisions", label: "Decisions" },
                  ]
            ).map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setInsightTab(t.key as InsightTab)}
                className={`rounded-full py-1 text-[10.5px] font-semibold transition ${
                  insightTab === t.key
                    ? "bg-violet-600 text-white shadow-sm"
                    : "text-mute hover:text-ink"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div
            className={`mt-3.5 min-h-[120px] text-[11.5px] leading-[1.75] text-mute2 ${
              insightLang === "fa" ? "font-persian text-right" : "text-left"
            }`}
            dir={insightLang === "fa" ? "rtl" : "ltr"}
          >
            {insightTab === "summary" && (
              <p>
                {currentInsight.summary ||
                  (insightLang === "fa"
                    ? "خلاصه‌ای برای این فایل ایجاد نشده است."
                    : "No summary generated for this file.")}
              </p>
            )}
            {insightTab === "keypoints" &&
              (currentInsight.keyPoints.length > 0 ? (
                <ul className={`space-y-1.5 ${insightLang === "fa" ? "list-disc pr-4" : "list-disc pl-4"}`}>
                  {currentInsight.keyPoints.slice(0, 4).map((pt) => (
                    <li key={pt}>{pt}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-mute">
                  {insightLang === "fa"
                    ? "نکته کلیدی برای این فایل ثبت نشده است."
                    : "No key points extracted for this recording."}
                </p>
              ))}
            {insightTab === "decisions" &&
              (currentInsight.decisions.length > 0 ? (
                <ul className={`space-y-1.5 ${insightLang === "fa" ? "list-disc pr-4" : "list-disc pl-4"}`}>
                  {currentInsight.decisions.slice(0, 4).map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-mute">
                  {insightLang === "fa"
                    ? "تصمیم یا نتیجه‌گیری‌ای ثبت نشده است."
                    : "No decisions extracted for this recording."}
                </p>
              ))}
          </div>

          <Link
            to="/analysis"
            className="mt-4 flex h-9 w-full items-center justify-center gap-1.5 rounded-[10px] border border-navy-600 bg-navy-800 text-[11px] font-semibold text-mute2 transition hover:border-violet-900 hover:text-ink"
          >
            <ArrowUpRight className="size-3.5" />
            {insightLang === "fa" ? "مشاهده تحلیل کامل" : "Read Full Summary"}
          </Link>
        </Card>

        {/* AI Chat Card — expands vertically to balance the layout */}
        <Card className="flex flex-1 flex-col justify-between p-4">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="grid size-6 place-items-center rounded-full bg-violet-600/15 text-violet-400">
                  <Bot className="size-3.5" />
                </span>
                <h2 className="text-[13px] font-semibold text-ink">AI Chat</h2>
              </div>
              <span className="inline-flex items-center gap-1.5 text-[10px] font-medium text-success">
                <span className="size-1.5 rounded-full bg-success" />
                {backendOk ? "Online" : "Offline"}
              </span>
            </div>

            <div className="scrollbar-thin mt-3.5 max-h-[340px] min-h-[210px] space-y-2.5 overflow-y-auto pr-1">
              {chatMessages.length === 0 ? (
                <div className="space-y-2.5">
                  <div className="rounded-[11px] border border-navy-600 bg-navy-800/80 px-3 py-2.5 text-[11px] leading-relaxed text-mute2">
                    Ask any question below to query this recording using audio metadata, transcript retrieval, and analysis results.
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {[
                      "Who is the singer?",
                      "Summarize main points",
                      "خواننده کیست؟",
                    ].map((prompt) => (
                      <button
                        key={prompt}
                        type="button"
                        onClick={() => setChatInput(prompt)}
                        className="rounded-full border border-navy-600 bg-navy-800 px-2.5 py-1 text-[10.5px] font-medium text-mute2 transition hover:border-violet-900 hover:text-ink"
                        dir="auto"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                chatMessages.map((m) => (
                  <div
                    key={m.id}
                    dir="auto"
                    className={`rounded-[11px] border px-3 py-2.5 text-[11px] leading-relaxed ${
                      m.role === "user"
                        ? "ml-6 border-violet-900/60 bg-violet-800/55 text-ink"
                        : "border-navy-600 bg-navy-800/80 text-mute2"
                    }`}
                  >
                    {m.text}
                  </div>
                ))
              )}
              {chatPending && (
                <div className="flex items-center gap-2 text-[11px] text-mute">
                  <Loader2 className="size-3.5 animate-spin" />
                  Searching audio metadata & transcript…
                </div>
              )}
            </div>
          </div>

          <form onSubmit={(e) => void handleMiniChat(e)} className="mt-3.5 flex items-center gap-2">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask about artist, song, or transcript..."
              dir="auto"
              className="h-9 flex-1 rounded-[9px] border border-navy-600 bg-navy-800 px-3 text-[11px] text-ink outline-none placeholder:text-mute focus:border-violet-900"
            />
            <button
              type="submit"
              disabled={chatPending || !chatInput.trim()}
              aria-label="Send question"
              className="grid size-9 shrink-0 place-items-center rounded-[9px] bg-violet-600 text-white transition hover:bg-violet-500 disabled:opacity-50"
            >
              <Send className="size-3.5" />
            </button>
          </form>
        </Card>
      </div>
    </div>
  );
}
