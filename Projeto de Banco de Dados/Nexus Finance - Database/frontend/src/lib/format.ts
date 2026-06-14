export const fmt = (v: number | string | null | undefined) =>
  Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const today = () => new Date().toISOString().split("T")[0];

export const fmtDate = (date?: string) =>
  date ? new Date(`${date}T12:00:00`).toLocaleDateString("pt-BR") : "-";
