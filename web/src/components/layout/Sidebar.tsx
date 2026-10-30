import { NavLink } from "react-router-dom";
import {
  Home,
  Upload,
  FolderOpen,
  MessageCircle,
  Activity,
  Download,
  Settings,
  Sparkles,
} from "lucide-react";
import { useWorkspace } from "@/lib/workspace";

const items = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/upload", label: "Upload Audio", icon: Upload },
  { to: "/files", label: "My Files", icon: FolderOpen },
  { to: "/chat", label: "AI Chat", icon: MessageCircle },
  { to: "/analysis", label: "Analysis", icon: Activity },
  { to: "/export", label: "Export", icon: Download },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { settings } = useWorkspace();
  const initials = settings.displayName
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <aside
      className="flex h-full w-[248px] shrink-0 flex-col border-r border-navy-600/80 bg-navy-900 select-none"
      aria-label="Primary navigation"
    >
      <NavLink
        to="/"
        onClick={onNavigate}
        className="flex items-center gap-3.5 px-5 py-[20px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/60"
      >
        <div className="grid size-[40px] shrink-0 place-items-center rounded-full bg-gradient-to-br from-violet-600 via-[#693bff] to-electric text-white shadow-[0_8px_24px_-6px_rgba(105,59,255,0.95)] ring-1 ring-white/15">
          <svg viewBox="0 0 24 24" className="size-5" fill="none" aria-hidden="true">
            <rect x="3" y="9.5" width="2.2" height="5" rx="1.1" fill="currentColor" opacity="0.85" />
            <rect x="7" y="6" width="2.2" height="12" rx="1.1" fill="currentColor" />
            <rect x="11" y="3.5" width="2.2" height="17" rx="1.1" fill="currentColor" />
            <rect x="15" y="7" width="2.2" height="10" rx="1.1" fill="currentColor" />
            <rect x="19" y="9" width="2.2" height="6" rx="1.1" fill="currentColor" opacity="0.85" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-[13px] font-bold leading-[1.25] text-ink">
            Persian Speech
            <br />
            Intelligence
          </p>
          <p className="mt-1 text-[10px] text-mute">From Speech to Action</p>
        </div>
      </NavLink>
      <div className="psi-divider" />

      <nav className="mt-4 flex flex-col gap-1.5 px-3.5">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `group flex h-[42px] items-center gap-3 rounded-[10px] px-3.5 text-[12px] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/60 ${
                isActive
                  ? "border border-violet-900 bg-violet-800 font-semibold text-ink shadow-[0_0_20px_-6px_rgba(105,59,255,0.55)]"
                  : "border border-transparent text-mute2 hover:bg-navy-800/80 hover:text-ink"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  className={`size-[16px] shrink-0 ${
                    isActive ? "text-violet-400" : "text-mute group-hover:text-mute2"
                  }`}
                />
                <span className="flex-1 truncate">{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto space-y-2.5 p-3.5">
        <NavLink
          to="/settings"
          onClick={onNavigate}
          className="flex items-center gap-3 rounded-[13px] border border-navy-600 bg-navy-850/90 px-3.5 py-3 transition hover:border-violet-900"
        >
          <div className="grid size-[34px] shrink-0 place-items-center rounded-[10px] bg-violet-800/80 text-violet-400">
            <Sparkles className="size-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[11.5px] font-semibold text-ink">Premium Workspace</p>
            <p className="truncate text-[10px] text-mute">Unlock advanced features</p>
          </div>
        </NavLink>

        <NavLink
          to="/settings"
          onClick={onNavigate}
          className="flex items-center gap-3 rounded-[13px] border border-navy-600 bg-navy-850/90 px-3.5 py-3 transition hover:border-violet-900"
        >
          <div className="grid size-[36px] shrink-0 place-items-center rounded-full bg-violet-600/30 border border-violet-500/40 text-[11px] font-bold text-violet-200">
            {initials || "PG"}
          </div>
          <div className="min-w-0">
            <p className="truncate text-[11.5px] font-semibold text-ink">{settings.displayName}</p>
            <p className="truncate text-[10px] text-mute">{settings.email}</p>
          </div>
        </NavLink>
      </div>
    </aside>
  );
}
