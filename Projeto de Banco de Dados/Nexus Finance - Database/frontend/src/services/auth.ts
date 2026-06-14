import { api, setToken } from "./api";

export interface User {
  id: number;
  username: string;
  email: string;
}

export const authService = {
  register(username: string, password: string) {
    return api.post<{ ok: boolean; message: string }>("/auth/register", { username, password });
  },

  async login(identifier: string, password: string) {
    const res = await api.post<{ token: string }>("/auth/login", { identifier, password });
    setToken(res.token);
    return res;
  },

  me() {
    return api.get<User>("/auth/me");
  },

  async logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      setToken(null);
    }
  },
};
