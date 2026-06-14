import { useState } from "react";
import { CheckCircle2, Clock3, Landmark } from "lucide-react";

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

export function ReceitasTab({
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
  const incomeCategories = categories.filter((c) => c.type === "income");
  const defaultWallet = wallets[0]?.id ?? "";
  const defaultCategory = incomeCategories[0]?.id ?? "";

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
        type: "inflow",
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
  const recebido = data.filter((r) => r.status === "settled").reduce((s, r) => s + r.amount, 0);

  const getCategoryName = (id: number | null) =>
    categories.find((c) => c.id === id)?.name ?? "-";

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KPI label="Total Receitas" value={fmt(total)} tone="green" icon={<Landmark className="h-4 w-4" />} />
        <KPI label="Recebido" value={fmt(recebido)} tone="green" icon={<CheckCircle2 className="h-4 w-4" />} />
        <KPI label="Pendente" value={fmt(total - recebido)} tone="gold" icon={<Clock3 className="h-4 w-4" />} />
      </div>

      <Section title="Adicionar Receita" tone="green">
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
              tone="green"
            />
          </Field>

          <Field label="Descrição">
            <Input
              placeholder="Ex: Salário março..."
              value={f.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </Field>

          <Field label="Categoria" half>
            <Select value={String(f.category_id)} onChange={(e) => set("category_id", e.target.value !== "" ? Number(e.target.value) : "")}>
              <option value="">Sem categoria</option>
              {incomeCategories.map((c) => (
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
              <option value="settled">Recebido</option>
              <option value="pending">Pendente</option>
            </Select>
          </Field>

          <Field label="Observações" half>
            <Input placeholder="Anotações..." value={f.notes} onChange={(e) => set("notes", e.target.value)} />
          </Field>

          <div className="md:col-span-2">
            <Btn tone="green" onClick={add} disabled={saving}>
              {saving ? "Salvando..." : "+ Adicionar Receita"}
            </Btn>
          </div>
        </div>
      </Section>

      <Section title="Histórico" tone="green">
        <Table
          tone="green"
          onDelete={del}
          rows={data}
          cols={[
            { key: "date", label: "Data", render: (v) => fmtDate(String(v || "")) },
            { key: "description", label: "Descrição" },
            { key: "amount", label: "Valor", mono: true, render: (v) => fmt(Number(v || 0)) },
            {
              key: "category_id",
              label: "Categoria",
              render: (v) => <Badge text={getCategoryName(v as number | null)} tone="green" />,
            },
            {
              key: "status",
              label: "Status",
              render: (v) => (
                <Badge
                  text={v === "settled" ? "Recebido" : "Pendente"}
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
