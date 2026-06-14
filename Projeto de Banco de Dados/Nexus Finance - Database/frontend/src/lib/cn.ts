export const cn = (...arr: Array<string | false | null | undefined>) => arr.filter(Boolean).join(" ");
