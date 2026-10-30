export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-[13px] border border-dashed border-navy-600 bg-navy-800/40 px-6 py-10 text-center">
      <p className="text-[13px] font-semibold text-ink">{title}</p>
      <p className="mt-2 text-[12px] text-mute">{body}</p>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-[10px] border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[12px] text-rose-200">
      {message}
    </div>
  );
}

export function PlaceholderNote({ children }: { children: string }) {
  return (
    <p className="mt-2 text-[10px] uppercase tracking-wide text-mute/80">
      Placeholder · {children}
    </p>
  );
}
