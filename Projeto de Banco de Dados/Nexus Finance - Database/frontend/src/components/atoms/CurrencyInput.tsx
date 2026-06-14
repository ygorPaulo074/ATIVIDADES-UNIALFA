import { useEffect, useState, type ChangeEvent, type KeyboardEvent as ReactKeyboardEvent } from "react";

import { X } from "lucide-react";

import { cn } from "../../lib/cn";
import { toneMap } from "../../lib/theme";
import type { NumberOrEmpty, Tone } from "../../types/domain";
import { Input } from "./Input";

export function CurrencyInput({
  value,
  onChange,
  placeholder = "R$ 0,00",
  tone = "green",
}: {
  value: NumberOrEmpty | string;
  onChange: (value: NumberOrEmpty) => void;
  placeholder?: string;
  tone?: Tone;
}) {
  const toCents = (v: NumberOrEmpty | string) => Math.round((parseFloat(String(v || 0)) || 0) * 100);
  const [cents, setCents] = useState(toCents(value));

  useEffect(() => {
    setCents(!value && value !== 0 ? 0 : toCents(value));
  }, [value]);

  const display = (v: number) =>
    v === 0 ? "" : (v / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  const update = (next: number) => {
    setCents(next);
    onChange(next === 0 ? "" : next / 100);
  };

  const onKeyDown = (e: ReactKeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      e.preventDefault();
      update(Math.floor(cents / 10));
      return;
    }
    if (e.key === "Delete" || e.key === "Escape") {
      e.preventDefault();
      update(0);
    }
  };

  const onChangeInput = (e: ChangeEvent<HTMLInputElement>) => {
    const digits = e.target.value.replace(/\D/g, "");
    if (!digits) {
      update(0);
      return;
    }
    update(Math.min(parseInt(digits, 10), 99999999));
  };

  return (
    <div className="relative">
      <Input
        inputMode="numeric"
        value={display(cents)}
        placeholder={placeholder}
        onChange={onChangeInput}
        onKeyDown={onKeyDown}
        className={cn(cents > 0 ? toneMap[tone].text : "text-slate-500")}
      />
      {cents > 0 && (
        <button
          type="button"
          onClick={() => update(0)}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-xs text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
          aria-label="Limpar valor"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
