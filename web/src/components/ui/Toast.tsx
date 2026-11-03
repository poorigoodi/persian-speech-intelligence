import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

type Tone = "success" | "error" | "info";
type Toast = { id: number; message: string; tone: Tone };

type ToastValue = { push: (message: string, tone?: Tone) => void };

const Ctx = createContext<ToastValue | null>(null);

const ICONS = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
};

const TONES = {
  success: "border-success/35 bg-navy-800 text-success",
  error: "border-danger/35 bg-navy-800 text-danger",
  info: "border-violet-900/60 bg-navy-800 text-violet-300",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);

  const push = useCallback((message: string, tone: Tone = "info") => {
    counter.current += 1;
    const id = counter.current;
    setToasts((prev) => [...prev.slice(-2), { id, message, tone }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 3800);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed bottom-5 right-5 z-[95] flex w-[min(92vw,340px)] flex-col gap-2"
        role="status"
        aria-live="polite"
      >
        {toasts.map((toast) => {
          const Icon = ICONS[toast.tone];
          return (
            <div
              key={toast.id}
              className={`animate-fadeup rounded-[11px] border px-3.5 py-2.5 text-[12px] shadow-glow backdrop-blur ${TONES[toast.tone]}`}
            >
              <div className="flex items-start gap-2">
                <Icon className="mt-0.5 size-4 shrink-0" />
                <span className="leading-snug">{toast.message}</span>
              </div>
            </div>
          );
        })}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
