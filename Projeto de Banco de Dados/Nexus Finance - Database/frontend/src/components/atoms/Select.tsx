import type { SelectHTMLAttributes } from "react";

import { cn } from "../../lib/cn";
import { baseInputClass } from "../../lib/theme";

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  const { children, className, ...rest } = props;
  return (
    <select {...rest} className={cn(baseInputClass, "cursor-pointer appearance-none pr-9", className)}>
      {children}
    </select>
  );
}
