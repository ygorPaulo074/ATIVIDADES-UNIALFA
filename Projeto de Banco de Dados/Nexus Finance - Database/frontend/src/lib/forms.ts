import type { ChangeEvent } from "react";

// Discrimina se o valor recebido é um evento de input/select (vs. um valor direto)
export const asInputValue = (v: unknown): v is ChangeEvent<HTMLInputElement | HTMLSelectElement> =>
  typeof v === "object" && v !== null && "target" in v;
