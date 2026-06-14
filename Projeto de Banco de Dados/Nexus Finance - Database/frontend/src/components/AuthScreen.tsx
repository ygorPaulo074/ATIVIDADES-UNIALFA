import { useState, type FormEvent } from "react";

import { ApiError } from "../services/api";
import { authService, type User } from "../services/auth";

type Mode = "login" | "register";

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-slate-100 " +
  "placeholder:text-slate-500 outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-400/20";

export default function AuthScreen({ onAuthed }: { onAuthed: (user: User) => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [identifier, setIdentifier] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const switchMode = (m: Mode) => {
    setMode(m);
    setErr(null);
    setMsg(null);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    setBusy(true);
    try {
      if (mode === "register") {
        const r = await authService.register(username, password);
        setMsg(r.message);
        switchMode("login");
      } else {
        await authService.login(identifier, password);
        onAuthed(await authService.me());
      }
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Erro inesperado");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen place-items-center bg-slate-950 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-800 bg-slate-900/70 p-7">
        <h1 className="mb-1 text-xl font-extrabold text-slate-100">
          {mode === "login" ? "Entrar" : "Criar conta"}
        </h1>
        <p className="mb-5 text-sm text-slate-400">Controle Financeiro</p>

        <form onSubmit={submit} className="flex flex-col gap-3">
          {mode === "register" && (
            <input
              className={inputClass}
              placeholder="Nome de usuário"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          )}
          {mode === "login" && (
            <input
              className={inputClass}
              placeholder="Nome de usuário"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
            />
          )}
          <input
            className={inputClass}
            type="password"
            placeholder="Senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {err && <div className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300">{err}</div>}
          {msg && <div className="rounded-lg bg-green-500/10 px-3 py-2 text-xs text-green-300">{msg}</div>}

          <button
            type="submit"
            disabled={busy}
            className="mt-1 rounded-lg bg-blue-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-400 disabled:opacity-60"
          >
            {busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>

        <div className="mt-4 text-center text-xs text-slate-400">
          {mode === "login" ? (
            <>
              Não tem conta?{" "}
              <button className="font-semibold text-blue-400" onClick={() => switchMode("register")}>
                Cadastre-se
              </button>
            </>
          ) : (
            <>
              Já tem conta?{" "}
              <button className="font-semibold text-blue-400" onClick={() => switchMode("login")}>
                Entrar
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
