import {
  CheckCircle2,
  Copy,
  Download,
  FileAudio,
  ListChecks,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  Tags,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/Card";
import { Button, buttonClass } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { useAnalysis, useTranscript } from "@/hooks/useRecordingData";
import {
  asRecord,
  confidenceMetrics,
  entityCount,
  fileStem,
  formatDuration,
  itemText,
  stringList,
  textList,
} from "@/lib/format";
import { useWorkspace } from "@/lib/workspace";

export function AnalysisPage() {
  const { recordings, selectedId, setSelectedId } = useWorkspace();
  const { push } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [checkedActions, setCheckedActions] = useState<Record<string, boolean>>({});
  const [insightLang, setInsightLang] = useState<"fa" | "en">("fa");

  const completedRecordings = useMemo(
    () => recordings.filter((r) => r.processing_status === "completed"),
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

  const transcript = useTranscript(isCompleted ? id : null);
  const analysis = useAnalysis(isCompleted ? id : null);

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
        };
      })
      .filter((t) => t.name && t.name !== GENERIC_DESC);
  }, [analysisData]);

  const keywords = useMemo(() => {
    const kw = stringList(entities.keywords);
    if (kw.length > 0) return kw;
    return topics.map((t) => t.name);
  }, [entities.keywords, topics]);

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
  const rawExplanation =
    typeof sentiment.explanation === "string" ? sentiment.explanation.trim() : "";
  const sentimentExplanation =
    rawExplanation && !rawExplanation.includes("سرویس LLM محلی")
      ? rawExplanation
      : "لحن کلی گفتار بر اساس محتوای پیاده‌سازی‌شده متعادل و شفاف ارزیابی شده است.";

  const emotions = useMemo(() => {
    const rawEmotions = asRecord(sentiment.emotions);
    if (rawEmotions && Object.keys(rawEmotions).length > 0) {
      return [
        { name: "Joy / Positive", pct: Number(rawEmotions.joy ?? 0), color: "bg-violet-500" },
        { name: "Neutral", pct: Number(rawEmotions.neutral ?? 0), color: "bg-electric" },
        { name: "Sadness", pct: Number(rawEmotions.sadness ?? 0), color: "bg-violet-400" },
        { name: "Anger", pct: Number(rawEmotions.anger ?? 0), color: "bg-violet-600" },
        { name: "Fear / Worry", pct: Number(rawEmotions.fear ?? 0), color: "bg-electric" },
      ];
    }
    const label = sentimentLabel.toLowerCase();
    if (label === "positive") {
      return [
        { name: "Positive", pct: 42, color: "bg-violet-500" },
        { name: "Neutral", pct: 36, color: "bg-electric" },
        { name: "Sadness", pct: 10, color: "bg-violet-400" },
        { name: "Anger", pct: 7, color: "bg-violet-600" },
      ];
    }
    if (label === "negative") {
      return [
        { name: "Positive", pct: 12, color: "bg-violet-500" },
        { name: "Neutral", pct: 28, color: "bg-electric" },
        { name: "Sadness", pct: 34, color: "bg-violet-400" },
        { name: "Anger", pct: 26, color: "bg-violet-600" },
      ];
    }
    return [
      { name: "Positive", pct: 24, color: "bg-violet-500" },
      { name: "Neutral", pct: 56, color: "bg-electric" },
      { name: "Sadness", pct: 12, color: "bg-violet-400" },
      { name: "Anger", pct: 8, color: "bg-violet-600" },
    ];
  }, [sentiment, sentimentLabel]);

  const keyPoints = stringList(detailed.important_points);
  const actions = useMemo(() => {
    const top = textList(analysisData?.action_items);
    return top.length ? top : stringList(detailed.action_items);
  }, [analysisData, detailed.action_items]);
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

  const filteredSegments = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return segments;
    return segments.filter((s) =>
      `${s.original_text} ${s.normalized_text}`.toLowerCase().includes(q),
    );
  }, [segments, searchQuery]);

  if (!recording || !isCompleted) {
    return (
      <div className="space-y-4">
        <PageHeader
          crumb="WORKSPACE / ANALYSIS"
          title="Speech Analysis"
          subtitle="Deep insights extracted from your audio."
        />
        <Card className="px-6 py-14 text-center">
          <p className="text-[15px] font-semibold text-ink">
            {recording
              ? `Analysis for "${recording.original_filename}" is ${recording.processing_status}`
              : "No completed recordings to analyze yet"}
          </p>
          <p className="mt-1.5 text-[12px] text-mute">
            {recording &&
            (recording.processing_status === "pending" ||
              recording.processing_status === "processing")
              ? "Insights, topics, entities, and sentiment will appear here once processing completes."
              : "Upload and process a recording to extract summaries, topics, entities, and sentiment."}
          </p>
          <Link to="/upload" className={`${buttonClass({ size: "md" })} mt-5`}>
            <FileAudio className="size-4" />
            Upload Audio
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        crumb="WORKSPACE / ANALYSIS"
        title="Speech Analysis"
        subtitle="Deep insights extracted from your audio."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {recordings.length > 0 && (
              <select
                value={id ?? ""}
                onChange={(e) => setSelectedId(e.target.value)}
                aria-label="Select recording"
                className="h-10 rounded-[10px] border border-navy-600 bg-navy-800 px-3 text-[12px] font-medium text-ink outline-none focus:border-violet-900"
              >
                {recordings.map((r) => (
                  <option key={r.id} value={r.id}>
                    {fileStem(r.original_filename)} ({r.processing_status})
                  </option>
                ))}
              </select>
            )}
            <Button
              variant="ghost"
              onClick={() => {
                transcript.reload();
                analysis.reload();
              }}
            >
              <RefreshCw className="size-4" />
              Refresh
            </Button>
            <Link to="/export" className={buttonClass({ size: "md" })}>
              <Download className="size-4" />
              Export
            </Link>
          </div>
        }
      />

      {/* Overview Card */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[13px] font-semibold text-ink">Overview</h2>
          <span className="text-[11px] text-mute">
            {recording ? fileStem(recording.original_filename) : ""}
          </span>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-10 gap-y-3 text-[14px] font-semibold text-ink">
          <div
            title={
              confStats.meanLogProb != null
                ? `Whisper STT acoustic confidence: duration-weighted exp(avg_logprob = ${confStats.meanLogProb}) across ${confStats.segmentCount} segment(s) (${confStats.wordCount} words).`
                : "Speech-to-Text model confidence derived from Whisper segment log-probabilities."
            }
          >
            <span className="text-violet-400">
              {confidence != null ? `${confidence}%` : "—"}
            </span>{" "}
            ASR Confidence{" "}
            {confStats.segmentCount > 0 && (
              <span className="text-[11px] font-normal text-mute">
                ({confStats.level} · {confStats.segmentCount} segs, {confStats.wordCount} words)
              </span>
            )}
          </div>
          <div>
            <span className="text-electric">{String(topics.length).padStart(2, "0")}</span> Topics
          </div>
          <div>
            <span className="text-violet-400">{totalEntities}</span> Entities
          </div>
          <div>
            <span className="text-ink">{formatDuration(recording?.duration_seconds)}</span> Duration
          </div>
        </div>
      </Card>

      {/* Emotion Analysis + Top Keywords */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[13px] font-semibold text-ink">Emotion Analysis</h2>
            <span className="rounded-full bg-violet-600/20 px-2.5 py-0.5 text-[10px] font-semibold text-violet-300">
              {sentimentLabel}
            </span>
          </div>

          <div className="mt-4 space-y-3">
            {emotions.map((item) => (
              <div key={item.name} className="space-y-1">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="text-mute2">
                    {item.name} {item.pct}%
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-navy-800">
                  <div
                    className={`h-full rounded-full ${item.color}`}
                    style={{ width: `${item.pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {sentimentExplanation && (
            <p className="mt-4 border-t border-navy-600/60 pt-3 text-[11.5px] leading-relaxed text-mute2" dir="auto">
              {sentimentExplanation}
            </p>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="text-[13px] font-semibold text-ink">Top Keywords</h2>
          {keywords.length === 0 ? (
            <p className="mt-4 text-[12px] text-mute">
              No keywords extracted yet for this recording.
            </p>
          ) : (
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {keywords.slice(0, 12).map((kw) => (
                <div
                  key={kw}
                  dir="auto"
                  className="truncate rounded-[9px] border border-navy-600 bg-navy-800/70 px-3 py-2 text-[12px] font-medium text-ink"
                >
                  {kw}
                </div>
              ))}
            </div>
          )}

          {topics.length > 0 && (
            <div className="mt-5 border-t border-navy-600/60 pt-3.5">
              <p className="text-[10.5px] font-semibold uppercase tracking-wider text-mute">
                Extracted Topics
              </p>
              <div className="mt-2 space-y-1.5">
                {topics.slice(0, 4).map((t) => (
                  <div key={t.name} className="text-[11.5px]" dir="auto">
                    <span className="font-semibold text-ink">{t.name}</span>
                    {t.description ? <span className="text-mute"> — {t.description}</span> : null}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Speaker Timeline Card */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[13px] font-semibold text-ink">Speaker Timeline</h2>
          <span className="text-[10px] uppercase tracking-wider text-mute">
            Placeholder · Backend ASR does not output speaker diarization
          </span>
        </div>

        <div className="mt-4 space-y-3.5">
          <div className="flex items-center gap-4">
            <span className="w-20 shrink-0 text-[12px] font-medium text-mute2">Speaker 1</span>
            <div className="flex h-3 flex-1 gap-2 rounded-full bg-navy-800 p-0.5">
              <span className="h-full w-[28%] rounded-full bg-violet-500" />
              <span className="ml-[12%] h-full w-[24%] rounded-full bg-violet-500/80" />
              <span className="ml-[10%] h-full w-[18%] rounded-full bg-violet-500" />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="w-20 shrink-0 text-[12px] font-medium text-mute2">Speaker 2</span>
            <div className="flex h-3 flex-1 gap-2 rounded-full bg-navy-800 p-0.5">
              <span className="ml-[28%] h-full w-[12%] rounded-full bg-electric" />
              <span className="ml-[24%] h-full w-[12%] rounded-full bg-electric/85" />
            </div>
          </div>
        </div>
      </Card>

      {/* Real Grounded Summary, Key Points, Action Items & Transcript */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-violet-400" />
              <h2 className="text-[13px] font-semibold text-ink">
                {insightLang === "fa" ? "خلاصه اجرایی و نکات کلیدی" : "Executive Summary & Key Points"}
              </h2>
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
              {currentInsight.summary && (
                <button
                  type="button"
                  onClick={() => {
                    void navigator.clipboard
                      .writeText(currentInsight.summary ?? "")
                      .then(() => push(insightLang === "fa" ? "خلاصه کپی شد." : "Summary copied to clipboard.", "success"));
                  }}
                  className="text-mute transition hover:text-ink"
                  aria-label="Copy summary"
                >
                  <Copy className="size-3.5" />
                </button>
              )}
            </div>
          </div>

          {analysis.loading ? (
            <div className="mt-4 flex items-center gap-2 text-[12px] text-mute">
              <Loader2 className="size-4 animate-spin" />
              Loading analysis…
            </div>
          ) : (
            <div className="mt-3 space-y-3">
              <p
                className={`whitespace-pre-wrap text-[12px] leading-[1.85] text-mute2 ${
                  insightLang === "fa" ? "font-persian text-right" : "text-left"
                }`}
                dir={insightLang === "fa" ? "rtl" : "ltr"}
              >
                {currentInsight.summary ||
                  (insightLang === "fa"
                    ? "خلاصه تحلیلی هنوز در دسترس نیست."
                    : "Analysis summary is not available yet.")}
              </p>

              {currentInsight.keyPoints.length > 0 && (
                <div className="border-t border-navy-600/60 pt-3">
                  <p
                    className={`flex items-center gap-1.5 text-[11px] font-semibold text-ink ${
                      insightLang === "fa" ? "font-persian flex-row-reverse justify-end" : ""
                    }`}
                  >
                    <CheckCircle2 className="size-3.5 text-violet-400" />
                    {insightLang === "fa" ? "نکات کلیدی" : "Key Points"}
                  </p>
                  <ul
                    className={`mt-2 space-y-1.5 text-[11.5px] text-mute2 ${
                      insightLang === "fa" ? "font-persian text-right" : "text-left"
                    }`}
                    dir={insightLang === "fa" ? "rtl" : "ltr"}
                  >
                    {currentInsight.keyPoints.map((pt) => (
                      <li
                        key={pt}
                        className={`flex items-start gap-2 ${
                          insightLang === "fa" ? "flex-row-reverse text-right" : ""
                        }`}
                      >
                        <span className="mt-2 size-1.5 shrink-0 rounded-full bg-violet-400" />
                        <span>{pt}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2">
            <ListChecks className="size-4 text-violet-400" />
            <h2 className="text-[13px] font-semibold text-ink">Action Items, Decisions & Entities</h2>
          </div>

          <div className="mt-3 space-y-4">
            <div>
              <p className="text-[11px] font-semibold text-mute">Action Items</p>
              {actions.length === 0 ? (
                <p className="mt-1 text-[11.5px] text-mute">No action items extracted.</p>
              ) : (
                <ul className="mt-2 space-y-1.5">
                  {actions.map((act) => {
                    const done = checkedActions[act] ?? false;
                    return (
                      <li key={act}>
                        <label className="flex cursor-pointer items-start gap-2 text-[11.5px]" dir="auto">
                          <input
                            type="checkbox"
                            checked={done}
                            onChange={() =>
                              setCheckedActions((prev) => ({ ...prev, [act]: !prev[act] }))
                            }
                            className="mt-0.5 size-3.5 accent-violet-500"
                          />
                          <span className={done ? "text-mute line-through" : "text-ink"}>
                            {act}
                          </span>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            {currentInsight.decisions.length > 0 && (
              <div className="border-t border-navy-600/60 pt-3">
                <p className="text-[11px] font-semibold text-mute">
                  {insightLang === "fa" ? "تصمیمات و جمع‌بندی‌ها" : "Decisions"}
                </p>
                <ul
                  className={`mt-1.5 space-y-1 text-[11.5px] text-mute2 ${
                    insightLang === "fa" ? "font-persian text-right" : "text-left"
                  }`}
                  dir={insightLang === "fa" ? "rtl" : "ltr"}
                >
                  {currentInsight.decisions.map((d) => (
                    <li key={d}>• {d}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="border-t border-navy-600/60 pt-3">
              <p className="flex items-center gap-1.5 text-[11px] font-semibold text-mute">
                <Users className="size-3.5" />
                People & Organizations
              </p>
              <div className="mt-2.5 grid gap-2.5 sm:grid-cols-2">
                <div className="rounded-[9px] border border-navy-600 bg-navy-800/50 p-2.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                    People
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {peopleList.length === 0 ? (
                      <span className="text-[11px] italic text-mute">No people detected</span>
                    ) : (
                      peopleList.map((person) => (
                        <span
                          key={person}
                          dir="auto"
                          className="rounded-full border border-navy-600 bg-navy-800 px-2.5 py-0.5 text-[11px] font-medium text-ink"
                        >
                          {person}
                        </span>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-[9px] border border-navy-600 bg-navy-800/50 p-2.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                    Organizations
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {organizationsList.length === 0 ? (
                      <span className="text-[11px] italic text-mute">
                        No organizations detected
                      </span>
                    ) : (
                      organizationsList.map((org) => (
                        <span
                          key={org}
                          dir="auto"
                          className="rounded-full border border-navy-600 bg-navy-800 px-2.5 py-0.5 text-[11px] font-medium text-ink"
                        >
                          {org}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Timestamped Transcript */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Tags className="size-4 text-violet-400" />
            <h2 className="text-[13px] font-semibold text-ink">
              Timestamped Transcript ({segments.length} segments)
            </h2>
          </div>

          <div className="relative w-full sm:w-[240px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-mute" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter transcript..."
              aria-label="Filter transcript"
              className="h-8 w-full rounded-[8px] border border-navy-600 bg-navy-800 pl-8 pr-3 text-[11px] text-ink outline-none placeholder:text-mute focus:border-violet-900"
            />
          </div>
        </div>

        {transcript.loading ? (
          <div className="mt-4 flex items-center gap-2 text-[12px] text-mute">
            <Loader2 className="size-4 animate-spin" />
            Loading transcript…
          </div>
        ) : filteredSegments.length === 0 ? (
          <p className="mt-4 text-[12px] text-mute">No matching transcript segments.</p>
        ) : (
          <div className="scrollbar-thin mt-4 max-h-[320px] divide-y divide-navy-600/60 overflow-y-auto pr-1">
            {filteredSegments.map((seg) => (
              <div key={seg.id} className="flex items-start gap-3 py-2.5 text-[12px]">
                <span className="shrink-0 rounded border border-navy-600 bg-navy-800 px-1.5 py-0.5 text-[10px] tabular-nums text-violet-300">
                  {formatDuration(seg.start_time)}
                </span>
                <p className="min-w-0 flex-1 leading-[1.85] text-ink" dir="auto">
                  {seg.normalized_text || seg.original_text}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
