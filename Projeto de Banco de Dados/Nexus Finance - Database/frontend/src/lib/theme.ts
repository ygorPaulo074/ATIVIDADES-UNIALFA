import type { Tone } from "../types/domain";

export const baseInputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-400/20";

export const toneMap: Record<
  Tone,
  {
    text: string;
    softBg: string;
    border: string;
    line: string;
    btn: string;
    badge: string;
  }
> = {
  accent: {
    text: "text-blue-400",
    softBg: "bg-blue-500/10",
    border: "border-blue-400/40",
    line: "bg-blue-500",
    btn: "bg-blue-500 hover:bg-blue-400 text-white shadow-blue-500/30",
    badge: "bg-blue-500/15 text-blue-300",
  },
  green: {
    text: "text-emerald-400",
    softBg: "bg-emerald-500/10",
    border: "border-emerald-400/40",
    line: "bg-emerald-500",
    btn: "bg-emerald-500 hover:bg-emerald-400 text-white shadow-emerald-500/30",
    badge: "bg-emerald-500/15 text-emerald-300",
  },
  red: {
    text: "text-rose-400",
    softBg: "bg-rose-500/10",
    border: "border-rose-400/40",
    line: "bg-rose-500",
    btn: "bg-rose-500 hover:bg-rose-400 text-white shadow-rose-500/30",
    badge: "bg-rose-500/15 text-rose-300",
  },
  gold: {
    text: "text-amber-400",
    softBg: "bg-amber-500/10",
    border: "border-amber-400/40",
    line: "bg-amber-500",
    btn: "bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-amber-500/30",
    badge: "bg-amber-500/15 text-amber-300",
  },
  purple: {
    text: "text-violet-400",
    softBg: "bg-violet-500/10",
    border: "border-violet-400/40",
    line: "bg-violet-500",
    btn: "bg-violet-500 hover:bg-violet-400 text-white shadow-violet-500/30",
    badge: "bg-violet-500/15 text-violet-300",
  },
};
