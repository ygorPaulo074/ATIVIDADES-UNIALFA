import { useState } from "react";

import { Button as Btn } from "../atoms/Button";
import { Input } from "../atoms/Input";
import { Select } from "../atoms/Select";
import { Field } from "../molecules/Field";
import { KPI } from "../molecules/KPI";
import { Section } from "../molecules/Section";
import { Badge } from "../atoms/Badge";
import { fmt, fmtDate } from "../../lib/format";
import { cashFlowApi } from "../../services/finance";
import type { CashFlowRow } from "../../types/domain";

function firstDayOfMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

function lastDayOfMonth() {
  const d = new Date();
  const last = new Date(d.getFullYear(), d.getMonth() + 1, 0);
  return `${last.getFullYear()}-${String(last.getMonth() + 1).padStart(2, "0")}-${String(last.getDate()).padStart(2, "0")}`;
}

export function CashFlowTab() {
  const [start, setStart] = useState(firstDayOfMonth());
  const [end, setEnd] = useState(lastDayOfMonth());
  const [granularity, setGranularity] = useState<"daily" | "weekly" | "monthly">("monthly");
  const [rows, setRows] = useState<CashFlowRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const fetch = async () => {
    if (!start || !end) return;
    setLoading(true);
    setError(null);
    try {
      const data = await cashFlowApi.get(start, end, granularity);
      setRows(data);
      setLoaded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar fluxo de caixa");
    } finally {
      setLoading(false);
    }
  };

  const totalInflow = rows.reduce((s, r) => s + r.inflow, 0);
  const totalOutflow = rows.reduce((s, r) => s + r.outflow, 0);
  const totalNet = totalInflow - totalOutflow;
  const finalBalance = rows.length > 0 ? rows[rows.length - 1].running_balance : 0;

  return (
    <div className="flex flex-col gap-5">
      <Section title="Parâmetros" tone="accent">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <Field label="Início">
            <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </Field>
          <Field label="Fim">
            <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </Field>
          <Field label="Granularidade">
            <Select
              value={granularity}
              onChange={(e) => setGranularity(e.target.value as "daily" | "weekly" | "monthly")}
            >
              <option value="daily">Diário</option>
              <option value="weekly">Semanal</option>
              <option value="monthly">Mensal</option>
            </Select>
          </Field>
          <Field label=" ">
            <Btn tone="accent" onClick={fetch} disabled={loading}>
              {loading ? "Carregando..." : "Calcular"}
            </Btn>
          </Field>
        </div>
        {error && (
          <div className="mt-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
            {error}
          </div>
        )}
      </Section>

      {loaded && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KPI label="Total Entradas" value={fmt(totalInflow)} tone="green" icon="↓" />
            <KPI label="Total Saídas" value={fmt(totalOutflow)} tone="red" icon="↑" />
            <KPI
              label="Resultado Líquido"
              value={fmt(totalNet)}
              tone={totalNet >= 0 ? "green" : "red"}
              icon={totalNet >= 0 ? "+" : "-"}
            />
            <KPI label="Saldo Final" value={fmt(finalBalance)} tone="accent" icon="=" />
          </div>

          <Section title="Fluxo por Período" tone="accent">
            {rows.length === 0 ? (
              <div className="py-8 text-center text-slate-500">Nenhum dado no período selecionado.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-500">
                      <th className="py-2 text-left">Período</th>
                      <th className="py-2 text-left">Tipo</th>
                      <th className="py-2 text-right">Entradas</th>
                      <th className="py-2 text-right">Saídas</th>
                      <th className="py-2 text-right">Líquido</th>
                      <th className="py-2 text-right">Saldo Acumulado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                        <td className="py-2.5 text-slate-300">{fmtDate(row.bucket)}</td>
                        <td className="py-2.5">
                          <Badge
                            text={row.kind === "realized" ? "Realizado" : "Projetado"}
                            tone={row.kind === "realized" ? "green" : "gold"}
                          />
                        </td>
                        <td className="py-2.5 text-right font-mono text-emerald-400">{fmt(row.inflow)}</td>
                        <td className="py-2.5 text-right font-mono text-rose-400">{fmt(row.outflow)}</td>
                        <td className={`py-2.5 text-right font-mono font-semibold ${row.net >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                          {row.net >= 0 ? "+" : ""}{fmt(row.net)}
                        </td>
                        <td className="py-2.5 text-right font-mono font-bold text-slate-100">
                          {fmt(row.running_balance)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>
        </>
      )}
    </div>
  );
}
