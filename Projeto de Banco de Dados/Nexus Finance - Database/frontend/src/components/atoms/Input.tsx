import type { InputHTMLAttributes } from "react";

import { cn } from "../../lib/cn";
import { baseInputClass } from "../../lib/theme";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(baseInputClass, props.className)} />;
}
