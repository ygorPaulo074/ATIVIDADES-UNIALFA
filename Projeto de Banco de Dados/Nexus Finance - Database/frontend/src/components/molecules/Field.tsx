import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

export function Field({ label, children, half }: { label: string; children: ReactNode; half?: boolean }) {
  return (
    <div className={cn("flex flex-col gap-1.5", half ? "md:col-span-1" : "md:col-span-2")}>
      <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</label>
      {children}
    </div>
  );
}
