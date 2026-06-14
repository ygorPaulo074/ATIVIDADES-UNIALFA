import { useState } from "react";

import { Badge } from "../atoms/Badge";
import { Button as Btn } from "../atoms/Button";
import { CurrencyInput } from "../atoms/CurrencyInput";
import { Input } from "../atoms/Input";
import { Select } from "../atoms/Select";
import { Field } from "../molecules/Field";
import { KPI } from "../molecules/KPI";
import { Section } from "../molecules/Section";
import { Table } from "../organisms/Table";
import { cn } from "../../lib/cn";
import { fmt, today } from "../../lib/format";
import { investmentApi } from "../../services/finance";
import type {
  ContributionForm,
  Investment,
  InvestmentForm,
  InvestmentType,
} from "../../types/domain";

const INVESTMENT_TYPE_LABELS: Record<InvestmentType, string> = {
  stock:        "Ações",
  reit:         "FIIs",
  etf:          "ETFs",
  bdr:          "BDRs",
  crypto:       "Criptomoedas",
  treasury:     "Tesouro Direto",
  fixed_income: "Renda Fixa",
};

const INVESTMENT_TYPES = Object.keys(INVESTMENT_TYPE_LABELS) as InvestmentType[];

export function InvestTab({
  data,
  onRefresh,
}: {
  data: Investment[];
  onRefresh: () => void;
}) {
  const emptyInv: InvestmentForm = {
    symbol: "",
    type: "fixed_income",
    quantity: "",
    currency: "BRL",
    track_brapi: false,
    purchase_date: today(),
    maturity_date: "",
    notes: "",
  };

  const emptyContrib: ContributionForm = {
    type: "deposit",
    amount: "",
    date: today(),
    notes: "",
  };

  const [f, setF] = useState<InvestmentForm>(emptyInv);
  const [contributing, setContributing] = useState<Investment | null>(null);
  const [contribForm, setContribForm] = useState<ContributionForm>(emptyContrib);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setField = <K extends keyof InvestmentForm>(key: K, value: InvestmentForm[K]) =>
    setF((prev) => ({ ...prev, [key]: value }));

  const add = async () => {
    if (!f.symbol || f.quantity === "") return;
    setSaving(true);
    setError(null);
    try {
      await investmentApi.create({
        symbol: f.symbol.toUpperCase(),
        type: f.type,
        quantity: Number(f.quantity),
        currency: f.currency,
        track_brapi: f.track_brapi,
        purchase_date: f.purchase_date,
        maturity_date: f.maturity_date || null,
        notes: f.notes || null,
      });
      onRefresh();
      setF(emptyInv);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const addContribution = async () => {
    if (!contributing || contribForm.amount === "") return;
    setSaving(true);
    try {
      await investmentApi.addContribution(contributing.id, {
        type: contribForm.type,
        amount: Number(contribForm.amount),
        date: contribForm.date,
        notes: contribForm.notes || null,
      });
      onRefresh();
      setContributing(null);
      setContribForm(emptyContrib);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao registrar aporte");
    } finally {
      setSaving(false);
    }
  };

  const del = async (id: number) => {
    await investmentApi.delete(id);
    onRefresh();
  };

  const syncBrapi = async () => {
    setSyncing(true);
    setError(null);
    try {
      const res = await investmentApi.syncBrapi();
      onRefresh();
      alert(`Sincronizado: ${res.updated} ativo(s) atualizado(s)`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao sincronizar brapi");
    } finally {
      setSyncing(false);
    }
  };

  const totalInvestido = data.reduce((s, r) => s + r.invested, 0);
  const totalAtual = data.reduce((s, r) => s + (r.position ?? r.invested), 0);
  const rend = totalAtual - totalInvestido;
  const rendPct = totalInvestido > 0 ? (rend / totalInvestido) * 100 : 0;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPI label="Total Investido" value={fmt(totalInvestido)} tone="gold" icon="💼" />
        <KPI label="Valor Atual" value={fmt(totalAtual)} tone="gold" icon="📈" />
        <KPI
          label="Rendimento"
          value={`${rendPct >= 0 ? "+" : ""}${rendPct.toFixed(2)}%`}
          tone={rend >= 0 ? "green" : "red"}
          icon={rend >= 0 ? "🚀" : "📉"}
        />
        <KPI
          label="Ganho / Perda"
          value={fmt(rend)}
          tone={rend >= 0 ? "green" : "red"}
          icon={rend >= 0 ? "✅" : "⚠️"}
        />
      </div>

      {contributing && (
        <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-5">
          <div className="mb-3 font-semibold text-amber-300">
            Registrar aporte em: {contributing.symbol}
          </div>
          {error && (
            <div className="mb-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
              {error}
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <Field label="Tipo">
              <Select
                value={contribForm.type}
                onChange={(e) => setContribForm((p) => ({ ...p, type: e.target.value as "deposit" | "withdrawal" }))}
              >
                <option value="deposit">Aporte</option>
                <option value="withdrawal">Retirada</option>
              </Select>
            </Field>
            <Field label="Valor">
              <CurrencyInput
                value={contribForm.amount}
                onChange={(v) => setContribForm((p) => ({ ...p, amount: typeof v === "object" ? Number(v.target.value) : v }))}
                tone="gold"
              />
            </Field>
            <Field label="Data">
              <Input type="date" value={contribForm.date} onChange={(e) => setContribForm((p) => ({ ...p, date: e.target.value }))} />
            </Field>
            <Field label="Observações">
              <Input value={contribForm.notes} onChange={(e) => setContribForm((p) => ({ ...p, notes: e.target.value }))} />
            </Field>
          </div>
          <div className="mt-4 flex gap-3">
            <Btn tone="gold" onClick={addContribution} disabled={saving}>
              {saving ? "Salvando..." : "Confirmar"}
            </Btn>
            <Btn tone="accent" onClick={() => { setContributing(null); setError(null); }}>
              Cancelar
            </Btn>
          </div>
        </div>
      )}

      <Section title="Adicionar Investimento" tone="gold">
        {error && !contributing && (
          <div className="mb-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
            {error}
          </div>
        )}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Ativo (símbolo)">
            <Input
              placeholder="Ex: PETR4, MXRF11, BTC..."
              value={f.symbol}
              onChange={(e) => setField("symbol", e.target.value.toUpperCase())}
            />
          </Field>

          <Field label="Tipo" half>
            <Select value={f.type} onChange={(e) => setField("type", e.target.value as InvestmentType)}>
              {INVESTMENT_TYPES.map((t) => (
                <option key={t} value={t}>{INVESTMENT_TYPE_LABELS[t]}</option>
              ))}
            </Select>
          </Field>

          <Field label="Quantidade" half>
            <Input
              type="number"
              step="any"
              placeholder="0"
              value={f.quantity === "" ? "" : String(f.quantity)}
              onChange={(e) => setField("quantity", e.target.value === "" ? "" : Number(e.target.value))}
            />
          </Field>

          <Field label="Data de Compra" half>
            <Input type="date" value={f.purchase_date} onChange={(e) => setField("purchase_date", e.target.value)} />
          </Field>

          <Field label="Moeda" half>
            <Select value={f.currency} onChange={(e) => setField("currency", e.target.value)}>
              <option value="BRL">BRL</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </Select>
          </Field>

          <Field label="Vencimento" half>
            <Input type="date" value={f.maturity_date} onChange={(e) => setField("maturity_date", e.target.value)} />
          </Field>

          <Field label="Observações">
            <Input placeholder="Corretora, obs..." value={f.notes} onChange={(e) => setField("notes", e.target.value)} />
          </Field>

          <Field label="Rastrear via brapi?" half>
            <Select
              value={f.track_brapi ? "sim" : "nao"}
              onChange={(e) => setField("track_brapi", e.target.value === "sim")}
            >
              <option value="nao">Não (manual)</option>
              <option value="sim">Sim (atualização automática)</option>
            </Select>
          </Field>

          <div className="flex items-center gap-3 md:col-span-2">
            <Btn tone="gold" onClick={add} disabled={saving}>
              {saving ? "Salvando..." : "+ Adicionar Investimento"}
            </Btn>
            <Btn tone="accent" onClick={syncBrapi} disabled={syncing}>
              {syncing ? "Sincronizando..." : "↻ Sincronizar brapi"}
            </Btn>
          </div>
        </div>
      </Section>

      <Section title="Carteira" tone="gold">
        <Table
          tone="gold"
          onDelete={del}
          rows={data}
          cols={[
            { key: "symbol", label: "Ativo" },
            {
              key: "type",
              label: "Tipo",
              render: (v) => (
                <Badge text={INVESTMENT_TYPE_LABELS[v as InvestmentType] ?? String(v)} tone="gold" />
              ),
            },
            {
              key: "invested",
              label: "Investido",
              mono: true,
              render: (v) => fmt(Number(v || 0)),
            },
            {
              key: "position",
              label: "Atual",
              mono: true,
              render: (v) => (v != null ? fmt(Number(v)) : <span className="text-slate-500">—</span>),
            },
            {
              key: "return_value",
              label: "Rendimento",
              render: (v) => {
                if (v == null) return <span className="text-slate-500">—</span>;
                const r = Number(v);
                return (
                  <span className={cn("font-semibold", r >= 0 ? "text-emerald-400" : "text-rose-400")}>
                    {r >= 0 ? "+" : ""}
                    {fmt(r)}
                  </span>
                );
              },
            },
            {
              key: "_actions",
              label: "",
              render: (_, row) => (
                <button
                  type="button"
                  onClick={() => { setContributing(row as Investment); setContribForm(emptyContrib); }}
                  className="rounded px-2 py-1 text-[11px] font-semibold text-amber-400 hover:bg-amber-500/10"
                >
                  + Aporte
                </button>
              ),
            },
          ]}
        />
      </Section>
    </div>
  );
}
