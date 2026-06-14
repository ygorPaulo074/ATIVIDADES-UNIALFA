import { api } from "./api";
import type {
  Bill,
  BillPayload,
  Category,
  CashFlowRow,
  Contribution,
  ContributionPayload,
  Investment,
  InvestmentPayload,
  PaymentMethod,
  Transaction,
  TransactionPayload,
  Wallet,
  WalletPayload,
} from "../types/domain";

// ---- Wallets ----
export const walletApi = {
  list: () => api.get<Wallet[]>("/wallets"),
  create: (data: WalletPayload) => api.post<Wallet>("/wallets", data),
  update: (id: number, data: Partial<WalletPayload>) => api.patch<Wallet>(`/wallets/${id}`, data),
  delete: (id: number) => api.del<{ ok: boolean }>(`/wallets/${id}`),
};

// ---- Categories ----
export const categoryApi = {
  list: () => api.get<Category[]>("/categories"),
  create: (data: { name: string; type: "income" | "expense" }) =>
    api.post<Category>("/categories", data),
  delete: (id: number) => api.del<{ ok: boolean }>(`/categories/${id}`),
};

// ---- Payment methods ----
export const paymentMethodApi = {
  list: () => api.get<PaymentMethod[]>("/payment-methods"),
};

// ---- Transactions ----
export const transactionApi = {
  list: () => api.get<Transaction[]>("/transactions"),
  create: (data: TransactionPayload) => api.post<Transaction>("/transactions", data),
  update: (id: number, data: Partial<TransactionPayload>) =>
    api.patch<Transaction>(`/transactions/${id}`, data),
  delete: (id: number) => api.del<{ ok: boolean }>(`/transactions/${id}`),
};

// ---- Bills ----
export const billApi = {
  list: () => api.get<Bill[]>("/bills"),
  create: (data: BillPayload) => api.post<Bill>("/bills", data),
  pay: (id: number, wallet_id: number, amount: number, date?: string) =>
    api.post<{ tx_id: number }>(`/bills/${id}/pay`, { wallet_id, amount, date }),
  cancel: (id: number) => api.post<{ ok: boolean }>(`/bills/${id}/cancel`),
  delete: (id: number) => api.del<{ ok: boolean }>(`/bills/${id}`),
};

// ---- Investments ----
export const investmentApi = {
  list: () => api.get<Investment[]>("/investments"),
  create: (data: InvestmentPayload) => api.post<Investment>("/investments", data),
  update: (id: number, data: Partial<InvestmentPayload>) =>
    api.patch<Investment>(`/investments/${id}`, data),
  delete: (id: number) => api.del<{ ok: boolean }>(`/investments/${id}`),
  listContributions: (id: number) => api.get<Contribution[]>(`/investments/${id}/contributions`),
  addContribution: (id: number, data: ContributionPayload) =>
    api.post<Contribution>(`/investments/${id}/contributions`, data),
  syncBrapi: () => api.post<{ updated: number; symbols: string[] }>("/investments/sync-brapi"),
};

// ---- Cash flow ----
export const cashFlowApi = {
  get: (start: string, end: string, granularity: "daily" | "weekly" | "monthly" = "monthly") =>
    api.get<CashFlowRow[]>(`/cash-flow?start=${start}&end=${end}&granularity=${granularity}`),
};
