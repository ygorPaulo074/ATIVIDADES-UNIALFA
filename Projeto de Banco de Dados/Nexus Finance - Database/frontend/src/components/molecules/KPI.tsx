import type { ReactNode } from "react";

import { cn } from "../../lib/cn";
import { toneMap } from "../../lib/theme";
import type { Tone } from "../../types/domain";

export function KPI({ label, value, tone, icon }: { label: string; value: string; tone: Tone; icon: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
        <span className={cn("inline-flex h-7 w-7 items-center justify-center rounded-lg", toneMap[tone].softBg, toneMap[tone].text)}>
          {icon}
        </span>
      </div>
      <span className={cn("text-2xl font-bold tabular-nums", toneMap[tone].text)}>{value}</span>
    </div>
  );
}
