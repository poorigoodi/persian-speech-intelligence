import { Maximize2, Pause, Play, Volume2, VolumeX } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { formatDuration } from "@/lib/format";

const BAR_COUNT = 120;

// Deterministic initial placeholder heights (in %) used only before Web Audio API decodes the real signal
const FALLBACK_BARS: number[] = Array.from({ length: BAR_COUNT }, (_, i) => {
  const wave = Math.sin(i * 0.23) * 0.3 + Math.cos(i * 0.61) * 0.22 + 0.52;
  return Math.round(Math.min(96, Math.max(18, wave * 90)));
});

// Cache decoded waveform peaks per audio URL so switching tabs doesn't re-decode
const waveformCache = new Map<string, { peaks: number[]; duration: number }>();

async function extractWaveformPeaks(
  url: string,
  barCount: number,
  signal: AbortSignal,
): Promise<{ peaks: number[]; duration: number } | null> {
  const cached = waveformCache.get(url);
  if (cached) return cached;

  try {
    const response = await fetch(url, { signal });
    if (!response.ok) return null;
    const arrayBuffer = await response.arrayBuffer();
    if (signal.aborted) return null;

    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return null;

    const ctx = new AudioCtx();
    try {
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
      const channelData = audioBuffer.getChannelData(0);
      const totalSamples = channelData.length;
      if (totalSamples === 0) return null;

      const samplesPerBar = Math.max(1, Math.floor(totalSamples / barCount));
      const rawAmps: number[] = [];

      for (let i = 0; i < barCount; i++) {
        const start = i * samplesPerBar;
        const end = i === barCount - 1 ? totalSamples : Math.min(totalSamples, start + samplesPerBar);
        const step = Math.max(1, Math.floor((end - start) / 256));
        let sumSq = 0;
        let peak = 0;
        let count = 0;
        for (let j = start; j < end; j += step) {
          const sample = Math.abs(channelData[j] ?? 0);
          sumSq += sample * sample;
          if (sample > peak) peak = sample;
          count++;
        }
        const rms = count > 0 ? Math.sqrt(sumSq / count) : 0;
        rawAmps.push(rms * 0.65 + peak * 0.35);
      }

      const maxAmp = Math.max(...rawAmps, 0.001);
      const peaks = rawAmps.map((v) => {
        const normalized = Math.pow(v / maxAmp, 0.75);
        return Math.round(Math.min(100, Math.max(16, normalized * 100)));
      });

      const result = { peaks, duration: audioBuffer.duration };
      waveformCache.set(url, result);
      return result;
    } finally {
      void ctx.close().catch(() => undefined);
    }
  } catch {
    return null;
  }
}

export function AudioPlayer({
  src,
  duration,
  seekRequest,
}: {
  src?: string;
  duration?: number | null;
  seekRequest?: { time: number; token: number } | null;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const waveformTrackRef = useRef<HTMLDivElement | null>(null);

  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState<number>(
    duration && duration > 0 ? duration : 0,
  );
  const [speed, setSpeed] = useState(1);
  const [bars, setBars] = useState<number[]>(FALLBACK_BARS);
  const [isDraggingWaveform, setIsDraggingWaveform] = useState(false);

  // Reset playback state when switching recording / audio source
  useEffect(() => {
    setPlaying(false);
    setCurrentTime(0);
    setAudioDuration(duration && duration > 0 ? duration : 0);
  }, [src, duration]);

  // Decode actual audio waveform from `src`
  useEffect(() => {
    if (!src) {
      setBars(FALLBACK_BARS);
      return;
    }
    const controller = new AbortController();
    void extractWaveformPeaks(src, BAR_COUNT, controller.signal).then((decoded) => {
      if (!decoded || controller.signal.aborted) return;
      setBars(decoded.peaks);
      if (decoded.duration > 0 && Number.isFinite(decoded.duration)) {
        setAudioDuration((prev) => (prev > 0 ? prev : decoded.duration));
      }
    });
    return () => controller.abort();
  }, [src]);

  // Keep 60fps synchronization between audio element and waveform / slider while playing
  useEffect(() => {
    if (!playing) return;
    let rafId = 0;
    const sync = () => {
      const el = audioRef.current;
      if (el && !el.paused) {
        setCurrentTime(el.currentTime);
        if (el.duration && Number.isFinite(el.duration) && el.duration > 0) {
          setAudioDuration(el.duration);
        }
      }
      rafId = window.requestAnimationFrame(sync);
    };
    rafId = window.requestAnimationFrame(sync);
    return () => window.cancelAnimationFrame(rafId);
  }, [playing]);

  const effectiveDuration = useMemo(() => {
    if (audioDuration > 0 && Number.isFinite(audioDuration)) return audioDuration;
    if (duration && duration > 0 && Number.isFinite(duration)) return duration;
    return 0;
  }, [audioDuration, duration]);

  const handleSeek = useCallback(
    (nextTime: number) => {
      const maxDur = effectiveDuration > 0 ? effectiveDuration : Math.max(0, nextTime);
      const clamped = Math.max(0, Math.min(maxDur, nextTime));
      setCurrentTime(clamped);
      const el = audioRef.current;
      if (el && src) {
        try {
          el.currentTime = clamped;
        } catch {
          /* ignore if media not ready */
        }
      }
    },
    [effectiveDuration, src],
  );

  // External seek requests (e.g. clicking a transcript segment timestamp)
  useEffect(() => {
    if (!seekRequest) return;
    handleSeek(seekRequest.time);
    const el = audioRef.current;
    if (el && src) {
      void el
        .play()
        .then(() => setPlaying(true))
        .catch(() => setPlaying(false));
    }
  }, [seekRequest, handleSeek, src]);

  const progress = useMemo(() => {
    if (effectiveDuration <= 0) return 0;
    return Math.min(1, Math.max(0, currentTime / effectiveDuration));
  }, [currentTime, effectiveDuration]);

  const seekFromClientX = useCallback(
    (clientX: number) => {
      const track = waveformTrackRef.current;
      if (!track || effectiveDuration <= 0) return;
      const rect = track.getBoundingClientRect();
      if (rect.width <= 0) return;
      const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      handleSeek(ratio * effectiveDuration);
    },
    [effectiveDuration, handleSeek],
  );

  return (
    <div
      ref={containerRef}
      className="rounded-[14px] border border-navy-600 bg-navy-700 px-5 py-4"
    >
      {src && (
        <audio
          ref={audioRef}
          src={src}
          preload="metadata"
          muted={muted}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          onDurationChange={(e) => {
            if (e.currentTarget.duration && Number.isFinite(e.currentTarget.duration)) {
              setAudioDuration(e.currentTarget.duration);
            }
          }}
          onLoadedMetadata={(e) => {
            if (e.currentTarget.duration && Number.isFinite(e.currentTarget.duration)) {
              setAudioDuration(e.currentTarget.duration);
            }
          }}
          onEnded={() => {
            setPlaying(false);
            if (effectiveDuration > 0) setCurrentTime(effectiveDuration);
          }}
        />
      )}

      <div className="flex items-center gap-4 sm:gap-5">
        <button
          type="button"
          onClick={() => {
            if (!src) return;
            const el = audioRef.current;
            if (!el) return;
            if (playing) {
              el.pause();
              setPlaying(false);
            } else {
              if (effectiveDuration > 0 && currentTime >= effectiveDuration - 0.15) {
                el.currentTime = 0;
                setCurrentTime(0);
              }
              void el
                .play()
                .then(() => setPlaying(true))
                .catch(() => setPlaying(false));
            }
          }}
          disabled={!src}
          title={playing ? "Pause audio" : "Play audio"}
          aria-label={playing ? "Pause" : "Play"}
          className="grid size-[52px] shrink-0 place-items-center rounded-full bg-gradient-to-br from-violet-600 to-[#7c4dff] text-white shadow-[0_8px_28px_-6px_rgba(105,59,255,0.95)] transition hover:scale-[1.03] disabled:cursor-not-allowed disabled:opacity-75"
        >
          {playing ? (
            <Pause className="size-5 fill-current" />
          ) : (
            <Play className="ml-0.5 size-5 fill-current" />
          )}
        </button>

        <div className="min-w-0 flex-1">
          {/* Shared-width track container so waveform and seek slider align 1:1 from 0% to 100% */}
          <div className="w-full">
            <div
              ref={waveformTrackRef}
              onPointerDown={(e) => {
                e.currentTarget.setPointerCapture(e.pointerId);
                setIsDraggingWaveform(true);
                seekFromClientX(e.clientX);
              }}
              onPointerMove={(e) => {
                if (!isDraggingWaveform) return;
                seekFromClientX(e.clientX);
              }}
              onPointerUp={(e) => {
                if (isDraggingWaveform) {
                  setIsDraggingWaveform(false);
                  e.currentTarget.releasePointerCapture(e.pointerId);
                }
              }}
              onPointerCancel={() => setIsDraggingWaveform(false)}
              role="slider"
              aria-label="Audio waveform timeline"
              aria-valuemin={0}
              aria-valuemax={Math.round(effectiveDuration)}
              aria-valuenow={Math.round(currentTime)}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "ArrowRight") handleSeek(currentTime + 5);
                if (e.key === "ArrowLeft") handleSeek(currentTime - 5);
              }}
              className="flex h-[46px] w-full cursor-pointer select-none items-center justify-between gap-[2px] overflow-hidden touch-none"
            >
              {bars.map((pctHeight, i) => {
                const barProgress = (i + 0.5) / bars.length;
                const played = progress > 0 && barProgress <= progress;
                const heightPx = Math.max(7, Math.round((pctHeight / 100) * 42));
                return (
                  <span
                    key={i}
                    className={`flex-1 rounded-full transition-colors duration-75 ${
                      played
                        ? "bg-gradient-to-t from-violet-600 to-electric"
                        : "bg-navy-600/85"
                    }`}
                    style={{ height: `${heightPx}px`, minWidth: "2px", maxWidth: "5px" }}
                  />
                );
              })}
            </div>

            {/* Range slider aligned to the exact 100% width of the waveform above */}
            <input
              type="range"
              min={0}
              max={effectiveDuration > 0 ? effectiveDuration : 1}
              step={0.05}
              value={Math.min(currentTime, effectiveDuration > 0 ? effectiveDuration : 1)}
              onChange={(e) => handleSeek(Number(e.target.value))}
              aria-label="Seek audio position"
              className="mt-2 block h-1.5 w-full cursor-pointer appearance-none rounded-full bg-navy-600 accent-violet-500"
            />
          </div>

          {/* Time readout & player controls */}
          <div className="mt-2 flex items-center justify-between gap-3 text-[11px] text-mute">
            <span className="shrink-0 tabular-nums text-mute2">
              {formatDuration(currentTime)}{" "}
              <span className="text-mute">/ {formatDuration(effectiveDuration)}</span>
            </span>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMuted((m) => !m)}
                className="text-mute transition hover:text-ink"
                aria-label={muted ? "Unmute" : "Mute"}
                title={muted ? "Unmute" : "Mute"}
              >
                {muted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
              </button>

              <button
                type="button"
                onClick={() => {
                  const next = speed === 1 ? 1.25 : speed === 1.25 ? 1.5 : speed === 1.5 ? 2 : 1;
                  setSpeed(next);
                  if (audioRef.current) audioRef.current.playbackRate = next;
                }}
                className="rounded-[7px] border border-navy-600 bg-navy-800 px-2 py-0.5 text-[10px] font-semibold text-mute2 transition hover:border-violet-900 hover:text-ink"
                title="Playback speed"
              >
                {speed}x
              </button>

              <button
                type="button"
                onClick={() => {
                  if (containerRef.current?.requestFullscreen) {
                    void containerRef.current.requestFullscreen().catch(() => undefined);
                  }
                }}
                className="text-mute transition hover:text-ink"
                aria-label="Fullscreen player"
                title="Fullscreen player"
              >
                <Maximize2 className="size-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
