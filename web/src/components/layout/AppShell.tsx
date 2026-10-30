import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { useWorkspace } from "@/lib/workspace";

export function AppShell() {
  const { error, backendOk } = useWorkspace();
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-navy-950 text-ink">
      <div className="hidden lg:flex lg:h-screen lg:sticky lg:top-0">
        <Sidebar />
      </div>

      {navOpen && (
        <div className="fixed inset-0 z-[80] flex lg:hidden">
          <div
            className="absolute inset-0 bg-navy-950/75 backdrop-blur-sm"
            onClick={() => setNavOpen(false)}
            aria-hidden="true"
          />
          <div className="relative h-full animate-fadeup">
            <Sidebar onNavigate={() => setNavOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenu={() => setNavOpen(true)} />
        {!backendOk && error && (
          <div className="mx-4 mt-3 rounded-[10px] border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[12px] text-amber-100 sm:mx-6">
            API offline: {error}. Start FastAPI on port 8000. The interface stays available.
          </div>
        )}
        <main className="min-h-0 flex-1 px-4 py-5 sm:px-6 lg:px-7 lg:py-6">
          <div key={location.pathname} className="animate-fadeup">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

export function PageHeader({
  crumb,
  title,
  subtitle,
  actions,
}: {
  crumb: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-400">
          {crumb}
        </p>
        <h1 className="mt-1.5 text-[22px] font-semibold tracking-[-0.01em] text-ink sm:text-[26px]">
          {title}
        </h1>
        {subtitle && <p className="mt-1.5 max-w-[640px] text-[12px] leading-relaxed text-mute">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
