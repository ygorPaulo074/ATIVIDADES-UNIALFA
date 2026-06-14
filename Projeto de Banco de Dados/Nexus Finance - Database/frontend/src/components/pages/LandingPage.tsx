import { KPI } from "../molecules/KPI";
import { cn } from "../../lib/cn";
import { IA_ENABLED } from "../../lib/config";
import { fmt } from "../../lib/format";
import { toneMap } from "../../lib/theme";
import type { TabId, Tone } from "../../types/domain";

export function LandingPage({
  onOpenPanel,
  onGoToTab,
  onSelectTab,
  selectedTab,
  totalRec,
  totalDesp,
  saldo,
  receberPendente,
  pagarPendente,
  totalInvestido,
}: {
  onOpenPanel: () => void;
  onGoToTab: (tab: TabId) => void;
  onSelectTab: (tab: TabId) => void;
  selectedTab: TabId;
  totalRec: number;
  totalDesp: number;
  saldo: number;
  receberPendente: number;
  pagarPendente: number;
  totalInvestido: number;
}) {
  const quickActions: Array<{ label: string; tab: TabId; tone: Tone }> = [
    { label: "Lançar Receita", tab: "receitas", tone: "green" },
    { label: "Registrar Despesa", tab: "despesas", tone: "red" },
    { label: "Ver A Receber", tab: "receber", tone: "accent" },
    { label: "Ver Investimentos", tab: "investimentos", tone: "gold" },
  ];

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
      <img
        src="/hero-financas.jpg.png"
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full object-cover"
      />
      <video
        className="pointer-events-none absolute inset-0 h-full w-full object-cover"
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        poster="/hero-financas.jpg.png"
      >
        <source src="/hero-financas.mp4.mp4" type="video/mp4" />
        <source src="/hero-financas.mp4.mp4" type="video/mp4" />
      </video>
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,rgba(2,6,23,0.88),rgba(15,23,42,0.82)_45%,rgba(2,6,23,0.92))]" />
      <div className="pointer-events-none absolute -left-20 top-10 h-72 w-72 rounded-full bg-blue-500/20 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-violet-500/20 blur-3xl" />
      <div className="pointer-events-none absolute left-1/2 top-1/3 h-64 w-64 -translate-x-1/2 rounded-full bg-emerald-500/10 blur-3xl" />

      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 pb-16 pt-8 sm:px-6">
        <section className="overflow-hidden rounded-3xl border border-slate-700/80 bg-slate-900/60 p-7 backdrop-blur-[2px] sm:p-10">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-300">Página inicial</p>
            <h1 className="mt-3 max-w-3xl text-3xl font-black leading-tight sm:text-5xl">
              Controle financeiro pessoal em um único lugar.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-200 sm:text-base">
              Acompanhe receitas, despesas, contas a pagar, contas a receber e investimentos em um só painel. A análise com IA voltará em
              breve.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={onOpenPanel}
                className="rounded-lg bg-emerald-500 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-emerald-500/30 transition hover:bg-emerald-400"
              >
                Começar agora
              </button>
              <button
                type="button"
                onClick={() => IA_ENABLED && onGoToTab("ia")}
                disabled={!IA_ENABLED}
                className={cn(
                  "rounded-lg px-6 py-3 text-sm font-bold transition",
                  IA_ENABLED
                    ? "border border-violet-400/40 bg-violet-500/10 text-violet-200 hover:bg-violet-500/20"
                    : "cursor-not-allowed border border-slate-700 bg-slate-800/60 text-slate-500",
                )}
              >
                {IA_ENABLED ? "Ver análise com IA" : "IA temporariamente desativada"}
              </button>
            </div>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <KPI label="Receitas Registradas" value={fmt(totalRec)} tone="green" icon="↓" />
          <KPI label="Despesas Registradas" value={fmt(totalDesp)} tone="red" icon="↑" />
          <KPI label="Saldo Atual" value={fmt(saldo)} tone={saldo >= 0 ? "green" : "red"} icon={saldo >= 0 ? "✅" : "⚠️"} />
          <KPI label="A Receber" value={fmt(receberPendente)} tone="accent" icon="📨" />
          <KPI label="A Pagar" value={fmt(pagarPendente)} tone="red" icon="📬" />
          <KPI label="Investimentos" value={fmt(totalInvestido)} tone="gold" icon="📈" />
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <h2 className="text-lg font-bold">Atalhos rápidos</h2>
          <p className="mt-1 text-sm text-slate-400">Entre direto na área que você quer atualizar agora.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {quickActions.map((action) => (
              <button
                key={action.label}
                type="button"
                onClick={() => onSelectTab(action.tab)}
                className={cn(
                  "rounded-xl border px-4 py-3 text-left text-sm font-semibold transition",
                  selectedTab === action.tab
                    ? cn(toneMap[action.tone].border, toneMap[action.tone].softBg, toneMap[action.tone].text)
                    : "border-slate-700 bg-slate-900/60 text-slate-300 hover:border-slate-600 hover:bg-slate-800/70",
                )}
              >
                {action.label}
              </button>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
