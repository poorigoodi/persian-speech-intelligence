import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost" | "subtle" | "danger" | "icon";
type Size = "sm" | "md";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-[10px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/70 focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950 disabled:opacity-50 disabled:pointer-events-none";

const SIZES: Record<Size, string> = {
  sm: "h-8 px-3 text-[11px]",
  md: "h-10 px-4 text-[12px]",
};

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-violet-600 text-white shadow-[0_10px_30px_-12px_rgba(105,59,255,0.9)] hover:bg-[#7a4dff]",
  ghost:
    "border border-navy-600 bg-navy-800 text-ink hover:border-violet-900 hover:bg-navy-750",
  subtle: "bg-white/5 text-mute2 hover:bg-white/10 hover:text-ink",
  danger: "border border-rose-500/30 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20",
  icon: "size-9 border border-navy-600 bg-navy-800 text-mute hover:border-violet-900 hover:text-ink",
};

export function buttonClass({
  variant = "primary",
  size = "md",
}: { variant?: Variant; size?: Size } = {}): string {
  return `${BASE} ${variant === "icon" ? "" : SIZES[size]} ${VARIANTS[variant]}`;
}

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

export function Button({ variant = "primary", size = "md", className = "", ...props }: Props) {
  return <button className={`${buttonClass({ variant, size })} ${className}`} {...props} />;
}
