import type { ReactNode } from "react";

import { X } from "lucide-react";

import { cn } from "../../lib/cn";
import { toneMap } from "../../lib/theme";
import type { RowBase, TableColumn, Tone } from "../../types/domain";

export function Table<T extends RowBase>({
  cols,
  rows,
  onDelete,
  tone,
}: {
  cols: Array<TableColumn<T>>;
  rows: T[];
  onDelete: (id: number) => void;
  tone: Tone;
}) {
  if (!rows.length) {
    return <div className="py-10 text-center text-sm text-slate-500">Nenhum registro ainda. Adicione acima.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {cols.map((col) => (
              <th key={col.key} className="border-b border-slate-800 px-3 py-2 text-left text-[11px] uppercase tracking-wider text-slate-500">
                {col.label}
              </th>
            ))}
            <th className="border-b border-slate-800" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={row.id} className={cn("border-b border-slate-800/60", index % 2 ? "bg-white/[0.03]" : "") }>
              {cols.map((col) => {
                const raw = (row as Record<string, unknown>)[col.key];
                return (
                  <td
                    key={`${row.id}-${col.key}`}
                    className={cn(
                      "whitespace-nowrap px-3 py-2",
                      col.mono ? cn("font-semibold tabular-nums", toneMap[tone].text) : "text-slate-300",
                    )}
                  >
                    {col.render ? col.render(raw, row) : ((raw ?? "-") as ReactNode)}
                  </td>
                );
              })}
              <td className="px-3 py-2">
                <button
                  type="button"
                  onClick={() => onDelete(row.id)}
                  className="rounded p-1 text-rose-400/70 transition hover:bg-rose-500/10 hover:text-rose-300"
                  aria-label="Excluir registro"
                >
                  <X className="h-4 w-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
