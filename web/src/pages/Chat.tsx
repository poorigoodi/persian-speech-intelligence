import {
  ArrowUp,
  Loader2,
  Quote,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/Card";
import { Button, buttonClass } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api, ApiError } from "@/lib/api";
import { fileStem, formatDuration } from "@/lib/format";
import type { WorkspaceChatMessage } from "@/lib/workspace";
import { useWorkspace } from "@/lib/workspace";

const SUGGESTIONS = [
  "موضوع اصلی این فایل صوتی چیست؟",
  "چه نکات مهمی مطرح شد؟",
  "گوینده در این فایل چه کسی است و چه می‌گوید؟",
  "Summarize the main points discussed.",
];

export function ChatPage() {
  const {
    recordings,
    selectedId,
    setSelectedId,
    chatMessagesByRec,
    appendChatMessage,
    clearChatMessages,
    chatDraftByRec,
    setChatDraft,
  } = useWorkspace();
  const [pending, setPending] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const recording = useMemo(
    () => recordings.find((item) => item.id === selectedId) ?? recordings[0] ?? null,
    [recordings, selectedId],
  );
  const recordingId = recording?.id ?? null;
  const ready = recording?.processing_status === "completed";
  const messages = recordingId ? chatMessagesByRec[recordingId] ?? [] : [];
  const input = recordingId ? chatDraftByRec[recordingId] ?? "" : "";
  const setInput = (val: string) => {
    if (recordingId) setChatDraft(recordingId, val);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);

  async function send(question: string) {
    const text = question.trim();
    if (!text || !recordingId || pending || !ready) return;

    setInput("");
    const userMsg: WorkspaceChatMessage = { id: crypto.randomUUID(), role: "user", text };
    appendChatMessage(recordingId, userMsg);
    setPending(true);

    try {
      const response = await api.chat(recordingId, text);
      const assistantMsg: WorkspaceChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: response.answer,
        grounded: response.grounded,
        evidence: response.evidence,
      };
      appendChatMessage(recordingId, assistantMsg);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "The assistant is unavailable right now.";
      const errMsg: WorkspaceChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: message,
        error: true,
      };
      appendChatMessage(recordingId, errMsg);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        crumb="WORKSPACE / AI CHAT"
        title="AI Chat"
        subtitle="Ask questions about your transcribed audio."
        actions={
          messages.length > 0 && recordingId ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => clearChatMessages(recordingId)}
            >
              <Trash2 className="size-3.5" />
              Clear Chat
            </Button>
          ) : undefined
        }
      />

      {recordings.length === 0 ? (
        <Card className="px-6 py-14 text-center">
          <h2 className="text-[16px] font-semibold text-ink">No recordings available</h2>
          <p className="mx-auto mt-2 max-w-[400px] text-[12px] text-mute">
            Upload a Persian or English audio file first to start asking grounded questions over its transcript.
          </p>
          <Link to="/upload" className={`${buttonClass({ size: "md" })} mt-5`}>
            <Upload className="size-4" />
            Upload Audio
          </Link>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
          {/* Left Card: Conversations */}
          <Card className="flex flex-col justify-between p-5">
            <div>
              <h2 className="text-[13px] font-semibold text-ink">Conversations</h2>
              <ul className="mt-4 space-y-2">
                {recordings.map((rec) => {
                  const active = rec.id === recordingId;
                  return (
                    <li key={rec.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(rec.id)}
                        className={`w-full rounded-[10px] border px-3 py-2.5 text-left transition ${
                          active
                            ? "border-violet-900 bg-violet-800/70 text-ink"
                            : "border-transparent bg-navy-800/40 text-mute2 hover:border-navy-600 hover:text-ink"
                        }`}
                      >
                        <p className="truncate text-[12px] font-medium">
                          {fileStem(rec.original_filename)}
                        </p>
                        <div className="mt-1 flex items-center justify-between text-[10px] text-mute">
                          <span>{formatDuration(rec.duration_seconds)}</span>
                          <StatusBadge status={rec.processing_status} />
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div className="mt-6 border-t border-navy-600/60 pt-4">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-mute2">
                <Sparkles className="size-3.5 text-violet-400" />
                Suggested Prompts
              </div>
              <div className="mt-2.5 space-y-1.5">
                {SUGGESTIONS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    disabled={!ready || pending}
                    onClick={() => void send(prompt)}
                    dir="auto"
                    className="w-full rounded-[8px] border border-navy-600 bg-navy-800/60 px-2.5 py-1.5 text-left text-[10.5px] text-mute2 transition hover:border-violet-900 hover:text-ink disabled:opacity-45"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </Card>

          {/* Right Card: Chat Workspace */}
          <Card className="flex min-h-[540px] flex-col justify-between p-5">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-navy-600/70 pb-3.5">
                <div>
                  <h2 className="text-[13px] font-semibold text-ink">Chat Workspace</h2>
                  <p className="mt-0.5 text-[11px] text-mute">
                    {recording ? fileStem(recording.original_filename) : "Select a recording"}
                  </p>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/25 bg-emerald-400/10 px-2.5 py-1 text-[10px] font-semibold text-emerald-200">
                  <ShieldCheck className="size-3.5" />
                  Grounded RAG
                </span>
              </div>

              {!ready && recording && (
                <div className="mt-4 rounded-[10px] border border-amber-400/30 bg-amber-400/10 px-3.5 py-2.5 text-[11.5px] text-amber-200">
                  Recording status is <b>{recording.processing_status}</b>. AI Chat becomes active once transcription and indexing finish.
                </div>
              )}

              <div className="scrollbar-thin mt-4 max-h-[390px] space-y-4 overflow-y-auto pr-1">
                {messages.length === 0 && !pending ? (
                  <div className="space-y-4 py-3">
                    <div className="ml-auto max-w-[75%] rounded-[12px] border border-violet-900/60 bg-violet-800/50 px-4 py-3 text-[12px] text-ink">
                      What are the main challenges or key points mentioned in this recording?
                    </div>

                    <div className="max-w-[82%] rounded-[12px] border border-navy-600 bg-navy-800/80 px-4 py-3.5 text-[12px] leading-relaxed text-mute2">
                      <p className="font-semibold text-ink">
                        Ask any question below about{" "}
                        <span className="text-violet-300">
                          {recording ? fileStem(recording.original_filename) : "your audio"}
                        </span>
                        :
                      </p>
                      <ol className="mt-2 list-decimal space-y-1 pl-4 text-[11.5px]">
                        <li>Answers are strictly grounded in retrieved transcript segments</li>
                        <li>Supporting timestamps and Persian quotes are shown under each answer</li>
                        <li>If the audio lacks evidence, the assistant explicitly states so</li>
                      </ol>
                    </div>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div key={message.id} className="space-y-2">
                      {message.role === "user" ? (
                        <div
                          dir="auto"
                          className="ml-auto max-w-[78%] rounded-[12px] border border-violet-900/70 bg-violet-800/55 px-4 py-3 text-[12px] leading-relaxed text-ink"
                        >
                          {message.text}
                        </div>
                      ) : (
                        <div className="max-w-[86%] space-y-2">
                          <div
                            dir="auto"
                            className={`rounded-[12px] border px-4 py-3 text-[12px] leading-[1.85] ${
                              message.error
                                ? "border-rose-500/30 bg-rose-500/10 text-rose-200"
                                : "border-navy-600 bg-navy-800/80 text-ink"
                            }`}
                          >
                            {message.text}
                          </div>

                          {!message.error && (
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[9.5px] font-semibold ${
                                  message.grounded
                                    ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
                                    : "border-amber-400/25 bg-amber-400/10 text-amber-200"
                                }`}
                              >
                                <ShieldCheck className="size-3" />
                                {message.grounded
                                  ? "Grounded in transcript"
                                  : "Not found in transcript"}
                              </span>
                            </div>
                          )}

                          {message.evidence && message.evidence.length > 0 && (
                            <div className="space-y-1.5">
                              {message.evidence.slice(0, 3).map((ev, idx) => (
                                <div
                                  key={`${message.id}-${idx}`}
                                  className="rounded-[9px] border border-navy-600 bg-navy-800/45 px-3 py-2"
                                >
                                  <div className="flex items-center gap-1.5 text-[10px] font-medium text-violet-300">
                                    <Quote className="size-3" />
                                    <span className="tabular-nums">
                                      {formatDuration(ev.start_time)} – {formatDuration(ev.end_time)}
                                    </span>
                                    {ev.score != null && (
                                      <span className="ml-auto text-mute">
                                        score {ev.score.toFixed(2)}
                                      </span>
                                    )}
                                  </div>
                                  <p
                                    className="mt-1 text-[11px] leading-relaxed text-mute2"
                                    dir="auto"
                                  >
                                    {ev.text}
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))
                )}

                {pending && (
                  <div className="flex items-center gap-2 text-[11.5px] text-mute">
                    <Loader2 className="size-4 animate-spin text-violet-400" />
                    Retrieving transcript segments & generating grounded answer…
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                void send(input);
              }}
              className="mt-4 flex items-center gap-2 pt-3"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={!ready || pending}
                placeholder={
                  ready
                    ? "Ask anything about your audio..."
                    : "Waiting for recording processing to complete..."
                }
                dir="auto"
                className="h-11 flex-1 rounded-[10px] border border-navy-600 bg-navy-800 px-4 text-[12px] text-ink outline-none transition placeholder:text-mute focus:border-violet-900 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!ready || pending || !input.trim()}
                aria-label="Send message"
                className="grid size-11 shrink-0 place-items-center rounded-[10px] bg-violet-600 text-white transition hover:bg-[#7a4dff] disabled:opacity-40"
              >
                {pending ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
              </button>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
