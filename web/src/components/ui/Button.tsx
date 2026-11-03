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
    "bg-violet-600 text-white shadow-[0_8px_24px_-10px_rgba(109,40,217,0.75)] hover:bg-violet-500",
  ghost:
    "border border-navy-600 bg-navy-800 text-ink hover:border-violet-900 hover:bg-navy-750",
  subtle: "bg-navy-800/80 text-mute2 hover:bg-navy-800 hover:text-ink",
  danger: "border border-danger/35 bg-danger/10 text-danger hover:bg-danger/20",
  icon: "size-9 border border-navy-600 bg-navy-800 text-mute2 hover:border-violet-900 hover:text-ink",
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
