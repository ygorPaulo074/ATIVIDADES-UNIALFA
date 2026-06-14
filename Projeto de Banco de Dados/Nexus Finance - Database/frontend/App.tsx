import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Bot,
  BarChart2,
  CreditCard,
  Landmark,
  LineChart,
  Loader2,
  Wallet,
  type LucideIcon,
} from "lucide-react";

import AuthScreen from "./src/components/AuthScreen";
import { getToken } from "./src/services/api";
import { authService, type User } from "./src/services/auth";
import {
  billApi,
  categoryApi,
  investmentApi,
  paymentMethodApi,
  transactionApi,
  walletApi,
} from "./src/services/finance";

import { ContasTab } from "./src/components/pages/ContasTab";
import { DespesasTab } from "./src/components/pages/DespesasTab";
import { IATab } from "./src/components/pages/IATab";
import { InvestTab } from "./src/components/pages/InvestTab";
import { PagarTab } from "./src/components/pages/PagarTab";
import { ReceberTab } from "./src/components/pages/ReceberTab";
import { ReceitasTab } from "./src/components/pages/ReceitasTab";
import { CashFlowTab } from "./src/components/pages/CashFlowTab";
import { Button as Btn } from "./src/components/atoms/Button";
import { cn } from "./src/lib/cn";
import { IA_ENABLED } from "./src/lib/config";
import { fmt } from "./src/lib/format";
import { toneMap } from "./src/lib/theme";
import type {
  AllData,
  Bill,
  Category,
  Investment,
  PaymentMethod,
  TabId,
  Tone,
  Transaction,
  Wallet as WalletType,
} from "./src/types/domain";

const tabs: Array<{ id: TabId; label: string; icon: LucideIcon; tone: Tone; disabled?: boolean }> = [
  { id: "receitas",     label: "Receitas",        icon: ArrowDown,   tone: "green" },
  { id: "despesas",     label: "Despesas",         icon: ArrowUp,     tone: "red" },
  { id: "receber",      label: "A Receber",        icon: Wallet,      tone: "accent" },
  { id: "pagar",        label: "A Pagar",          icon: CreditCard,  tone: "red" },
  { id: "investimentos",label: "Investimentos",    icon: LineChart,   tone: "gold" },
  { id: "fluxo",        label: "Fluxo de Caixa",  icon: BarChart2,   tone: "accent" },
  { id: "contas",       label: "Contas Bancárias", icon: Landmark,    tone: "accent" },
  { id: "ia",           label: "Análise IA",       icon: Bot,         tone: "purple", disabled: !IA_ENABLED },
];

export default function App() {
  const [active, setActive] = useState<TabId>("receitas");
  const [authLoading, setAuthLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Shared resources
  const [wallets, setWallets] = useState<WalletType[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);

  // Financial data
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [bills, setBills] = useState<Bill[]>([]);
  const [investments, setInvestments] = useState<Investment[]>([]);

  // Auth check on mount
  useEffect(() => {
    void (async () => {
      if (getToken()) {
        try {
          setUser(await authService.me());
        } catch {
          /* token inválido */
        }
      }
      setAuthLoading(false);
    })();
  }, []);

  const loadAll = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const [w, cats, pm, txs, bls, invs] = await Promise.all([
        walletApi.list(),
        categoryApi.list(),
        paymentMethodApi.list(),
        transactionApi.list(),
        billApi.list(),
        investmentApi.list(),
      ]);
      setWallets(w);
      setCategories(cats);
      setPaymentMethods(pm);
      setTransactions(txs);
      setBills(bls);
      setInvestments(invs);
    } catch (e) {
      console.error("Erro ao carregar dados:", e);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  // Derived slices
  const inflows  = useMemo(() => transactions.filter((t) => t.type === "inflow"),  [transactions]);
  const outflows = useMemo(() => transactions.filter((t) => t.type === "outflow"), [transactions]);
  const receivables = useMemo(() => bills.filter((b) => b.type === "receivable"),  [bills]);
  const payables    = useMemo(() => bills.filter((b) => b.type === "payable"),     [bills]);

  // Header KPIs
  const totalRec  = useMemo(() => inflows.filter(t => t.status === "settled").reduce((s, t) => s + t.amount, 0), [inflows]);
  const totalDesp = useMemo(() => outflows.filter(t => t.status === "settled").reduce((s, t) => s + t.amount, 0), [outflows]);
  const saldo = totalRec - totalDesp;

  const allData: AllData = useMemo(() => ({
    transactions,
    bills,
    investments,
    wallets,
    categories,
    paymentMethods,
  }), [transactions, bills, investments, wallets, categories, paymentMethods]);

  if (authLoading) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-950">
        <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
      </div>
    );
  }

  if (!user) {
    return <AuthScreen onAuthed={setUser} />;
  }

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-950">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
          <span className="text-sm text-slate-400">Carregando dados...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-900/95 backdrop-blur">
        <div className="mx-auto flex h-20 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3 rounded-xl border border-slate-700/80 bg-slate-900/70 px-2 py-1.5">
            <img
              src="/hero-logotipo.jpg.jpg"
              alt="Logotipo FinanControl"
              className="h-10 w-10 rounded-lg object-cover ring-1 ring-blue-400/40"
            />
            <div className="text-left leading-tight">
              <div className="text-base font-extrabold tracking-tight text-slate-100">FinanControl</div>
              <div className="text-[11px] font-medium text-slate-400">
                {user.username} · {wallets.length} conta{wallets.length !== 1 ? "s" : ""} bancária{wallets.length !== 1 ? "s" : ""}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden items-center gap-4 text-xs sm:flex">
              <span className="inline-flex items-center gap-1 font-semibold text-emerald-400">
                <ArrowDown className="h-3.5 w-3.5" /> {fmt(totalRec)}
              </span>
              <span className="inline-flex items-center gap-1 font-semibold text-rose-400">
                <ArrowUp className="h-3.5 w-3.5" /> {fmt(totalDesp)}
              </span>
              <span className={cn("font-bold", saldo >= 0 ? "text-emerald-400" : "text-rose-400")}>
                = {fmt(saldo)}
              </span>
            </div>
            <Btn
              tone="red"
              small
              onClick={async () => {
                await authService.logout();
                setUser(null);
              }}
            >
              Sair
            </Btn>
          </div>
        </div>
      </header>

      <div className="border-b border-slate-800 bg-slate-900">
        <div className="mx-auto flex w-full max-w-6xl gap-1 overflow-x-auto px-4 sm:px-6">
          {tabs.map((tab) => {
            const isActive = tab.id === active;
            const isDisabled = Boolean(tab.disabled);
            const TabIcon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => { if (!isDisabled) setActive(tab.id); }}
                disabled={isDisabled}
                className={cn(
                  "flex items-center gap-1.5 whitespace-nowrap border-b-2 px-4 py-3 text-sm transition",
                  isDisabled
                    ? "cursor-not-allowed border-transparent text-slate-600"
                    : isActive
                    ? cn(
                        tab.tone === "gold" ? "text-amber-300" : toneMap[tab.tone].text,
                        toneMap[tab.tone].softBg,
                        toneMap[tab.tone].border,
                      )
                    : "border-transparent text-slate-500 hover:text-slate-300",
                )}
              >
                <TabIcon className="h-4 w-4" /> {tab.label}
                {tab.id === "ia" && (
                  <span
                    className={cn(
                      "rounded px-1.5 py-0.5 text-[10px] font-bold text-white",
                      IA_ENABLED ? "bg-violet-500" : "bg-slate-600",
                    )}
                  >
                    {IA_ENABLED ? "IA" : "OFF"}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-6 sm:px-6">
        {active === "receitas" && (
          <ReceitasTab
            data={inflows}
            wallets={wallets}
            categories={categories}
            paymentMethods={paymentMethods}
            onRefresh={loadAll}
          />
        )}
        {active === "despesas" && (
          <DespesasTab
            data={outflows}
            wallets={wallets}
            categories={categories}
            paymentMethods={paymentMethods}
            onRefresh={loadAll}
          />
        )}
        {active === "receber" && (
          <ReceberTab
            data={receivables}
            wallets={wallets}
            categories={categories}
            paymentMethods={paymentMethods}
            onRefresh={loadAll}
          />
        )}
        {active === "pagar" && (
          <PagarTab
            data={payables}
            wallets={wallets}
            categories={categories}
            paymentMethods={paymentMethods}
            onRefresh={loadAll}
          />
        )}
        {active === "investimentos" && (
          <InvestTab
            data={investments}
            onRefresh={loadAll}
          />
        )}
        {active === "fluxo" && <CashFlowTab />}
        {active === "contas" && (
          <ContasTab
            wallets={wallets}
            onRefresh={loadAll}
          />
        )}
        {active === "ia" && (
          <IATab
            allData={allData}
            onRefresh={loadAll}
          />
        )}
      </main>
    </div>
  );
}
