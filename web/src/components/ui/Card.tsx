import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`psi-card ${className}`} {...props} />;
}

export function CardTitle({ children }: { children: string }) {
  return <h2 className="text-[13px] font-semibold text-ink">{children}</h2>;
}
