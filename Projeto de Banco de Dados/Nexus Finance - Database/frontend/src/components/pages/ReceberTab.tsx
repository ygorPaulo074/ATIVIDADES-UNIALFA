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
import { fmt, fmtDate, today } from "../../lib/format";
import { billApi } from "../../services/finance";
import type {
  Bill,
  BillForm,
  Category,
  PayBillForm,
  PaymentMethod,
  StatusInfo,
  Tone,
  Wallet,
} from "../../types/domain";

const STATUS_MAP: Record<string, StatusInfo> = {
  a_vencer: { label: "A Vencer", tone: "accent" },
  atrasada:  { label: "Atrasada", tone: "red" },
  quitada:   { label: "Quitada", tone: "green" },
  parcial:   { label: "Parcial", tone: "gold" },
  cancelada: { label: "Cancelada", tone: "red" },
};

export function ReceberTab({
  data,
  wallets,
  categories,
  paymentMethods,
  onRefresh,
}: {
  data: Bill[];
  wallets: Wallet[];
  categories: Category[];
  paymentMethods: PaymentMethod[];
  onRefresh: () => void;
}) {
  const incomeCategories = categories.filter((c) => c.type === "income");

  const emptyBill: BillForm = {
    description: "",
    amount: "",
    due_date: today(),
    counterparty: "",
    category_id: "",
    payment_method_id: "",
  };

  const emptyPay: PayBillForm = {
    wallet_id: wallets[0]?.id ?? "",
    amount: "",
    date: today(),
  };

  const [f, setF] = useState<BillForm>(emptyBill);
  const [paying, setPaying] = useState<Bill | null>(null);
  const [payForm, setPayForm] = useState<PayBillForm>(emptyPay);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setField = <K extends keyof BillForm>(key: K, value: BillForm[K]) =>
    setF((prev) => ({ ...prev, [key]: value }));

  const add = async () => {
    if (!f.description || f.amount === "") return;
    setSaving(true);
    setError(null);
    try {
      await billApi.create({
        type: "receivable",
        description: f.description,
        amount: Number(f.amount),
        due_date: f.due_date,
        counterparty: f.counterparty || null,
        category_id: f.category_id !== "" ? Number(f.category_id) : null,
        payment_method_id: f.payment_method_id !== "" ? Number(f.payment_method_id) : null,
      });
      onRefresh();
      setF(emptyBill);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const confirmPay = async () => {
    if (!paying || payForm.wallet_id === "" || payForm.amount === "") return;
    setSaving(true);
    try {
      await billApi.pay(paying.id, Number(payForm.wallet_id), Number(payForm.amount), payForm.date || undefined);
      onRefresh();
      setPaying(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao confirmar recebimento");
    } finally {
      setSaving(false);
    }
  };

  const cancel = async (id: number) => {
    await billApi.cancel(id);
    onRefresh();
  };

  const del = async (id: number) => {
    await billApi.delete(id);
    onRefresh();
  };

  const aberto = data
    .filter((r) => r.status === "a_vencer" || r.status === "atrasada" || r.status === "parcial")
    .reduce((s, r) => s + r.amount, 0);
  const recebido = data.filter((r) => r.status === "quitada").reduce((s, r) => s + r.amount, 0);

  const getCategoryName = (id: number | null) =>
    categories.find((c) => c.id === id)?.name ?? "-";

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <KPI label="A Receber" value={fmt(aberto)} tone="accent" icon="📨" />
        <KPI label="Já Recebido" value={fmt(recebido)} tone="green" icon="✅" />
      </div>

      {paying && (
        <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-5">
          <div className="mb-3 font-semibold text-emerald-300">
            Confirmar recebimento: {paying.description}
          </div>
          {error && (
            <div className="mb-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
              {error}
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Field label="Conta Bancária">
              <Select
                value={String(payForm.wallet_id)}
                onChange={(e) => setPayForm((p) => ({ ...p, wallet_id: Number(e.target.value) }))}
              >
                {wallets.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </Select>
            </Field>
            <Field label="Valor recebido">
              <CurrencyInput
                value={payForm.amount}
                onChange={(v) => setPayForm((p) => ({ ...p, amount: typeof v === "object" ? Number(v.target.value) : v }))}
                tone="green"
              />
            </Field>
            <Field label="Data">
              <Input type="date" value={payForm.date} onChange={(e) => setPayForm((p) => ({ ...p, date: e.target.value }))} />
            </Field>
          </div>
          <div className="mt-4 flex gap-3">
            <Btn tone="green" onClick={confirmPay} disabled={saving}>
              {saving ? "Salvando..." : "Confirmar Recebimento"}
            </Btn>
            <Btn tone="accent" onClick={() => { setPaying(null); setError(null); }}>
              Cancelar
            </Btn>
          </div>
        </div>
      )}

      <Section title="Adicionar Conta a Receber" tone="accent">
        {error && !paying && (
          <div className="mb-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
            {error}
          </div>
        )}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Devedor">
            <Input
              placeholder="Nome do devedor..."
              value={f.counterparty}
              onChange={(e) => setField("counterparty", e.target.value)}
            />
          </Field>

          <Field label="Valor" half>
            <CurrencyInput
              value={f.amount}
              onChange={(v) => setField("amount", typeof v === "object" ? Number(v.target.value) : v)}
              tone="accent"
            />
          </Field>

          <Field label="Vencimento" half>
            <Input type="date" value={f.due_date} onChange={(e) => setField("due_date", e.target.value)} />
          </Field>

          <Field label="Descrição">
            <Input placeholder="Motivo..." value={f.description} onChange={(e) => setField("description", e.target.value)} />
          </Field>

          <Field label="Categoria" half>
            <Select value={String(f.category_id)} onChange={(e) => setField("category_id", e.target.value !== "" ? Number(e.target.value) : "")}>
              <option value="">Sem categoria</option>
              {incomeCategories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </Select>
          </Field>

          <Field label="Forma de Pagamento" half>
            <Select value={String(f.payment_method_id)} onChange={(e) => setField("payment_method_id", e.target.value !== "" ? Number(e.target.value) : "")}>
              <option value="">Não especificado</option>
              {paymentMethods.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </Select>
          </Field>

          <div className="md:col-span-2">
            <Btn tone="accent" onClick={add} disabled={saving}>
              {saving ? "Salvando..." : "+ Adicionar"}
            </Btn>
          </div>
        </div>
      </Section>

      <Section title="Contas a Receber" tone="accent">
        <Table
          tone="accent"
          onDelete={del}
          rows={data}
          cols={[
            { key: "counterparty", label: "Devedor", render: (v) => String(v || "-") },
            { key: "due_date", label: "Vencimento", render: (v) => fmtDate(String(v || "")) },
            { key: "amount", label: "Valor", mono: true, render: (v) => fmt(Number(v || 0)) },
            {
              key: "category_id",
              label: "Categoria",
              render: (v) => <Badge text={getCategoryName(v as number | null)} tone="accent" />,
            },
            {
              key: "status",
              label: "Status",
              render: (v) => {
                const s = STATUS_MAP[String(v)] ?? { label: String(v), tone: "accent" as Tone };
                return <Badge text={s.label} tone={s.tone} />;
              },
            },
            {
              key: "_actions",
              label: "",
              render: (_, row) =>
                row.status !== "quitada" && row.status !== "cancelada" ? (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => { setPaying(row as Bill); setPayForm({ ...emptyPay, amount: (row as Bill).amount }); }}
                      className="rounded px-2 py-1 text-[11px] font-semibold text-emerald-400 hover:bg-emerald-500/10"
                    >
                      Receber
                    </button>
                    <button
                      type="button"
                      onClick={() => cancel((row as Bill).id)}
                      className="rounded px-2 py-1 text-[11px] font-semibold text-slate-500 hover:bg-slate-800"
                    >
                      Cancelar
                    </button>
                  </div>
                ) : null,
            },
          ]}
        />
      </Section>
    </div>
  );
}
