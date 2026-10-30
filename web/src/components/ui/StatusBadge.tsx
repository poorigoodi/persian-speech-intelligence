import type { ProcessingStatus } from "@/lib/types";

const map: Record<ProcessingStatus, string> = {
  completed: "text-emerald-400",
  processing: "text-sky-400",
  pending: "text-amber-400",
  failed: "text-rose-400",
};

export function StatusBadge({ status }: { status: ProcessingStatus | string }) {
  const cls = map[status as ProcessingStatus] || "text-mute";
  const label = status.charAt(0).toUpperCase() + status.slice(1);
  return <span className={`text-[11px] font-medium ${cls}`}>{label}</span>;
}
