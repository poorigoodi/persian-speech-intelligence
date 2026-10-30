import { statusTone } from "@/lib/status";

export function StatusPill({
  status,
  className = "",
}: {
  status: string;
  className?: string;
}) {
  const tone = statusTone(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-[3px] text-[10px] font-semibold capitalize ${tone.bg} ${tone.border} ${tone.text} ${className}`}
    >
      <span
        className={`size-[5px] rounded-full ${tone.dot} ${status === "processing" ? "animate-pulse" : ""}`}
      />
      {tone.label}
    </span>
  );
}
