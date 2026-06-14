import { useEffect, useRef, useState, type ChangeEvent, type ReactNode } from "react";

import { BrainCircuit, CheckCircle2, Clock3, CreditCard, Download, Loader2, Search, Send, X } from "lucide-react";

import { Button as Btn } from "../atoms/Button";
import { Input } from "../atoms/Input";
import { Section } from "../molecules/Section";
import { cn } from "../../lib/cn";
import { API_BASE } from "../../lib/config";
import { fmt, fmtDate, today } from "../../lib/format";
import type {
  AllData,
  ChatMessage,
  TransacaoImport,
} from "../../types/domain";

function parseInlineBold(text: string): ReactNode[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .filter(Boolean)
    .map((part, idx) =>
      part.startsWith("**") && part.endsWith("**") ? <strong key={idx}>{part.slice(2, -2)}</strong> : part,
    );
}

function renderMarkdown(text: string): ReactNode[] {
  return text.split("\n").map((line, idx) => {
    if (line.startsWith("### "))
      return <h3 key={idx} className="mt-5 text-sm font-bold text-violet-400">{line.slice(4)}</h3>;
    if (line.startsWith("## "))
      return <h2 key={idx} className="mt-6 text-base font-extrabold text-slate-100">{line.slice(3)}</h2>;
    if (line.startsWith("- ") || line.startsWith("• "))
      return (
        <div key={idx} className="my-1 flex items-start gap-2">
          <span className="mt-1 text-violet-400">▸</span>
          <span className="text-sm leading-6 text-slate-300">{parseInlineBold(line.slice(2))}</span>
        </div>
      );
    if (!line.trim() || line.trim() === "---") return <div key={idx} className="h-2" />;
    return (
      <p key={idx} className="my-1 text-sm leading-7 text-slate-300">
        {parseInlineBold(line)}
      </p>
    );
  });
}

export function IATab({
  allData,
  onRefresh,
}: {
  allData: AllData;
  onRefresh: () => void;
}) {
  const { transactions, bills, investments, categories } = allData;

  const inflows  = transactions.filter((t) => t.type === "inflow");
  const outflows = transactions.filter((t) => t.type === "outflow");

  const [chatId, setChatId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [uploadando, setUploadando] = useState(false);
  const [extratoCarregado, setExtratoCarregado] = useState<{ banco: string; periodo: string; total: number } | null>(null);
  const [transacoesImport, setTransacoesImport] = useState<TransacaoImport[]>([]);
  const [showImport, setShowImport] = useState(false);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const hasData = inflows.length > 0 || outflows.length > 0 || investments.length > 0;

  useEffect(() => {
    fetch(`${API_BASE}/chats`, { method: "POST" })
      .then((r) => r.json())
      .then((data: { id: string }) => setChatId(data.id))
      .catch((err) => console.warn("[IATab] não foi possível criar chat inicial:", err));
  }, []);

  const ensureChatId = async (): Promise<string> => {
    if (chatId) return chatId;
    const r = await fetch(`${API_BASE}/chats`, { method: "POST" });
    if (!r.ok) throw new Error(`Falha ao criar chat (HTTP ${r.status})`);
    const data = (await r.json()) as { id: string };
    setChatId(data.id);
    return data.id;
  };

  const getCategoryName = (id: number | null) =>
    categories.find((c) => c.id === id)?.name ?? "Sem categoria";

  const buildContext = () => {
    const totalRec  = inflows.filter(t => t.status === "settled").reduce((s, t) => s + t.amount, 0);
    const totalDesp = outflows.filter(t => t.status === "settled").reduce((s, t) => s + t.amount, 0);
    const totalInv  = investments.reduce((s, r) => s + (r.position ?? r.invested), 0);
    const totalAport = investments.reduce((s, r) => s + r.invested, 0);
    const saldo = totalRec - totalDesp;
    const taxaPoup = totalRec > 0 ? ((saldo / totalRec) * 100).toFixed(1) : "0";

    const billsVencidas = bills.filter((b) => b.status === "atrasada").length;
    const aReceber = bills.filter((b) => b.type === "receivable" && (b.status === "a_vencer" || b.status === "parcial")).reduce((s, b) => s + b.amount, 0);

    const byCat = categories
      .filter((c) => c.type === "expense")
      .map((cat) => ({
        categoria: cat.name,
        total: outflows.filter((t) => t.category_id === cat.id && t.status === "settled").reduce((s, t) => s + t.amount, 0),
      }))
      .filter((x) => x.total > 0)
      .sort((a, b) => b.total - a.total);

    return `
DADOS FINANCEIROS DO USUÁRIO (em R$):

RESUMO GERAL:
- Total de Receitas (liquidadas): ${fmt(totalRec)} (${inflows.length} lançamentos)
- Total de Despesas (liquidadas): ${fmt(totalDesp)} (${outflows.length} lançamentos)
- Saldo: ${fmt(saldo)}
- Taxa de Poupança: ${taxaPoup}%
- Carteira de Investimentos (valor atual): ${fmt(totalInv)} | Investido: ${fmt(totalAport)} | Rendimento: ${fmt(totalInv - totalAport)}
- Contas a Receber (pendentes): ${fmt(aReceber)}
- Contas vencidas a pagar: ${billsVencidas}

DESPESAS POR CATEGORIA:
${byCat.map((c) => `- ${c.categoria}: ${fmt(c.total)} (${totalDesp > 0 ? ((c.total / totalDesp) * 100).toFixed(1) : 0}% do total)`).join("\n")}

INVESTIMENTOS:
${investments.map((r) => `- ${r.symbol} (${r.type}): Investido ${fmt(r.invested)}, Atual ${r.position != null ? fmt(r.position) : "sem cotação"}, Rendimento ${r.return_value != null ? fmt(r.return_value) : "—"}`).join("\n") || "Nenhum investimento cadastrado"}

ÚLTIMAS RECEITAS:
${inflows.slice(0, 10).map((r) => `- ${fmtDate(r.date)} | ${r.description} | ${fmt(r.amount)} | ${getCategoryName(r.category_id)}`).join("\n")}

ÚLTIMAS DESPESAS:
${outflows.slice(0, 15).map((r) => `- ${fmtDate(r.date)} | ${r.description} | ${fmt(r.amount)} | ${getCategoryName(r.category_id)}`).join("\n")}
    `.trim();
  };

  const runAnalysis = async () => {
    if (!hasData) return;
    setLoading(true);
    setAnalysis(null);
    const contextMsg = `Analise meus dados financeiros e forneça uma análise completa e personalizada em português brasileiro.\n\n${buildContext()}\n\nForneça uma análise estruturada com:\n\n## Diagnóstico Geral\nAvalie a saúde financeira atual de forma direta e honesta.\n\n## Pontos Positivos\nListe o que estou fazendo bem.\n\n## Alertas e Riscos\nIdentifique problemas, gastos excessivos, padrões preocupantes.\n\n## Padrões Detectados\nIdentifique sazonalidade, categorias que crescem, comportamentos recorrentes.\n\n## Recomendações Prioritárias\nListe de 3 a 5 ações concretas que devo tomar agora.\n\n## Projeção\nCom base nos dados, projete a situação financeira em 3 e 6 meses.\n\nSeja direto, use números reais e evite conselhos genéricos.`;
    try {
      const id = await ensureChatId();
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: id, message: contextMsg }),
      });
      const data = (await res.json()) as { response: string };
      setAnalysis(data.response);
      setChatHistory([{ role: "assistant", content: data.response, isAnalysis: true }]);
    } catch {
      setAnalysis("Erro ao conectar com a IA. Verifique se o servidor está rodando.");
    }
    setLoading(false);
  };

  const buildFinancialContext = () => {
    const fmtTx = (t: typeof transactions[0]) =>
      `ID:${t.id} | ${t.date} | ${t.description} | R$${t.amount.toFixed(2)} | ${getCategoryName(t.category_id)} | Status:${t.status}${t.notes ? ` | Obs:${t.notes}` : ""}`;

    return [
      `=== DADOS FINANCEIROS ATUAIS ===`,
      ``,
      `DESPESAS (${outflows.length} registros):`,
      outflows.length > 0 ? outflows.map(fmtTx).join("\n") : "Nenhuma despesa cadastrada.",
      ``,
      `RECEITAS (${inflows.length} registros):`,
      inflows.length > 0 ? inflows.map(fmtTx).join("\n") : "Nenhuma receita cadastrada.",
      ``,
      `CATEGORIAS VÁLIDAS:`,
      `  Despesas: ${categories.filter(c => c.type === "expense").map(c => c.name).join(", ")}`,
      `  Receitas: ${categories.filter(c => c.type === "income").map(c => c.name).join(", ")}`,
      ``,
      `Nota: para criar ou editar lançamentos financeiros, use os formulários nas abas Receitas e Despesas.`,
    ].join("\n");
  };

  const buildReviewContext = () => {
    const lista = transacoesImport
      .map((t, i) => `indice:${i} | ${t.data} | ${t.descricao} | R$${Math.abs(t.valor).toFixed(2)} | ${t.categoria} | ${t.selecionada ? "incluído" : "excluído"}`)
      .join("\n");
    return [
      `=== LANÇAMENTOS PENDENTES DE IMPORTAÇÃO (${transacoesImport.length}) ===`,
      lista,
      ``,
      `Categorias válidas: ${categories.filter(c => c.type === "expense").map(c => c.name).join(", ")}`,
      ``,
      `Ações disponíveis:`,
      `  {"acao":"editar_pendente","indice":N,"categoria":"...","descricao":"...","valor":0.00,"data":"YYYY-MM-DD"}`,
      `  {"acao":"remover_pendente","indice":N}`,
      `  {"acao":"editar_por_descricao","contem":"TEXTO","categoria":"..."}`,
      `  {"acao":"remover_por_descricao","contem":"TEXTO"}`,
      `  {"acao":"selecionar_pendente","indice":N,"selecionada":true}`,
    ].join("\n");
  };

  const limparResposta = (r: string) => r.replace(/```json[\s\S]*?```/g, "").trim();

  const aplicarAcoesReview = (acoes: Array<Record<string, unknown>>) => {
    setTransacoesImport((prev) => {
      let lista = [...prev];
      for (const a of acoes) {
        if (a.acao === "editar_pendente" && typeof a.indice === "number") {
          lista = lista.map((t, i) =>
            i === a.indice
              ? {
                  ...t,
                  ...(a.categoria !== undefined && { categoria: String(a.categoria) }),
                  ...(a.descricao !== undefined && { descricao: String(a.descricao) }),
                  ...(a.valor !== undefined && { valor: -Math.abs(Number(a.valor)) }),
                  ...(a.data !== undefined && { data: String(a.data) }),
                }
              : t,
          );
        } else if (a.acao === "remover_pendente" && typeof a.indice === "number") {
          lista = lista.filter((_, i) => i !== a.indice);
        } else if (a.acao === "editar_por_descricao" && typeof a.contem === "string") {
          const termo = a.contem.toUpperCase();
          lista = lista.map((t) =>
            t.descricao.includes(termo)
              ? { ...t, ...(a.categoria !== undefined && { categoria: String(a.categoria) }) }
              : t,
          );
        } else if (a.acao === "remover_por_descricao" && typeof a.contem === "string") {
          const termo = a.contem.toUpperCase();
          lista = lista.filter((t) => !t.descricao.includes(termo));
        } else if (a.acao === "selecionar_pendente" && typeof a.indice === "number") {
          lista = lista.map((t, i) => (i === a.indice ? { ...t, selecionada: Boolean(a.selecionada) } : t));
        }
      }
      return lista;
    });
  };

  const updateTransacao = (i: number, patch: Partial<TransacaoImport>) =>
    setTransacoesImport((prev) => prev.map((t, j) => (j === i ? { ...t, ...patch } : t)));

  const sendQuestion = async (msgOverride?: string) => {
    const userMsg = (msgOverride ?? question).trim();
    if (!userMsg || chatLoading) return;
    if (!msgOverride) setQuestion("");
    setChatLoading(true);
    setChatHistory((prev) => [...prev, { role: "user", content: userMsg }]);
    try {
      const id = await ensureChatId();
      const contexto = showImport ? buildReviewContext() : buildFinancialContext();
      const mensagem = `${contexto}\n\n---\n\n${userMsg}`;
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: id, message: mensagem }),
      });
      const data = (await res.json()) as { response: string };
      if (showImport) {
        const match = data.response.match(/```json\s*([\s\S]*?)\s*```/);
        if (match) {
          try { aplicarAcoesReview(JSON.parse(match[1]) as Array<Record<string, unknown>>); } catch { /* json inválido */ }
        }
      }
      setChatHistory((prev) => [...prev, { role: "assistant", content: limparResposta(data.response) }]);
    } catch {
      setChatHistory((prev) => [...prev, { role: "assistant", content: "Erro ao conectar. Tente novamente." }]);
    }
    setChatLoading(false);
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const arquivo = e.target.files?.[0];
    if (!arquivo) return;
    setUploadando(true);
    try {
      const id = await ensureChatId();
      const formData = new FormData();
      formData.append("chat_id", id);
      formData.append("arquivo", arquivo);
      const res = await fetch(`${API_BASE}/upload-extrato`, { method: "POST", body: formData });
      if (!res.ok) {
        const err = (await res.json()) as { detail: string };
        alert(`Erro do servidor: ${err.detail}`);
      } else {
        const dados = (await res.json()) as {
          banco: string; periodo: string; total_transacoes: number; mensagem: string;
          transacoes: Array<{ data: string; descricao: string; valor: number; tipo: string; categoria: string }>;
        };
        setExtratoCarregado({ banco: dados.banco, periodo: dados.periodo, total: dados.total_transacoes });
        setChatHistory((prev) => [...prev, { role: "assistant", content: dados.mensagem }]);
        const todas = (dados.transacoes ?? []).map((t) => ({
          ...t,
          tipo: t.valor < 0 ? ("debito" as const) : ("credito" as const),
          selecionada: t.valor < 0,
        }));
        setTransacoesImport(todas);
        setShowImport(todas.length > 0);
      }
    } catch (err) {
      alert(`Erro de conexão: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setUploadando(false);
      e.target.value = "";
    }
  };

  const expenseCategoryNames = categories.filter(c => c.type === "expense").map(c => c.name);

  const suggestions = [
    "Onde posso cortar gastos esse mês?",
    "Minha taxa de poupança é boa?",
    "Qual categoria gasto mais desnecessariamente?",
    "Como estão meus investimentos comparado à inflação?",
    "Vou conseguir poupar mais no próximo mês?",
  ];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-violet-500/30 bg-gradient-to-br from-violet-500/20 to-blue-500/10 p-7">
        <div>
          <div className="mb-1 inline-flex items-center gap-2 text-2xl font-extrabold text-slate-100">
            <BrainCircuit className="h-6 w-6 text-violet-300" />
            Análise Inteligente
          </div>
          <div className="max-w-[520px] text-sm leading-6 text-slate-300">
            A IA analisa seus dados financeiros e detecta padrões, tendências e oportunidades de melhoria.
          </div>
        </div>
        <Btn tone="purple" onClick={runAnalysis} disabled={loading || !hasData}>
          <span className="inline-flex items-center gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <BrainCircuit className="h-4 w-4" />}
            {loading ? "Analisando..." : "Gerar análise completa"}
          </span>
        </Btn>
      </div>

      <div className="flex items-center gap-2.5 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-2.5 text-xs text-amber-200/80">
        <Clock3 className="h-4 w-4 shrink-0 text-amber-300/90" />
        <span>
          As conversas e análises da IA são temporárias e{" "}
          <strong className="font-semibold text-amber-100">expiram em 24 horas</strong>. Seus lançamentos não são afetados.
        </span>
      </div>

      {!hasData && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-center">
          <Search className="mx-auto mb-3 h-9 w-9 text-slate-400" />
          <div className="mb-1 text-base font-bold text-slate-100">Sem dados para analisar</div>
          <div className="text-sm text-slate-500">Adicione receitas e despesas nas outras abas.</div>
        </div>
      )}

      {loading && (
        <div className="rounded-2xl border border-violet-500/30 bg-slate-900/70 p-10 text-center">
          <Loader2 className="mx-auto mb-3 h-8 w-8 animate-spin text-violet-400" />
          <div className="mb-1 text-base font-bold text-violet-400">Analisando seus dados financeiros...</div>
          <div className="text-sm text-slate-500">Gerando recomendações personalizadas.</div>
        </div>
      )}

      {analysis && !loading && (
        <div className="overflow-hidden rounded-2xl border border-violet-500/30 bg-slate-900/70">
          <div className="flex items-center gap-2 border-b border-slate-800 bg-violet-500/10 px-6 py-4">
            <div className="h-5 w-1 rounded-full bg-violet-500" />
            <span className="text-sm font-bold text-slate-100">Análise Completa</span>
          </div>
          <div className="px-7 py-6">{renderMarkdown(analysis)}</div>
        </div>
      )}

      <Section title="Pergunte sobre suas finanças" tone="purple">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadando}
            className="inline-flex items-center gap-2 rounded-xl border border-violet-500/40 bg-violet-500/10 px-4 py-2 text-xs font-semibold text-violet-300 transition hover:bg-violet-500/25 disabled:opacity-50"
          >
            {uploadando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CreditCard className="h-3.5 w-3.5" />}
            {uploadando ? "Processando..." : "Carregar extrato CSV"}
          </button>
          <input ref={fileInputRef} type="file" accept=".csv" onChange={handleFileChange} className="hidden" />

          {extratoCarregado && (
            <div className="inline-flex items-center gap-2 rounded-xl border border-green-500/40 bg-green-500/10 px-3 py-1.5 text-xs text-green-300">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>{extratoCarregado.banco} · {extratoCarregado.total} transações · {extratoCarregado.periodo}</span>
              <button type="button" onClick={() => setExtratoCarregado(null)} className="ml-1 text-green-400 hover:text-red-400">
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
        </div>

        {showImport && transacoesImport.length > 0 && (
          <div className="mb-5 overflow-hidden rounded-2xl border border-violet-500/30 bg-slate-900/80">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 bg-violet-500/10 px-5 py-3">
              <div className="flex items-center gap-2">
                <Download className="h-4 w-4 text-violet-300" />
                <span className="text-sm font-bold text-slate-100">Revisar extrato</span>
                <span className="rounded-full bg-violet-500/30 px-2 py-0.5 text-[11px] font-semibold text-violet-200">
                  {transacoesImport.filter((t) => t.selecionada).length}/{transacoesImport.length}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button type="button" onClick={() => setTransacoesImport((p) => p.map((t) => ({ ...t, selecionada: true })))} className="text-[11px] text-slate-400 hover:text-slate-200">Todos</button>
                <span className="text-slate-700">·</span>
                <button type="button" onClick={() => setTransacoesImport((p) => p.map((t) => ({ ...t, selecionada: false })))} className="text-[11px] text-slate-400 hover:text-slate-200">Nenhum</button>
                <button type="button" onClick={() => setShowImport(false)} className="ml-1 text-slate-500 hover:text-slate-300"><X className="h-4 w-4" /></button>
              </div>
            </div>

            <div className="max-h-80 overflow-y-auto">
              {transacoesImport.map((t, i) => (
                <div key={`${t.data}-${i}`} className={cn("flex items-center gap-2 border-b border-slate-800/50 px-4 py-2 transition", t.selecionada ? "hover:bg-slate-800/30" : "opacity-40")}>
                  <input type="checkbox" checked={t.selecionada} onChange={(e) => updateTransacao(i, { selecionada: e.target.checked })} className="h-3.5 w-3.5 shrink-0 accent-violet-500" />
                  <input type="date" value={t.data} onChange={(e) => updateTransacao(i, { data: e.target.value })} className="w-28 shrink-0 bg-transparent text-[11px] text-slate-500 focus:outline-none focus:text-slate-300" />
                  <input type="text" value={t.descricao} onChange={(e) => updateTransacao(i, { descricao: e.target.value.toUpperCase() })} className="min-w-0 flex-1 truncate bg-transparent text-xs text-slate-300 focus:outline-none focus:text-slate-100" />
                  <select value={t.categoria} onChange={(e) => updateTransacao(i, { categoria: e.target.value })} className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300 focus:outline-none">
                    {expenseCategoryNames.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <input type="number" value={Math.abs(t.valor)} step="0.01" min="0"
                    onChange={(e) => updateTransacao(i, { valor: -Math.abs(parseFloat(e.target.value) || 0) })}
                    className={cn("w-20 shrink-0 bg-transparent text-right text-xs font-semibold focus:outline-none", t.valor < 0 ? "text-red-400" : "text-green-400")}
                  />
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between border-t border-slate-800 px-5 py-3">
              <span className="text-xs text-slate-500">
                <span className="font-semibold text-slate-300">{transacoesImport.filter((t) => t.selecionada).length}</span> de {transacoesImport.length} selecionadas
              </span>
              <div className="text-xs text-slate-400">
                Revise e importe via aba <span className="font-semibold text-slate-200">Despesas</span> após confirmar.
              </div>
            </div>
          </div>
        )}

        {!showImport && chatHistory.filter((m) => !m.isAnalysis).length === 0 && (
          <div className="mb-5">
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Sugestões</div>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <button key={s} type="button" onClick={() => setQuestion(s)} className="rounded-full border border-violet-500/35 bg-violet-500/15 px-3.5 py-1.5 text-xs text-slate-300 transition hover:bg-violet-500/30 hover:text-slate-100">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {chatHistory.filter((m) => !m.isAnalysis).length > 0 && (
          <div className="mb-4 flex max-h-96 flex-col gap-3 overflow-y-auto">
            {chatHistory.filter((m) => !m.isAnalysis).map((msg, i) => (
              <div key={`${msg.role}-${i}`} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
                <div className={cn("max-w-[80%] border px-4 py-3 text-sm leading-6 text-slate-100",
                  msg.role === "user"
                    ? "rounded-[18px_18px_4px_18px] border-violet-400 bg-violet-500"
                    : "rounded-[18px_18px_18px_4px] border-slate-700 bg-slate-800")}>
                  {msg.role === "assistant" ? renderMarkdown(msg.content) : msg.content}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex gap-1.5 px-2 py-1">
                {[0, 1, 2].map((i) => <div key={i} className="h-2 w-2 animate-bounce rounded-full bg-violet-400" style={{ animationDelay: `${i * 0.15}s` }} />)}
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        )}

        <div className="flex gap-2.5">
          <Input
            className="flex-1 border-violet-500/40 focus:border-violet-400 focus:ring-violet-400/20"
            placeholder="Ex: Qual mês gastei mais? Como reduzir despesas?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendQuestion()}
            disabled={chatLoading}
          />
          <Btn tone="purple" onClick={() => sendQuestion()} disabled={chatLoading || !question.trim()} small>
            <span className="inline-flex items-center gap-1.5">
              {chatLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
              Enviar
            </span>
          </Btn>
        </div>
      </Section>
    </div>
  );
}
