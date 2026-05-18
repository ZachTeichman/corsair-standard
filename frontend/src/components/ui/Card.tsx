import type { HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-white/10 bg-white/[0.045] shadow-corsair backdrop-blur-xl",
        "light:border-black/10 light:bg-white/75",
        className,
      )}
      {...props}
    />
  );
}

