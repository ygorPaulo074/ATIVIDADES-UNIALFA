// Base da API (o proxy do Vite encaminha /api/* para o backend).
export const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

// Feature flag da aba de Análise IA.
export const IA_ENABLED = true;
