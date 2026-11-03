import type { ProcessingStatus } from "@/lib/types";

const map: Record<ProcessingStatus, string> = {
  completed: "text-success",
  processing: "text-electric",
  pending: "text-warning",
  failed: "text-danger",
};

export function StatusBadge({ status }: { status: ProcessingStatus | string }) {
  const cls = map[status as ProcessingStatus] || "text-mute";
  const label = status.charAt(0).toUpperCase() + status.slice(1);
  return <span className={`text-[11px] font-medium ${cls}`}>{label}</span>;
}
