// Cliente HTTP base. Lê o token de sessão do localStorage e o injeta no header.
// O proxy do Vite encaminha /api/* para o backend (ver vite.config.ts).
const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";
const TOKEN_KEY = "session_token";

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);

export const setToken = (token: string | null): void => {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    // Só desloga se de fato havia uma sessão (401 de uma requisição autenticada).
    // Num login/cadastro que falha, mostra o motivo real vindo do backend.
    if (getToken()) setToken(null);
    let detail = "Sessão expirada";
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* resposta sem JSON */
    }
    throw new ApiError(401, detail);
  }
  if (!res.ok) {
    let detail = `Erro ${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* resposta sem JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get("content-type") ?? "";
  return (contentType.includes("application/json") ? await res.json() : await res.text()) as T;
}

export const api = {
  get:   <T>(path: string)                  => request<T>("GET",    path),
  post:  <T>(path: string, body?: unknown)  => request<T>("POST",   path, body),
  patch: <T>(path: string, body?: unknown)  => request<T>("PATCH",  path, body),
  del:   <T>(path: string)                  => request<T>("DELETE", path),
};
