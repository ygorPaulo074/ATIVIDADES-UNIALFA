import type { ReactNode } from "react";

// ─── Primitivos de UI ─────────────────────────────────────────────────────────

export type Tone = "accent" | "green" | "red" | "gold" | "purple";
export type TabId = "receitas" | "despesas" | "receber" | "pagar" | "investimentos" | "ia" | "fluxo" | "contas";
export type NumberOrEmpty = number | "";

export type RuntimeStorage = {
  get: (key: string) => Promise<{ value: string } | null>;
  set: (key: string, value: string) => Promise<void>;
};

declare global {
  interface Window {
    storage?: RuntimeStorage;
  }
}

// ─── Entidades do banco ───────────────────────────────────────────────────────

export interface Wallet {
  id: number;
  name: string;
  initial_balance: number;
  balance: number;
}

export interface WalletPayload {
  name: string;
  initial_balance: number;
}

export interface Category {
  id: number;
  name: string;
  type: "income" | "expense";
}

export interface PaymentMethod {
  id: number;
  name: string;
}

export interface Transaction {
  id: number;
  wallet_id: number;
  type: "inflow" | "outflow";
  description: string;
  amount: number;
  date: string;
  category_id: number | null;
  payment_method_id: number | null;
  notes: string | null;
  status: "settled" | "pending";
}

export interface TransactionPayload {
  wallet_id: number;
  type: "inflow" | "outflow";
  description: string;
  amount: number;
  date: string;
  category_id?: number | null;
  payment_method_id?: number | null;
  notes?: string | null;
  status?: "settled" | "pending";
}

export interface Bill {
  id: number;
  type: "payable" | "receivable";
  description: string;
  amount: number;
  due_date: string;
  counterparty: string | null;
  category_id: number | null;
  payment_method_id: number | null;
  status: "quitada" | "parcial" | "atrasada" | "a_vencer" | "cancelada";
  cancelled_at: string | null;
  recurrence_id: number | null;
  installment_plan_id: number | null;
  installment_number: number | null;
}

export interface BillPayload {
  type: "payable" | "receivable";
  description: string;
  amount: number;
  due_date: string;
  counterparty?: string | null;
  category_id?: number | null;
  payment_method_id?: number | null;
}

export type InvestmentType =
  | "stock"
  | "reit"
  | "etf"
  | "bdr"
  | "crypto"
  | "treasury"
  | "fixed_income";

export interface Investment {
  id: number;
  symbol: string;
  type: InvestmentType;
  quantity: number;
  currency: string;
  track_brapi: boolean;
  purchase_date: string;
  maturity_date: string | null;
  notes: string | null;
  invested: number;
  position: number | null;
  return_value: number | null;
}

export interface InvestmentPayload {
  symbol: string;
  type: InvestmentType;
  quantity: number;
  currency?: string;
  track_brapi?: boolean;
  purchase_date: string;
  maturity_date?: string | null;
  notes?: string | null;
}

export interface Contribution {
  id: number;
  type: "deposit" | "withdrawal";
  amount: number;
  date: string;
  notes: string | null;
}

export interface ContributionPayload {
  type: "deposit" | "withdrawal";
  amount: number;
  date: string;
  notes?: string | null;
}

export interface CashFlowRow {
  bucket: string;
  kind: "realized" | "projected";
  inflow: number;
  outflow: number;
  net: number;
  running_balance: number;
}

// ─── AllData (usado pela IATab) ───────────────────────────────────────────────

export interface AllData {
  transactions: Transaction[];
  bills: Bill[];
  investments: Investment[];
  wallets: Wallet[];
  categories: Category[];
  paymentMethods: PaymentMethod[];
}

// ─── Formulários ─────────────────────────────────────────────────────────────

export interface TransactionForm {
  wallet_id: number | "";
  description: string;
  amount: NumberOrEmpty;
  date: string;
  category_id: number | "";
  payment_method_id: number | "";
  notes: string;
  status: "settled" | "pending";
}

export interface BillForm {
  description: string;
  amount: NumberOrEmpty;
  due_date: string;
  counterparty: string;
  category_id: number | "";
  payment_method_id: number | "";
}

export interface PayBillForm {
  wallet_id: number | "";
  amount: NumberOrEmpty;
  date: string;
}

export interface InvestmentForm {
  symbol: string;
  type: InvestmentType;
  quantity: NumberOrEmpty;
  currency: string;
  track_brapi: boolean;
  purchase_date: string;
  maturity_date: string;
  notes: string;
}

export interface ContributionForm {
  type: "deposit" | "withdrawal";
  amount: NumberOrEmpty;
  date: string;
  notes: string;
}

// ─── Componentes de tabela ────────────────────────────────────────────────────

export type RowBase = { id: number };

export type TableColumn<T extends RowBase> = {
  key: string;
  label: string;
  mono?: boolean;
  render?: (value: unknown, row: T) => ReactNode;
};

export type StatusInfo = {
  label: string;
  tone: Tone;
};

// ─── Import de extrato (IATab) ────────────────────────────────────────────────

export interface TransacaoImport {
  data: string;
  descricao: string;
  valor: number;
  tipo: "debito" | "credito";
  categoria: string;
  selecionada: boolean;
}

// ─── Chat / IA ────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  isAnalysis?: boolean;
}

export type TipoAcao =
  | "criar_despesa"
  | "editar_despesa"
  | "excluir_despesa"
  | "criar_receita"
  | "editar_receita"
  | "excluir_receita"
  | "criar_categoria_desp"
  | "criar_categoria_rec";

export interface AcaoPendente {
  acao: TipoAcao;
  id?: number;
  nome?: string;
  data?: string;
  descricao?: string;
  valor?: number;
  categoria?: string;
  forma?: string;
  pago?: "Sim" | "Não";
  recebido?: "Sim" | "Não";
  obs?: string;
  aprovada: boolean;
}
