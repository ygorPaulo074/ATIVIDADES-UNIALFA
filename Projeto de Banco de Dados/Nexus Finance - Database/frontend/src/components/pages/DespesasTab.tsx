import { useState } from "react";
import { CheckCircle2, Clock3, CreditCard } from "lucide-react";

import { Badge } from "../atoms/Badge";
import { Button as Btn } from "../atoms/Button";
import { CurrencyInput } from "../atoms/CurrencyInput";
import { Input } from "../atoms/Input";
import { Select } from "../atoms/Select";
import { Field } from "../molecules/Field";
import { KPI } from "../molecules/KPI";
import { Section } from "../molecules/Section";
import { Table } from "../organisms/Table";
import { fmt, fmtDate, today } from "../../lib/format";
import { transactionApi } from "../../services/finance";
import type {
  Category,
  PaymentMethod,
  Transaction,
  TransactionForm,
  Wallet,
} from "../../types/domain";

export function DespesasTab({
  data,
  wallets,
  categories,
  paymentMethods,
  onRefresh,
}: {
  data: Transaction[];
  wallets: Wallet[];
  categories: Category[];
  paymentMethods: PaymentMethod[];
  onRefresh: () => void;
}) {
  const expenseCategories = categories.filter((c) => c.type === "expense");
  const defaultWallet = wallets[0]?.id ?? "";
  const defaultCategory = expenseCategories[0]?.id ?? "";

  const empty: TransactionForm = {
    wallet_id: defaultWallet,
    description: "",
    amount: "",
    date: today(),
    category_id: defaultCategory,
    payment_method_id: "",
    notes: "",
    status: "settled",
  };

  const [f, setF] = useState<TransactionForm>(empty);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof TransactionForm>(key: K, value: TransactionForm[K]) =>
    setF((prev) => ({ ...prev, [key]: value }));

  const add = async () => {
    if (!f.description || f.amount === "" || f.wallet_id === "") return;
    setSaving(true);
    setError(null);
    try {
      await transactionApi.create({
        wallet_id: Number(f.wallet_id),
        type: "outflow",
        description: f.description,
        amount: Number(f.amount),
        date: f.date,
        category_id: f.category_id !== "" ? Number(f.category_id) : null,
        payment_method_id: f.payment_method_id !== "" ? Number(f.payment_method_id) : null,
        notes: f.notes || null,
        status: f.status,
      });
      onRefresh();
      setF({ ...empty, wallet_id: f.wallet_id, category_id: f.category_id });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const del = async (id: number) => {
    await transactionApi.delete(id);
    onRefresh();
  };

  const total = data.reduce((s, r) => s + r.amount, 0);
  const pago = data.filter((r) => r.status === "settled").reduce((s, r) => s + r.amount, 0);

  const getCategoryName = (id: number | null) =>
    categories.find((c) => c.id === id)?.name ?? "-";

  const byCat = expenseCategories
    .map((cat) => ({
      cat,
      total: data
        .filter((r) => r.category_id === cat.id)
        .reduce((s, r) => s + r.amount, 0),
    }))
    .filter((x) => x.total > 0)
    .sort((a, b) => b.total - a.total);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KPI label="Total Despesas" value={fmt(total)} tone="red" icon={<CreditCard className="h-4 w-4" />} />
        <KPI label="Pago" value={fmt(pago)} tone="green" icon={<CheckCircle2 className="h-4 w-4" />} />
        <KPI label="Pendente" value={fmt(total - pago)} tone="gold" icon={<Clock3 className="h-4 w-4" />} />
      </div>

      {byCat.length > 0 && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Distribuição por Categoria
          </div>
          <div className="flex flex-col gap-2.5">
            {byCat.map(({ cat, total: catTotal }) => (
              <div key={cat.id} className="flex items-center gap-3">
                <span className="min-w-[110px] text-sm text-slate-300">{cat.name}</span>
                <div className="h-2 flex-1 overflow-hidden rounded bg-slate-800">
                  <div
                    className="h-full rounded bg-rose-500 transition-all duration-500"
                    style={{ width: `${Math.min((catTotal / total) * 100, 100)}%` }}
                  />
                </div>
                <span className="min-w-[100px] text-right text-sm font-bold text-rose-400">
                  {fmt(catTotal)}
                </span>
                <span className="min-w-[36px] text-right text-[11px] text-slate-500">
                  {((catTotal / total) * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Section title="Adicionar Despesa" tone="red">
        {error && (
          <div className="mb-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
            {error}
          </div>
        )}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Conta Bancária">
            <Select value={String(f.wallet_id)} onChange={(e) => set("wallet_id", Number(e.target.value))}>
              <option value="">Selecione a conta...</option>
              {wallets.map((w) => (
                <option key={w.id} value={w.id}>{w.name} — {fmt(w.balance)}</option>
              ))}
            </Select>
          </Field>

          <Field label="Data" half>
            <Input type="date" value={f.date} onChange={(e) => set("date", e.target.value)} />
          </Field>

          <Field label="Valor" half>
            <CurrencyInput
              value={f.amount}
              onChange={(v) => set("amount", typeof v === "object" ? Number(v.target.value) : v)}
              tone="red"
            />
          </Field>

          <Field label="Descrição">
            <Input
              placeholder="Ex: Mercado, Aluguel..."
              value={f.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </Field>

          <Field label="Categoria" half>
            <Select value={String(f.category_id)} onChange={(e) => set("category_id", e.target.value !== "" ? Number(e.target.value) : "")}>
              <option value="">Sem categoria</option>
              {expenseCategories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </Select>
          </Field>

          <Field label="Forma de Pagamento" half>
            <Select value={String(f.payment_method_id)} onChange={(e) => set("payment_method_id", e.target.value !== "" ? Number(e.target.value) : "")}>
              <option value="">Não especificado</option>
              {paymentMethods.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </Select>
          </Field>

          <Field label="Status" half>
            <Select value={f.status} onChange={(e) => set("status", e.target.value as "settled" | "pending")}>
              <option value="settled">Pago</option>
              <option value="pending">Pendente</option>
            </Select>
          </Field>

          <Field label="Observações" half>
            <Input placeholder="Anotações..." value={f.notes} onChange={(e) => set("notes", e.target.value)} />
          </Field>

          <div className="md:col-span-2">
            <Btn tone="red" onClick={add} disabled={saving}>
              {saving ? "Salvando..." : "+ Adicionar Despesa"}
            </Btn>
          </div>
        </div>
      </Section>

      <Section title="Histórico" tone="red">
        <Table
          tone="red"
          onDelete={del}
          rows={data}
          cols={[
            { key: "date", label: "Data", render: (v) => fmtDate(String(v || "")) },
            { key: "description", label: "Descrição" },
            { key: "amount", label: "Valor", mono: true, render: (v) => fmt(Number(v || 0)) },
            {
              key: "category_id",
              label: "Categoria",
              render: (v) => <Badge text={getCategoryName(v as number | null)} tone="red" />,
            },
            {
              key: "status",
              label: "Status",
              render: (v) => (
                <Badge
                  text={v === "settled" ? "Pago" : "Pendente"}
                  tone={v === "settled" ? "green" : "gold"}
                />
              ),
            },
          ]}
        />
      </Section>
    </div>
  );
}
