import { X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

type Props = {
  open: boolean;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
};

export function Modal({ open, title, description, children, footer, onClose }: Props) {
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    panelRef.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-navy-950/80 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="psi-modal-title"
        tabIndex={-1}
        className="relative w-full max-w-[420px] animate-fadeup rounded-[16px] border border-navy-600 bg-navy-700 p-5 shadow-glow focus:outline-none"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="psi-modal-title" className="text-[15px] font-semibold text-ink">
              {title}
            </h2>
            {description && <p className="mt-1.5 text-[12px] leading-relaxed text-mute">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-md p-1 text-mute transition hover:bg-white/5 hover:text-ink"
          >
            <X className="size-4" />
          </button>
        </div>
        {children && <div className="mt-4">{children}</div>}
        {footer && <div className="mt-5 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}
