import { useState } from "react";
import { Landmark, PlusCircle, Trash2 } from "lucide-react";

import { Button as Btn } from "../atoms/Button";
import { CurrencyInput } from "../atoms/CurrencyInput";
import { Input } from "../atoms/Input";
import { Field } from "../molecules/Field";
import { KPI } from "../molecules/KPI";
import { Section } from "../molecules/Section";
import { fmt } from "../../lib/format";
import { walletApi } from "../../services/finance";
import type { Wallet } from "../../types/domain";

export function ContasTab({
  wallets,
  onRefresh,
}: {
  wallets: Wallet[];
  onRefresh: () => void;
}) {
  const [name, setName] = useState("");
  const [initialBalance, setInitialBalance] = useState<number | "">("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalBalance = wallets.reduce((s, w) => s + w.balance, 0);

  const add = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await walletApi.create({
        name: name.trim(),
        initial_balance: initialBalance !== "" ? Number(initialBalance) : 0,
      });
      onRefresh();
      setName("");
      setInitialBalance("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar conta");
    } finally {
      setSaving(false);
    }
  };

  const del = async (id: number) => {
    try {
      await walletApi.delete(id);
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao excluir conta");
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KPI
          label="Total em Contas"
          value={fmt(totalBalance)}
          tone="accent"
          icon={<Landmark className="h-4 w-4" />}
        />
        <KPI
          label="Contas Cadastradas"
          value={String(wallets.length)}
          tone="accent"
          icon={<PlusCircle className="h-4 w-4" />}
        />
      </div>

      <Section title="Nova Conta Bancária" tone="accent">
        {error && (
          <div className="mb-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
            {error}
          </div>
        )}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Nome da Conta">
            <Input
              placeholder="Ex: Nubank, Bradesco Corrente..."
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <Field label="Saldo Inicial" half>
            <CurrencyInput
              value={initialBalance}
              onChange={(v) =>
                setInitialBalance(typeof v === "object" ? Number(v.target.value) : v)
              }
              tone="accent"
            />
          </Field>
          <div className="md:col-span-2">
            <Btn tone="accent" onClick={add} disabled={saving || !name.trim()}>
              {saving ? "Salvando..." : "+ Adicionar Conta"}
            </Btn>
          </div>
        </div>
      </Section>

      <Section title="Contas Cadastradas" tone="accent">
        {wallets.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-500">
            Nenhuma conta cadastrada. Adicione uma conta acima.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {wallets.map((w) => (
              <div
                key={w.id}
                className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <Landmark className="h-5 w-5 text-blue-400" />
                  <div>
                    <div className="text-sm font-semibold text-slate-100">{w.name}</div>
                    <div className="text-xs text-slate-500">
                      Saldo inicial: {fmt(w.initial_balance)}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span
                    className={`text-base font-bold ${
                      w.balance >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {fmt(w.balance)}
                  </span>
                  <button
                    type="button"
                    onClick={() => del(w.id)}
                    className="rounded p-1 text-slate-600 hover:bg-slate-800 hover:text-rose-400"
                    title="Excluir conta"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
