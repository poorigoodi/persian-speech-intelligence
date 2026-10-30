import { Maximize2, Pause, Play, Volume2, VolumeX } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { formatDuration } from "@/lib/format";

const BARS = [
  41, 28, 30, 36, 35, 16, 22, 15, 15, 14, 17, 41, 26, 21, 39, 39, 42, 22, 30, 23, 10, 15, 15, 10, 12,
  33, 38, 28, 20, 10, 13, 26, 37, 16, 32, 35, 15, 16, 16, 27, 28, 30, 30, 12, 22, 39, 20, 42, 32, 29,
  32, 26, 19, 11, 34, 41, 22, 36, 38, 15, 11, 25, 39, 11, 16, 37, 13, 28, 24, 33, 39, 15, 13, 27, 25,
  42, 11, 33, 26, 34, 17, 16, 12, 30, 26, 24, 14, 37, 20, 19, 26, 11, 25, 11, 12, 11, 37, 40, 29, 18,
  37, 20, 37, 18, 36,
];

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
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [t, setT] = useState(0);
  const [dur, setDur] = useState(duration ?? 0);
  const [speed, setSpeed] = useState(1);

  useEffect(() => {
    setPlaying(false);
    setT(0);
    setDur(duration ?? 0);
  }, [src, duration]);

  useEffect(() => {
    if (!seekRequest) return;
    const target = Math.max(0, Math.min(dur || seekRequest.time || 0, seekRequest.time));
    setT(target);
    const element = audioRef.current;
    if (element && src) {
      element.currentTime = target;
      void element
        .play()
        .then(() => setPlaying(true))
        .catch(() => setPlaying(false));
    }
  }, [seekRequest, dur, src]);

  const effectiveDuration = dur > 0 ? dur : duration && duration > 0 ? duration : 2732;
  const progress = effectiveDuration ? Math.min(1, Math.max(0, t / effectiveDuration)) : 0.27;
  const activeBars = useMemo(
    () => Math.max(1, Math.round((t > 0 ? progress : 0.28) * BARS.length)),
    [progress, t],
  );

  function handleSeek(nextTime: number) {
    setT(nextTime);
    if (audioRef.current && src) {
      audioRef.current.currentTime = nextTime;
    }
  }

  return (
    <div
      ref={containerRef}
      className="rounded-[14px] border border-navy-600 bg-navy-700 px-5 py-4"
    >
      {src && (
        <audio
          ref={audioRef}
          src={src}
          muted={muted}
          onTimeUpdate={(e) => setT(e.currentTarget.currentTime)}
          onLoadedMetadata={(e) => {
            if (e.currentTarget.duration && Number.isFinite(e.currentTarget.duration)) {
              setDur(e.currentTarget.duration);
            }
          }}
          onEnded={() => setPlaying(false)}
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
              void el.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
            }
          }}
          disabled={!src}
          title={
            src
              ? playing
                ? "Pause audio"
                : "Play audio"
              : "Audio playback is available for files uploaded in this browser session"
          }
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
          <div
            className="flex h-[46px] cursor-pointer items-center gap-[4px] overflow-hidden"
            onClick={(event) => {
              const rect = event.currentTarget.getBoundingClientRect();
              const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
              handleSeek(ratio * effectiveDuration);
            }}
            role="presentation"
          >
            {BARS.map((h, i) => {
              const played = i < activeBars;
              return (
                <span
                  key={i}
                  className={`w-[3px] shrink-0 rounded-full transition-colors ${
                    played
                      ? "bg-gradient-to-t from-violet-600 to-violet-400"
                      : i % 3 === 0
                        ? "bg-[#22d3ee]"
                        : "bg-[#38bdf8]/85"
                  }`}
                  style={{ height: `${h}px` }}
                />
              );
            })}
          </div>

          <div className="mt-2.5 flex items-center gap-3 text-[11px] text-mute">
            <span className="shrink-0 tabular-nums text-mute2">
              {formatDuration(t)} <span className="text-mute">/ {formatDuration(effectiveDuration)}</span>
            </span>

            <input
              type="range"
              min={0}
              max={effectiveDuration || 1}
              step={0.1}
              value={t}
              onChange={(e) => handleSeek(Number(e.target.value))}
              aria-label="Seek audio position"
              className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-navy-600 accent-violet-500"
            />

            <button
              type="button"
              onClick={() => setMuted((m) => !m)}
              className="text-mute transition hover:text-ink"
              aria-label={muted ? "Unmute" : "Mute"}
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
            >
              <Maximize2 className="size-3.5" />
            </button>
          </div>
        </div>
      </div>

      {!src && (
        <p className="mt-2 text-[10px] text-mute/80">
          Note: Backend does not expose an audio stream endpoint. Live audio playback is active for files uploaded in this browser session.
        </p>
      )}
    </div>
  );
}
