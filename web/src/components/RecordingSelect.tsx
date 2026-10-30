import { ChevronsUpDown, FileAudio } from "lucide-react";
import { useWorkspace } from "@/lib/workspace";
import type { RecordingSummary } from "@/lib/types";
import { fileStem } from "@/lib/format";

type Props = {
  value: string | null;
  onChange: (id: string) => void;
  recordings?: RecordingSummary[];
  label?: string;
  className?: string;
};

export function RecordingSelect({
  value,
  onChange,
  recordings,
  label = "Recording",
  className = "",
}: Props) {
  const workspace = useWorkspace();
  const items = recordings ?? workspace.recordings;

  return (
    <label className={`block ${className}`}>
      <span className="psi-label">{label}</span>
      <div className="relative mt-1.5">
        <FileAudio className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-mute" />
        <select
          value={value ?? ""}
          onChange={(event) => onChange(event.target.value)}
          disabled={items.length === 0}
          className="h-10 w-full appearance-none rounded-[10px] border border-navy-600 bg-navy-800 pl-9 pr-9 text-[12px] font-medium text-ink outline-none transition focus:border-violet-900 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {items.length === 0 && <option value="">No recordings yet</option>}
          {items.map((recording) => (
            <option key={recording.id} value={recording.id}>
              {fileStem(recording.original_filename)} · {recording.processing_status}
            </option>
          ))}
        </select>
        <ChevronsUpDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-mute" />
      </div>
    </label>
  );
}
