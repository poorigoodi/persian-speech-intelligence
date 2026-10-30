import { Bell, Menu, Moon, Search, Sun } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { useWorkspace } from "@/lib/workspace";
import { useToast } from "@/components/ui/Toast";

export function TopBar({ onMenu }: { onMenu?: () => void }) {
  const navigate = useNavigate();
  const { settings, setSettings } = useWorkspace();
  const { push } = useToast();
  const [q, setQ] = useState("");
  const isLight = settings.theme === "light";
  const initials = settings.displayName
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const query = q.trim();
    if (!query) return;
    navigate(`/files?q=${encodeURIComponent(query)}`);
    setQ("");
  }

  return (
    <header className="flex h-[64px] shrink-0 items-center gap-3 border-b border-navy-600/80 bg-navy-950/90 px-4 sm:px-6 lg:px-7">
      <button
        type="button"
        onClick={onMenu}
        aria-label="Open navigation"
        className="grid size-9 place-items-center rounded-[10px] border border-navy-600 bg-navy-800 text-mute transition hover:text-ink lg:hidden"
      >
        <Menu className="size-[18px]" />
      </button>

      <form onSubmit={onSubmit} className="relative max-w-[640px] flex-1">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 size-[15px] -translate-y-1/2 text-mute" />
        <input
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="Search files, topics, or ask a question..."
          aria-label="Search files, topics, or ask a question"
          className="h-[38px] w-full rounded-[10px] border border-navy-600 bg-navy-800/90 pl-9 pr-3.5 text-[11.5px] text-ink outline-none transition placeholder:text-mute focus:border-violet-900 focus:ring-1 focus:ring-violet-900/40"
        />
      </form>

      <div className="ml-auto flex items-center gap-4">
        <button
          type="button"
          onClick={() =>
            setSettings({
              ...settings,
              theme: isLight ? "dark" : "light",
            })
          }
          className="grid size-9 place-items-center rounded-[10px] border border-navy-600 bg-navy-800/80 text-mute transition hover:border-violet-900 hover:text-ink"
          aria-label={isLight ? "Switch to dark mode" : "Switch to light mode"}
          title={isLight ? "Switch to Dark Mode" : "Switch to Light Mode"}
        >
          {isLight ? <Moon className="size-[16px]" /> : <Sun className="size-[16px]" />}
        </button>
        <button
          type="button"
          onClick={() =>
            push("Notifications are up to date.", "info")
          }
          className="text-mute transition hover:text-ink"
          aria-label="Notifications"
          title="Notifications"
        >
          <Bell className="size-[17px]" />
        </button>
        <button
          type="button"
          onClick={() => navigate("/settings")}
          aria-label="Open profile settings"
          className="grid size-[34px] place-items-center rounded-full bg-violet-600 text-[11px] font-bold text-white shadow-[0_0_16px_-4px_rgba(105,59,255,0.9)] transition hover:bg-[#7a4dff]"
        >
          {initials || "PG"}
        </button>
      </div>
    </header>
  );
}
