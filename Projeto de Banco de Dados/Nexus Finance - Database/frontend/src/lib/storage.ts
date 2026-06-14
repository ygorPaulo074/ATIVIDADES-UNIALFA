// Persistência local (localStorage / window.storage). Será substituída pela API
// na migração dos recursos; mantida por enquanto para não quebrar as abas.
export const KEY = (t: string) => `finapp_${t}`;

export async function loadData<T>(type: string): Promise<T[]> {
  try {
    if (window.storage?.get) {
      const v = await window.storage.get(KEY(type));
      return v ? (JSON.parse(v.value) as T[]) : [];
    }
    const raw = localStorage.getItem(KEY(type));
    return raw ? (JSON.parse(raw) as T[]) : [];
  } catch {
    return [];
  }
}

export async function saveData<T>(type: string, data: T[]): Promise<void> {
  try {
    const value = JSON.stringify(data);
    if (window.storage?.set) {
      await window.storage.set(KEY(type), value);
      return;
    }
    localStorage.setItem(KEY(type), value);
  } catch {
    /* ignore */
  }
}
